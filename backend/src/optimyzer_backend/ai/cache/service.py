"""Sprint 11 — CacheService: high-level API для AI endpoints.

API дизайн:
- sync get/set (SQLite быстрая, нет смысла в async для типичных < 5ms операций)
- async обёртки (aget, aset) для FastAPI endpoints, через asyncio.to_thread

Singleton pattern: `get_cache()` возвращает один процесс-wide instance.
Тесты используют `reset_cache_for_tests(path)` чтобы изолировать storage.

PROMPT_VERSION константы — каждый AI endpoint определяет свою; повышение
версии автоматически invalidates старые entries (через cache_key, не через
delete — старые просто никогда не находятся при lookup).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from optimyzer_backend.ai.cache.canonicalize import compute_cache_key
from optimyzer_backend.ai.cache.models import CacheEntry, CacheStats, CacheType
from optimyzer_backend.ai.cache.storage import CacheStorage


logger = logging.getLogger(__name__)


class CacheService:
    """High-level facade поверх CacheStorage."""

    def __init__(self, storage: CacheStorage):
        self.storage = storage

    # ---------- Sync API ----------

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Lookup cached entry. Returns response dict or None.

        Не возвращает expired entries (как будто их нет — они будут удалены
        периодическим cleanup_expired или при следующем upsert).

        Side effect: increments hit_count + updates last_accessed_at.
        """
        import json

        entry = self.storage.get(cache_key)
        if entry is None:
            return None
        now = datetime.utcnow()
        if entry.is_expired(now):
            logger.debug("cache_get expired key=%s..", cache_key[:12])
            return None
        self.storage.record_hit(cache_key, now)
        try:
            return json.loads(entry.response_json)
        except json.JSONDecodeError:
            logger.warning("cache_get corrupted JSON key=%s..", cache_key[:12])
            self.storage.delete(cache_key)
            return None

    def get_entry(self, cache_key: str) -> Optional[CacheEntry]:
        """Возвращает CacheEntry без записи hit. Для cache_age_seconds расчёта."""
        entry = self.storage.get(cache_key)
        if entry is None or entry.is_expired():
            return None
        return entry

    def set(
        self,
        *,
        cache_key: str,
        cache_type: CacheType,
        response: dict[str, Any],
        prompt_version: str,
        model_used: str,
        ttl_days: Optional[int] = None,
        input_size_bytes: int = 0,
    ) -> None:
        """Store response in cache.

        ttl_days=None → forever (но всё равно подлежит invalidation через
        PROMPT_VERSION bump).
        """
        import json

        now = datetime.utcnow()
        expires_at = (
            now + timedelta(days=ttl_days) if ttl_days is not None else None
        )
        response_json = json.dumps(response, ensure_ascii=False)
        self.storage.upsert(
            cache_key=cache_key,
            cache_type=cache_type,
            prompt_version=prompt_version,
            model_used=model_used,
            response_json=response_json,
            input_size_bytes=input_size_bytes,
            response_size_bytes=len(response_json.encode("utf-8")),
            generated_at=now,
            expires_at=expires_at,
        )

    def invalidate_by_version(
        self, cache_type: CacheType, old_version: str
    ) -> int:
        """Удалить entries старой версии prompt'а."""
        n = self.storage.delete_by_type_version(cache_type, old_version)
        logger.info(
            "cache invalidation type=%s old_version=%s deleted=%d",
            cache_type.value,
            old_version,
            n,
        )
        return n

    def cleanup_expired(self) -> int:
        """Удалить все expired entries. Возвращает число удалённых."""
        return self.storage.cleanup_expired(datetime.utcnow())

    def clear_all(self) -> int:
        return self.storage.clear_all()

    def get_stats(self) -> CacheStats:
        return self.storage.get_stats()

    def compute_key(
        self,
        canonical_input: str,
        cache_type: CacheType,
        prompt_version: str,
        model: str,
    ) -> str:
        """Удобная обёртка над compute_cache_key."""
        return compute_cache_key(
            canonical_input, cache_type.value, prompt_version, model
        )

    # ---------- Async API (FastAPI) ----------

    async def aget(self, cache_key: str) -> Optional[dict[str, Any]]:
        return await asyncio.to_thread(self.get, cache_key)

    async def aget_entry(self, cache_key: str) -> Optional[CacheEntry]:
        return await asyncio.to_thread(self.get_entry, cache_key)

    async def aset(
        self,
        *,
        cache_key: str,
        cache_type: CacheType,
        response: dict[str, Any],
        prompt_version: str,
        model_used: str,
        ttl_days: Optional[int] = None,
        input_size_bytes: int = 0,
    ) -> None:
        await asyncio.to_thread(
            self.set,
            cache_key=cache_key,
            cache_type=cache_type,
            response=response,
            prompt_version=prompt_version,
            model_used=model_used,
            ttl_days=ttl_days,
            input_size_bytes=input_size_bytes,
        )


# ---------- Singleton ----------

_cache_lock = threading.Lock()
_cache_instance: Optional[CacheService] = None


def _default_db_path() -> Path:
    """Путь к ai_cache.db в данных приложения пользователя.

    На сервере кэш лежал в project_root/data. В десктопе писать рядом с exe
    нельзя (Program Files только на чтение), поэтому — туда же, где остальные
    данные приложения: APPDATA/1c-optimyzer.
    """
    import os

    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    p = Path(base) / "1c-optimyzer"
    p.mkdir(parents=True, exist_ok=True)
    return p / "ai_cache.db"


def get_cache() -> CacheService:
    """Global cache instance (lazy init)."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = CacheService(CacheStorage(_default_db_path()))
                logger.info("ai_cache initialized at %s", _default_db_path())
    return _cache_instance


def reset_cache_for_tests(db_path: Optional[Path] = None) -> CacheService:
    """Reset singleton — для тестов (изоляция).

    Если db_path передан, использует его. Иначе in-memory SQLite.
    """
    global _cache_instance
    with _cache_lock:
        if _cache_instance is not None:
            try:
                _cache_instance.storage.close()
            except Exception:
                pass
        if db_path is None:
            # In-memory SQLite — каждый тест получает чистый instance
            import tempfile

            tmp = tempfile.mkdtemp(prefix="ai_cache_test_")
            db_path = Path(tmp) / "ai_cache.db"
        _cache_instance = CacheService(CacheStorage(db_path))
        return _cache_instance
