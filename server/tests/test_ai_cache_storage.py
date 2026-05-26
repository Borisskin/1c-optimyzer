"""Sprint 11 Phase A — тесты SQLite storage слоя."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from services.ai_cache.models import CacheType
from services.ai_cache.storage import CacheStorage


@pytest.fixture
def storage() -> CacheStorage:
    """Изолированный SQLite storage на каждый тест."""
    tmpdir = tempfile.mkdtemp(prefix="ai_cache_test_")
    db_path = Path(tmpdir) / "cache.db"
    s = CacheStorage(db_path)
    yield s
    s.close()


class TestCRUD:
    def test_get_missing_returns_none(self, storage: CacheStorage):
        assert storage.get("nonexistent_key") is None

    def test_upsert_then_get(self, storage: CacheStorage):
        now = datetime.utcnow()
        storage.upsert(
            cache_key="k1",
            cache_type=CacheType.PLAN_MSSQL_XML,
            prompt_version="v1",
            model_used="haiku",
            response_json='{"foo": "bar"}',
            input_size_bytes=100,
            response_size_bytes=50,
            generated_at=now,
            expires_at=None,
        )
        entry = storage.get("k1")
        assert entry is not None
        assert entry.cache_key == "k1"
        assert entry.cache_type == CacheType.PLAN_MSSQL_XML
        assert entry.prompt_version == "v1"
        assert entry.model_used == "haiku"
        assert entry.response_json == '{"foo": "bar"}'
        assert entry.hit_count == 0

    def test_upsert_overwrites(self, storage: CacheStorage):
        now = datetime.utcnow()
        storage.upsert(
            cache_key="k",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json='{"a": 1}',
            input_size_bytes=10,
            response_size_bytes=10,
            generated_at=now,
            expires_at=None,
        )
        # Set hit count
        storage.record_hit("k", now)
        # Upsert should reset hit_count
        storage.upsert(
            cache_key="k",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json='{"a": 2}',
            input_size_bytes=10,
            response_size_bytes=10,
            generated_at=now,
            expires_at=None,
        )
        entry = storage.get("k")
        assert entry.response_json == '{"a": 2}'
        assert entry.hit_count == 0

    def test_record_hit_increments(self, storage: CacheStorage):
        now = datetime.utcnow()
        storage.upsert(
            cache_key="k",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json="{}",
            input_size_bytes=0,
            response_size_bytes=2,
            generated_at=now,
            expires_at=None,
        )
        storage.record_hit("k", now)
        storage.record_hit("k", now)
        storage.record_hit("k", now)
        entry = storage.get("k")
        assert entry.hit_count == 3

    def test_delete(self, storage: CacheStorage):
        now = datetime.utcnow()
        storage.upsert(
            cache_key="k",
            cache_type=CacheType.QUERY,
            prompt_version="v1",
            model_used="haiku",
            response_json="{}",
            input_size_bytes=0,
            response_size_bytes=2,
            generated_at=now,
            expires_at=None,
        )
        assert storage.delete("k") is True
        assert storage.get("k") is None
        # idempotent
        assert storage.delete("k") is False


class TestExpiry:
    def test_cleanup_expired(self, storage: CacheStorage):
        past = datetime.utcnow() - timedelta(days=1)
        future = datetime.utcnow() + timedelta(days=1)

        for i, expires_at in enumerate([past, past, future, None]):
            storage.upsert(
                cache_key=f"k{i}",
                cache_type=CacheType.QUERY,
                prompt_version="v1",
                model_used="haiku",
                response_json="{}",
                input_size_bytes=0,
                response_size_bytes=2,
                generated_at=datetime.utcnow() - timedelta(days=10),
                expires_at=expires_at,
            )

        deleted = storage.cleanup_expired(datetime.utcnow())
        assert deleted == 2
        # Only expired removed
        assert storage.get("k0") is None
        assert storage.get("k1") is None
        assert storage.get("k2") is not None
        assert storage.get("k3") is not None  # forever


class TestInvalidation:
    def test_delete_by_type_version(self, storage: CacheStorage):
        now = datetime.utcnow()
        # 2 entries для plan_mssql_xml v1
        for i in range(2):
            storage.upsert(
                cache_key=f"mssql_v1_{i}",
                cache_type=CacheType.PLAN_MSSQL_XML,
                prompt_version="v1",
                model_used="haiku",
                response_json="{}",
                input_size_bytes=0,
                response_size_bytes=2,
                generated_at=now,
                expires_at=None,
            )
        # 1 для plan_mssql_xml v2
        storage.upsert(
            cache_key="mssql_v2",
            cache_type=CacheType.PLAN_MSSQL_XML,
            prompt_version="v2",
            model_used="haiku",
            response_json="{}",
            input_size_bytes=0,
            response_size_bytes=2,
            generated_at=now,
            expires_at=None,
        )
        # 1 для plan_pg_text v1
        storage.upsert(
            cache_key="pg_v1",
            cache_type=CacheType.PLAN_PG_TEXT,
            prompt_version="v1",
            model_used="haiku",
            response_json="{}",
            input_size_bytes=0,
            response_size_bytes=2,
            generated_at=now,
            expires_at=None,
        )

        # Invalidate plan_mssql_xml v1 — should delete 2
        deleted = storage.delete_by_type_version(
            CacheType.PLAN_MSSQL_XML, "v1"
        )
        assert deleted == 2
        # v2 не тронут
        assert storage.get("mssql_v2") is not None
        # plan_pg_text не тронут
        assert storage.get("pg_v1") is not None


class TestStats:
    def test_empty_stats(self, storage: CacheStorage):
        stats = storage.get_stats()
        assert stats.total_entries == 0
        assert stats.total_size_bytes == 0
        assert stats.total_hits == 0
        assert stats.entries_by_type == {}
        assert stats.top_hits == []

    def test_stats_aggregation(self, storage: CacheStorage):
        now = datetime.utcnow()
        for i in range(5):
            storage.upsert(
                cache_key=f"plan_{i}",
                cache_type=CacheType.PLAN_MSSQL_XML,
                prompt_version="v1",
                model_used="haiku",
                response_json='{"hello": "world"}',
                input_size_bytes=100,
                response_size_bytes=18,
                generated_at=now,
                expires_at=None,
            )
        for i in range(3):
            storage.upsert(
                cache_key=f"q_{i}",
                cache_type=CacheType.QUERY,
                prompt_version="v1",
                model_used="haiku",
                response_json='{"x": 1}',
                input_size_bytes=50,
                response_size_bytes=8,
                generated_at=now,
                expires_at=None,
            )
        # Some hits
        storage.record_hit("plan_0", now)
        storage.record_hit("plan_0", now)
        storage.record_hit("q_0", now)

        stats = storage.get_stats()
        assert stats.total_entries == 8
        assert stats.total_size_bytes == 5 * 18 + 3 * 8
        assert stats.total_hits == 3
        assert stats.entries_by_type[CacheType.PLAN_MSSQL_XML.value] == 5
        assert stats.entries_by_type[CacheType.QUERY.value] == 3
        # top_hits sorted by hit_count desc
        assert stats.top_hits[0][1] == 2  # plan_0 with 2 hits


class TestPersistence:
    def test_data_survives_reopen(self, tmp_path: Path):
        """Запись + закрытие + переоткрытие — данные сохранены."""
        db_path = tmp_path / "persist.db"
        s1 = CacheStorage(db_path)
        s1.upsert(
            cache_key="persistent",
            cache_type=CacheType.LOGCFG,
            prompt_version="v1",
            model_used="haiku",
            response_json='{"persisted": true}',
            input_size_bytes=0,
            response_size_bytes=20,
            generated_at=datetime.utcnow(),
            expires_at=None,
        )
        s1.close()

        s2 = CacheStorage(db_path)
        entry = s2.get("persistent")
        assert entry is not None
        assert entry.response_json == '{"persisted": true}'
        s2.close()
