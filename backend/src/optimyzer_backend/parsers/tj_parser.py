"""Парсер технологического журнала 1С.

Формат события:
    <mm>:<ss>.<microsec>-<duration_us>,<EventType>,<level>,<key1>=<value1>,...

Имя файла кодирует timestamp до часа: YYMMDDHH.log
Полный timestamp = (year, month, day, hour) из filename + (mm, ss, microsec) из события.

Multi-line events: значения могут содержать переносы строк (Sql='...\n...'),
balanced single quotes используются для определения границы значения.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Имя файла: YYMMDDHH.log
_FILE_TS_RE = re.compile(r"(\d{2})(\d{2})(\d{2})(\d{2})\.log$", re.IGNORECASE)

# Начало события: 32:14.402023-8124000,DBMSSQL,5,...
_EVENT_HEAD_RE = re.compile(
    r"^(?P<min>\d{1,2}):(?P<sec>\d{2})\.(?P<usec>\d{1,6})-(?P<dur>\d+|),(?P<type>[A-Za-z][A-Za-z0-9_]*),(?P<level>\d+)"
)

# Известные «канонические» типы — Sprint 0 minimum (CALL, DBMSSQL, EXCP, TLOCK, TDEADLOCK + SCALL/CONN/SDBL служебные)
KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "CALL",
        "SCALL",
        "DBMSSQL",
        "EXCP",
        "TLOCK",
        "TDEADLOCK",
        "CONN",
        "SDBL",
        "MEM",
        "LEAKS",
        "ATTN",
        "QERR",
    }
)


@dataclass
class RawEvent:
    """Сырое событие — после lexer'а, до интерпретации."""

    minute: int
    second: int
    microsec: int
    duration_us: int | None
    event_type: str
    level: int
    fields: dict[str, str] = field(default_factory=dict)
    source_file: str = ""
    source_line_start: int = 0


@dataclass
class ParsedEvent:
    """Полностью распарсенное событие, готовое к insert."""

    ts: datetime
    duration_us: int | None
    event_type: str
    level: int
    session_id: int | None = None
    user_name: str | None = None
    context: str | None = None
    process: str | None = None
    process_pid: int | None = None
    sql_text: str | None = None
    sql_text_normalized: str | None = None
    sql_text_hash: str | None = None
    rows_read: int | None = None
    rows_modified: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    source_line_start: int = 0

    def as_row(self, archive_id: str, event_id: int) -> tuple:
        """Возвращает tuple для batch insert в DuckDB."""
        import json as _json

        return (
            event_id,
            archive_id,
            self.ts,
            self.duration_us,
            self.event_type,
            self.session_id,
            self.user_name,
            self.context,
            self.process,
            self.process_pid,
            self.sql_text,
            self.sql_text_normalized,
            self.sql_text_hash,
            self.rows_read,
            self.rows_modified,
            _json.dumps(self.extra, ensure_ascii=False) if self.extra else None,
            self.source_file,
            self.source_line_start,
        )


# ---------- File timestamp ----------


def parse_filename_timestamp(filename: str) -> tuple[int, int, int, int] | None:
    """Возвращает (year, month, day, hour) или None."""
    m = _FILE_TS_RE.search(filename)
    if not m:
        return None
    yy, mm, dd, hh = (int(g) for g in m.groups())
    year = 2000 + yy
    return year, mm, dd, hh


# ---------- Lexer: stream raw events ----------


def iter_raw_events(text: str, source_file: str = "") -> Iterator[RawEvent]:
    """Stream-парсер: на входе содержимое .log файла, на выходе — поток сырых событий.

    Multi-line поддерживается через look-ahead: следующая строка считается продолжением
    текущего события, если она НЕ начинается с pattern `\\d+:\\d+\\.\\d+-`.
    """
    lines = text.splitlines(keepends=False)
    i = 0
    n = len(lines)
    while i < n:
        head_match = _EVENT_HEAD_RE.match(lines[i])
        if not head_match:
            i += 1
            continue

        buf = [lines[i]]
        start_idx = i
        i += 1
        while i < n and not _EVENT_HEAD_RE.match(lines[i]):
            buf.append(lines[i])
            i += 1

        raw_text = "\n".join(buf)
        ev = _parse_one(raw_text, head_match, source_file, start_idx + 1)
        if ev is not None:
            yield ev


def _parse_one(raw: str, head: re.Match, source_file: str, line_no: int) -> RawEvent | None:
    dur_str = head.group("dur")
    duration = int(dur_str) if dur_str else None

    rest_start = head.end()
    tail = raw[rest_start:]
    # tail обычно начинается с ',key=value,key=value,...' либо пусто
    if tail.startswith(","):
        tail = tail[1:]

    fields = _parse_kv_fields(tail)

    return RawEvent(
        minute=int(head.group("min")),
        second=int(head.group("sec")),
        microsec=_pad_microsec(head.group("usec")),
        duration_us=duration,
        event_type=head.group("type"),
        level=int(head.group("level")),
        fields=fields,
        source_file=source_file,
        source_line_start=line_no,
    )


def _pad_microsec(s: str) -> int:
    """Дополнить микросекунды до 6 знаков справа."""
    return int(s.ljust(6, "0")[:6])


