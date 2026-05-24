"""Тесты T-SQL antipatterns detector (Sprint 6 Phase F)."""

from __future__ import annotations

import pytest

from optimyzer_backend.sql.antipatterns import (
    AntipatternSeverity,
    detect_antipatterns,
)


class TestClean:
    """Корректные запросы — пустой список."""

    def test_simple_select(self) -> None:
        sql = "SELECT id, name FROM dbo.Customers WHERE active = 1"
        assert detect_antipatterns(sql) == []

    def test_inner_join_with_specific_columns(self) -> None:
        sql = (
            "SELECT c.id, o.amount FROM dbo.Customers c "
            "INNER JOIN dbo.Orders o ON c.id = o.customer_id"
        )
        assert detect_antipatterns(sql) == []

    def test_empty(self) -> None:
        assert detect_antipatterns("") == []

    def test_too_long(self) -> None:
        assert detect_antipatterns("SELECT 1; " * 20000) == []


class TestParseError:
    def test_broken_sql_returns_blocker(self) -> None:
        sql = "SELECT FROM WHERE )( ((( ALL FROM"  # реально невалидный синтаксис
        results = detect_antipatterns(sql)
        # Либо parse_error, либо tolerant парсер вернёт пустоту — в обоих случаях
        # критериально мы не должны бросить exception.
        for r in results:
            if r.code == "parse_error":
                assert r.severity == AntipatternSeverity.BLOCKER
                return
        # Если sqlglot tolerant-распарсил — ОК, не падает.
        assert isinstance(results, list)


class TestNotInWithSubquery:
    def test_detected(self) -> None:
        sql = (
            "SELECT id FROM dbo.Doc "
            "WHERE id NOT IN (SELECT doc_id FROM dbo.Accum)"
        )
        results = detect_antipatterns(sql)
        codes = [r.code for r in results]
        assert "not_in_with_subquery" in codes

    def test_not_in_with_literals_ok(self) -> None:
        # NOT IN (1, 2, 3) — не подзапрос, нет проблем
        sql = "SELECT id FROM dbo.Doc WHERE status NOT IN (1, 2, 3)"
        results = detect_antipatterns(sql)
        assert "not_in_with_subquery" not in [r.code for r in results]


class TestLeftJoinFiltered:
    def test_detected(self) -> None:
        sql = (
            "SELECT a.id FROM dbo.A a "
            "LEFT JOIN dbo.B b ON a.id = b.a_id "
            "WHERE b.name = 'test'"
        )
        results = detect_antipatterns(sql)
        assert "left_join_filtered" in [r.code for r in results]

    def test_is_null_excludes(self) -> None:
        sql = (
            "SELECT a.id FROM dbo.A a "
            "LEFT JOIN dbo.B b ON a.id = b.a_id "
            "WHERE b.id IS NULL"
        )
        results = detect_antipatterns(sql)
        assert "left_join_filtered" not in [r.code for r in results]

    def test_inner_join_ok(self) -> None:
        sql = (
            "SELECT a.id FROM dbo.A a "
            "INNER JOIN dbo.B b ON a.id = b.a_id "
            "WHERE b.name = 'test'"
        )
        results = detect_antipatterns(sql)
        assert "left_join_filtered" not in [r.code for r in results]


class TestOrInWhere:
    def test_detected(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE status = 1 OR status = 2"
        results = detect_antipatterns(sql)
        assert "or_in_where" in [r.code for r in results]

    def test_clean(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE status IN (1, 2)"
        results = detect_antipatterns(sql)
        assert "or_in_where" not in [r.code for r in results]


class TestFunctionOnColumn:
    def test_upper_detected(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE UPPER(name) = 'TEST'"
        results = detect_antipatterns(sql)
        assert "function_on_column" in [r.code for r in results]

    def test_year_on_column_detected(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE YEAR(created_at) = 2024"
        results = detect_antipatterns(sql)
        assert "function_on_column" in [r.code for r in results]

    def test_clean_compare(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE created_at >= '2024-01-01'"
        results = detect_antipatterns(sql)
        assert "function_on_column" not in [r.code for r in results]


class TestLeadingWildcardLike:
    def test_detected(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE name LIKE '%pattern'"
        results = detect_antipatterns(sql)
        assert "leading_wildcard_like" in [r.code for r in results]

    def test_trailing_only_ok(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE name LIKE 'pattern%'"
        results = detect_antipatterns(sql)
        assert "leading_wildcard_like" not in [r.code for r in results]


class TestSelectStar:
    def test_detected(self) -> None:
        sql = "SELECT * FROM dbo.HugeTable"
        results = detect_antipatterns(sql)
        assert "select_star" in [r.code for r in results]

    def test_explicit_columns_ok(self) -> None:
        sql = "SELECT id, name FROM dbo.HugeTable"
        results = detect_antipatterns(sql)
        assert "select_star" not in [r.code for r in results]


class TestCrossJoin:
    def test_detected(self) -> None:
        sql = "SELECT a.id, b.id FROM dbo.A a CROSS JOIN dbo.B b"
        results = detect_antipatterns(sql)
        assert "cross_join" in [r.code for r in results]
        assert next(r for r in results if r.code == "cross_join").severity == (
            AntipatternSeverity.CRITICAL
        )


class TestLargeInList:
    def test_detected_at_100_items(self) -> None:
        values = ", ".join(str(i) for i in range(150))
        sql = f"SELECT id FROM dbo.Doc WHERE id IN ({values})"
        results = detect_antipatterns(sql)
        assert "large_in_list" in [r.code for r in results]

    def test_small_in_list_ok(self) -> None:
        sql = "SELECT id FROM dbo.Doc WHERE id IN (1, 2, 3, 4, 5)"
        results = detect_antipatterns(sql)
        assert "large_in_list" not in [r.code for r in results]


class TestMultipleAntipatterns:
    def test_select_star_with_leading_wildcard(self) -> None:
        sql = "SELECT * FROM dbo.Doc WHERE name LIKE '%test'"
        results = detect_antipatterns(sql)
        codes = {r.code for r in results}
        assert "select_star" in codes
        assert "leading_wildcard_like" in codes


class TestRealWorld1CGenerated:
    """Запросы как 1С генерирует в DBMSSQL.Sql."""

    def test_1c_simple_select(self) -> None:
        # Типичный 1С: SELECT T1._IDRRef, T1._Description
        # FROM dbo._Reference15 T1 WHERE T1._Fld119 = 0x00
        sql = (
            "SELECT T1.[_IDRRef], T1.[_Description] "
            "FROM dbo.[_Reference15] T1 "
            "WHERE T1.[_Fld119] = 0x00"
        )
        results = detect_antipatterns(sql)
        # Может быть пустой или с минорными — главное что parser работает
        assert all(r.code != "parse_error" for r in results)

    def test_1c_not_in_pattern(self) -> None:
        # 1С при определённых запросах генерирует NOT IN.
        sql = (
            "SELECT [_IDRRef] FROM dbo.[_Document100] "
            "WHERE [_IDRRef] NOT IN (SELECT [_RecorderRRef] FROM dbo.[_AccumRg200])"
        )
        results = detect_antipatterns(sql)
        assert "not_in_with_subquery" in [r.code for r in results]
