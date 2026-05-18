"""End-to-end OQL: parse → validate → compile → execute against DuckDB."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from optimyzer_backend.oql import SQLCompiler, parse_oql, validate
from optimyzer_backend.parsers.tj_parser import ParsedEvent
from optimyzer_backend.storage.duckdb_store import DuckDBStore


def _ev(
    et: str,
    ts: datetime,
    dur: int | None = 1000,
    role: str = "rphost",
    pid: int = 1234,
    session_id: int | None = None,
    context: str | None = None,
    sql_text: str | None = None,
) -> ParsedEvent:
    return ParsedEvent(
        ts=ts,
        duration_us=dur,
        event_type=et,
        level=3,
        process_role=role,
        process_pid=pid,
        session_id=session_id,
        context=context,
        sql_text=sql_text,
    )


@pytest.fixture
def store_with_data(tmp_path: Path):
    s = DuckDBStore("test-oql", db_path=tmp_path / "oql.duckdb")
    s.open()
    events = [
        _ev("CALL", datetime(2026, 5, 17, 18, 0, 0), 500, role="rphost", pid=1000, context="A"),
        _ev("CALL", datetime(2026, 5, 17, 18, 0, 1), 1500, role="rphost", pid=1000, context="B"),
        _ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 2), 5000, role="rphost", pid=1000,
            sql_text="SELECT 1"),
        _ev("DBMSSQL", datetime(2026, 5, 17, 18, 0, 3), 12000, role="rmngr", pid=2000,
            sql_text="SELECT 2"),
        _ev("TDEADLOCK", datetime(2026, 5, 17, 18, 0, 4), 0, role="rphost", pid=1000),
        _ev("TLOCK", datetime(2026, 5, 17, 18, 0, 5), 100, role="ragent", pid=3000),
        _ev("EXCP", datetime(2026, 5, 17, 18, 0, 6), 50, role="1cv8c", pid=4000),
    ]
    with s.appender() as ap:
        ap.append_many(events)
    s.create_indexes()
    yield s
    s.close()


def _run(store: DuckDBStore, oql: str) -> list[tuple]:
    ast = parse_oql(oql)
    errors = validate(ast)
    assert errors == [], f"validation errors: {errors}"
    compiler = SQLCompiler(active_archive_id=store.archive_id)
    sql, params = compiler.compile(ast)
    return store.open().execute(sql, params).fetchall()


def test_take_returns_all(store_with_data: DuckDBStore) -> None:
    rows = _run(store_with_data, "events | take 100")
    assert len(rows) == 7


def test_where_filters_event_type(store_with_data: DuckDBStore) -> None:
    rows = _run(store_with_data, 'events | where event_type == "DBMSSQL"')
    assert len(rows) == 2


def test_where_role_filter(store_with_data: DuckDBStore) -> None:
    rows = _run(store_with_data, 'events | where role == "rphost"')
    assert len(rows) == 4


def test_duration_threshold(store_with_data: DuckDBStore) -> None:
    rows = _run(store_with_data, "events | where duration_ms > 1ms")
    # > 1ms = > 1000us; events with dur > 1000: 1500, 5000, 12000
    assert len(rows) == 3


def test_in_clause(store_with_data: DuckDBStore) -> None:
    rows = _run(store_with_data, 'events | where event_type in ("EXCP", "TDEADLOCK")')
    assert len(rows) == 2


def test_order_desc_take(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data, "events | order by duration_us desc | take 3"
    )
    # rows[i][duration_us-index] — but we have SELECT *, durations descending
    # check first row has duration 12000
    # column index depends на schema; используем dict-style через cursor.description?
    # Здесь fetchall() возвращает tuples в порядке schema. duration_us — 4-й (0:id,1:archive_id,2:ts,3:duration_us)
    assert rows[0][3] == 12000
    assert rows[1][3] == 5000
    assert rows[2][3] == 1500


def test_summarize_count_by_event_type(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data,
        "events | summarize n = count(*) by event_type | order by n desc",
    )
    # CALL: 2, DBMSSQL: 2, плюс по 1 на TDEADLOCK/TLOCK/EXCP — 5 групп
    assert len(rows) == 5
    # Топ — CALL или DBMSSQL с count=2
    assert rows[0][1] == 2


def test_summarize_count_by_role(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data, "events | summarize cnt = count(*) by process_role"
    )
    role_counts = {r[0]: r[1] for r in rows}
    assert role_counts["rphost"] == 4
    assert role_counts["rmngr"] == 1
    assert role_counts["ragent"] == 1
    assert role_counts["1cv8c"] == 1


def test_summarize_avg_duration(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data, "events | summarize avg_us = avg(duration_us)"
    )
    # avg of [500, 1500, 5000, 12000, 0, 100, 50]
    expected = (500 + 1500 + 5000 + 12000 + 0 + 100 + 50) / 7
    assert abs(rows[0][0] - expected) < 0.01


def test_project_returns_only_selected(store_with_data: DuckDBStore) -> None:
    ast = parse_oql("events | project event_type, duration_us | take 1")
    compiler = SQLCompiler(active_archive_id=store_with_data.archive_id)
    sql, params = compiler.compile(ast)
    cur = store_with_data.open().execute(sql, params)
    columns = [d[0] for d in cur.description]
    assert columns == ["event_type", "duration_us"]


def test_contains_finds_substring(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data,
        'events | where sql_text contains "SELECT"',
    )
    assert len(rows) == 2


def test_render_hint_extracted_via_query(store_with_data: DuckDBStore) -> None:
    ast = parse_oql("events | take 5 | render bar")
    compiler = SQLCompiler(active_archive_id=store_with_data.archive_id)
    compiler.compile(ast)
    assert compiler.render_hint() == "bar"


def test_distinct_count(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data,
        "events | summarize uniq_pid = countd(process_pid)",
    )
    # 4 distinct pid: 1000, 2000, 3000, 4000
    assert rows[0][0] == 4


def test_compound_where(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data,
        'events | where role == "rphost" and event_type == "CALL"',
    )
    assert len(rows) == 2


def test_or_clause(store_with_data: DuckDBStore) -> None:
    rows = _run(
        store_with_data,
        'events | where event_type == "TDEADLOCK" or event_type == "TLOCK"',
    )
    assert len(rows) == 2
