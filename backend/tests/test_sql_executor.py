"""Тесты SQL Executor (Sprint 2 Phase B)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from optimyzer_backend.sql.executor import SQLExecutionError, SQLExecutor


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    """Создаёт DuckDB с минимальной events таблицей для query тестов."""
    db_path = tmp_path / "test_archive.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE events (
            id BIGINT,
            archive_id VARCHAR,
            ts TIMESTAMP,
            duration_us BIGINT,
            event_type VARCHAR,
            process_role VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO events VALUES
            (1, 'a', '2026-05-19 10:00:00', 1000, 'CALL', 'rphost'),
            (2, 'a', '2026-05-19 10:00:01', 5000, 'DBMSSQL', 'rphost'),
            (3, 'a', '2026-05-19 10:00:02', 100, 'EXCP', 'rmngr'),
            (4, 'a', '2026-05-19 10:00:03', 50000, 'TDEADLOCK', 'rphost')
        """
    )
    conn.close()
    return db_path


def test_basic_select(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT id, event_type FROM events ORDER BY id")
    assert result["row_count"] == 4
    assert result["truncated"] is False
    assert [c["name"] for c in result["columns"]] == ["id", "event_type"]
    assert result["rows"][0] == [1, "CALL"]


def test_aggregation(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute(
            "SELECT process_role, COUNT(*) AS cnt FROM events GROUP BY process_role ORDER BY cnt DESC"
        )
    assert result["row_count"] == 2
    # rphost=3, rmngr=1
    assert result["rows"][0] == ["rphost", 3]
    assert result["rows"][1] == ["rmngr", 1]


def test_truncation_signaled(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT * FROM events", max_rows=2)
    assert result["row_count"] == 2
    assert result["truncated"] is True


def test_timestamp_serialized_as_iso(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT ts FROM events ORDER BY id LIMIT 1")
    ts_val = result["rows"][0][0]
    assert isinstance(ts_val, str)
    assert ts_val.startswith("2026-05-19")


def test_missing_db_raises(tmp_path: Path) -> None:
    with pytest.raises(SQLExecutionError):
        with SQLExecutor("missing", db_path=tmp_path / "nope.duckdb") as ex:
            ex.execute("SELECT 1")


def test_syntax_error_raises(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        with pytest.raises(SQLExecutionError):
            ex.execute("SELECT FROM WHERE")  # garbage


def test_read_only_blocks_writes(seeded_db: Path) -> None:
    """Даже если validator пропустит запись — read-only connection отклонит."""
    with SQLExecutor("test", db_path=seeded_db) as ex:
        with pytest.raises(SQLExecutionError):
            # NB: проходим напрямую в executor, минуя validator
            ex.execute("INSERT INTO events VALUES (99, 'x', NOW(), 1, 'X', 'rphost')")


def test_columns_and_row_count_match(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT id FROM events WHERE event_type = 'EXCP'")
    assert result["row_count"] == len(result["rows"])
    assert result["row_count"] == 1


def test_empty_result(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT * FROM events WHERE event_type = 'NONEXISTENT'")
    assert result["row_count"] == 0
    assert result["truncated"] is False
    assert result["rows"] == []


def test_executed_ms_set(seeded_db: Path) -> None:
    with SQLExecutor("test", db_path=seeded_db) as ex:
        result = ex.execute("SELECT 1")
    assert isinstance(result["executed_ms"], float)
    assert result["executed_ms"] >= 0
