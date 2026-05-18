"""Тесты DuckDB Appender API (Sprint 1 — ADR-011)."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pytest

from optimyzer_backend.parsers.tj_parser import ParsedEvent
from optimyzer_backend.storage.duckdb_store import DuckDBStore


def _ev(et: str, ts: datetime, dur: int | None = 1000, role: str = "rphost", pid: int = 1234) -> ParsedEvent:
    return ParsedEvent(
        ts=ts,
        duration_us=dur,
        event_type=et,
        level=3,
        process_role=role,
        process_pid=pid,
    )


@pytest.fixture
def store(tmp_path: Path):
    s = DuckDBStore("test-archive", db_path=tmp_path / "test.duckdb")
    s.open()
    yield s
    s.close()


def test_appender_inserts_single_event(store: DuckDBStore) -> None:
    ev = _ev("CALL", datetime(2026, 5, 17, 18, 0, 0))
    with store.appender() as ap:
        ap.append_event(ev)
    assert store.count_events() == 1


def test_appender_inserts_many(store: DuckDBStore) -> None:
    events = [_ev("CALL", datetime(2026, 5, 17, 18, 0, i % 60), i * 10) for i in range(1000)]
    with store.appender() as ap:
        appended = ap.append_many(events)
    assert appended == 1000
    assert store.count_events() == 1000


def test_appender_tracks_next_id(store: DuckDBStore) -> None:
    with store.appender(start_id=42) as ap:
        ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 0)))
        ap.append_event(_ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 1)))
        assert ap.next_id == 44
        assert ap.rows_appended == 2


def test_appender_process_role_persisted(store: DuckDBStore) -> None:
    with store.appender() as ap:
        ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 0), role="rphost", pid=28220))
        ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 1), role="rmngr", pid=24128))
        ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 2), role="1cv8c", pid=12044))

    conn = store.open()
    rows = conn.execute(
        "SELECT process_role, process_pid FROM events ORDER BY id"
    ).fetchall()
    assert rows == [("rphost", 28220), ("rmngr", 24128), ("1cv8c", 12044)]


def test_appender_indexes_after_bulk(store: DuckDBStore) -> None:
    """Стандартный flow: bulk append → create_indexes()."""
    events = [_ev("CALL", datetime(2026, 5, 17, 18, 0, i % 60)) for i in range(5000)]
    with store.appender() as ap:
        ap.append_many(events)
    store.create_indexes()
    assert store.count_events() == 5000

    # Index on process_role доступен
    conn = store.open()
    result = conn.execute(
        "SELECT COUNT(*) FROM events WHERE archive_id = ? AND process_role = ?",
        [store.archive_id, "rphost"],
    ).fetchone()
    assert result[0] == 5000


def test_appender_performance_10k_under_5s(store: DuckDBStore) -> None:
    """Sanity: 10K events через Appender быстрее 5 секунд.

    Real benchmark — Phase J acceptance gate на 12 GiB корпусе. Здесь только
    проверяем что bulk-insert не O(N²) и без exceptions на тысячах строк.
    """
    events = [
        _ev(
            "CALL" if i % 3 else "DBMSSQL",
            datetime(2026, 5, 17, 18, (i // 60) % 60, i % 60),
            dur=(i % 1000) * 100,
        )
        for i in range(10_000)
    ]
    start = time.monotonic()
    with store.appender() as ap:
        ap.append_many(events)
    elapsed = time.monotonic() - start
    assert store.count_events() == 10_000
    assert elapsed < 5.0, f"Appender took {elapsed:.2f}s for 10K events (expected <5s)"


def test_appender_exception_discards_buffer(store: DuckDBStore) -> None:
    """При исключении внутри блока буфер сбрасывается БЕЗ записи в DB (partial state guard)."""
    with pytest.raises(RuntimeError):
        with store.appender() as ap:
            ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 0)))
            raise RuntimeError("simulated")
    # После исключения — таблица пустая, никаких partial inserts
    assert store.count_events() == 0
    # Можно запустить ingest снова с тем же start_id
    with store.appender() as ap2:
        ap2.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 1)))
    assert store.count_events() == 1


def test_appender_uses_archive_id(store: DuckDBStore) -> None:
    with store.appender() as ap:
        ap.append_event(_ev("CALL", datetime(2026, 5, 17, 18, 0, 0)))
    conn = store.open()
    row = conn.execute("SELECT archive_id FROM events LIMIT 1").fetchone()
    assert row[0] == "test-archive"


def test_delete_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / "to_delete.duckdb"
    store = DuckDBStore("doomed", db_path=db_path)
    store.open()
    store.close()
    assert db_path.exists()
    DuckDBStore.delete_db_file("doomed", db_path=db_path)
    assert not db_path.exists()
    # idempotent
    DuckDBStore.delete_db_file("doomed", db_path=db_path)
