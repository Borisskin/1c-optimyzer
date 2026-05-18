"""Тесты multi-archive comparison (Sprint 2 Phase G)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from optimyzer_backend.sql.comparison import compare_slow_queries, compare_summary


def _seed_archive(path: Path, events: list[tuple[Any, ...]]) -> None:
    conn = duckdb.connect(str(path))
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
    conn.executemany(
        "INSERT INTO events VALUES (" + ",".join(["?"] * 19) + ")", events
    )
    conn.close()


@pytest.fixture
def two_archives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    db_dir = tmp_path / "duckdb"
    db_dir.mkdir()
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )

    aid_a = "baseline"
    aid_b = "compared"

    # Baseline: 3 events, 1 query (fast), no deadlocks.
    a_events = [
        (1, aid_a, "2026-05-19 10:00:00", 1000, "CALL", None, None, None, None, "rphost", 1, None, None, None, None, None, None, "f", 1),
        (2, aid_a, "2026-05-19 10:00:01", 100_000, "DBMSSQL", None, None, None, None, "rphost", 1, "SELECT 1", "SELECT 1", "h1", 1, 0, None, "f", 2),
        (3, aid_a, "2026-05-19 10:00:02", 50, "EXCP", None, None, None, None, "rphost", 1, None, None, None, None, None, "{}", "f", 3),
    ]
    # Compared: 5 events, same query но в 4x медленнее (regression), +new deadlocks, +new query.
    b_events = [
        (1, aid_b, "2026-05-19 10:00:00", 1500, "CALL", None, None, None, None, "rphost", 1, None, None, None, None, None, None, "f", 1),
        (2, aid_b, "2026-05-19 10:00:01", 400_000, "DBMSSQL", None, None, None, None, "rphost", 1, "SELECT 1", "SELECT 1", "h1", 1, 0, None, "f", 2),
        (3, aid_b, "2026-05-19 10:00:02", 50, "EXCP", None, None, None, None, "rphost", 1, None, None, None, None, None, "{}", "f", 3),
        (4, aid_b, "2026-05-19 10:00:03", 800_000, "DBMSSQL", None, None, None, None, "rphost", 1, "SELECT 2", "SELECT 2", "h2", 1, 0, None, "f", 4),
        (5, aid_b, "2026-05-19 10:00:04", 90_000_000, "TDEADLOCK", None, None, None, None, "rphost", 1, None, None, None, None, None, "{}", "f", 5),
    ]
    _seed_archive(db_dir / f"{aid_a}.duckdb", a_events)
    _seed_archive(db_dir / f"{aid_b}.duckdb", b_events)
    return aid_a, aid_b


def test_compare_summary_reports_events_delta(two_archives: tuple[str, str]) -> None:
    a, b = two_archives
    result = compare_summary(a, b)
    metrics = {m["key"]: m for m in result["metrics"]}
    assert metrics["events_count"]["a"] == 3
    assert metrics["events_count"]["b"] == 5
    assert metrics["events_count"]["delta"] == 2
    assert metrics["events_count"]["delta_percent"] is not None


def test_compare_summary_detects_new_deadlocks(two_archives: tuple[str, str]) -> None:
    a, b = two_archives
    result = compare_summary(a, b)
    deadlocks = next(m for m in result["metrics"] if m["key"] == "deadlocks")
    assert deadlocks["a"] == 0
    assert deadlocks["b"] == 1


def test_compare_summary_delta_percent_when_baseline_zero(
    two_archives: tuple[str, str],
) -> None:
    a, b = two_archives
    result = compare_summary(a, b)
    deadlocks = next(m for m in result["metrics"] if m["key"] == "deadlocks")
    # baseline=0 → delta_percent должен быть None (защита от div by 0)
    assert deadlocks["delta_percent"] is None


def test_compare_slow_queries_finds_regression(two_archives: tuple[str, str]) -> None:
    a, b = two_archives
    result = compare_slow_queries(a, b)
    # h1 встречается в обоих, avg вырос с 100ms до 400ms (+300%) → regression
    regressions = result["regressed"]
    assert any(r["sql_text_hash"] == "h1" for r in regressions)


def test_compare_slow_queries_reports_new_queries(two_archives: tuple[str, str]) -> None:
    a, b = two_archives
    result = compare_slow_queries(a, b)
    only_b_hashes = {r["sql_text_hash"] for r in result["only_b"]}
    # h2 — новый запрос в compared, не было в baseline
    assert "h2" in only_b_hashes
