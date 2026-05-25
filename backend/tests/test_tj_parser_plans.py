"""Sprint 7 Phase D + Sprint 8 Phase B — тесты на извлечение planSQLText.

Sprint 7 Phase D — DBMSSQL события с MSSQL planSQLText.
Sprint 8 Phase B — DBPOSTGRS события с PostgreSQL EXPLAIN TEXT и engine field.

Acceptance B.1 (см. SPRINT_8_PHASE_B_PROMT.md):
- 6+ новых тестов для DBPOSTGRS parsing
- Regression: DBMSSQL продолжает работать
- engine field правильный для всех database events
- planSQLText decoded для PG multiline plans
"""

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


# ============================================================
# Sprint 7 Phase D regression — engine field на MSSQL
# ============================================================


def test_dbmssql_engine_is_mssql():
    """DBMSSQL события должны иметь engine='mssql' (Sprint 8 Phase B)."""
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_SIMPLE)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.engine == "mssql"


def test_call_event_has_no_engine():
    """Non-database events (CALL, EXCP, TLOCK) должны иметь engine=None."""
    raw = _parse_one_event(CALL_WITH_FAKE_PLAN_FIELD)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.engine is None


# ============================================================
# Sprint 8 Phase B — DBPOSTGRS parsing (PostgreSQL ТЖ events)
# ============================================================

# Минимальный DBPOSTGRS event — только Sql, без plan.
DBPOSTGRS_SIMPLE = (
    "27:17.223021-1,DBPOSTGRS,3,process=rphost,p:processName=pgBase,"
    "OSThread=21928,DBMS=DBPOSTGRS,DataBase=localhost\\pgBase,Trans=0,dbpid=,"
    "Sql=\"SELECT 1\""
)

# Real-world DBPOSTGRS event с planSQLText в double quotes (как 1С формирует
# для PG — в отличие от DBMSSQL где single quotes). См. discovery sample:
# tools/sprint8_discovery/pg_tj_samples/dbpostgrs_sample.log
DBPOSTGRS_WITH_PLAN = (
    "27:17.223021-1,DBPOSTGRS,3,process=rphost,p:processName=pgBase,"
    "OSThread=21928,t:clientID=622,t:applicationName=Designer,t:computerName=WIN,"
    "t:connectID=239,DBMS=DBPOSTGRS,DataBase=localhost\\pgBase,Trans=0,dbpid=,"
    "Sql=\"select spcname from pg_tablespace where spcname = 'v81c_index' or spcname = 'v81c_data';\n"
    "\",planSQLText=\"Seq Scan on pg_catalog.pg_tablespace  (cost=0.00..1.02 rows=2 width=64) (actual time=0.011..0.011 rows=0.00 loops=1)\n"
    "  Output: spcname\n"
    "  Filter: ((pg_tablespace.spcname = 'v81c_index'::name) OR (pg_tablespace.spcname = 'v81c_data'::name))\n"
    "  Rows Removed by Filter: 2\n"
    "  Buffers: shared hit=1\n"
    "Query Identifier: 4542859770577971149\n"
    "Planning:\n"
    "  Buffers: shared hit=190\n"
    "Planning Time: 0.783 ms\n"
    "Execution Time: 0.024 ms\n"
    "\",RowsAffected=0,Result=PGRES_TUPLES_OK"
)

# Без plan, но с PGRES_COMMAND_OK (DDL/DML операция типа BEGIN/SET).
DBPOSTGRS_NO_PLAN_COMMAND = (
    "27:17.500000-1,DBPOSTGRS,3,process=rphost,p:processName=pgBase,"
    "Sql=\"BEGIN\",RowsAffected=0,Result=PGRES_COMMAND_OK"
)


def test_parse_dbpostgrs_simple():
    """Минимальный DBPOSTGRS event парсится — event_type/sql_text заполнены."""
    raw = _parse_one_event(DBPOSTGRS_SIMPLE)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.event_type == "DBPOSTGRS"
    assert ev.sql_text == "SELECT 1"
    assert ev.engine == "postgres"
    assert ev.plan_text is None