def _parse_kv_fields(text: str) -> dict[str, str]:
    """Разобрать поток `k=v,k='v...',k="v..."` в словарь.

    Значения могут быть:
      - без кавычек (до следующей запятой или конца)
      - в одинарных кавычках 'value with , and newlines'
      - в двойных кавычках "value"
    Внутри кавычек запятые/переносы игнорируются. Удвоенная кавычка == escape ('' либо "").
    """
    fields: dict[str, str] = {}
    i = 0
    n = len(text)
    while i < n:
        # пропустить leading-разделитель/пробелы
        while i < n and text[i] in ", ":
            i += 1
        if i >= n:
            break
        # ключ — до '='
        eq = text.find("=", i)
        if eq < 0:
            break
        key = text[i:eq].strip()
        i = eq + 1
        if not key:
            # битый сегмент — пропустить до следующей запятой
            comma = text.find(",", i)
            i = comma + 1 if comma > 0 else n
            continue
        # значение
        if i < n and text[i] in "'\"":
            quote = text[i]
            i += 1
            value_buf: list[str] = []
            while i < n:
                ch = text[i]
                if ch == quote:
                    # удвоенная кавычка — escape
                    if i + 1 < n and text[i + 1] == quote:
                        value_buf.append(quote)
                        i += 2
                        continue
                    i += 1
                    break
                value_buf.append(ch)
                i += 1
            value = "".join(value_buf)
        else:
            # значение до следующей запятой (не учитывая запятые внутри возможных вложенных скобок)
            comma = text.find(",", i)
            if comma < 0:
                value = text[i:]
                i = n
            else:
                value = text[i:comma]
                i = comma
        fields[key] = value
    return fields


# ---------- Interpreter: RawEvent -> ParsedEvent ----------


def interpret(raw: RawEvent, file_ts: tuple[int, int, int, int]) -> ParsedEvent:
    year, month, day, hour = file_ts
    # microseconds in datetime — 0..999_999
    try:
        ts = datetime(year, month, day, hour, raw.minute, raw.second, raw.microsec)
    except ValueError:
        # invalid date components — fall back to midnight of given day
        ts = datetime(year, month, day, hour, 0, 0, 0)

    f = raw.fields
    process = f.get("process") or f.get("p:processName")
    process_pid = _to_int(f.get("OSThread"))
    session_id = _to_int(f.get("t:clientID") or f.get("SessionID") or f.get("Sid"))
    user_name = f.get("Usr") or f.get("UserName")
    context = f.get("Context")

    sql_text: str | None = None
    sql_norm: str | None = None
    sql_hash: str | None = None
    rows_read: int | None = None
    rows_modified: int | None = None

    if raw.event_type == "DBMSSQL":
        sql_text = f.get("Sql")
        rows_read = _to_int(f.get("Rows"))
        rows_modified = _to_int(f.get("RowsAffected"))
        if sql_text:
            sql_norm = normalize_sql(sql_text)
            sql_hash = hashlib.blake2b(sql_norm.encode("utf-8"), digest_size=16).hexdigest()

    # Всё, что не известно как явное поле — складываем в extra
    known_keys = {
        "process",
        "p:processName",
        "OSThread",
        "t:clientID",
        "SessionID",
        "Sid",
        "Usr",
        "UserName",
        "Context",
        "Sql",
        "Rows",
        "RowsAffected",
    }
    extra = {k: v for k, v in f.items() if k not in known_keys}

    return ParsedEvent(
        ts=ts,
        duration_us=raw.duration_us,
        event_type=raw.event_type,
        level=raw.level,
        session_id=session_id,
        user_name=user_name,
        context=context,
        process=process,
        process_pid=process_pid,
        sql_text=sql_text,
        sql_text_normalized=sql_norm,
        sql_text_hash=sql_hash,
        rows_read=rows_read,
        rows_modified=rows_modified,
        extra=extra,
        source_file=raw.source_file,
        source_line_start=raw.source_line_start,
    )


def _to_int(v: str | None) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


# ---------- SQL normalization ----------

_NUM_LITERAL = re.compile(r"\b\d+(?:\.\d+)?\b")
_STR_LITERAL = re.compile(r"'(?:[^']|'')*'")
_PARAM_REF = re.compile(r"@P\d+|@PN\d*")
_WS = re.compile(r"\s+")


def normalize_sql(sql: str) -> str:
    """Простая нормализация SQL: literals → ?, params → ?, whitespace squash."""
    s = sql
    s = _STR_LITERAL.sub("?", s)
    s = _NUM_LITERAL.sub("?", s)
    s = _PARAM_REF.sub("?", s)
    s = _WS.sub(" ", s).strip()
    return s


# ---------- High-level: parse a file ----------


def parse_file(path: str | Path) -> Iterator[ParsedEvent]:
    """Парсит один .log файл. Возвращает поток ParsedEvent."""
    p = Path(path)
    file_ts = parse_filename_timestamp(p.name)
    if file_ts is None:
        # Без timestamp в имени — fall back на mtime
        import time

        mtime = p.stat().st_mtime
        st = time.localtime(mtime)
        file_ts = (st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour)

    text = _read_text_robust(p)
    for raw in iter_raw_events(text, source_file=str(p)):
        yield interpret(raw, file_ts)


def _read_text_robust(p: Path) -> str:
    """Читает файл как UTF-8 c fallback на Windows-1251."""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp1251", errors="replace")
