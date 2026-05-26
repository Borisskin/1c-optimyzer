"""Sprint 11 — AI response cache (content-canonical).

Single-tier SQLite cache в `<server_data>/ai_cache.db`. Cache key = sha256
от canonicalized входа + cache_type + prompt_version + model.

Архитектурная мотивация (ADR-057): spec предполагал two-tier
(per-archive DuckDB + global SQLite), но в текущей архитектуре AI вызывается
напрямую `frontend → server/v1/ai/...`, минуя backend sidecar. Per-archive
cache потребовал бы рефакторинга всего AI flow через backend. Single-tier
shared cache даёт 90% бенефита (cross-user hits) при 10% сложности.

Использование::

    from services.ai_cache import get_cache, CacheType

    cache = get_cache()
    key = cache.compute_key(canonicalized_input, CacheType.PLAN_MSSQL_XML,
                            prompt_version="v1", model="claude-haiku-4-5")
    cached = cache.get(key)
    if cached:
        return PlanExplainResponse(**cached)
    response = await ai_call(...)
    cache.set(key, CacheType.PLAN_MSSQL_XML, response.model_dump(),
              prompt_version="v1", model_used=response.model_used, ttl_days=None)
"""

from __future__ import annotations

from services.ai_cache.canonicalize import (
    canonicalize_logcfg_description,
    canonicalize_plan_mssql_text,
    canonicalize_plan_mssql_xml,
    canonicalize_plan_pg_json,
    canonicalize_plan_pg_text,
    canonicalize_sdbl,
    compute_cache_key,
)
from services.ai_cache.models import CacheEntry, CacheStats, CacheType
from services.ai_cache.service import CacheService, get_cache, reset_cache_for_tests

__all__ = [
    # types
    "CacheEntry",
    "CacheType",
    "CacheStats",
    # service
    "CacheService",
    "get_cache",
    "reset_cache_for_tests",
    # canonicalization
    "canonicalize_plan_mssql_xml",
    "canonicalize_plan_mssql_text",
    "canonicalize_plan_pg_text",
    "canonicalize_plan_pg_json",
    "canonicalize_sdbl",
    "canonicalize_logcfg_description",
    "compute_cache_key",
]
