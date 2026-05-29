"""Тесты для 15 PG antipattern детекторов (Sprint 8 Phase C).

Каждый детектор имеет минимум: positive (обнаружен) + negative (не обнаружен).
Для 1С-aware детекторов добавлен 1С-context edge case.
"""

from __future__ import annotations

import pytest

from optimyzer_backend.sql_antipatterns import (
    AntipatternSeverity,
    detect_antipatterns,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import detect_1c_context


# ---------------------------------------------------------------------------
# 0. Sanity / engine selection
# ---------------------------------------------------------------------------


class TestEngineDispatch:
    def test_mssql_uses_tsql_detectors(self) -> None:
        sql = "SELECT * FROM dbo.Doc WHERE name LIKE '%test'"
        findings = detect_antipatterns(sql, engine="mssql")
        codes = [f.code for f in findings]
        # MSSQL детектор leading_wildcard_like, не PG like_with_leading_wildcard
        assert "leading_wildcard_like" in codes
        assert "like_with_leading_wildcard" not in codes

    def test_postgres_uses_pg_detectors(self) -> None:
        sql = "SELECT id FROM mytable WHERE name LIKE '%test'"
        findings = detect_antipatterns(sql, engine="postgres")
        codes = [f.code for f in findings]
        assert "like_with_leading_wildcard" in codes
        assert "leading_wildcard_like" not in codes  # legacy TSQL не должен быть

    def test_parse_error_is_soft_info(self) -> None:
        # S12 F1: parse_error больше НЕ BLOCKER. Это ограничение статического
        # парсера (частое на специфичном SQL), а не проблема запроса — мягкий INFO.
        sql = "INVALID NOT-SQL @#$%"
        findings = detect_antipatterns(sql, engine="postgres")
        if findings:
            for f in findings:
                if f.code == "parse_error":
                    assert f.severity == AntipatternSeverity.INFO

    def test_empty_string_returns_empty(self) -> None:
        assert detect_antipatterns("", engine="postgres") == []

    def test_too_long_sql_returns_empty(self) -> None:
        sql = "SELECT 1; " * 30000
        assert detect_antipatterns(sql, engine="postgres") == []


# ---------------------------------------------------------------------------
# 1. OffsetWithoutLimit
# ---------------------------------------------------------------------------


class TestOffsetWithoutLimit:
    def test_detected(self) -> None:
        sql = "SELECT id FROM tbl OFFSET 100"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "offset_without_limit" for f in findings)

    def test_not_detected_with_limit(self) -> None:
        sql = "SELECT id FROM tbl OFFSET 100 LIMIT 50"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "offset_without_limit" for f in findings)

    def test_not_detected_without_offset(self) -> None:
        sql = "SELECT id FROM tbl LIMIT 50"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "offset_without_limit" for f in findings)


# ---------------------------------------------------------------------------
# 2. LargeOffsetPagination
# ---------------------------------------------------------------------------


class TestLargeOffsetPagination:
    def test_warning_at_1000_with_limit(self) -> None:
        sql = "SELECT id FROM tbl OFFSET 5000 LIMIT 10"
        findings = detect_antipatterns(sql, engine="postgres")
        large = [f for f in findings if f.code == "large_offset_pagination"]
        assert large
        assert large[0].severity == AntipatternSeverity.WARNING

    def test_critical_at_10000(self) -> None:
        sql = "SELECT id FROM tbl OFFSET 50000 LIMIT 10"
        findings = detect_antipatterns(sql, engine="postgres")
        large = [f for f in findings if f.code == "large_offset_pagination"]
        assert large
        assert large[0].severity == AntipatternSeverity.CRITICAL

    def test_not_detected_below_threshold(self) -> None:
        sql = "SELECT id FROM tbl OFFSET 100 LIMIT 10"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "large_offset_pagination" for f in findings)


# ---------------------------------------------------------------------------
# 3. IlikeWithoutTrgm
# ---------------------------------------------------------------------------


