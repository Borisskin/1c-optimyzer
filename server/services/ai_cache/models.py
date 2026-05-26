"""Sprint 11 — типы для AI cache.

CacheType — фиксированный набор cache типов. Имена устойчивы (используются
как column value, поэтому их нельзя переименовывать без миграции).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional


class CacheType(StrEnum):
    """Тип AI ответа в кеше.

    Имена устойчивы — изменение требует data migration.
    """

    PLAN_MSSQL_XML = "plan_mssql_xml"
    PLAN_MSSQL_TEXT = "plan_mssql_text"
    PLAN_PG_TEXT = "plan_pg_text"
    PLAN_PG_JSON = "plan_pg_json"
    QUERY = "query"
    LOGCFG = "logcfg"
    REGRESSION = "regression"  # Sprint 11 Phase F — AI summary для регрессий


@dataclass
class CacheEntry:
    """Одна запись в кеше."""

    cache_key: str
    cache_type: CacheType
    prompt_version: str
    model_used: str
    response_json: str  # serialized AI response
    input_size_bytes: int
    response_size_bytes: int
    generated_at: datetime
    expires_at: Optional[datetime]  # None = forever
    hit_count: int
    last_accessed_at: datetime

    def age_seconds(self, now: Optional[datetime] = None) -> int:
        """Сколько секунд прошло с момента генерации."""
        ref = now or datetime.utcnow()
        return max(0, int((ref - self.generated_at).total_seconds()))

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        ref = now or datetime.utcnow()
        return ref >= self.expires_at


@dataclass
class CacheStats:
    """Агрегированная статистика для Settings → AI Cache UI."""

    total_entries: int
    total_size_bytes: int
    entries_by_type: dict[str, int]
    total_hits: int  # сумма hit_count
    top_hits: list[tuple[str, int]]  # [(cache_key_prefix, hits), ...] top-10
    oldest_at: Optional[datetime]
    newest_at: Optional[datetime]
