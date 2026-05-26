"""Sprint 11 Phase A — тесты CacheService (high-level facade)."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from services.ai_cache.models import CacheType
from services.ai_cache.service import CacheService, reset_cache_for_tests
from services.ai_cache.storage import CacheStorage


@pytest.fixture
def cache() -> CacheService:
    tmpdir = tempfile.mkdtemp(prefix="ai_cache_test_")
    db_path = Path(tmpdir) / "cache.db"
    yield CacheService(CacheStorage(db_path))


class TestSyncApi:
    def test_get_miss_returns_none(self, cache: CacheService):
        assert cache.get("missing") is None

    def test_set_then_get(self, cache: CacheService):
        cache.set(
            cache_key="k",
            cache_type=CacheType.PLAN_MSSQL_XML,
            response={"summary": "test"},
            prompt_version="v1",
            model_used="haiku",
        )
        cached = cache.get("k")
        assert cached == {"summary": "test"}

    def test_get_increments_hit_count(self, cache: CacheService):
        cache.set(
            cache_key="k",
            cache_type=CacheType.QUERY,
            response={"x": 1},
            prompt_version="v1",
            model_used="haiku",
        )
        cache.get("k")
        cache.get("k")
        cache.get("k")
        entry = cache.storage.get("k")
        assert entry.hit_count == 3

    def test_ttl_days_sets_expires_at(self, cache: CacheService):
        cache.set(
            cache_key="k",
            cache_type=CacheType.QUERY,
            response={},
            prompt_version="v1",
            model_used="haiku",
            ttl_days=30,
        )
        entry = cache.storage.get("k")
        assert entry.expires_at is not None
        # Approximately 30 days in future (allow ±1 day boundary slop)
        delta = entry.expires_at - datetime.utcnow()
        assert timedelta(days=29) <= delta <= timedelta(days=30, hours=1)

    def test_ttl_none_forever(self, cache: CacheService):
        cache.set(
            cache_key="k",
            cache_type=CacheType.PLAN_MSSQL_XML,
            response={},
            prompt_version="v1",
            model_used="haiku",
            ttl_days=None,
        )
        entry = cache.storage.get("k")
        assert entry.expires_at is None

    def test_expired_entry_returns_none(self, cache: CacheService):
        # Manually insert expired entry
        past = datetime.utcnow() - timedelta(days=1)
        cache.storage.upsert(
            cache_key="expired",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json='{"x":1}',
            input_size_bytes=0,
            response_size_bytes=10,
            generated_at=past - timedelta(days=10),
            expires_at=past,
        )
        assert cache.get("expired") is None

    def test_corrupted_json_deleted(self, cache: CacheService):
        cache.storage.upsert(
            cache_key="bad",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json="{not valid json",
            input_size_bytes=0,
            response_size_bytes=10,
            generated_at=datetime.utcnow(),
            expires_at=None,
        )
        # First call returns None and deletes entry
        assert cache.get("bad") is None
        # Verify deleted
        assert cache.storage.get("bad") is None

    def test_get_entry_no_hit_increment(self, cache: CacheService):
        cache.set(
            cache_key="k",
            cache_type=CacheType.QUERY,
            response={"x": 1},
            prompt_version="v1",
            model_used="haiku",
        )
        cache.get_entry("k")
        cache.get_entry("k")
        # get_entry не увеличивает hit_count
        entry = cache.storage.get("k")
        assert entry.hit_count == 0


class TestInvalidation:
    def test_invalidate_by_version(self, cache: CacheService):
        for i in range(3):
            cache.set(
                cache_key=f"k_v1_{i}",
                cache_type=CacheType.PLAN_MSSQL_XML,
                response={"i": i},
                prompt_version="v1",
                model_used="haiku",
            )
        cache.set(
            cache_key="k_v2",
            cache_type=CacheType.PLAN_MSSQL_XML,
            response={"new": True},
            prompt_version="v2",
            model_used="haiku",
        )

        deleted = cache.invalidate_by_version(CacheType.PLAN_MSSQL_XML, "v1")
        assert deleted == 3
        assert cache.get("k_v1_0") is None
        assert cache.get("k_v2") == {"new": True}


class TestComputeKey:
    def test_compute_key_uses_cache_type_value(self, cache: CacheService):
        key1 = cache.compute_key("x", CacheType.PLAN_MSSQL_XML, "v1", "haiku")
        # Same as direct invocation
        from services.ai_cache.canonicalize import compute_cache_key
        key2 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        assert key1 == key2


class TestAsyncApi:
    @pytest.mark.asyncio
    async def test_aget_aset(self, cache: CacheService):
        await cache.aset(
            cache_key="async_k",
            cache_type=CacheType.QUERY,
            response={"async": "yes"},
            prompt_version="v1",
            model_used="haiku",
        )
        cached = await cache.aget("async_k")
        assert cached == {"async": "yes"}

    @pytest.mark.asyncio
    async def test_aget_entry(self, cache: CacheService):
        await cache.aset(
            cache_key="async_k",
            cache_type=CacheType.QUERY,
            response={"async": "yes"},
            prompt_version="v1",
            model_used="haiku",
        )
        entry = await cache.aget_entry("async_k")
        assert entry is not None
        assert entry.cache_key == "async_k"


class TestSingleton:
    def test_reset_for_tests_isolates(self):
        c1 = reset_cache_for_tests()
        c1.set(
            cache_key="k",
            cache_type=CacheType.QUERY,
            response={"first": True},
            prompt_version="v1",
            model_used="haiku",
        )
        # New reset = new DB
        c2 = reset_cache_for_tests()
        assert c2.get("k") is None

    def test_reset_for_tests_with_path(self, tmp_path: Path):
        db_path = tmp_path / "shared.db"
        c1 = reset_cache_for_tests(db_path)
        c1.set(
            cache_key="k",
            cache_type=CacheType.QUERY,
            response={"shared": True},
            prompt_version="v1",
            model_used="haiku",
        )
        # Reusing same path
        c2 = reset_cache_for_tests(db_path)
        # Same DB → entry persists
        assert c2.get("k") == {"shared": True}


class TestStatsAndCleanup:
    def test_get_stats(self, cache: CacheService):
        for i in range(3):
            cache.set(
                cache_key=f"k{i}",
                cache_type=CacheType.PLAN_MSSQL_XML,
                response={"i": i},
                prompt_version="v1",
                model_used="haiku",
            )
        stats = cache.get_stats()
        assert stats.total_entries == 3

    def test_cleanup_expired(self, cache: CacheService):
        past = datetime.utcnow() - timedelta(days=1)
        cache.storage.upsert(
            cache_key="expired",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json="{}",
            input_size_bytes=0,
            response_size_bytes=2,
            generated_at=past - timedelta(days=10),
            expires_at=past,
        )
        cache.set(
            cache_key="fresh",
            cache_type=CacheType.QUERY,
            response={},
            prompt_version="v1",
            model_used="haiku",
        )
        deleted = cache.cleanup_expired()
        assert deleted == 1
        assert cache.get("fresh") == {}

    def test_clear_all(self, cache: CacheService):
        for i in range(5):
            cache.set(
                cache_key=f"k{i}",
                cache_type=CacheType.QUERY,
                response={"i": i},
                prompt_version="v1",
                model_used="haiku",
            )
        n = cache.clear_all()
        assert n == 5
        assert cache.get_stats().total_entries == 0


class TestRoundtripWithCanonicalization:
    """End-to-end: одинаковый план с разными actual stats → cache hit."""

    def test_mssql_xml_runtime_doesnt_break_cache(self, cache: CacheService):
        from services.ai_cache.canonicalize import canonicalize_plan_mssql_xml

        plan_run1 = (
            '<Op NodeId="0" EstimatedRows="100" ActualRows="100"/>'
        )
        plan_run2 = (
            '<Op NodeId="0" EstimatedRows="100" ActualRows="50000"/>'
        )

        key1 = cache.compute_key(
            canonicalize_plan_mssql_xml(plan_run1),
            CacheType.PLAN_MSSQL_XML,
            "v1",
            "haiku",
        )
        key2 = cache.compute_key(
            canonicalize_plan_mssql_xml(plan_run2),
            CacheType.PLAN_MSSQL_XML,
            "v1",
            "haiku",
        )
        assert key1 == key2  # cache hit despite different ActualRows

        cache.set(
            cache_key=key1,
            cache_type=CacheType.PLAN_MSSQL_XML,
            response={"summary": "from run1"},
            prompt_version="v1",
            model_used="haiku",
        )
        # Second run lookups with key2 (same key) → hit
        assert cache.get(key2) == {"summary": "from run1"}

    def test_prompt_version_bump_invalidates(self, cache: CacheService):
        """Real flow: bump PROMPT_VERSION → old cache misses, but lookup with new returns miss too."""
        from services.ai_cache.canonicalize import canonicalize_sdbl

        sdbl = "ВЫБРАТЬ * ИЗ Т"
        canonical = canonicalize_sdbl(sdbl)

        key_v1 = cache.compute_key(
            canonical, CacheType.QUERY, "v1", "haiku"
        )
        key_v2 = cache.compute_key(
            canonical, CacheType.QUERY, "v2", "haiku"
        )
        assert key_v1 != key_v2

        cache.set(
            cache_key=key_v1,
            cache_type=CacheType.QUERY,
            response={"answer": "old"},
            prompt_version="v1",
            model_used="haiku",
        )

        # Lookup with v2 key → miss
        assert cache.get(key_v2) is None
        # Old entry still findable with v1 key (but in prod we wouldn't compute that)
        assert cache.get(key_v1) == {"answer": "old"}
