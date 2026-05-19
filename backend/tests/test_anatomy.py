"""Sprint 3 Phase C — Operation / Session Anatomy backend tests.

Использует тот же seeded_archive fixture, что и test_views.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from optimyzer_backend.sql.anatomy import get_operation_anatomy, get_session_anatomy


@pytest.fixture
def seeded_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    archive_id = "test_anatomy"
    db_dir = tmp_path / "duckdb"
    db_dir.mkdir()
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )
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
    op_real = "Документ.Реализация.МодульОбъекта"
    op_other = "Отчёт.OSV.МодульМенеджера"
    rows: list[tuple[Any, ...]] = [
        # session 100 — много событий в op_real
        (1, archive_id, "2026-05-19 10:00:00", 500, "CALL", 100, "u1", "ctxA", op_real, "p", "rphost", 1000, None, None, None, None, None, None, "f", 1),
        (2, archive_id, "2026-05-19 10:00:01", 1_500_000, "DBMSSQL", 100, "u1", "ctxA", op_real, "p", "rphost", 1000, "SELECT * FROM X WHERE id=1", "SELECT * FROM X WHERE id=?", "h1", 10, 0, None, "f", 2),
        (3, archive_id, "2026-05-19 10:00:02", 200_000, "DBMSSQL", 100, "u1", "ctxA", op_real, "p", "rphost", 1000, "SELECT * FROM X WHERE id=2", "SELECT * FROM X WHERE id=?", "h1", 5, 0, None, "f", 3),
        (4, archive_id, "2026-05-19 10:00:03", 50, "EXCP", 100, "u1", "ctxA", op_real, "p", "rphost", 1000, None, None, None, None, None, '{"Descr":"NULL pointer"}', "f", 4),
        # session 200 — другая операция
        (5, archive_id, "2026-05-19 11:00:00", 800_000, "TLOCK", 200, "u2", "ctxB", "Документ.Поступление.МодульОбъекта", "p", "rphost", 1001, None, None, None, None, None, None, "f", 5),
        # session 300 — op_other (rmngr)
        (6, archive_id, "2026-05-19 12:00:00", 70_000_000, "DBMSSQL", 300, "u3", "ctxC", op_other, "p", "rmngr", 2000, "SELECT * FROM Y", "SELECT * FROM Y", "h2", 100, 0, None, "f", 6),
    ]
    conn.executemany(
        "INSERT INTO events VALUES (" + ",".join(["?"] * 20) + ")", rows
    )
    conn.close()
    return archive_id


# ---------- get_operation_anatomy ----------


def test_operation_anatomy_summary_metrics(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "Документ.Реализация.МодульОбъекта")
    s = result["summary"]
    assert s["found"] is True
    assert s["total_events"] == 4
    assert s["sql_count"] == 2
    assert s["exception_count"] == 1
    assert s["lock_count"] == 0
    assert s["unique_sessions"] == 1


def test_operation_anatomy_unknown_operation(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "НесуществующаяОперация")
    assert result["summary"]["found"] is False
    assert result["timeline"]["row_count"] == 0
    assert result["breakdown"] == []
    assert result["top_sql"]["row_count"] == 0


def test_operation_anatomy_breakdown_by_event_type(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "Документ.Реализация.МодульОбъекта")
    types = {row["event_type"]: row for row in result["breakdown"]}
    assert "CALL" in types
    assert "DBMSSQL" in types
    assert "EXCP" in types
    assert types["DBMSSQL"]["events"] == 2
    assert types["CALL"]["events"] == 1


def test_operation_anatomy_top_sql_aggregates_by_hash(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "Документ.Реализация.МодульОбъекта")
    sql_result = result["top_sql"]
    assert sql_result["row_count"] == 1  # 2 DBMSSQL events с одинаковым sql_text_hash 'h1'
    cols = [c["name"] for c in sql_result["columns"]]
    calls_col = cols.index("calls")
    assert sql_result["rows"][0][calls_col] == 2


def test_operation_anatomy_related_exceptions(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "Документ.Реализация.МодульОбъекта")
    exc = result["related_exceptions"]
    assert exc["row_count"] == 1
    cols = [c["name"] for c in exc["columns"]]
    extra_col = cols.index("extra")
    # extra хранится как JSON; DuckDB возвращает строку или dict
    assert "Descr" in str(exc["rows"][0][extra_col])


def test_operation_anatomy_timeline_descending(seeded_archive: str) -> None:
    result = get_operation_anatomy(seeded_archive, "Документ.Реализация.МодульОбъекта")
    tl = result["timeline"]
    assert tl["row_count"] == 4
    cols = [c["name"] for c in tl["columns"]]
    ts_col = cols.index("ts")
    timestamps = [row[ts_col] for row in tl["rows"]]
    # DESC ordering
    assert timestamps == sorted(timestamps, reverse=True)


# ---------- get_session_anatomy ----------


def test_session_anatomy_summary(seeded_archive: str) -> None:
    result = get_session_anatomy(seeded_archive, 100)
    s = result["summary"]
    assert s["found"] is True
    assert s["total_events"] == 4
    assert s["distinct_operations"] == 1
    assert s["sql_count"] == 2
    assert s["exception_count"] == 1


def test_session_anatomy_unknown_session(seeded_archive: str) -> None:
    result = get_session_anatomy(seeded_archive, 999)
    assert result["summary"]["found"] is False
    assert result["timeline"]["row_count"] == 0


def test_session_anatomy_timeline_ascending(seeded_archive: str) -> None:
    result = get_session_anatomy(seeded_archive, 100)
    tl = result["timeline"]
    cols = [c["name"] for c in tl["columns"]]
    ts_col = cols.index("ts")
    timestamps = [row[ts_col] for row in tl["rows"]]
    # ASC ordering (session anatomy показывает события по времени вперёд)
    assert timestamps == sorted(timestamps)
