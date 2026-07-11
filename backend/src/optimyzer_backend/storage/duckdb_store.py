"""DuckDB storage layer per archive (Sprint 1 — Appender API, ADR-011)."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend.parsers.tj_parser import ParsedEvent

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id BIGINT NOT NULL,
    archive_id VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    duration_us BIGINT,
    event_type VARCHAR NOT NULL,
    session_id INTEGER,
    user_name VARCHAR,
    context VARCHAR,
    context_normalized VARCHAR,
    process VARCHAR,
    process_role VARCHAR,
    process_pid INTEGER,
    sql_text TEXT,
    sql_text_normalized TEXT,
    sql_text_hash VARCHAR(32),
    plan_text TEXT,
    rows_read BIGINT,
    rows_modified BIGINT,
    extra JSON,
    source_file VARCHAR,
    source_line_start INTEGER,
    engine VARCHAR
);
"""

INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_events_id ON events(id);",
    "CREATE INDEX IF NOT EXISTS idx_events_archive ON events(archive_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_ts ON events(archive_id, ts);",
    "CREATE INDEX IF NOT EXISTS idx_events_type ON events(archive_id, event_type);",
    "CREATE INDEX IF NOT EXISTS idx_events_duration ON events(archive_id, duration_us);",
    "CREATE INDEX IF NOT EXISTS idx_events_sql_hash ON events(archive_id, sql_text_hash);",
    "CREATE INDEX IF NOT EXISTS idx_events_role ON events(archive_id, process_role);",
    "CREATE INDEX IF NOT EXISTS idx_events_ctx_norm ON events(archive_id, context_normalized);",
    "CREATE INDEX IF NOT EXISTS idx_events_engine ON events(archive_id, engine);",
]

EVENT_COLUMNS = [
    "id",
    "archive_id",
    "ts",
    "duration_us",
    "event_type",
    "session_id",
    "user_name",
    "context",
    "context_normalized",
    "process",
    "process_role",
    "process_pid",
    "sql_text",
    "sql_text_normalized",
    "sql_text_hash",
    "plan_text",
    "rows_read",
    "rows_modified",
    "extra",
    "source_file",
    "source_line_start",
    "engine",
]


def default_db_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    p = Path(base) / "1c-optimyzer" / "duckdb"
    p.mkdir(parents=True, exist_ok=True)
    return p


# По умолчанию DuckDB забирает до 80% RAM. На машине пользователя рядом работают
# WebView2, парсер ТЖ и ОС — суммарно это могло приводить к исчерпанию памяти и
# аварийному завершению процесса при загрузке большого ТЖ (симптом на фронте —
# "Ошибка RPC: Идет закрытие канала. (os error 232)"). Оставляем запас и включаем
# сброс на локальный диск, чтобы тяжёлые запросы спиллили, а не падали.
_MEMORY_LIMIT_FRACTION = 0.60


def _physical_ram_bytes() -> int | None:
    """Объём физической RAM в байтах (Windows/POSIX) или None."""
    try:
        import ctypes

        class _MemStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MemStatusEx()
        stat.dwLength = ctypes.sizeof(_MemStatusEx)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
            return int(stat.ullTotalPhys)
    except Exception:
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, AttributeError, OSError):
        return None


def _resolve_memory_limit() -> str | None:
    """Абсолютный лимит памяти для DuckDB (напр. '4800MiB') или None (дефолт).

    Переопределяется env-переменной ``OPTIMYZER_DUCKDB_MEMORY_LIMIT`` (значение
    трактуется как есть, напр. '2GB'). Иначе — доля физической RAM.
    """
    override = os.environ.get("OPTIMYZER_DUCKDB_MEMORY_LIMIT")
    if override:
        return override
    ram = _physical_ram_bytes()
    if not ram:
        return None
    mib = int(ram * _MEMORY_LIMIT_FRACTION / (1024 * 1024))
    mib = max(512, mib)  # не опускаемся ниже 512 MiB
    return f"{mib}MiB"


