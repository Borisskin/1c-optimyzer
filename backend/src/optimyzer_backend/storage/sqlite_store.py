"""SQLite store для app-level metadata (recent archives, settings)."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recent_archives (
    archive_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    size_bytes INTEGER,
    events_count INTEGER,
    loaded_at TEXT NOT NULL,
    parsing_time_sec REAL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def default_metadata_path() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    p = Path(base) / "1c-optimyzer"
    p.mkdir(parents=True, exist_ok=True)
    return p / "metadata.sqlite"


class SqliteStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_metadata_path()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_recent_archive(
        self,
        archive_id: str,
        path: str,
        size_bytes: int,
        events_count: int,
        parsing_time_sec: float | None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO recent_archives (archive_id, path, size_bytes, events_count, loaded_at, parsing_time_sec)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(archive_id) DO UPDATE SET
                    path = excluded.path,
                    size_bytes = excluded.size_bytes,
                    events_count = excluded.events_count,
                    loaded_at = excluded.loaded_at,
                    parsing_time_sec = excluded.parsing_time_sec
                """,
                (archive_id, path, size_bytes, events_count, datetime.utcnow().isoformat(), parsing_time_sec),
            )

    def list_recent_archives(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT archive_id, path, size_bytes, events_count, loaded_at, parsing_time_sec "
                "FROM recent_archives ORDER BY loaded_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