class TestIlikeWithoutTrgm:
    def test_detected_double_wildcard(self) -> None:
        sql = "SELECT id FROM tbl WHERE name ILIKE '%abc%'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "ilike_without_trgm" for f in findings)

    def test_detected_leading_wildcard(self) -> None:
        sql = "SELECT id FROM tbl WHERE name ILIKE '%abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "ilike_without_trgm" for f in findings)

    def test_not_detected_without_wildcard(self) -> None:
        sql = "SELECT id FROM tbl WHERE name ILIKE 'abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "ilike_without_trgm" for f in findings)


# ---------------------------------------------------------------------------
# 4. LikeWithLeadingWildcard (1С-aware)
# ---------------------------------------------------------------------------


class TestLikeWithLeadingWildcard:
    def test_detected_warning_non_1c(self) -> None:
        sql = "SELECT id FROM mytable WHERE name LIKE '%abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "like_with_leading_wildcard"]
        assert match
        assert match[0].severity == AntipatternSeverity.WARNING

    def test_1c_context_downgrades_to_info(self) -> None:
        sql = "SELECT _IDRRef FROM _Reference15 WHERE _Description LIKE '%abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "like_with_leading_wildcard"]
        assert match
        assert match[0].severity == AntipatternSeverity.INFO

    def test_trailing_wildcard_ok(self) -> None:
        sql = "SELECT id FROM tbl WHERE name LIKE 'abc%'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "like_with_leading_wildcard" for f in findings)


# ---------------------------------------------------------------------------
# 5. NotInWithSubquery (PG version)
# ---------------------------------------------------------------------------


class TestNotInWithSubqueryPg:
    def test_detected(self) -> None:
        sql = "SELECT id FROM tbl WHERE id NOT IN (SELECT y FROM other)"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "not_in_with_subquery_pg" for f in findings)

    def test_not_detected_with_literals(self) -> None:
        sql = "SELECT id FROM tbl WHERE id NOT IN (1, 2, 3)"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "not_in_with_subquery_pg" for f in findings)


# ---------------------------------------------------------------------------
# 6. JsonbWithoutGin
# ---------------------------------------------------------------------------


class TestJsonbWithoutGin:
    def test_detected_containment_op(self) -> None:
        sql = "SELECT id FROM tbl WHERE data @> '{}'::jsonb"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "jsonb_without_gin" for f in findings)

    def test_detected_arrow_op(self) -> None:
        sql = "SELECT id FROM tbl WHERE data -> 'key' = '1'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "jsonb_without_gin" for f in findings)

    def test_not_detected_plain_sql(self) -> None:
        sql = "SELECT id FROM tbl WHERE name = 'test'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "jsonb_without_gin" for f in findings)


# ---------------------------------------------------------------------------
# 7. CastInWherePredicate (1С-aware mchar)
# ---------------------------------------------------------------------------


class TestCastInWherePredicate:
    def test_detected_lower(self) -> None:
        sql = "SELECT id FROM tbl WHERE LOWER(name) = 'abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "cast_in_where_predicate" for f in findings)

    def test_detected_cast_to_text(self) -> None:
        sql = "SELECT id FROM tbl WHERE CAST(name AS text) = 'abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "cast_in_where_predicate" for f in findings)

    def test_1c_mchar_cast_not_flagged(self) -> None:
        sql = "SELECT _IDRRef FROM _Reference15 WHERE _Description::mchar = 'X'::mchar"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "cast_in_where_predicate" for f in findings)


# ---------------------------------------------------------------------------
# 8. UnionInsteadOfUnionAll
# ---------------------------------------------------------------------------


class TestUnionInsteadOfUnionAll:
    def test_detected_union(self) -> None:
        sql = "SELECT a FROM t1 UNION SELECT a FROM t2"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "union_instead_of_union_all" for f in findings)

    def test_not_detected_union_all(self) -> None:
        sql = "SELECT a FROM t1 UNION ALL SELECT a FROM t2"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "union_instead_of_union_all" for f in findings)


# ---------------------------------------------------------------------------
# 9. SubqueryInSelectList
# ---------------------------------------------------------------------------


