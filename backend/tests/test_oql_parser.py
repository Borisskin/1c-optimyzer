"""Тесты OQL parser — grammar coverage + error messages."""

from __future__ import annotations

import pytest

from optimyzer_backend.oql import (
    BinaryCmp,
    DurationLit,
    Ident,
    LimitOp,
    LogicalOp,
    NumberLit,
    OQLParseError,
    OrderOp,
    ProjectOp,
    Query,
    RenderOp,
    Source,
    StringLit,
    SummarizeOp,
    TakeOp,
    TimerangeOp,
    WhereOp,
    parse_oql,
)


def test_basic_source_only() -> None:
    q = parse_oql("events")
    assert isinstance(q, Query)
    assert q.source.name == "events"
    assert q.pipes == []


def test_take_pipeline() -> None:
    q = parse_oql("events | take 10")
    assert len(q.pipes) == 1
    assert isinstance(q.pipes[0], TakeOp)
    assert q.pipes[0].count == 10


def test_limit_pipeline() -> None:
    q = parse_oql("events | limit 50")
    assert isinstance(q.pipes[0], LimitOp)
    assert q.pipes[0].count == 50


def test_where_equality() -> None:
    q = parse_oql('events | where event_type == "DBMSSQL"')
    pipe = q.pipes[0]
    assert isinstance(pipe, WhereOp)
    cmp_node = pipe.expr
    assert isinstance(cmp_node, BinaryCmp)
    assert isinstance(cmp_node.left, Ident) and cmp_node.left.name == "event_type"
    assert cmp_node.op == "=="
    assert isinstance(cmp_node.right, StringLit) and cmp_node.right.value == "DBMSSQL"


def test_where_duration_literal_ms() -> None:
    q = parse_oql("events | where duration_ms > 1000ms")
    pipe = q.pipes[0]
    cmp = pipe.expr
    assert isinstance(cmp, BinaryCmp)
    assert isinstance(cmp.right, DurationLit)
    assert cmp.right.value == 1000.0
    assert cmp.right.unit == "ms"


def test_where_and_chain() -> None:
    q = parse_oql('events | where event_type == "CALL" and duration_us > 100')
    pipe = q.pipes[0]
    expr = pipe.expr
    assert isinstance(expr, LogicalOp)
    assert expr.op == "and"
    assert len(expr.items) == 2


def test_where_or_chain() -> None:
    q = parse_oql('events | where event_type == "EXCP" or event_type == "TDEADLOCK"')
    pipe = q.pipes[0]
    assert isinstance(pipe.expr, LogicalOp)
    assert pipe.expr.op == "or"


def test_project_columns() -> None:
    q = parse_oql("events | project ts, duration_us, sql_text")
    pipe = q.pipes[0]
    assert isinstance(pipe, ProjectOp)
    assert pipe.columns == ["ts", "duration_us", "sql_text"]


def test_order_single_default_asc() -> None:
    q = parse_oql("events | order by ts")
    pipe = q.pipes[0]
    assert isinstance(pipe, OrderOp)
    assert pipe.terms[0].column == "ts"
    assert pipe.terms[0].direction == "asc"


def test_order_desc() -> None:
    q = parse_oql("events | order by duration_us desc")
    pipe = q.pipes[0]
    assert pipe.terms[0].direction == "desc"


def test_order_multiple() -> None:
    q = parse_oql("events | order by event_type asc, duration_us desc")
    assert len(q.pipes[0].terms) == 2


def test_summarize_count_star() -> None:
    q = parse_oql("events | summarize cnt = count(*)")
    pipe = q.pipes[0]
    assert isinstance(pipe, SummarizeOp)
    assert pipe.aggregations[0].alias == "cnt"
    assert pipe.aggregations[0].func == "count"
    assert pipe.aggregations[0].arg == "*"


def test_summarize_with_group_by() -> None:
    q = parse_oql("events | summarize cnt = count(*) by event_type, process_role")
    pipe = q.pipes[0]
    assert pipe.group_by == ["event_type", "process_role"]


def test_summarize_multiple_aggs() -> None:
    q = parse_oql("events | summarize n = count(*), avg_d = avg(duration_us)")
    pipe = q.pipes[0]
    assert len(pipe.aggregations) == 2
    assert pipe.aggregations[1].func == "avg"


def test_timerange_last_24h() -> None:
    q = parse_oql("events | timerange last 24h")
    pipe = q.pipes[0]
    assert isinstance(pipe, TimerangeOp)
    # 24h = 24 * 3_600_000_000 microseconds
    assert pipe.duration_us == 24 * 3_600_000_000


