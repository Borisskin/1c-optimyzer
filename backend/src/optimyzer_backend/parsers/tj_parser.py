"""Парсер технологического журнала 1С.

Формат события:
    <mm>:<ss>.<microsec>-<duration_us>,<EventType>,<level>,<key1>=<value1>,...

Имя файла кодирует timestamp до часа: YYMMDDHH.log
Полный timestamp = (year, month, day, hour) из filename + (mm, ss, microsec) из события.

Multi-line events: значения могут содержать переносы строк (Sql='...\n...'),
balanced single quotes используются для определения границы значения.

Sprint 1: process_role/process_pid берутся из имени родительской папки
(`rphost_28220` → role='rphost', pid=28220), не из OSThread. OSThread
теперь попадает в ``extra`` JSON, см. ADR-014.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from optimyzer_backend.ingest.source import LogFile, LogSource

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


# Sprint 3 — нормализация поля Context.
# Сырой context часто выглядит как `Тип.Имя.Сущность : <line> : <statement>`,
# где `: <line> : <statement>` — позиция внутри модуля. Для group by нужна
# семантическая часть до первого ':' — она идентифицирует операцию платформы
# и стабильна между ревизиями кода.
#
# Examples:
#   'Документ.РеализацияТоваровУслуг.МодульОбъекта : 123 : Result = ...'
#     -> 'Документ.РеализацияТоваровУслуг.МодульОбъекта'
#   'ВнешняяОбработка.Foo.Форма.MainForm.Форма : 546 : ...'
#     -> 'ВнешняяОбработка.Foo.Форма.MainForm.Форма'
_CONTEXT_NORMALIZE_RE = re.compile(r"^([^:]+?)(?:\s*:.*)?$", re.DOTALL)


def normalize_context(raw_context: str | None) -> str | None:
    """Извлекает 'Тип.Имя.Сущность' из сырого `Context` поля ТЖ.

    Возвращает None, если на входе None/пусто. Все ведущие и хвостовые
    пробелы (включая переносы строк) обрезаются. Если ':' нет вообще —
    возвращается стрипанный исходник.
    """
    if not raw_context:
        return None
    stripped = raw_context.strip()
    if not stripped:
        return None
    match = _CONTEXT_NORMALIZE_RE.match(stripped)
    if not match:
        return stripped
    return match.group(1).strip() or None


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
    context_normalized: str | None = None
    process: str | None = None
    process_role: str = "unknown"
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
        """Возвращает tuple для batch insert в DuckDB (порядок = EVENT_COLUMNS в storage)."""
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
            self.context_normalized,
            self.process,
            self.process_role,
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
    yield from iter_raw_events_lines(text.splitlines(keepends=False), source_file=source_file)


def iter_raw_events_lines(lines: Iterable[str], source_file: str = "") -> Iterator[RawEvent]:
    """Streaming-вариант: принимает итератор строк (без хвостовых ``\\n``).

    Используется FolderSource для построчного чтения без загрузки файла в память.
    """
    buf: list[str] = []
    start_idx = 0
    head_match: re.Match | None = None
    line_no = 0

    for line in lines:
        # Убираем хвостовой \n/\r (Path.open может возвращать строки с ним)
        if line.endswith("\n"):
            line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
        line_no += 1

        m = _EVENT_HEAD_RE.match(line)
        if m is not None:
            # Зафиксировать предыдущее событие, если было
            if head_match is not None:
                raw_text = "\n".join(buf)
                ev = _parse_one(raw_text, head_match, source_file, start_idx)
                if ev is not None:
                    yield ev
            head_match = m
            buf = [line]
            start_idx = line_no
        else:
            if head_match is not None:
                buf.append(line)
            # иначе — мусор до первого header'а, игнорируем

    if head_match is not None:
        raw_text = "\n".join(buf)
        ev = _parse_one(raw_text, head_match, source_file, start_idx)
        if ev is not None:
            yield ev


def _parse_one(raw: str, head: re.Match, source_file: str, line_no: int) -> RawEvent | None:
    dur_str = head.group("dur")
    duration = int(dur_str) if dur_str else None

    rest_start = head.end()
    tail = raw[rest_start:]
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
        while i < n and text[i] in ", ":
            i += 1
        if i >= n:
            break
        eq = text.find("=", i)
        if eq < 0:
            break
        key = text[i:eq].strip()
        i = eq + 1
        if not key:
            comma = text.find(",", i)
            i = comma + 1 if comma > 0 else n
            continue
        if i < n and text[i] in "'\"":
            quote = text[i]
            i += 1
            value_buf: list[str] = []
            while i < n:
                ch = text[i]
                if ch == quote:
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


def interpret(
    raw: RawEvent,
    file_ts: tuple[int, int, int, int],
    process_role: str = "unknown",
    file_pid: int | None = None,
) -> ParsedEvent:
    """Преобразует RawEvent в ParsedEvent.

    ``process_role`` и ``file_pid`` извлекаются из имени родительской папки
    (см. ADR-014). Если они не переданы — поля остаются ``unknown``/``None``,
    а семантика event-уровневых полей сохраняется.
    """
    year, month, day, hour = file_ts
    try:
        ts = datetime(year, month, day, hour, raw.minute, raw.second, raw.microsec)
    except ValueError:
        ts = datetime(year, month, day, hour, 0, 0, 0)

    f = raw.fields
    process = f.get("process") or f.get("p:processName")
    session_id = _to_int(f.get("t:clientID") or f.get("SessionID") or f.get("Sid"))
    user_name = f.get("Usr") or f.get("UserName")
    context = f.get("Context")
    context_norm = normalize_context(context)

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

    # Известные поля выносим из extra
    known_keys = {
        "process",
        "p:processName",
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
        context_normalized=context_norm,
        process=process,
        process_role=process_role,
        process_pid=file_pid,
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

# В T-SQL префикс N перед строкой обозначает Unicode-литерал (NVARCHAR):
# N'строка'. Без префикса в regex буква N оставалась в нормализованном
# выводе мусором ("N?"), хотя смысл такой же что и обычная строка.
# Захватываем N (или n) опционально вместе со строкой → ?.
_STR_LITERAL = re.compile(r"[Nn]?'(?:[^']|'')*'")
# Hex-литералы T-SQL: 0x01, 0xDEADBEEF. Без отдельной regex они оставались
# как есть (1С-платформа использует 0x00000000 в CASE WHEN ... = 0x01).
# ВАЖНО: hex обрабатываем ДО _NUM_LITERAL — иначе `\b\d+\b` поймает
# первую цифру 0 из «0x01» и оставит «x01» в выводе.
_HEX_LITERAL = re.compile(r"\b0[xX][0-9a-fA-F]+\b")
_NUM_LITERAL = re.compile(r"\b\d+(?:\.\d+)?\b")
_PARAM_REF = re.compile(r"@P\d+|@PN\d*")
_WS = re.compile(r"\s+")


def normalize_sql(sql: str) -> str:
    """Простая нормализация SQL: literals → ?, params → ?, whitespace squash.

    Покрывает: Unicode-строки (N'...'), обычные строки ('...'), hex-литералы
    (0x...), числа, T-SQL параметры (@P1, @PN2). Порядок важен:
    STR/HEX/NUM/PARAM (см. комментарии у regex).
    """
    s = sql
    s = _STR_LITERAL.sub("?", s)
    s = _HEX_LITERAL.sub("?", s)
    s = _NUM_LITERAL.sub("?", s)
    s = _PARAM_REF.sub("?", s)
    s = _WS.sub(" ", s).strip()
    return s


# ---------- High-level: parse a file ----------


def parse_file(
    path: str | Path,
    process_role: str = "unknown",
    file_pid: int | None = None,
) -> Iterator[ParsedEvent]:
    """Парсит один .log файл целиком в память. Возвращает поток ParsedEvent.

    Для больших файлов (10+ ГБ из discovery) используй ``parse_log_file_streaming``
    с FolderSource — он читает построчно.
    """
    p = Path(path)
    file_ts = parse_filename_timestamp(p.name)
    if file_ts is None:
        import time

        mtime = p.stat().st_mtime
        st = time.localtime(mtime)
        file_ts = (st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour)

    text = _read_text_robust(p)
    for raw in iter_raw_events(text, source_file=str(p)):
        yield interpret(raw, file_ts, process_role=process_role, file_pid=file_pid)


def parse_log_file_streaming(
    source: "LogSource",
    log_file: "LogFile",
    encoding: str = "utf-8-sig",
) -> Iterator[ParsedEvent]:
    """Streaming parser — построчное чтение через LogSource.open()."""
    file_ts = parse_filename_timestamp(log_file.path.name)
    if file_ts is None:
        import time

        mtime = log_file.path.stat().st_mtime
        st = time.localtime(mtime)
        file_ts = (st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour)

    lines = source.open(log_file, encoding=encoding)
    for raw in iter_raw_events_lines(lines, source_file=log_file.relative_path):
        yield interpret(
            raw,
            file_ts,
            process_role=log_file.process_role,
            file_pid=log_file.process_pid,
        )


def _read_text_robust(p: Path) -> str:
    """Читает файл как UTF-8 (с BOM или без) c fallback на Windows-1251."""
    try:
        return p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp1251", errors="replace")
