"""DuckDB storage layer per archive."""

from __future__ import annotations

import os
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend.parsers.tj_parser import ParsedEvent

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id BIGINT PRIMARY KEY,
    archive_id VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    duration_us BIGINT,
    event_type VARCHAR NOT NULL,
    session_id INTEGER,
    user_name VARCHAR,
    context VARCHAR,
    process VARCHAR,
    process_pid INTEGER,
    sql_text TEXT,
    sql_text_normalized TEXT,
    sql_text_hash VARCHAR(32),
    rows_read BIGINT,
    rows_modified BIGINT,
    extra JSON,
    source_file VARCHAR,
    source_line_start INTEGER
);
"""

INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_events_archive ON events(archive_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_ts ON events(archive_id, ts);",
    "CREATE INDEX IF NOT EXISTS idx_events_type ON events(archive_id, event_type);",
    "CREATE INDEX IF NOT EXISTS idx_events_duration ON events(archive_id, duration_us);",
    "CREATE INDEX IF NOT EXISTS idx_events_sql_hash ON events(archive_id, sql_text_hash);",
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
    "process",
    "process_pid",
    "sql_text",
    "sql_text_normalized",
    "sql_text_hash",
    "rows_read",
    "rows_modified",
    "extra",
    "source_file",
    "source_line_start",
]


def default_db_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    p = Path(base) / "1c-optimyzer" / "duckdb"
    p.mkdir(parents=True, exist_ok=True)
    return p


class DuckDBStore:
    """Per-archive embedded DuckDB instance."""

    def __init__(self, archive_id: str, db_path: Path | None = None) -> None:
        self.archive_id = archive_id
        self.db_path = db_path or (default_db_dir() / f"{archive_id}.duckdb")
        self._conn: duckdb.DuckDBPyConnection | None = None

    def open(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            self._conn.execute(SCHEMA_DDL)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DuckDBStore":
        self.open()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def create_indexes(self) -> None:
        conn = self.open()
        for stmt in INDEX_DDL:
            conn.execute(stmt)

    def bulk_insert(self, events: Iterable[ParsedEvent], start_id: int = 1, batch: int = 10_000) -> int:
        """Bulk-insert через DuckDB executemany. Возвращает кол-во записанных строк."""
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
            sql = (
                "SELECT ts, event_type, duration_us, session_id, user_name, context, sql_text "
                "FROM events WHERE archive_id = ? AND duration_us IS NOT NULL "
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
        # сериализация datetime/Decimal/etc для JSON
        for r in rows:
            for i, v in enumerate(r):
                if hasattr(v, "isoformat"):
                    r[i] = v.isoformat()
        return columns, rows