def test_timerange_last_500ms() -> None:
    q = parse_oql("events | timerange last 500ms")
    pipe = q.pipes[0]
    assert pipe.duration_us == 500_000


@pytest.mark.parametrize("unit, expected_factor", [
    ("us", 1),
    ("ms", 1_000),
    ("s", 1_000_000),
    ("m", 60_000_000),
    ("h", 3_600_000_000),
    ("d", 86_400_000_000),
])
def test_all_duration_units(unit: str, expected_factor: int) -> None:
    q = parse_oql(f"events | timerange last 1{unit}")
    assert q.pipes[0].duration_us == expected_factor


def test_render_table() -> None:
    q = parse_oql("events | render table")
    pipe = q.pipes[-1]
    assert isinstance(pipe, RenderOp)
    assert pipe.kind == "table"


@pytest.mark.parametrize("kind", ["table", "bar", "line", "histogram", "timeline", "scatter"])
def test_all_render_kinds(kind: str) -> None:
    q = parse_oql(f"events | render {kind}")
    assert q.pipes[-1].kind == kind


def test_comments_ignored() -> None:
    q = parse_oql("// Заголовок\nevents | take 5 // tail\n")
    assert q.pipes[0].count == 5


def test_cyrillic_string_literal() -> None:
    q = parse_oql('events | where context == "РасчётыСервер"')
    cmp = q.pipes[0].expr
    assert cmp.right.value == "РасчётыСервер"


def test_in_clause() -> None:
    q = parse_oql('events | where event_type in ("CALL", "DBMSSQL")')
    pipe = q.pipes[0]
    expr = pipe.expr
    assert expr.__class__.__name__ == "InCmp"
    assert len(expr.values) == 2


def test_contains_operator() -> None:
    q = parse_oql('events | where sql_text contains "SELECT"')
    cmp = q.pipes[0].expr
    assert cmp.op == "contains"


def test_startswith_operator() -> None:
    q = parse_oql('events | where context startswith "Документ"')
    assert q.pipes[0].expr.op == "startswith"


def test_pipeline_with_multiple_pipes() -> None:
    q = parse_oql(
        'events | where event_type == "DBMSSQL" | order by duration_us desc | take 100'
    )
    assert len(q.pipes) == 3


def test_pipeline_full() -> None:
    q = parse_oql(
        'events\n'
        '| where event_type == "DBMSSQL" and duration_ms > 1000ms\n'
        '| project ts, duration_ms, sql_text_normalized\n'
        '| order by duration_ms desc\n'
        '| take 100\n'
        '| render table'
    )
    assert len(q.pipes) == 5


def test_error_empty_string() -> None:
    with pytest.raises(OQLParseError) as exc_info:
        parse_oql("")
    assert "пустой" in str(exc_info.value).lower()


def test_error_suggest_where_for_filter() -> None:
    with pytest.raises(OQLParseError) as exc_info:
        parse_oql('events | filter event_type == "CALL"')
    assert "where" in str(exc_info.value)


def test_error_suggest_take_for_limit_chain() -> None:
    # 'limit' валидна как keyword, но если в неожиданной позиции — мы не подсказываем.
    # Этот тест проверяет что 'top' даёт suggestion 'take'.
    with pytest.raises(OQLParseError) as exc_info:
        parse_oql("events | top 10")
    assert "take" in str(exc_info.value)


def test_error_unterminated_string() -> None:
    with pytest.raises(OQLParseError):
        parse_oql('events | where context == "unterminated')


def test_error_mismatched_parens() -> None:
    with pytest.raises(OQLParseError):
        parse_oql('events | where (event_type == "CALL"')


def test_negative_number_in_compare() -> None:
    q = parse_oql("events | where duration_us > -1")
    cmp = q.pipes[0].expr
    assert cmp.right.value == -1.0


def test_string_with_escape() -> None:
    q = parse_oql('events | where context == "Слово с \\"кавычками\\""')
    val = q.pipes[0].expr.right.value
    assert val == 'Слово с "кавычками"'


def test_count_distinct() -> None:
    q = parse_oql("events | summarize uniq = countd(session_id)")
    pipe = q.pipes[0]
    assert pipe.aggregations[0].func == "countd"
    assert pipe.aggregations[0].arg == "session_id"


def test_take_with_where_and_order() -> None:
    q = parse_oql(
        'events | where event_type == "TDEADLOCK" | order by ts asc | take 50'
    )
    assert len(q.pipes) == 3
