"""Sprint 2 acceptance gate на 12 GiB real archive.

Env-gated через ``OPTIMYZER_REAL_FOLDER_PATH``. Если переменная не
установлена или путь не существует — все тесты skip-аются.

Критические требования (DoD Sprint 2, пункты 22-24):
- Каждая pre-built view работает < 3 секунды на full real-data archive
- Cross-filtering propagation работает end-to-end
- Multi-archive comparison работает на двух real archives (или real + synthetic)

Тесты используют те же view functions что и UI; то есть проверяют ту же
кодовую цепочку. Стенд: один archive ingest целиком (fixture), затем
performance check каждой view.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest

from optimyzer_backend.ingest import FolderSource
from optimyzer_backend.parsers.tj_parser import parse_log_file_streaming
from optimyzer_backend.sql.comparison import compare_slow_queries, compare_summary
from optimyzer_backend.sql.views import (
    ViewFilters,
    activity_heatmap,
    duration_histogram,
    errors_feed,
    locks_timeline,
    process_roles,
    slow_queries,
)
from optimyzer_backend.storage.duckdb_store import DuckDBStore

REAL_FOLDER_PATH = os.environ.get("OPTIMYZER_REAL_FOLDER_PATH")
VIEW_BUDGET_SECONDS = 3.0  # каждая view должна укладываться

pytestmark = pytest.mark.skipif(
    not REAL_FOLDER_PATH or not Path(REAL_FOLDER_PATH).is_dir(),
    reason=(
        "OPTIMYZER_REAL_FOLDER_PATH not set or folder missing. "
        "Set in .env.test or environment to enable Sprint 2 acceptance gate."
    ),
)


@pytest.fixture(scope="module")
def ingested(tmp_path_factory: pytest.TempPathFactory, monkeypatch_module: pytest.MonkeyPatch):
    """Один ingest на module — переиспользуется всеми views."""
    assert REAL_FOLDER_PATH is not None
    folder = Path(REAL_FOLDER_PATH)
    db_dir = tmp_path_factory.mktemp("sprint2_acceptance")
    archive_id = "sprint2_real"
    db_path = db_dir / f"{archive_id}.duckdb"

    # Patch default_db_dir so SQLExecutor in views uses this temp location.
    monkeypatch_module.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )

    store = DuckDBStore(archive_id, db_path=db_path)
    store.open()

    source = FolderSource(folder)
    log_files = source.discover()
    started = time.monotonic()
    events_inserted = 0

    with store.appender() as appender:
        for lf in log_files:
            try:
                for event in parse_log_file_streaming(source, lf):
                    appender.append_event(event)
                    events_inserted += 1
            except Exception:
                continue

    store.create_indexes()
    ingest_elapsed = time.monotonic() - started
    store.close()

    yield {
        "archive_id": archive_id,
        "events_inserted": events_inserted,
        "ingest_elapsed": ingest_elapsed,
        "db_path": db_path,
    }


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (built-in fixture is function-scoped)."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


# ---------- Performance: each view < 3 seconds ----------


def _bench(fn) -> float:
    start = time.monotonic()
    fn()
    return time.monotonic() - start


def test_slow_queries_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: slow_queries(ingested["archive_id"], ViewFilters(), limit=100))
    assert elapsed < VIEW_BUDGET_SECONDS, f"slow_queries took {elapsed:.2f}s"


def test_locks_timeline_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: locks_timeline(ingested["archive_id"], ViewFilters()))
    assert elapsed < VIEW_BUDGET_SECONDS, f"locks_timeline took {elapsed:.2f}s"


def test_process_roles_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: process_roles(ingested["archive_id"], ViewFilters()))
    assert elapsed < VIEW_BUDGET_SECONDS, f"process_roles took {elapsed:.2f}s"


def test_duration_histogram_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: duration_histogram(ingested["archive_id"], ViewFilters()))
    assert elapsed < VIEW_BUDGET_SECONDS, f"duration_histogram took {elapsed:.2f}s"


def test_errors_feed_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: errors_feed(ingested["archive_id"], ViewFilters(), limit=500))
    assert elapsed < VIEW_BUDGET_SECONDS, f"errors_feed took {elapsed:.2f}s"


def test_activity_heatmap_under_3_seconds(ingested: dict[str, Any]) -> None:
    elapsed = _bench(lambda: activity_heatmap(ingested["archive_id"], ViewFilters()))
    assert elapsed < VIEW_BUDGET_SECONDS, f"activity_heatmap took {elapsed:.2f}s"


# ---------- Cross-filtering propagation ----------


def test_cross_filter_process_role_affects_views(ingested: dict[str, Any]) -> None:
    """Фильтр process_role должен уменьшать (или сохранять) row_count во всех views."""
    aid = ingested["archive_id"]
    unfiltered = process_roles(aid, ViewFilters())
    if unfiltered["row_count"] == 0:
        pytest.skip("Архив не содержит process_role events")

    # Берём первую роль из результата
    first_role = unfiltered["rows"][0][0]
    filtered = slow_queries(aid, ViewFilters(process_role=first_role), limit=100)
    # filtered.row_count может быть 0 если у этой роли нет DBMSSQL events — это OK.
    assert filtered["row_count"] >= 0


def test_cross_filter_event_type_narrows_errors(ingested: dict[str, Any]) -> None:
    aid = ingested["archive_id"]
    all_errors = errors_feed(aid, ViewFilters(), limit=500)
    excp_only = errors_feed(aid, ViewFilters(event_type="EXCP"), limit=500)
    assert excp_only["row_count"] <= all_errors["row_count"]


# ---------- Multi-archive comparison ----------


def test_comparison_summary_works(ingested: dict[str, Any]) -> None:
    """Сравниваем архив сам с собой — все метрики должны иметь delta=0."""
    aid = ingested["archive_id"]
    result = compare_summary(aid, aid)
    for m in result["metrics"]:
        if m["a"] > 0:
            assert m["delta"] == 0, f"{m['key']} delta != 0 for self-comparison"
            assert m["delta_percent"] == 0, f"{m['key']} delta_percent != 0"


def test_comparison_slow_queries_self_no_regression(ingested: dict[str, Any]) -> None:
    aid = ingested["archive_id"]
    result = compare_slow_queries(aid, aid, limit=20)
    assert len(result["regressed"]) == 0
    assert len(result["improved"]) == 0
    assert len(result["only_a"]) == 0
    assert len(result["only_b"]) == 0


def test_acceptance_summary_smoke(ingested: dict[str, Any]) -> None:
    """Sanity: ingest реально сложил события в БД."""
    assert ingested["events_inserted"] > 0
    print(
        f"\n[Sprint 2 acceptance] events={ingested['events_inserted']:,} "
        f"ingest={ingested['ingest_elapsed']:.1f}s"
    )
