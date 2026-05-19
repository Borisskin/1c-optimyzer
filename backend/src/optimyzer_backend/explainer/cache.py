"""Sprint 3 Phase F — AI explainer cache.

Отдельный SQLite файл `data/explainer_cache.db` (НЕ смешивать с app metadata).
Key = hash(archive_id + anatomy_kind + target_id). Value = AI text + tokens.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CacheEntry:
    cache_key: str
    archive_id: str
    anatomy_kind: str
    target_id: str
    rule_id: str | None
    ai_text: str
    model: str
    tokens_in: int
    tokens_out: int
    created_at: str


_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS explainer_cache (
    cache_key TEXT PRIMARY KEY,
    archive_id TEXT NOT NULL,
    anatomy_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rule_id TEXT,
    ai_text TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_explainer_cache_archive
ON explainer_cache(archive_id);
"""


def make_cache_key(archive_id: str, anatomy_kind: str, target_id: str | int) -> str:
    raw = f"{archive_id}|{anatomy_kind}|{target_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class ExplainerCache:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_DDL)

    def get(self, cache_key: str) -> CacheEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM explainer_cache WHERE cache_key = ?", [cache_key]
            ).fetchone()
        if row is None:
            return None
        return CacheEntry(**dict(row))

    def put(
        self,
        *,
        cache_key: str,
        archive_id: str,
        anatomy_kind: str,
        target_id: str,
        rule_id: str | None,
        ai_text: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO explainer_cache
                (cache_key, archive_id, anatomy_kind, target_id, rule_id,
                 ai_text, model, tokens_in, tokens_out, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    cache_key,
                    archive_id,
                    anatomy_kind,
                    target_id,
                    rule_id,
                    ai_text,
                    model,
                    tokens_in,
                    tokens_out,
                    now,
                ],
            )

    def evict_archive(self, archive_id: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM explainer_cache WHERE archive_id = ?", [archive_id]
            )
            return cur.rowcount

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM explainer_cache").fetchone()
            return {"entries": row["cnt"] if row else 0}
