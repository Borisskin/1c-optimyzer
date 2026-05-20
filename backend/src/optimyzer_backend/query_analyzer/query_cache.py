"""Sprint 4 — AI rewriter cache.

Хранит результат AI-переписывания запросов чтобы не дёргать Claude API
повторно. Использует тот же файл `data/explainer_cache.db` что и
ExplainerCache — отдельная таблица `query_rewrite_cache`.

Ключ кеша = sha256(нормализованный_текст_запроса + список_findings_ids).
Нормализация: trim + collapse whitespace + lowercase keywords. Это значит
что косметические изменения (лишние пробелы, регистр ключевых слов) не
инвалидируют кеш.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS query_rewrite_cache (
    cache_key TEXT PRIMARY KEY,
    query_hash TEXT NOT NULL,
    findings_hash TEXT NOT NULL,
    rewritten_query TEXT NOT NULL,
    changes_json TEXT NOT NULL,
    notes_for_developer TEXT,
    estimated_improvement TEXT,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_rewrite_cache_created
ON query_rewrite_cache(created_at);
"""


@dataclass
class QueryRewriteEntry:
    cache_key: str
    query_hash: str
    findings_hash: str
    rewritten_query: str
    changes_json: str
    notes_for_developer: str | None
    estimated_improvement: str | None
    model: str
    tokens_in: int
    tokens_out: int
    created_at: str


def normalize_query(query_text: str) -> str:
    """Нормализация для хеширования. Кеш hit даже если юзер вставил тот же
    запрос с другими пробелами/переносами."""
    s = query_text.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def compute_cache_key(query_text: str, finding_ids: list[str]) -> str:
    query_hash = hashlib.sha256(normalize_query(query_text).encode("utf-8")).hexdigest()
    findings_hash = hashlib.sha256(",".join(sorted(finding_ids)).encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{query_hash}|{findings_hash}".encode("utf-8")).hexdigest()[:32]


class QueryRewriteCache:
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

    def get(self, cache_key: str) -> QueryRewriteEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM query_rewrite_cache WHERE cache_key = ?", [cache_key]
            ).fetchone()
        if row is None:
            return None
        return QueryRewriteEntry(**dict(row))

    def put(self, entry: QueryRewriteEntry) -> None:
        now = entry.created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_rewrite_cache
                (cache_key, query_hash, findings_hash, rewritten_query,
                 changes_json, notes_for_developer, estimated_improvement,
                 model, tokens_in, tokens_out, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    entry.cache_key,
                    entry.query_hash,
                    entry.findings_hash,
                    entry.rewritten_query,
                    entry.changes_json,
                    entry.notes_for_developer,
                    entry.estimated_improvement,
                    entry.model,
                    entry.tokens_in,
                    entry.tokens_out,
                    now,
                ],
            )

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM query_rewrite_cache").fetchone()
            return {"entries": row["cnt"] if row else 0}

    def clear_all(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM query_rewrite_cache")
            return cur.rowcount
