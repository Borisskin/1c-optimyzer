"""Sprint 3 Phase H — real-data acceptance gate.

Env-gated tests которые работают на реальном архиве из APPDATA. По умолчанию
запускаются если найден хотя бы один .duckdb файл в %APPDATA%/1c-optimyzer/duckdb,
иначе skip.

DoD criteria:
- #19: Top Business Operations < 3 sec на 12 GiB
- #20: Operation Anatomy < 3 sec
- #21: Deadlock Anatomy works на synthetic fixture (real-data — N/A,
        0 TDEADLOCK в текущем архиве, см. EXTRA_JSON_FIELD_STUDY.md)
- #22: Rule classifier матчит 3/3 синтетических deadlock типа
- #23: AI explainer integration (skipped без ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import duckdb
import pytest

from optimyzer_backend.explainer import ExplainerEngine
from optimyzer_backend.sql.anatomy import get_operation_anatomy
from optimyzer_backend.sql.views import ViewFilters, top_business_operations


def _appdata_duckdb_dir() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    d = Path(appdata) / "1c-optimyzer" / "duckdb"
    return d if d.is_dir() else None


def _find_largest_archive() -> tuple[Path, str] | None:
    d = _appdata_duckdb_dir()
    if d is None:
        return None
    files = sorted(d.glob("*.duckdb"), key=lambda f: f.stat().st_size, reverse=True)
    # Хотя бы 100 MB — иначе это тестовый stub
    files = [f for f in files if f.stat().st_size > 100 * 1024 * 1024]
    if not files:
        return None
    archive_id = files[0].stem  # имя файла без .duckdb = archive_id
    return files[0], archive_id


def _has_real_archive() -> bool:
    return _find_largest_archive() is not None


@pytest.fixture
def real_archive(monkeypatch: pytest.MonkeyPatch) -> str:
    info = _find_largest_archive()
    if info is None:
        pytest.skip("Реальный архив не найден в %APPDATA%/1c-optimyzer/duckdb")
    db_path, archive_id = info
    # SQLExecutor использует default_db_dir → подменяем на реальный APPDATA путь
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_path.parent
    )
    # Прогоняем Sprint 3 миграцию (context_normalized) если архив старый Sprint 2 ingest.
    # DuckDBStore.open() idempotent — на свежих архивах no-op.
    from optimyzer_backend.storage.duckdb_store import DuckDBStore

    store = DuckDBStore(archive_id, db_path=db_path)
    store.open()
    store.close()
    return archive_id


# ---------- DoD #19: Top Business Operations < 3 sec ----------


@pytest.mark.skipif(not _has_real_archive(), reason="Нужен реальный архив")
def test_top_business_operations_under_3_seconds(real_archive: str) -> None:
    start = time.monotonic()
    result = top_business_operations(real_archive, ViewFilters(), limit=100)
    elapsed = time.monotonic() - start
    assert elapsed < 3.0, f"Top Business Operations took {elapsed:.2f}s, expected <3s"
    assert result["row_count"] > 0, "Должны быть operations с context_normalized"


# ---------- DoD #20: Operation Anatomy < 3 sec ----------


@pytest.mark.skipif(not _has_real_archive(), reason="Нужен реальный архив")
def test_operation_anatomy_under_3_seconds(real_archive: str) -> None:
    # Сначала найдём самую популярную операцию
    top = top_business_operations(real_archive, ViewFilters(), limit=1)
    if top["row_count"] == 0:
        pytest.skip("В архиве нет operations с context_normalized")
    cols = [c["name"] for c in top["columns"]]
    op_col = cols.index("operation")
    operation = top["rows"][0][op_col]

    start = time.monotonic()
    result = get_operation_anatomy(real_archive, operation)
    elapsed = time.monotonic() - start
    assert elapsed < 3.0, f"Operation Anatomy took {elapsed:.2f}s, expected <3s"
    assert result["summary"]["found"] is True


# ---------- DoD #22: Rule classifier на 3 типах synthetic deadlocks ----------


def test_rule_classifier_matches_3_synthetic_deadlock_types() -> None:
    """Acceptance DoD #22 (адаптировано под synthetic — см. SPRINT_3_REPORT
    Phase D Validation Status). Real-data validation в OPUS_HANDOVER."""
    rules_dir = Path(__file__).resolve().parents[1] / "explainers"
    engine = ExplainerEngine(rules_dir)

    # Type 1 — lock escalation (1 region, 2+ participants)
    m1 = engine.classify(
        {"event_type": "TDEADLOCK", "regions_count": 1, "participants_count": 2},
        applies_to="deadlock",
    )
    # Type 2 — different order (2+ regions, 2+ participants)
    m2 = engine.classify(
        {"event_type": "TDEADLOCK", "regions_count": 2, "participants_count": 2},
        applies_to="deadlock",
    )
    # Type 3 — fallback single-resource
    m3 = engine.classify({"event_type": "TDEADLOCK"}, applies_to="deadlock")

    assert m1 is not None and m1.rule_id == "deadlock_lock_escalation"
    assert m2 is not None and m2.rule_id == "deadlock_different_order"
    assert m3 is not None and m3.rule_id == "deadlock_single_resource"


# ---------- DoD #21: Deadlock Anatomy works on synthetic fixture ----------


def test_deadlock_anatomy_works_on_synthetic_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Adapted DoD #21: synthetic fixture validation.
    Real-data validation in OPUS_HANDOVER follow-up."""
    from optimyzer_backend.sql.deadlock_anatomy import get_deadlock_anatomy, list_deadlocks
    from tests.fixtures.synthetic_tdeadlock_archive import (
        SYNTHETIC_ARCHIVE_ID,
        create_synthetic_tdeadlock_archive,
        deadlock_event_ids,
    )

    db_dir = tmp_path / "duckdb"
    db_dir.mkdir()
    create_synthetic_tdeadlock_archive(db_dir / f"{SYNTHETIC_ARCHIVE_ID}.duckdb")
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )

    listing = list_deadlocks(SYNTHETIC_ARCHIVE_ID)
    assert listing["row_count"] == 3

    for eid in deadlock_event_ids():
        anatomy = get_deadlock_anatomy(SYNTHETIC_ARCHIVE_ID, eid)
        assert anatomy["found"] is True
        assert len(anatomy["parsed_extra"]["regions"]) >= 1


