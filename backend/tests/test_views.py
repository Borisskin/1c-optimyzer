"""Тесты pre-built views (Sprint 2 Phase D).

Используют seeded DuckDB + monkey-patch _ARCHIVES чтобы view functions
работали без полного ingest pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from optimyzer_backend.sql.views import (
    ViewFilters,
    activity_heatmap,
    duration_histogram,
    errors_feed,
    locks_timeline,
    process_roles,
    slow_queries,
    top_business_operations,
)
from optimyzer_backend.storage.duckdb_store import default_db_dir


@pytest.fixture
def seeded_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Создаёт events.duckdb в tmp dir и подменяет default_db_dir.

    Yields archive_id, который view functions используют для построения пути.
    """
    archive_id = "test_views"
    db_dir = tmp_path / "duckdb"
    db_dir.mkdir()
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )
    # views.py использует executor через SQLExecutor → его default_db_dir
    # уже замокан. Schema introspection использует свою копию — для тестов
    # не нужно.

    db_path = db_dir / f"{archive_id}.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE events (
            id BIGINT,
            archive_id VARCHAR,
            ts TIMESTAMP,
            duration_us BIGINT,
            event_type VARCHAR,
            session_id INTEGER,
            user_name VARCHAR,
            context VARCHAR,
            context_normalized VARCHAR,
            process VARCHAR,
            process_role VARCHAR,
            process_pid INTEGER,
            sql_text TEXT,
            sql_text_normalized TEXT,
            sql_text_hash VARCHAR(32),
            rows_read BIGINT,
            rows_modified BIGINT,
            extra JSON,
            source_file VARCHAR,
            source_line_start INTEGER
        )
        """
    )
    # Seeds: 10 events distributed across types/roles/timestamps.
    # context_normalized — Phase A normalization (Sprint 3) — для top_business_operations.
    # ctxA → "Документ.Реализация.МодульОбъекта" (популярная операция, 5 events)
    # ctxB → "Документ.Поступление.МодульОбъекта" (2 events, deadlock+lock)
    # ctxC → "Отчёт.OSV.МодульМенеджера" (1 EXCP)
    # ctxD → "ВнешняяОбработка.Test.Форма.Форма" (1 DBMSSQL)
    rows: list[tuple[Any, ...]] = [
        # id, archive_id, ts, duration_us, event_type, session_id, user_name,
        # context, context_normalized, process, process_role, process_pid, sql_text,
        # sql_text_normalized, sql_text_hash, rows_read, rows_modified, extra,
        # source_file, source_line_start
        (1, archive_id, "2026-05-19 10:00:00", 500, "CALL", 1, "u1", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1000, None, None, None, None, None, None, "f", 1),
        (2, archive_id, "2026-05-19 10:00:01", 1_500_000, "DBMSSQL", 1, "u1", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1000, "SELECT 1", "SELECT 1", "h1", 10, 0, None, "f", 2),
        (3, archive_id, "2026-05-19 10:00:02", 200_000, "DBMSSQL", 1, "u1", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1000, "SELECT 1", "SELECT 1", "h1", 5, 0, None, "f", 3),
        (4, archive_id, "2026-05-19 11:00:00", 50_000_000, "TDEADLOCK", 2, "u2", "ctxB", "Документ.Поступление.МодульОбъекта", "p", "rphost", 1001, None, None, None, None, None, None, "f", 4),
        (5, archive_id, "2026-05-19 11:00:30", 800_000, "TLOCK", 2, "u2", "ctxB", "Документ.Поступление.МодульОбъекта", "p", "rphost", 1001, None, None, None, None, None, None, "f", 5),
        (6, archive_id, "2026-05-19 12:00:00", 50, "EXCP", 3, "u3", "ctxC", "Отчёт.OSV.МодульМенеджера", "p", "rmngr", 2000, None, None, None, None, None, "{\"e\":1}", "f", 6),
        (7, archive_id, "2026-05-19 14:30:00", 70_000_000, "DBMSSQL", 4, "u4", "ctxD", "ВнешняяОбработка.Test.Форма.Форма", "p", "rphost", 1002, "SELECT 2", "SELECT 2", "h2", 100, 0, None, "f", 7),
        (8, archive_id, "2026-05-20 09:00:00", 1_000, "CALL", 5, "u5", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1003, None, None, None, None, None, None, "f", 8),
        (9, archive_id, "2026-05-20 09:00:01", 30_000, "CALL", 5, "u5", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1003, None, None, None, None, None, None, "f", 9),
        (10, archive_id, "2026-05-20 09:00:02", 5_000, "EXCP", 5, "u5", "ctxA", "Документ.Реализация.МодульОбъекта", "p", "rphost", 1003, None, None, None, None, None, "{\"e\":2}", "f", 10),
    ]
    conn.executemany(
        "INSERT INTO events VALUES (" + ",".join(["?"] * 20) + ")", rows
    )
    conn.close()
    return archive_id


def test_slow_queries_returns_aggregated(seeded_archive: str) -> None:
    result = slow_queries(seeded_archive, ViewFilters(), limit=10)
    # 2 unique sql_text_hash (h1, h2) — DBMSSQL events
    assert result["row_count"] == 2
    # h1 имеет 2 calls (1_500_000 + 200_000), h2 — 1 call (70_000_000).
    # Sort by total_duration: h2 first.
    columns = [c["name"] for c in result["columns"]]
    sql_hash_col = columns.index("sql_text_hash")
    assert result["rows"][0][sql_hash_col] == "h2"


def test_slow_queries_respects_process_role_filter(seeded_archive: str) -> None:
    result = slow_queries(
        seeded_archive, ViewFilters(process_role="rmngr"), limit=10
    )
    # rmngr не имеет DBMSSQL events
    assert result["row_count"] == 0


def test_locks_timeline_buckets_correctly(seeded_archive: str) -> None:
    result = locks_timeline(seeded_archive, ViewFilters())
    # 2 lock-events (TDEADLOCK + TLOCK), оба в 11:xx → 1 bucket (hour)
    assert result["row_count"] >= 1


def test_process_roles_distribution(seeded_archive: str) -> None:
    result = process_roles(seeded_archive, ViewFilters())
    rows = result["rows"]
    # 2 roles: rphost (9 events), rmngr (1 event)
    assert result["row_count"] == 2
    columns = [c["name"] for c in result["columns"]]
    role_col = columns.index("process_role")
    count_col = columns.index("events_count")
    role_to_count = {row[role_col]: row[count_col] for row in rows}
    assert role_to_count["rphost"] == 9
    assert role_to_count["rmngr"] == 1


def test_duration_histogram_returns_fixed_order(seeded_archive: str) -> None:
    result = duration_histogram(seeded_archive, ViewFilters())
    labels = [row[0] for row in result["rows"]]
    assert labels == [
        "< 1 мс",
        "1-10 мс",
        "10-100 мс",
        "100 мс - 1 с",
        "1-10 с",
        "10-60 с",
        "> 60 с",
    ]
    # Total = 9 events with duration_us NOT NULL (event 6 has 50, event 4 has 50M).
    total = sum(row[1] for row in result["rows"])
    assert total == 10  # all 10 events have non-null duration_us


def test_errors_feed_only_errors(seeded_archive: str) -> None:
    result = errors_feed(seeded_archive, ViewFilters())
    # EXCP × 2, TDEADLOCK × 1, TLOCK × 1 = 4 events
    assert result["row_count"] == 4
    columns = [c["name"] for c in result["columns"]]
    type_col = columns.index("event_type")
    types = {row[type_col] for row in result["rows"]}
    assert types == {"EXCP", "TDEADLOCK", "TLOCK"}
    # total_rows совпадает с row_count, когда выборка не упирается в limit
    assert result["total_rows"] == 4


def test_errors_feed_total_rows_when_limited(seeded_archive: str) -> None:
    """limit=2 при 4 событиях → row_count=2, total_rows=4."""
    result = errors_feed(seeded_archive, ViewFilters(), limit=2)
    assert result["row_count"] == 2
    assert result["total_rows"] == 4


def test_slow_queries_returns_total_rows(seeded_archive: str) -> None:
    result = slow_queries(seeded_archive, ViewFilters())
    assert "total_rows" in result
    assert result["total_rows"] == result["row_count"]


def test_top_business_operations_returns_total_rows(seeded_archive: str) -> None:
    result = top_business_operations(seeded_archive, ViewFilters())
    assert "total_rows" in result
    assert result["total_rows"] == result["row_count"]


def test_activity_heatmap_groups_by_hour_and_dow(seeded_archive: str) -> None:
    result = activity_heatmap(seeded_archive, ViewFilters())
    # Events spread across 2 days (2026-05-19 = Tuesday, 2026-05-20 = Wednesday).
    # Each event contributes to one (dow, hour) cell.
    assert result["row_count"] >= 4


def test_activity_heatmap_metric_total_duration(seeded_archive: str) -> None:
    result = activity_heatmap(seeded_archive, ViewFilters(), metric="total_duration_ms")
    columns = [c["name"] for c in result["columns"]]
    value_col = columns.index("value")
    assert all(isinstance(row[value_col], (int, float)) for row in result["rows"])


# ---------- Sprint 3 / Phase B — Top Business Operations ----------


def test_top_business_operations_groups_by_normalized_context(seeded_archive: str) -> None:
    result = top_business_operations(seeded_archive, ViewFilters(), limit=10)
    # 4 distinct context_normalized values → 4 rows
    assert result["row_count"] == 4
    columns = [c["name"] for c in result["columns"]]
    op_col = columns.index("operation")
    calls_col = columns.index("calls")
    operations = {row[op_col]: row[calls_col] for row in result["rows"]}
    # Документ.Реализация — 6 events (CALL×3 + DBMSSQL×2 + EXCP×1)
    assert operations["Документ.Реализация.МодульОбъекта"] == 6
    # Документ.Поступление — 2 events (TDEADLOCK + TLOCK)
    assert operations["Документ.Поступление.МодульОбъекта"] == 2


def test_top_business_operations_sql_duration_breakdown(seeded_archive: str) -> None:
    """sql_duration_ms должен суммировать только DBMSSQL events внутри операции."""
    result = top_business_operations(seeded_archive, ViewFilters(), limit=10)
    columns = [c["name"] for c in result["columns"]]
    op_col = columns.index("operation")
    sql_col = columns.index("sql_duration_ms")
    operations = {row[op_col]: row[sql_col] for row in result["rows"]}
    # Документ.Реализация имеет DBMSSQL: 1_500_000 + 200_000 = 1_700_000 us = 1700 ms
    assert operations["Документ.Реализация.МодульОбъекта"] == pytest.approx(1700, abs=1)
    # Документ.Поступление имеет 0 DBMSSQL (только locks)
    assert operations["Документ.Поступление.МодульОбъекта"] == pytest.approx(0, abs=1)


def test_top_business_operations_lock_and_exception_counters(seeded_archive: str) -> None:
    result = top_business_operations(seeded_archive, ViewFilters(), limit=10)
    columns = [c["name"] for c in result["columns"]]
    op_col = columns.index("operation")
    lock_col = columns.index("lock_events")
    exc_col = columns.index("exception_events")
    by_op = {row[op_col]: (row[lock_col], row[exc_col]) for row in result["rows"]}
    # Документ.Поступление — 2 lock events (TLOCK + TDEADLOCK), 0 EXCP
    assert by_op["Документ.Поступление.МодульОбъекта"] == (2, 0)
    # Документ.Реализация — 0 locks, 1 EXCP (event id=10)
    assert by_op["Документ.Реализация.МодульОбъекта"] == (0, 1)
    # Отчёт.OSV — 0 locks, 1 EXCP
    assert by_op["Отчёт.OSV.МодульМенеджера"] == (0, 1)


def test_top_business_operations_sort_by_calls(seeded_archive: str) -> None:
    result = top_business_operations(seeded_archive, ViewFilters(), sort_by="calls", limit=10)
    columns = [c["name"] for c in result["columns"]]
    calls_col = columns.index("calls")
    counts = [row[calls_col] for row in result["rows"]]
    # Сортировка DESC: 6, 2, 1, 1 (последние 2 в любом порядке)
    assert counts[0] == 6
    assert counts[1] == 2


def test_top_business_operations_respects_role_filter(seeded_archive: str) -> None:
    result = top_business_operations(
        seeded_archive, ViewFilters(process_role="rmngr"), limit=10
    )
    # rmngr только у event 6 (Отчёт.OSV) → 1 операция
    assert result["row_count"] == 1
    columns = [c["name"] for c in result["columns"]]
    op_col = columns.index("operation")
    assert result["rows"][0][op_col] == "Отчёт.OSV.МодульМенеджера"


