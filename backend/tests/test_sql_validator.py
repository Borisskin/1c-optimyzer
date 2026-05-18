"""Тесты SQL Validator (Sprint 2 Phase B, ADR-019)."""

from __future__ import annotations

import pytest

from optimyzer_backend.sql.validator import validate_sql


# ---------- разрешённые запросы ----------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM events LIMIT 10",
        "SELECT ts, event_type FROM events WHERE duration_us > 1000 ORDER BY ts",
        "select count(*) from events",
        "  SELECT 1  ",
        "WITH t AS (SELECT * FROM events) SELECT * FROM t",
        """
        SELECT event_type, COUNT(*) AS cnt
        FROM events
        GROUP BY event_type
        ORDER BY cnt DESC
        LIMIT 50
        """,
        "SELECT * FROM events WHERE sql_text LIKE '%CREATE%'",  # CREATE внутри строки разрешён
        "-- comment first\nSELECT 1",
        "/* block */\nSELECT 1",
    ],
)
def test_valid_selects_accepted(sql: str) -> None:
    ok, err = validate_sql(sql)
    assert ok, f"должен быть валидным: {sql!r}, ошибка: {err}"
    assert err is None


# ---------- запрещённые запросы ----------


@pytest.mark.parametrize(
    "sql,expected_kw",
    [
        ("INSERT INTO events VALUES (1)", "INSERT"),
        ("UPDATE events SET ts = NULL", "UPDATE"),
        ("DELETE FROM events", "DELETE"),
        ("DROP TABLE events", "DROP"),
        ("CREATE TABLE x (a INT)", "CREATE"),
        ("ALTER TABLE events ADD COLUMN x INT", "ALTER"),
        ("TRUNCATE TABLE events", "TRUNCATE"),
        ("ATTACH 'other.duckdb' AS o", "ATTACH"),
        ("COPY events TO 'out.csv'", "COPY"),
        ("PRAGMA show_tables", "PRAGMA"),
        ("CALL pragma_database_list()", "CALL"),
        ("VACUUM", "VACUUM"),
    ],
)
def test_blocked_keywords_rejected(sql: str, expected_kw: str) -> None:
    ok, err = validate_sql(sql)
    assert not ok, f"должен быть отклонён: {sql!r}"
    assert err is not None
    assert expected_kw in err


def test_empty_query_rejected() -> None:
    ok, err = validate_sql("")
    assert not ok
    assert err is not None and "Пустой" in err


def test_whitespace_query_rejected() -> None:
    ok, err = validate_sql("   \n\t  ")
    assert not ok


def test_multiple_statements_rejected() -> None:
    ok, err = validate_sql("SELECT 1; SELECT 2")
    assert not ok
    assert err is not None
    assert "один" in err.lower() or "single" in err.lower()


def test_select_followed_by_delete_rejected() -> None:
    """Защита от 'SELECT 1; DELETE FROM events' bypass."""
    ok, err = validate_sql("SELECT 1; DELETE FROM events")
    assert not ok


def test_keyword_inside_string_literal_allowed() -> None:
    """CREATE / DROP внутри строкового литерала не должен блокировать запрос."""
    ok, err = validate_sql("SELECT * FROM events WHERE sql_text LIKE '%CREATE TABLE%'")
    assert ok, err


def test_keyword_inside_block_comment_allowed() -> None:
    ok, err = validate_sql("/* INSERT INTO foo */ SELECT 1")
    assert ok, err


def test_keyword_inside_line_comment_allowed() -> None:
    ok, err = validate_sql("-- DROP TABLE foo\nSELECT 1")
    assert ok, err


def test_cte_with_delete_inside_rejected() -> None:
    """CTE с DELETE внутри блокируется (даже если top-level WITH)."""
    sql = "WITH t AS (DELETE FROM events RETURNING *) SELECT * FROM t"
    ok, err = validate_sql(sql)
    assert not ok
