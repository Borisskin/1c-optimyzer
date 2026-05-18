"""Тесты OQL compiler — AST → DuckDB SQL."""

from __future__ import annotations

import pytest

from optimyzer_backend.oql import OQLCompileError, SQLCompiler, parse_oql


def compile_query(query: str, archive_id: str = "arc-1") -> tuple[str, list]:
    ast = parse_oql(query)
    compiler = SQLCompiler(active_archive_id=archive_id)
    return compiler.compile(ast)


def test_compiles_basic_source() -> None:
    sql, params = compile_query("events")
    assert "FROM events" in sql
    assert "archive_id = ?" in sql
    assert params == ["arc-1"]


def test_compiles_take() -> None:
    sql, params = compile_query("events | take 10")
    assert sql.endswith("LIMIT ?")
    assert params == ["arc-1", 10]


def test_compiles_limit() -> None:
    sql, params = compile_query("events | limit 50")
    assert sql.endswith("LIMIT ?")
    assert params == ["arc-1", 50]


def test_compiles_where_equality() -> None:
    sql, params = compile_query('events | where event_type == "CALL"')
    assert "event_type = ?" in sql
    assert params == ["arc-1", "CALL"]


def test_compiles_where_ne() -> None:
    sql, params = compile_query('events | where event_type != "CALL"')
    assert "event_type <> ?" in sql


def test_compiles_duration_coercion_ms_to_us() -> None:
    sql, params = compile_query("events | where duration_ms > 1000ms")
    assert "duration_us > ?" in sql
    assert params == ["arc-1", 1_000_000]


def test_compiles_duration_in_s() -> None:
    sql, params = compile_query("events | where duration > 5s")
    assert "duration_us > ?" in sql
    assert params == ["arc-1", 5_000_000]


def test_compiles_alias_resolution() -> None:
    sql, params = compile_query('events | where role == "rphost"')
    assert "process_role = ?" in sql
    assert params == ["arc-1", "rphost"]


def test_compiles_project() -> None:
    sql, _ = compile_query("events | project ts, duration_us")
    assert "SELECT ts, duration_us FROM" in sql


def test_compiles_project_with_aliases() -> None:
    sql, _ = compile_query("events | project ts, duration, role, pid")
    assert "SELECT ts, duration_us, process_role, process_pid FROM" in sql


def test_compiles_order_by_desc() -> None:
    sql, _ = compile_query("events | order by duration_us desc")
    assert "ORDER BY duration_us DESC" in sql


def test_compiles_summarize_count_star() -> None:
    sql, _ = compile_query("events | summarize cnt = count(*)")
    assert "COUNT(*) AS cnt" in sql


def test_compiles_summarize_group_by() -> None:
    sql, _ = compile_query("events | summarize cnt = count(*) by event_type")
    assert "GROUP BY event_type" in sql
    assert "event_type, COUNT(*) AS cnt" in sql


def test_compiles_summarize_avg_duration() -> None:
    sql, _ = compile_query("events | summarize avg_us = avg(duration_us)")
    assert "AVG(duration_us) AS avg_us" in sql


def test_compiles_countd() -> None:
    sql, _ = compile_query("events | summarize uniq = countd(session_id)")
    assert "COUNT(DISTINCT session_id) AS uniq" in sql


def test_compiles_in_clause() -> None:
    sql, params = compile_query('events | where event_type in ("CALL", "DBMSSQL")')
    assert "event_type IN (?, ?)" in sql
    assert params == ["arc-1", "CALL", "DBMSSQL"]


def test_compiles_contains() -> None:
    sql, params = compile_query('events | where sql_text contains "SELECT"')
    assert "sql_text LIKE '%' || ? || '%'" in sql
    assert "SELECT" in params


def test_compiles_startswith() -> None:
    sql, params = compile_query('events | where context startswith "Документ"')
    assert "context LIKE ? || '%'" in sql
    assert "Документ" in params


def test_compiles_and_or() -> None:
    sql, params = compile_query(
        'events | where event_type == "CALL" and duration_us > 100'
    )
    assert " AND " in sql
    assert "event_type = ?" in sql
    assert "duration_us > ?" in sql


def test_compiles_role_filter() -> None:
    sql, params = compile_query('events | where process_role == "rphost"')
    assert "process_role = ?" in sql
    assert params == ["arc-1", "rphost"]


def test_compiler_rejects_unknown_source() -> None:
    with pytest.raises(OQLCompileError) as exc:
        compile_query('metrics | take 10')
    assert "metrics" in str(exc.value)
    assert "Module 1" in str(exc.value)


def test_compiler_rejects_unknown_column_in_project() -> None:
    with pytest.raises(OQLCompileError):
        compile_query("events | project unknown_col")


def test_compiler_rejects_unknown_column_in_where() -> None:
    with pytest.raises(OQLCompileError):
        compile_query('events | where unknown_col == "x"')


def test_parameterized_no_string_concat() -> None:
    """Защита от injection — все literal values как параметры, не concat."""
    sql, params = compile_query('events | where context == "; DROP TABLE events; --"')
    assert "DROP TABLE" not in sql
    assert "; DROP TABLE events; --" in params


def test_render_hint_extracted() -> None:
    ast = parse_oql("events | render bar")
    compiler = SQLCompiler(active_archive_id="arc-1")
    compiler.compile(ast)
    assert compiler.render_hint() == "bar"


def test_render_hint_none_when_absent() -> None:
    ast = parse_oql("events | take 5")
    compiler = SQLCompiler(active_archive_id="arc-1")
    compiler.compile(ast)
    assert compiler.render_hint() is None


def test_full_pipeline_compiles() -> None:
    sql, params = compile_query(
        'events | where event_type == "DBMSSQL" and duration_ms > 1000ms '
        '| project ts, duration_ms, sql_text_normalized '
        '| order by duration_ms desc '
        '| take 100'
    )
    assert "SELECT ts, duration_us, sql_text_normalized FROM events" in sql
    assert "ORDER BY duration_us DESC" in sql
    assert "LIMIT ?" in sql
    # arc-1, "DBMSSQL", 1_000_000 (1000ms), 100
    assert params == ["arc-1", "DBMSSQL", 1_000_000, 100]
