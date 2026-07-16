"""Sprint 11 — SQLite storage для AI cache.

Sync API (SQLite сама блокирующая; для FastAPI оборачиваем в
``asyncio.to_thread`` в CacheService). Использует один файл —
по умолчанию ``<project_root>/data/ai_cache.db``.

Schema:
    cache_entries — основная таблица с AI responses

Performance:
    cache_key — PK с automatic index, lookup O(log N)
    Индексы на cache_type, expires_at, hit_count для analytics/cleanup
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from optimyzer_backend.ai.cache.models import CacheEntry, CacheStats, CacheType


_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS cache_entries (
    cache_key TEXT PRIMARY KEY,
    cache_type TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_used TEXT NOT NULL,
    response_json TEXT NOT NULL,
    input_size_bytes INTEGER NOT NULL DEFAULT 0,
    response_size_bytes INTEGER NOT NULL DEFAULT 0,
    generated_at TEXT NOT NULL,
    expires_at TEXT,
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)
    WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cache_hits ON cache_entries(hit_count DESC);
CREATE INDEX IF NOT EXISTS idx_cache_type_version
    ON cache_entries(cache_type, prompt_version);
"""


def _iso(dt: datetime) -> str:
    """Сериализация datetime в ISO-8601 (наносекунды отбрасываем)."""
    return dt.replace(microsecond=dt.microsecond // 1000 * 1000).isoformat(
        timespec="microseconds"
    )


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    return datetime.fromisoformat(s)


def _row_to_entry(row: sqlite3.Row) -> CacheEntry:
    return CacheEntry(
        cache_key=row["cache_key"],
        cache_type=CacheType(row["cache_type"]),
        prompt_version=row["prompt_version"],
        model_used=row["model_used"],
        response_json=row["response_json"],
        input_size_bytes=row["input_size_bytes"],
        response_size_bytes=row["response_size_bytes"],
        generated_at=_parse_iso(row["generated_at"]),
        expires_at=_parse_iso(row["expires_at"]),
        hit_count=row["hit_count"],
        last_accessed_at=_parse_iso(row["last_accessed_at"]),
    )


class CacheStorage:
    """SQLite storage для AI cache (sync API).

    Thread-safe: использует threading.local для connection pooling
    + check_same_thread=False (SQLite в threading mode).
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Per-thread connection (SQLite не любит cross-thread reuse)."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row
            # WAL mode для concurrent read + write
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        conn.executescript(_SCHEMA_DDL)
        conn.commit()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ---------- CRUD ----------

    def get(self, cache_key: str) -> Optional[CacheEntry]:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM cache_entries WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_entry(row)

    def upsert(
        self,
        *,
        cache_key: str,
        cache_type: CacheType,
        prompt_version: str,
        model_used: str,
        response_json: str,
        input_size_bytes: int,
        response_size_bytes: int,
        generated_at: datetime,
        expires_at: Optional[datetime],
    ) -> None:
        """INSERT OR REPLACE — старый entry заменяется (hit_count reset)."""
        conn = self._connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO cache_entries
            (cache_key, cache_type, prompt_version, model_used, response_json,
             input_size_bytes, response_size_bytes, generated_at, expires_at,
             hit_count, last_accessed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                cache_key,
                cache_type.value,
                prompt_version,
                model_used,
                response_json,
                input_size_bytes,
                response_size_bytes,
                _iso(generated_at),
                _iso(expires_at) if expires_at else None,
                _iso(generated_at),
            ),
        )
        conn.commit()

    def record_hit(self, cache_key: str, accessed_at: datetime) -> None:
        """Increment hit_count + update last_accessed_at."""
        conn = self._connect()
        conn.execute(
            """
            UPDATE cache_entries
            SET hit_count = hit_count + 1,
                last_accessed_at = ?
            WHERE cache_key = ?
            """,
            (_iso(accessed_at), cache_key),
        )
        conn.commit()

    def delete(self, cache_key: str) -> bool:
        conn = self._connect()
        cur = conn.execute(
            "DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,)
        )
        conn.commit()
        return cur.rowcount > 0

    # ---------- Bulk operations ----------

    def delete_by_type_version(
        self, cache_type: CacheType, prompt_version: str
    ) -> int:
        """Bulk invalidation when prompt version bumped."""
        conn = self._connect()
        cur = conn.execute(
            """
            DELETE FROM cache_entries
            WHERE cache_type = ? AND prompt_version = ?
            """,
            (cache_type.value, prompt_version),
        )
        conn.commit()
        return cur.rowcount

    def cleanup_expired(self, now: datetime) -> int:
        """Удалить все entries с expires_at < now. Возвращает число удалённых."""
        conn = self._connect()
        cur = conn.execute(
            """
            DELETE FROM cache_entries
            WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
            (_iso(now),),
        )
        conn.commit()
        return cur.rowcount

    def clear_all(self) -> int:
        conn = self._connect()
        cur = conn.execute("DELETE FROM cache_entries")
        conn.commit()
        return cur.rowcount

    # ---------- Stats ----------

    def get_stats(self) -> CacheStats:
        conn = self._connect()
        total_row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(response_size_bytes), 0) AS total_size,
                COALESCE(SUM(hit_count), 0) AS total_hits,
                MIN(generated_at) AS oldest_at,
                MAX(generated_at) AS newest_at
            FROM cache_entries
            """
        ).fetchone()
        by_type_rows = conn.execute(
            """
            SELECT cache_type, COUNT(*) AS cnt
            FROM cache_entries
            GROUP BY cache_type
            """
        ).fetchall()
        top_rows = conn.execute(
            """
            SELECT cache_key, hit_count
            FROM cache_entries
            WHERE hit_count > 0
            ORDER BY hit_count DESC
            LIMIT 10
            """
        ).fetchall()

        return CacheStats(
            total_entries=total_row["total"] or 0,
            total_size_bytes=total_row["total_size"] or 0,
            entries_by_type={r["cache_type"]: r["cnt"] for r in by_type_rows},
            total_hits=total_row["total_hits"] or 0,
            top_hits=[(r["cache_key"][:12], r["hit_count"]) for r in top_rows],
            oldest_at=_parse_iso(total_row["oldest_at"]),
            newest_at=_parse_iso(total_row["newest_at"]),
        )

    def iter_entries(self, limit: int = 500) -> Iterator[CacheEntry]:
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT * FROM cache_entries
            ORDER BY last_accessed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            yield _row_to_entry(row)