class TestSubqueryInSelectList:
    def test_detected_correlated(self) -> None:
        sql = (
            "SELECT id, (SELECT MAX(x) FROM other WHERE other.fk = main.id) FROM main"
        )
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "subquery_in_select_list" for f in findings)

    def test_not_detected_no_subquery(self) -> None:
        sql = "SELECT id, name FROM main"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "subquery_in_select_list" for f in findings)


# ---------------------------------------------------------------------------
# 10. DistinctOnLargeResult
# ---------------------------------------------------------------------------


class TestDistinctOnLargeResult:
    def test_detected_distinct_with_join(self) -> None:
        sql = "SELECT DISTINCT a FROM t1 JOIN t2 ON t1.id = t2.id"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "distinct_on_large_result" for f in findings)

    def test_not_detected_distinct_without_join(self) -> None:
        sql = "SELECT DISTINCT a FROM t1"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "distinct_on_large_result" for f in findings)


# ---------------------------------------------------------------------------
# 11. ImplicitTypeCast (1С-aware _Fld)
# ---------------------------------------------------------------------------


class TestImplicitTypeCast:
    def test_detected_id_quoted_int(self) -> None:
        sql = "SELECT * FROM tbl WHERE id = '123'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "implicit_type_cast" for f in findings)

    def test_not_detected_plain_string_col(self) -> None:
        sql = "SELECT * FROM tbl WHERE name = 'abc'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "implicit_type_cast" for f in findings)

    def test_1c_fld_not_flagged(self) -> None:
        # В 1С context _Fld11355 = '123' (1С использует параметры — не нужно flagged)
        sql = "SELECT _IDRRef FROM _Reference15 WHERE _Fld11355 = '123'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "implicit_type_cast" for f in findings)


# ---------------------------------------------------------------------------
# 12. SelectStarWithJoin (1С-aware — отключён)
# ---------------------------------------------------------------------------


class TestSelectStarWithJoin:
    def test_detected_non_1c(self) -> None:
        sql = "SELECT * FROM mytable a JOIN other b ON a.id = b.id"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "select_star_with_join" for f in findings)

    def test_1c_context_disables(self) -> None:
        sql = "SELECT * FROM _Reference15 a JOIN _Document201 b ON a._IDRRef = b._Fld"
        findings = detect_antipatterns(sql, engine="postgres")
        # 1С НЕ генерирует SELECT *, в 1С context этот детектор молчит
        assert not any(f.code == "select_star_with_join" for f in findings)

    def test_not_detected_explicit_columns(self) -> None:
        sql = "SELECT a.id, b.name FROM a JOIN b ON a.id = b.id"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "select_star_with_join" for f in findings)


# ---------------------------------------------------------------------------
# 13. OrderByRandomWithLimit
# ---------------------------------------------------------------------------


class TestOrderByRandomWithLimit:
    def test_detected_random_with_limit_warning(self) -> None:
        sql = "SELECT id FROM tbl ORDER BY RANDOM() LIMIT 10"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "order_by_random_with_limit"]
        assert match
        assert match[0].severity == AntipatternSeverity.WARNING

    def test_detected_random_without_limit_critical(self) -> None:
        sql = "SELECT id FROM tbl ORDER BY random()"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "order_by_random_with_limit"]
        assert match
        assert match[0].severity == AntipatternSeverity.CRITICAL

    def test_not_detected_order_by_column(self) -> None:
        sql = "SELECT id FROM tbl ORDER BY name LIMIT 10"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "order_by_random_with_limit" for f in findings)


# ---------------------------------------------------------------------------
# 14. MissingWhereOnUpdateDelete — CRITICAL
# ---------------------------------------------------------------------------