def _configure_connection(conn: duckdb.DuckDBPyConnection) -> None:
    """Ограничивает память DuckDB и задаёт локальный temp для спилла.

    Обе настройки best-effort: при любой ошибке остаёмся на дефолтах DuckDB
    (не роняем ingest из-за настройки лимита).
    """
    limit = _resolve_memory_limit()
    if limit:
        try:
            conn.execute(f"SET memory_limit='{limit}'")
        except Exception:
            pass
    try:
        tmp = default_db_dir() / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        conn.execute(f"SET temp_directory='{tmp.as_posix()}'")
    except Exception:
        pass


# DuckDB не разрешает в одном процессе открыть один и тот же файл с разной
# конфигурацией (read_write vs read_only). После ingestion store держит
# read_write connection живым, поэтому SQLExecutor / schema_introspection
# не могут открыть read_only — получают "Connection Error: Can't open a
# connection to same database file with a different configuration".
#
# Решение: registry активных connections. DuckDBStore при open() себя
# регистрирует; SQLExecutor / schema_introspection при наличии активного
# connection используют conn.cursor() (child connection того же parent —
# никаких config mismatch).
_ACTIVE_CONNECTIONS: dict[str, duckdb.DuckDBPyConnection] = {}


def register_active_connection(archive_id: str, conn: duckdb.DuckDBPyConnection) -> None:
    _ACTIVE_CONNECTIONS[archive_id] = conn


def unregister_active_connection(archive_id: str) -> None:
    _ACTIVE_CONNECTIONS.pop(archive_id, None)


def get_active_connection(archive_id: str) -> duckdb.DuckDBPyConnection | None:
    return _ACTIVE_CONNECTIONS.get(archive_id)


DEFAULT_BATCH_SIZE = 10_000