# ---------- DoD #23: AI explainer (live, skipped без API key) ----------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Требует ANTHROPIC_API_KEY в env",
)
def test_ai_explainer_live_for_uncached_event(tmp_path: Path) -> None:
    from optimyzer_backend.explainer.cache import ExplainerCache, make_cache_key
    from optimyzer_backend.explainer.claude_client import ClaudeExplainerClient

    cache = ExplainerCache(tmp_path / "test_cache.db")
    client = ClaudeExplainerClient()
    assert client.enabled is True

    cache_key = make_cache_key("test-archive", "deadlock", "104")
    assert cache.get(cache_key) is None  # uncached

    start = time.monotonic()
    result = client.generate(
        anatomy_kind="deadlock",
        anatomy_data={
            "event_type": "TDEADLOCK",
            "regions": [{"object_name": "РегистрНакопления.Партии", "mode": "Exclusive"}],
            "participants": ["1001", "1002"],
        },
        rule_context=None,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 15.0, f"AI explainer took {elapsed:.1f}s, expected <15s"
    assert result.ok is True
    assert len(result.text) > 50

    cache.put(
        cache_key=cache_key,
        archive_id="test-archive",
        anatomy_kind="deadlock",
        target_id="104",
        rule_id=None,
        ai_text=result.text,
        model=result.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
    )
    assert cache.get(cache_key) is not None  # cached after first call
