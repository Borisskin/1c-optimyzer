"""Sprint 7 Phase D — тесты на извлечение planSQLText из DBMSSQL событий."""

from __future__ import annotations

from optimyzer_backend.parsers.tj_parser import interpret, iter_raw_events


# Test data — типичные ТЖ-фрагменты со встроенным planSQLText.

DBMSSQL_WITH_PLAN_SIMPLE = (
    "32:14.402023-8124000,DBMSSQL,5,process=rphost,"
    "Sql='SELECT 1',planSQLText='Compute Scalar'"
)

DBMSSQL_WITH_PLAN_MULTILINE = (
    "33:15.500000-12345,DBMSSQL,5,process=rphost,"
    "Sql='SELECT TOP 100 * FROM dbo._Reference15',planSQLText='\n"
    "|--Clustered Index Seek(OBJECT:([_Reference15]), SEEK:(...))\n"
    "|     Estimated Rows = 100\n"
    "|     I/O cost: 0.003\n"
    "'"
)

# Escape сценарий — внутри plan_text есть одинарная кавычка (encoded как '').
DBMSSQL_WITH_PLAN_ESCAPED_QUOTES = (
    "11:22.333444-555,DBMSSQL,5,process=rphost,Sql='SELECT 1',"
    "planSQLText='|--Filter(WHERE:([Name]=''John''))'"
)

DBMSSQL_WITHOUT_PLAN = (
    "10:11.111111-22000,DBMSSQL,5,process=rphost,Sql='SELECT 1'"
)

CALL_WITH_FAKE_PLAN_FIELD = (
    "10:11.111111-22000,CALL,3,process=rphost,planSQLText='not extracted for CALL'"
)


def _parse_one_event(text: str):
    events = list(iter_raw_events(text, "test.log"))
    assert len(events) == 1, f"ожидалось 1 событие, получено {len(events)}"
    return events[0]


def test_plan_text_simple_extracted():
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_SIMPLE)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.event_type == "DBMSSQL"
    assert ev.plan_text == "Compute Scalar"
    # planSQLText не должно попасть в extra — оно в known_keys.
    assert "planSQLText" not in (ev.extra or {})


def test_plan_text_multiline_preserved():
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_MULTILINE)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.plan_text is not None
    assert "Clustered Index Seek" in ev.plan_text
    assert "Estimated Rows = 100" in ev.plan_text
    # Перенос строк сохранён (текст имеет 4 строки).
    assert ev.plan_text.count("\n") >= 3


def test_plan_text_escaped_quotes_decoded():
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_ESCAPED_QUOTES)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.plan_text == "|--Filter(WHERE:([Name]='John'))"


def test_no_plan_field_means_none():
    raw = _parse_one_event(DBMSSQL_WITHOUT_PLAN)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.plan_text is None


def test_plan_field_ignored_for_non_dbmssql():
    """planSQLText в CALL event не извлекаем — Sprint 7 ставит только DBMSSQL."""
    raw = _parse_one_event(CALL_WITH_FAKE_PLAN_FIELD)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.event_type == "CALL"
    assert ev.plan_text is None
    # Поле всё равно осталось в extra (т.к. interpret для не-DBMSSQL не чистит
    # planSQLText из known_keys для других типов событий — но это OK поведение).
    # Проверяем что хотя бы plan_text=None.


def test_plan_text_in_as_row_position():
    """Регресс на as_row: plan_text идёт после sql_text_hash, перед rows_read."""
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_SIMPLE)
    ev = interpret(raw, (2026, 5, 24, 22))
    row = ev.as_row(archive_id="test-arc", event_id=1)
    # Структура tuple по EVENT_COLUMNS — plan_text на индексе 15
    # (id, archive_id, ts, duration_us, event_type, session_id, user_name,
    #  context, context_normalized, process, process_role, process_pid,
    #  sql_text, sql_text_normalized, sql_text_hash, plan_text, rows_read, ...)
    assert row[15] == "Compute Scalar"


def test_plan_text_empty_string_treated_as_none():
    """planSQLText='' (пустая строка) → plan_text = None, не пустая."""
    text = "10:11.111111-22000,DBMSSQL,5,process=rphost,Sql='SELECT 1',planSQLText=''"
    raw = _parse_one_event(text)
    ev = interpret(raw, (2026, 5, 24, 22))
    # `f.get("planSQLText") or None` → пустая строка falsy → None.
    assert ev.plan_text is None
