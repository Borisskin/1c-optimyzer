"""Базовые тесты ТЖ-парсера: lexer, kv-fields, event-types."""

from __future__ import annotations

from optimyzer_backend.parsers.tj_parser import (
    _parse_kv_fields,
    interpret,
    iter_raw_events,
    parse_filename_timestamp,
)


def test_parse_filename_timestamp_valid():
    assert parse_filename_timestamp("26051718.log") == (2026, 5, 17, 18)
    assert parse_filename_timestamp("rphost_1234/26051723.log") == (2026, 5, 17, 23)


def test_parse_filename_timestamp_invalid():
    assert parse_filename_timestamp("badname.log") is None
    assert parse_filename_timestamp("foo.txt") is None


def test_kv_fields_simple():
    fields = _parse_kv_fields("a=1,b=2,c=3")
    assert fields == {"a": "1", "b": "2", "c": "3"}


def test_kv_fields_quoted_with_commas():
    fields = _parse_kv_fields("a=1,Context='Документ.Реализация, провод',b=2")
    assert fields["a"] == "1"
    assert fields["Context"] == "Документ.Реализация, провод"
    assert fields["b"] == "2"


def test_kv_fields_doubled_quote_escape():
    fields = _parse_kv_fields("Sql='it''s ok'")
    assert fields["Sql"] == "it's ok"


def test_iter_raw_events_single_line():
    text = "00:01.100000-2000,CALL,3,process=rphost,OSThread=1"
    events = list(iter_raw_events(text, "test.log"))
    assert len(events) == 1
    e = events[0]
    assert e.event_type == "CALL"
    assert e.minute == 0
    assert e.second == 1
    assert e.duration_us == 2000
    assert e.level == 3
    assert e.fields == {"process": "rphost", "OSThread": "1"}


def test_iter_raw_events_multiline(synthetic_dbmssql_log: str):
    events = list(iter_raw_events(synthetic_dbmssql_log, "test.log"))
    assert len(events) == 2
    dbmssql = events[0]
    assert dbmssql.event_type == "DBMSSQL"
    assert "SELECT" in dbmssql.fields["Sql"]
    assert "GROUP BY" in dbmssql.fields["Sql"]
    assert dbmssql.fields["Rows"] == "234"

    call = events[1]
    assert call.event_type == "CALL"
    assert call.duration_us == 15000


def test_unknown_event_type_does_not_crash(synthetic_mixed_log: str):
    events = list(iter_raw_events(synthetic_mixed_log, "test.log"))
    types = [e.event_type for e in events]
    assert "UNKNOWNFOO" in types
    assert "TDEADLOCK" in types
    assert len(events) == 6


def test_interpret_dbmssql_normalization():
    raw_events = list(
        iter_raw_events(
            "00:01.000000-1000,DBMSSQL,5,Sql='SELECT * FROM T1 WHERE x = 42 AND y = ''abc'''",
            "test.log",
        )
    )
    parsed = interpret(raw_events[0], (2026, 1, 1, 0))
    assert parsed.event_type == "DBMSSQL"
    assert parsed.sql_text is not None
    assert "42" in parsed.sql_text
    # нормализованный SQL должен заменить literals на ?
    assert parsed.sql_text_normalized is not None
    assert "42" not in parsed.sql_text_normalized
    assert parsed.sql_text_hash is not None


def test_interpret_timestamp_combines_filename_and_event():
    raw_events = list(iter_raw_events("32:14.402023-1000,CALL,3", "test.log"))
    parsed = interpret(raw_events[0], (2026, 5, 17, 18))
    assert parsed.ts.year == 2026
    assert parsed.ts.month == 5
    assert parsed.ts.day == 17
    assert parsed.ts.hour == 18
    assert parsed.ts.minute == 32
    assert parsed.ts.second == 14
    assert parsed.ts.microsecond == 402023