def _migrate_plan_text(conn: duckdb.DuckDBPyConnection) -> None:
    """Sprint 7 Phase D — idempotent add column plan_text.

    Существующие архивы (созданные до Sprint 7) не имели этой колонки.
    Backfill не делаем — старые архивы просто не содержали planSQLText
    в исходном ТЖ. Новые архивы заполняются парсером tj_parser автоматически.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
    if "plan_text" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN plan_text TEXT")


def _migrate_engine(conn: duckdb.DuckDBPyConnection) -> None:
    """Sprint 8 Phase B — idempotent add column engine + backfill.

    Заполняем из event_type для уже загруженных архивов: DBMSSQL → 'mssql',
    DBPOSTGRS → 'postgres'. Остальные event_type остаются NULL (CALL/EXCP/...
    не имеют database engine). UI использует это поле для определения формата
    плана (XML vs TEXT) и AI prompt routing (MSSQL terminology vs PG).
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
    if "engine" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN engine VARCHAR")
    # Backfill только NULL (idempotent — для уже-смигрированных строк WHERE NULL).
    conn.execute(
        """
        UPDATE events
        SET engine = CASE event_type
            WHEN 'DBMSSQL' THEN 'mssql'
            WHEN 'DBPOSTGRS' THEN 'postgres'
            ELSE NULL
        END
        WHERE engine IS NULL
          AND event_type IN ('DBMSSQL', 'DBPOSTGRS')
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_engine ON events(archive_id, engine)"
    )


def _migrate_context_normalized(conn: duckdb.DuckDBPyConnection) -> None:
    """Sprint 3 — idempotent add column + backfill из raw context.

    Использует regexp_replace в DuckDB чтобы извлечь часть до ':' (если он есть).
    Один проход, безопасно для уже-мигрированных архивов (WHERE NULL фильтр).
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
    if "context_normalized" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN context_normalized VARCHAR")
    # Backfill только незаполненных строк (idempotent).
    # DuckDB regexp_replace: ^([^:]+?)(\\s*:.*)?$ -> \\1 даёт префикс до ':'.
    conn.execute(
        """
        UPDATE events
        SET context_normalized = trim(regexp_replace(context, '^([^:]+?)(\\s*:.*)?$', '\\1'))
        WHERE context IS NOT NULL
          AND context <> ''
          AND context_normalized IS NULL
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_ctx_norm ON events(archive_id, context_normalized)"
    )


class AppenderHandle:
    """Bulk-insert API поверх DuckDB executemany с буферизацией (ADR-011).

    DuckDB 1.5.2 Python API не предоставляет row-by-row Appender, поэтому
    под капотом используется ``executemany`` с большим batch size (10_000).
    На 100K событий укладываемся в < 5 секунд, на 100M — в пределы 10 минут
    (ожидаемая верхняя планка ingestion на 12 GiB корпусе).
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        archive_id: str,
        sql: str,
        start_id: int = 1,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self._conn = conn
        self._sql = sql
        self.archive_id = archive_id
        self._next_id = start_id
        self._count = 0
        self._batch_size = batch_size
        self._buffer: list[tuple] = []

    @property
    def next_id(self) -> int:
        return self._next_id

    @property
    def rows_appended(self) -> int:
        return self._count

    def append_event(self, ev: ParsedEvent) -> None:
        row = ev.as_row(self.archive_id, self._next_id)
        self._buffer.append(row)
        self._next_id += 1
        self._count += 1
        if len(self._buffer) >= self._batch_size:
            self._flush_buffer()

    def append_many(self, events: Iterable[ParsedEvent]) -> int:
        appended = 0
        for ev in events:
            self.append_event(ev)
            appended += 1
        return appended

    def flush(self) -> None:
        self._flush_buffer()

    def _flush_buffer(self) -> None:
        if not self._buffer:
            return
        import pyarrow as pa

        # Преобразуем буфер в column-oriented arrays и оборачиваем в Arrow Table.
        # DuckDB читает Arrow zero-copy → намного быстрее executemany.
        cols = list(zip(*self._buffer))
        arrow_table = pa.table({EVENT_COLUMNS[i]: list(cols[i]) for i in range(len(EVENT_COLUMNS))})
        self._conn.register("_appender_batch", arrow_table)
        try:
            self._conn.execute(
                f"INSERT INTO events ({', '.join(EVENT_COLUMNS)}) "
                f"SELECT {', '.join(EVENT_COLUMNS)} FROM _appender_batch"
            )
        finally:
            self._conn.unregister("_appender_batch")
        self._buffer.clear()

    def close(self) -> None:
        self._flush_buffer()


class DuckDBStore:
    """Per-archive embedded DuckDB instance."""

    def __init__(self, archive_id: str, db_path: Path | None = None) -> None:
        self.archive_id = archive_id
        self.db_path = db_path or (default_db_dir() / f"{archive_id}.duckdb")
        self._conn: duckdb.DuckDBPyConnection | None = None

    def open(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            _configure_connection(self._conn)
            self._conn.execute(SCHEMA_DDL)
            _migrate_context_normalized(self._conn)
            _migrate_plan_text(self._conn)
            _migrate_engine(self._conn)
            register_active_connection(self.archive_id, self._conn)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            unregister_active_connection(self.archive_id)
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DuckDBStore":
        self.open()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def init_schema(self) -> None:
        """Создать таблицу events. Indexes — отдельно, после bulk insert."""
        self.open()

    def create_indexes(self) -> None:
        conn = self.open()
        for stmt in INDEX_DDL:
            conn.execute(stmt)

    @contextmanager
    def appender(
        self,
        table: str = "events",
        start_id: int = 1,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Iterator[AppenderHandle]:
        """Bulk-insert context manager (ADR-011).

        Под капотом — multi-row ``INSERT ... VALUES (...), (...), ...`` через
        один SQL statement на каждый batch. Это намного быстрее executemany,
        который в DuckDB на Windows прогоняет каждую строку отдельной транзакцией.

        Indexes лучше создавать ПОСЛЕ блочной вставки через ``create_indexes()``.
        """
        conn = self.open()
        if table != "events":
            raise ValueError(f"Appender supports only 'events' table (got {table!r})")
        handle = AppenderHandle(
            conn=conn,
            archive_id=self.archive_id,
            sql="",  # SQL build-ится динамически на batch flush
            start_id=start_id,
            batch_size=batch_size,
        )
        try:
            yield handle
        except Exception:
            handle._buffer.clear()
            raise
        handle.flush()

    def bulk_insert(self, events: Iterable[ParsedEvent], start_id: int = 1, batch: int = 10_000) -> int:
        """Legacy executemany insert — оставлен для совместимости с Sprint 0 тестами.

        Новый код должен использовать ``appender()`` context manager.
        """
        conn = self.open()
        placeholders = ", ".join(["?"] * len(EVENT_COLUMNS))
        sql = f"INSERT INTO events ({', '.join(EVENT_COLUMNS)}) VALUES ({placeholders})"

        chunk: list[tuple] = []
        next_id = start_id
        written = 0
        for ev in events:
            chunk.append(ev.as_row(self.archive_id, next_id))
            next_id += 1
            if len(chunk) >= batch:
                conn.executemany(sql, chunk)
                written += len(chunk)
                chunk.clear()
        if chunk:
            conn.executemany(sql, chunk)
            written += len(chunk)
        return written

    def count_events(self) -> int:
        conn = self.open()
        row = conn.execute("SELECT COUNT(*) FROM events WHERE archive_id = ?", [self.archive_id]).fetchone()
        return int(row[0]) if row else 0

    def db_size_bytes(self) -> int:
        try:
            return self.db_path.stat().st_size
        except FileNotFoundError:
            return 0

    def run_preset(self, preset: str, limit: int = 100) -> tuple[list[tuple[str, str]], list[list[Any]]]:
        """Возвращает (columns, rows). columns — список (name, type)."""
        conn = self.open()
        if preset == "first_100":
            sql = (
                "SELECT ts, event_type, duration_us, session_id, user_name, context, sql_text "
                "FROM events WHERE archive_id = ? ORDER BY ts LIMIT ?"
            )
            params = [self.archive_id, limit]
        elif preset == "longest":
            # EXCPCNTX/Context несут cumulative-длительность родительского
            # контекста (не самого события) — без исключения они доминируют в
            # топе как ложные «самые медленные» (на боевых данных — события до
            # ~10 часов). Консистентно с _NON_CUMULATIVE_DURATION_EXPR в sql/views.py.
            sql = (
                "SELECT ts, event_type, duration_us, session_id, user_name, context, sql_text "
                "FROM events WHERE archive_id = ? AND duration_us IS NOT NULL "
                "AND event_type NOT IN ('EXCPCNTX', 'Context') "
                "ORDER BY duration_us DESC LIMIT ?"
            )
            params = [self.archive_id, limit]
        elif preset == "deadlocks":
            sql = (
                "SELECT ts, event_type, duration_us, session_id, user_name, context "
                "FROM events WHERE archive_id = ? AND event_type = 'TDEADLOCK' "
                "ORDER BY ts LIMIT ?"
            )
            params = [self.archive_id, limit]
        else:
            raise ValueError(f"Unknown preset: {preset}")

        cur = conn.execute(sql, params)
        columns = [(d[0], str(d[1])) for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
        for r in rows:
            for i, v in enumerate(r):
                if hasattr(v, "isoformat"):
                    r[i] = v.isoformat()
        return columns, rows

    @classmethod
    def delete_db_file(cls, archive_id: str, db_path: Path | None = None) -> bool:
        """Удаляет .duckdb файл для archive_id (cleanup после ingest error).

        На Windows DuckDB может удерживать lock несколько мс после close() —
        делаем одну retry-попытку через 200мс. Возвращает True если файл удалён
        (или не существовал), False если lock не отпустили.
        """
        import time

        path = db_path or (default_db_dir() / f"{archive_id}.duckdb")
        for attempt in range(2):
            try:
                path.unlink()
                return True
            except FileNotFoundError:
                return True
            except PermissionError:
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                return False
        return False