def test_parse_dbpostgrs_with_plan():
    """DBPOSTGRS с planSQLText — план достаётся, multiline сохраняется."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.event_type == "DBPOSTGRS"
    assert ev.engine == "postgres"
    assert ev.plan_text is not None
    # Признаки PG plan: Seq Scan / Planning Time / Execution Time.
    assert "Seq Scan on pg_catalog.pg_tablespace" in ev.plan_text
    assert "Planning Time: 0.783 ms" in ev.plan_text
    assert "Execution Time: 0.024 ms" in ev.plan_text
    # Multiline preserved.
    assert ev.plan_text.count("\n") >= 10
    # SQL содержит реальный текст, не обрезан на запятой внутри quotes.
    assert ev.sql_text is not None
    assert "pg_tablespace" in ev.sql_text


def test_parse_dbpostgrs_engine_field():
    """engine='postgres' заполнено корректно для DBPOSTGRS."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.engine == "postgres"


def test_parse_dbpostgrs_multiline_plan_preserves_filter():
    """Многострочный план с Filter (...) — символы скобок и переносы строк сохранены."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    # Filter с двойной OR-конструкцией должен полностью попасть в plan_text.
    assert "Filter: ((pg_tablespace.spcname = 'v81c_index'::name)" in ev.plan_text
    assert "OR (pg_tablespace.spcname = 'v81c_data'::name))" in ev.plan_text


def test_parse_dbpostgrs_command_no_plan():
    """DBPOSTGRS BEGIN/COMMIT без planSQLText (Result=PGRES_COMMAND_OK)."""
    raw = _parse_one_event(DBPOSTGRS_NO_PLAN_COMMAND)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.event_type == "DBPOSTGRS"
    assert ev.engine == "postgres"
    assert ev.sql_text == "BEGIN"
    assert ev.plan_text is None
    # Result/RowsAffected попали в extra (так как они не специально обработаны).
    # Это OK — нет на них зависимостей в Sprint 8 Phase B.


def test_parse_dbpostgrs_rows_affected():
    """RowsAffected из DBPOSTGRS → rows_modified в ParsedEvent."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.rows_modified == 0  # из RowsAffected=0


def test_dbpostgrs_sql_normalization_works():
    """sql_text_normalized и sql_text_hash заполняются для DBPOSTGRS (как для DBMSSQL)."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    assert ev.sql_text_normalized is not None
    assert ev.sql_text_hash is not None
    # Литералы должны быть заменены на ?
    assert "?" in ev.sql_text_normalized
    assert "v81c_index" not in ev.sql_text_normalized  # литерал стал ?


def test_engine_field_in_as_row_position():
    """as_row() возвращает engine на последней позиции (после source_line_start)."""
    raw = _parse_one_event(DBPOSTGRS_WITH_PLAN)
    ev = interpret(raw, (2026, 5, 25, 14))
    row = ev.as_row(archive_id="test-arc", event_id=1)
    # Структура tuple по EVENT_COLUMNS:
    #   ..., extra[18], source_file[19], source_line_start[20], engine[21]
    assert row[21] == "postgres"
    # Sanity: общая длина = 22 элемента после добавления engine.
    assert len(row) == 22


def test_dbmssql_as_row_engine_position():
    """Regression: для DBMSSQL engine='mssql' на той же позиции."""
    raw = _parse_one_event(DBMSSQL_WITH_PLAN_SIMPLE)
    ev = interpret(raw, (2026, 5, 24, 22))
    row = ev.as_row(archive_id="test-arc", event_id=1)
    assert row[21] == "mssql"


def test_non_database_event_engine_is_none():
    """CALL/EXCP/TLOCK не должны иметь engine (это не SQL события)."""
    text = (
        "10:11.111111-22000,EXCP,3,process=rphost,Descr='ошибка соединения'"
    )
    raw = _parse_one_event(text)
    ev = interpret(raw, (2026, 5, 24, 22))
    assert ev.event_type == "EXCP"
    assert ev.engine is None
    row = ev.as_row(archive_id="test-arc", event_id=1)
    assert row[21] is None
