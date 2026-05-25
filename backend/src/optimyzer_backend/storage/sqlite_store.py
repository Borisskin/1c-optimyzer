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

CREATE TABLE IF NOT EXISTS saved_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    query TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_run_at TEXT,
    run_count INTEGER DEFAULT 0
);

-- Sprint 8 Phase B — opt-in PostgreSQL connections для re-EXPLAIN service.
-- Password НЕ хранится здесь — только metadata. Реальный пароль лежит в OS
-- keychain под ключом, который мы сохраняем как password_keychain_key.
CREATE TABLE IF NOT EXISTS pg_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 5432,
    database TEXT NOT NULL,
    username TEXT NOT NULL,
    password_keychain_key TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    is_default INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pg_connections_default
    ON pg_connections(is_default);
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

    def find_archive_id_by_path(self, path: str) -> str | None:
        """Возвращает archive_id для уже загруженного ранее path, либо None.

        Используется чтобы при повторной загрузке той же папки переиспользовать
        прежний archive_id — это критично для стабильности ключей AI-кеша
        (cache key = sha256(archive_id|kind|target)). Без этого reload папки
        делал старые AI-объяснения недоступными.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT archive_id FROM recent_archives WHERE path = ? LIMIT 1",
                (path,),
            ).fetchone()
            return row["archive_id"] if row else None

    def list_recent_archives(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT archive_id, path, size_bytes, events_count, loaded_at, parsing_time_sec "
                "FROM recent_archives ORDER BY loaded_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_recent_archive(self, archive_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM recent_archives WHERE archive_id = ?", (archive_id,))
            return cur.rowcount > 0

    def delete_all_recent_archives(self) -> int:
        with self._conn() as c:
            cur = c.execute("DELETE FROM recent_archives")
            return cur.rowcount

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

    # ---------- saved queries (Sprint 1) ----------

    def list_saved_queries(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, name, description, query, created_at, last_run_at, run_count "
                "FROM saved_queries ORDER BY COALESCE(last_run_at, created_at) DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def save_query(self, name: str, query: str, description: str | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO saved_queries (name, description, query) VALUES (?, ?, ?)",
                (name, description, query),
            )
            return int(cur.lastrowid or 0)

    def delete_saved_query(self, query_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))
            return cur.rowcount > 0

    def rename_saved_query(self, query_id: int, new_name: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "UPDATE saved_queries SET name = ? WHERE id = ?",
                (new_name, query_id),
            )
            return cur.rowcount > 0

    def mark_query_run(self, query_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "UPDATE saved_queries SET last_run_at = ?, run_count = run_count + 1 WHERE id = ?",
                (datetime.utcnow().isoformat(), query_id),
            )
            return cur.rowcount > 0
