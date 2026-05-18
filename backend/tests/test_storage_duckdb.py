"""Тесты для DuckDBStore: schema, bulk insert, preset queries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from optimyzer_backend.parsers.tj_parser import ParsedEvent
from optimyzer_backend.storage.duckdb_store import DuckDBStore


@pytest.fixture
def store(tmp_path: Path) -> DuckDBStore:
    s = DuckDBStore("test-archive", db_path=tmp_path / "test.duckdb")
    s.open()
    yield s
    s.close()


def _ev(et: str, ts: datetime, dur: int | None = 1000, sql: str | None = None) -> ParsedEvent:
    return ParsedEvent(
        ts=ts,
        duration_us=dur,
        event_type=et,
        level=3,
        sql_text=sql,
    )


def test_schema_created(store: DuckDBStore):
    rows = store.open().execute("SELECT COUNT(*) FROM events").fetchone()
    assert rows[0] == 0


def test_bulk_insert_and_count(store: DuckDBStore):
    events = [
        _ev("CALL", datetime(2026, 5, 17, 18, 0, 0), 500),
        _ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 1), 2000, sql="SELECT 1"),
        _ev("TDEADLOCK", datetime(2026, 5, 17, 18, 0, 2), 0),
    ]
    written = store.bulk_insert(events, start_id=1)
    assert written == 3
    assert store.count_events() == 3


def test_preset_first_100(store: DuckDBStore):
    events = [_ev("CALL", datetime(2026, 5, 17, 18, 0, i), i * 100) for i in range(5)]
    store.bulk_insert(events, start_id=1)
    cols, rows = store.run_preset("first_100", limit=100)
    assert len(rows) == 5
    col_names = [c[0] for c in cols]
    assert "event_type" in col_names
    assert "ts" in col_names


def test_preset_longest(store: DuckDBStore):
    events = [_ev("CALL", datetime(2026, 5, 17, 18, 0, i), i * 1000) for i in range(5)]
    store.bulk_insert(events, start_id=1)
    _, rows = store.run_preset("longest", limit=3)
    durations = [r[2] for r in rows]
    assert durations == sorted(durations, reverse=True)
    assert len(rows) == 3


def test_preset_deadlocks_only(store: DuckDBStore):
    events = [
        _ev("CALL", datetime(2026, 5, 17, 18, 0, 0)),
        _ev("TDEADLOCK", datetime(2026, 5, 17, 18, 0, 1)),
        _ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 2)),
        _ev("TDEADLOCK", datetime(2026, 5, 17, 18, 0, 3)),
    ]
    store.bulk_insert(events, start_id=1)
    _, rows = store.run_preset("deadlocks", limit=100)
    assert len(rows) == 2


def test_preset_unknown_raises(store: DuckDBStore):
    with pytest.raises(ValueError):
        store.run_preset("nonsense")


def test_indexes_created(store: DuckDBStore):
    """create_indexes не должен падать на пустой таблице."""
    store.create_indexes()
    # idempotent
    store.create_indexes()