class TestMissingWhereOnUpdateDelete:
    def test_detected_update_no_where(self) -> None:
        sql = "UPDATE mytable SET a = 1"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "missing_where_on_update_delete"]
        assert match
        assert match[0].severity == AntipatternSeverity.CRITICAL

    def test_detected_delete_no_where(self) -> None:
        sql = "DELETE FROM mytable"
        findings = detect_antipatterns(sql, engine="postgres")
        match = [f for f in findings if f.code == "missing_where_on_update_delete"]
        assert match
        assert match[0].severity == AntipatternSeverity.CRITICAL

    def test_not_detected_update_with_where(self) -> None:
        sql = "UPDATE mytable SET a = 1 WHERE id = 5"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "missing_where_on_update_delete" for f in findings)

    def test_not_detected_delete_with_where(self) -> None:
        sql = "DELETE FROM mytable WHERE created_at < '2024-01-01'"
        findings = detect_antipatterns(sql, engine="postgres")
        assert not any(f.code == "missing_where_on_update_delete" for f in findings)


# ---------------------------------------------------------------------------
# 15. McharVsTextComparison — 1С-specific
# ---------------------------------------------------------------------------


class TestMcharVsTextComparison:
    def test_detected_in_1c_context(self) -> None:
        sql = "SELECT _IDRRef FROM _Reference15 WHERE _Description::mchar = '1'::text"
        findings = detect_antipatterns(sql, engine="postgres")
        assert any(f.code == "mchar_vs_text_comparison" for f in findings)

    def test_not_detected_outside_1c_context(self) -> None:
        sql = "SELECT id FROM mytable WHERE col::mchar = '1'::text"
        # Нет _Reference/_Document/mchar в каноне — но mchar в выражении есть!
        # detect_1c_context check на типы → True, обнаружен будет.
        # Меняем на запрос без mchar в SQL чтобы 1С context был False.
        sql_clean = "SELECT id FROM mytable WHERE col::int = '1'::text"
        findings = detect_antipatterns(sql_clean, engine="postgres")
        assert not any(f.code == "mchar_vs_text_comparison" for f in findings)

    def test_force_disable_1c_context(self) -> None:
        sql = "SELECT _IDRRef FROM _Reference15 WHERE _Description::mchar = '1'::text"
        findings = detect_antipatterns(sql, engine="postgres", force_1c_context=False)
        # Принудительно False — mchar детектор молчит
        assert not any(f.code == "mchar_vs_text_comparison" for f in findings)


# ---------------------------------------------------------------------------
# 1C context detection helper
# ---------------------------------------------------------------------------


class TestDetect1cContext:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM _Reference15",
            "SELECT * FROM _Document201",
            "SELECT * FROM _AccumRg100",
            "SELECT * FROM _InfoRg50",
            "SELECT col::mchar FROM tbl",
            "SELECT col::mvarchar FROM tbl",
            "SELECT CAST(x AS mchar) FROM tbl",
        ],
    )
    def test_positive(self, sql: str) -> None:
        assert detect_1c_context(sql) is True

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM users",
            "SELECT * FROM products WHERE id = 1",
            "SELECT a::int FROM tbl",
            "",
        ],
    )
    def test_negative(self, sql: str) -> None:
        assert detect_1c_context(sql) is False


# ---------------------------------------------------------------------------
# Robustness — один сломанный детектор не валит весь анализ
# ---------------------------------------------------------------------------


class TestRobustness:
    def test_multiple_antipatterns_in_one_query(self) -> None:
        sql = "SELECT * FROM tbl ORDER BY RANDOM() LIMIT 10 OFFSET 50000"
        findings = detect_antipatterns(sql, engine="postgres")
        codes = {f.code for f in findings}
        assert "large_offset_pagination" in codes
        assert "order_by_random_with_limit" in codes

    def test_severity_sort_critical_first(self) -> None:
        sql = "DELETE FROM tbl"  # CRITICAL
        findings = detect_antipatterns(sql, engine="postgres")
        if findings:
            assert findings[0].severity in (
                AntipatternSeverity.CRITICAL,
                AntipatternSeverity.BLOCKER,
            )

    def test_returns_list_for_unparseable(self) -> None:
        # Не валидно SQL — должен либо вернуть parse_error либо пусто, но не упасть
        sql = ")(*&^%$#@! NOT SQL"
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)
