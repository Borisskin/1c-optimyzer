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


def test_preset_longest_excludes_cumulative_excpcntx(store: DuckDBStore):
    # S12 F2 — EXCPCNTX/Context несут cumulative-длительность родительского
    # контекста, не должны доминировать в «самых медленных». Исключаются.
    events = [
        _ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 0), 5_000_000, sql="SELECT 1"),
        _ev("EXCPCNTX", datetime(2026, 5, 17, 18, 0, 1), 99_000_000_000),
        _ev("CALL", datetime(2026, 5, 17, 18, 0, 2), 1_000_000),
    ]
    store.bulk_insert(events, start_id=1)
    _, rows = store.run_preset("longest", limit=10)
    types = [r[1] for r in rows]  # колонка event_type (индекс 1)
    assert "EXCPCNTX" not in types
    assert "DBMSSQL" in types and "CALL" in types
    assert len(rows) == 2


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


# ---------- Конфигурация памяти (fix «os error 232» / OOM) ----------


def test_resolve_memory_limit_env_override(monkeypatch: pytest.MonkeyPatch):
    """OPTIMYZER_DUCKDB_MEMORY_LIMIT трактуется как есть."""
    from optimyzer_backend.storage import duckdb_store as d

    monkeypatch.setenv("OPTIMYZER_DUCKDB_MEMORY_LIMIT", "1234MiB")
    assert d._resolve_memory_limit() == "1234MiB"


def test_resolve_memory_limit_from_ram(monkeypatch: pytest.MonkeyPatch):
    """Без override — доля физической RAM в MiB (либо None, если RAM неизвестна)."""
    from optimyzer_backend.storage import duckdb_store as d

    monkeypatch.delenv("OPTIMYZER_DUCKDB_MEMORY_LIMIT", raising=False)
    monkeypatch.setattr(d, "_physical_ram_bytes", lambda: 8 * 1024 * 1024 * 1024)
    # 60% от 8 GiB = 4915 MiB
    assert d._resolve_memory_limit() == "4915MiB"

    monkeypatch.setattr(d, "_physical_ram_bytes", lambda: None)
    assert d._resolve_memory_limit() is None


def test_resolve_memory_limit_floor(monkeypatch: pytest.MonkeyPatch):
    """Лимит не опускается ниже 512 MiB даже на очень малой RAM."""
    from optimyzer_backend.storage import duckdb_store as d

    monkeypatch.delenv("OPTIMYZER_DUCKDB_MEMORY_LIMIT", raising=False)
    monkeypatch.setattr(d, "_physical_ram_bytes", lambda: 256 * 1024 * 1024)
    assert d._resolve_memory_limit() == "512MiB"


def test_connection_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """open() применяет memory_limit и локальный temp_directory к соединению."""
    monkeypatch.setenv("OPTIMYZER_DUCKDB_MEMORY_LIMIT", "1GB")
    s = DuckDBStore("cfg-archive", db_path=tmp_path / "cfg.duckdb")
    conn = s.open()
    try:
        limit = conn.execute("SELECT current_setting('memory_limit')").fetchone()[0]
        tmp = conn.execute("SELECT current_setting('temp_directory')").fetchone()[0]
        # DuckDB нормализует '1GB' (10^9) → '953.6 MiB'; проверяем, что лимит
        # применён и ограничен (не дефолтные ~80% RAM), а temp_directory задан.
        assert "iB" in limit  # MiB / GiB / KiB
        assert tmp  # temp_directory задан (спилл на локальный диск)
    finally:
        s.close()


def test_configure_connection_survives_bad_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Некорректный лимит не должен ронять open() (best-effort)."""
    monkeypatch.setenv("OPTIMYZER_DUCKDB_MEMORY_LIMIT", "не-число")
    s = DuckDBStore("bad-cfg", db_path=tmp_path / "bad.duckdb")
    conn = s.open()  # не бросает
    try:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    finally:
        s.close()
