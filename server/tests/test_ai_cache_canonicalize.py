"""Sprint 11 Phase A — тесты canonicalization helpers.

Цель — убедиться что логически одинаковые входы (с разными runtime stats,
форматированием, порядком атрибутов) дают одинаковый canonical output и
одинаковый cache key.
"""

from __future__ import annotations

import json

import pytest

from services.ai_cache.canonicalize import (
    canonicalize_logcfg_description,
    canonicalize_plan_mssql_text,
    canonicalize_plan_mssql_xml,
    canonicalize_plan_pg_json,
    canonicalize_plan_pg_text,
    canonicalize_sdbl,
    compute_cache_key,
)
from services.ai_cache.models import CacheType


# ============================================================================
# MSSQL XML canonicalization
# ============================================================================


class TestCanonicalizePlanMssqlXml:
    def test_same_plan_different_actual_rows_same_canonical(self):
        plan1 = (
            '<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">'
            '<BatchSequence><Batch><Statements>'
            '<StmtSimple StatementId="1" EstimatedRows="100" ActualRows="100">'
            '<QueryPlan/>'
            '</StmtSimple>'
            '</Statements></Batch></BatchSequence>'
            '</ShowPlanXML>'
        )
        plan2 = (
            '<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">'
            '<BatchSequence><Batch><Statements>'
            '<StmtSimple StatementId="1" EstimatedRows="100" ActualRows="500">'
            '<QueryPlan/>'
            '</StmtSimple>'
            '</Statements></Batch></BatchSequence>'
            '</ShowPlanXML>'
        )
        assert canonicalize_plan_mssql_xml(plan1) == canonicalize_plan_mssql_xml(
            plan2
        )

    def test_attribute_order_doesnt_matter(self):
        plan_a_first = '<Op a="1" z="2"/>'
        plan_z_first = '<Op z="2" a="1"/>'
        assert canonicalize_plan_mssql_xml(
            plan_a_first
        ) == canonicalize_plan_mssql_xml(plan_z_first)

    def test_removes_actualcpums_actualelapsedms(self):
        plan = (
            '<RelOp NodeId="0" EstimatedRows="100" '
            'ActualCPUms="123" ActualElapsedms="456"/>'
        )
        canonical = canonicalize_plan_mssql_xml(plan)
        assert "ActualCPUms" not in canonical
        assert "ActualElapsedms" not in canonical
        assert "EstimatedRows" in canonical  # этот должен остаться

    def test_different_estimated_rows_different_canonical(self):
        """EstimatedRows — НЕ runtime, оптимизатор использует. Должен влиять на key."""
        plan1 = '<Op EstimatedRows="100"/>'
        plan2 = '<Op EstimatedRows="1000"/>'
        assert canonicalize_plan_mssql_xml(
            plan1
        ) != canonicalize_plan_mssql_xml(plan2)

    def test_invalid_xml_fallback(self):
        """Невалидный XML → fallback на whitespace collapse."""
        bad = "<<<not xml>>>"
        # Не должен бросать exception
        result = canonicalize_plan_mssql_xml(bad)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_xml_doesnt_crash(self):
        result = canonicalize_plan_mssql_xml("")
        assert isinstance(result, str)


# ============================================================================
# MSSQL TEXT canonicalization
# ============================================================================


class TestCanonicalizePlanMssqlText:
    def test_whitespace_normalized(self):
        plan1 = "|--Clustered Index Seek\n|     Estimated Rows = 100"
        plan2 = "|--Clustered Index Seek    \n|\t\tEstimated Rows = 100"
        assert canonicalize_plan_mssql_text(
            plan1
        ) == canonicalize_plan_mssql_text(plan2)

    def test_sqlcmd_line_numbers_removed(self):
        with_lines = "1> SELECT *\n2> FROM t"
        without_lines = "SELECT *\nFROM t"
        assert canonicalize_plan_mssql_text(
            with_lines
        ) == canonicalize_plan_mssql_text(without_lines)

    def test_float_precision_truncated(self):
        plan1 = "Estimated IO Cost = 0.001234"
        plan2 = "Estimated IO Cost = 0.001235"
        assert canonicalize_plan_mssql_text(
            plan1
        ) == canonicalize_plan_mssql_text(plan2)


# ============================================================================
# PG TEXT canonicalization
# ============================================================================


class TestCanonicalizePlanPgText:
    def test_actual_time_removed(self):
        plan1 = (
            "Seq Scan on t (cost=0.00..15.00 rows=500 width=20) "
            "(actual time=0.123..0.456 rows=500 loops=1)"
        )
        plan2 = (
            "Seq Scan on t (cost=0.00..15.00 rows=500 width=20) "
            "(actual time=10.000..20.000 rows=500 loops=1)"
        )
        assert canonicalize_plan_pg_text(plan1) == canonicalize_plan_pg_text(
            plan2
        )

    def test_buffers_lines_removed(self):
        plan1 = "Seq Scan on t\n  Buffers: shared hit=10 read=5\n"
        plan2 = "Seq Scan on t\n  Buffers: shared hit=999 read=888\n"
        assert canonicalize_plan_pg_text(plan1) == canonicalize_plan_pg_text(
            plan2
        )

    def test_planning_execution_time_removed(self):
        plan1 = "Seq Scan\nPlanning Time: 0.123 ms\nExecution Time: 4.567 ms"
        plan2 = "Seq Scan\nPlanning Time: 1.000 ms\nExecution Time: 9.999 ms"
        assert canonicalize_plan_pg_text(plan1) == canonicalize_plan_pg_text(
            plan2
        )

    def test_jit_lines_removed(self):
        plan1 = "Seq Scan\nJIT:\n  Functions: 4\n  Optimization: false\n  Timing: { Generation: 0.5 ms, Inlining: 0.0 ms }"
        plan2 = "Seq Scan\nJIT:\n  Functions: 5\n  Optimization: true\n  Timing: { Generation: 1.5 ms, Inlining: 0.2 ms }"
        assert canonicalize_plan_pg_text(plan1) == canonicalize_plan_pg_text(
            plan2
        )


# ============================================================================
# PG JSON canonicalization
# ============================================================================


class TestCanonicalizePlanPgJson:
    def test_actual_runtime_keys_stripped(self):
        plan1 = json.dumps(
            [
                {
                    "Plan": {
                        "Node Type": "Seq Scan",
                        "Total Cost": 15.0,
                        "Actual Rows": 500,
                        "Actual Total Time": 4.567,
                        "Actual Loops": 1,
                    }
                }
            ]
        )
        plan2 = json.dumps(
            [
                {
                    "Plan": {
                        "Node Type": "Seq Scan",
                        "Total Cost": 15.0,
                        "Actual Rows": 99999,
                        "Actual Total Time": 9999.0,
                        "Actual Loops": 50,
                    }
                }
            ]
        )
        assert canonicalize_plan_pg_json(plan1) == canonicalize_plan_pg_json(
            plan2
        )

    def test_buffers_stripped(self):
        plan1 = json.dumps(
            {"Plan": {"Node Type": "Seq Scan", "Buffers": {"Shared Hit": 10}}}
        )
        plan2 = json.dumps(
            {"Plan": {"Node Type": "Seq Scan", "Buffers": {"Shared Hit": 9999}}}
        )
        assert canonicalize_plan_pg_json(plan1) == canonicalize_plan_pg_json(
            plan2
        )

    def test_keys_sorted_deterministically(self):
        plan_a = json.dumps({"Plan": {"a": 1, "b": 2, "c": 3}})
        plan_b = json.dumps({"Plan": {"c": 3, "b": 2, "a": 1}})
        assert canonicalize_plan_pg_json(plan_a) == canonicalize_plan_pg_json(
            plan_b
        )

    def test_invalid_json_fallback(self):
        bad = "{not valid json"
        # Should not raise
        result = canonicalize_plan_pg_json(bad)
        assert isinstance(result, str)

    def test_node_type_preserved(self):
        plan = json.dumps({"Plan": {"Node Type": "Hash Join"}})
        canonical = canonicalize_plan_pg_json(plan)
        assert "Hash Join" in canonical


# ============================================================================
# SDBL canonicalization
# ============================================================================


class TestCanonicalizeSdbl:
    def test_whitespace_collapsed(self):
        sdbl1 = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты"
        sdbl2 = "ВЫБРАТЬ\n  *\n  ИЗ\t\tСправочник.Контрагенты"
        assert canonicalize_sdbl(sdbl1) == canonicalize_sdbl(sdbl2)

    def test_line_comments_removed(self):
        with_comment = "ВЫБРАТЬ * // это комментарий\nИЗ Т"
        without = "ВЫБРАТЬ * \nИЗ Т"
        assert canonicalize_sdbl(with_comment) == canonicalize_sdbl(without)

    def test_block_comments_removed(self):
        with_comment = "ВЫБРАТЬ /* TODO */ * ИЗ Т"
        without = "ВЫБРАТЬ  * ИЗ Т"
        assert canonicalize_sdbl(with_comment) == canonicalize_sdbl(without)

    def test_different_queries_different_canonical(self):
        sdbl1 = "ВЫБРАТЬ ПЕРВЫЕ 1 * ИЗ Т"
        sdbl2 = "ВЫБРАТЬ ПЕРВЫЕ 10 * ИЗ Т"
        assert canonicalize_sdbl(sdbl1) != canonicalize_sdbl(sdbl2)


# ============================================================================
# Logcfg description canonicalization
# ============================================================================


class TestCanonicalizeLogcfgDescription:
    def test_case_insensitive(self):
        d1 = "Медленный отчёт по продажам"
        d2 = "медленный ОТЧЁТ по продажам"
        assert canonicalize_logcfg_description(
            d1
        ) == canonicalize_logcfg_description(d2)

    def test_punctuation_normalized(self):
        d1 = "Медленно работает, нужна оптимизация!"
        d2 = "Медленно работает нужна оптимизация"
        assert canonicalize_logcfg_description(
            d1
        ) == canonicalize_logcfg_description(d2)

    def test_whitespace_collapsed(self):
        d1 = "Слово1   Слово2"
        d2 = "Слово1 Слово2"
        assert canonicalize_logcfg_description(
            d1
        ) == canonicalize_logcfg_description(d2)

    def test_different_descriptions_different_canonical(self):
        d1 = "Медленные SQL запросы"
        d2 = "Утечки памяти"
        assert canonicalize_logcfg_description(
            d1
        ) != canonicalize_logcfg_description(d2)


# ============================================================================
# Cache key computation
# ============================================================================


class TestComputeCacheKey:
    def test_deterministic(self):
        key1 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        key2 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        assert key1 == key2

    def test_different_inputs_different_keys(self):
        key1 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        key2 = compute_cache_key("y", "plan_mssql_xml", "v1", "haiku")
        assert key1 != key2

    def test_different_types_different_keys(self):
        """Same input, different cache type → different key."""
        key1 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        key2 = compute_cache_key("x", "plan_pg_text", "v1", "haiku")
        assert key1 != key2

    def test_different_prompt_version_different_keys(self):
        """Это критично для invalidation — bump v1→v2 invalidates кеш."""
        key_v1 = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        key_v2 = compute_cache_key("x", "plan_mssql_xml", "v2", "haiku")
        assert key_v1 != key_v2

    def test_different_model_different_keys(self):
        key_haiku = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku-4-5")
        key_sonnet = compute_cache_key(
            "x", "plan_mssql_xml", "v1", "sonnet-4-5"
        )
        assert key_haiku != key_sonnet

    def test_key_length_is_sha256_hex(self):
        key = compute_cache_key("x", "plan_mssql_xml", "v1", "haiku")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_cache_type_enum_values_stable(self):
        """Имена CacheType стабильны — нельзя менять без миграции."""
        assert CacheType.PLAN_MSSQL_XML.value == "plan_mssql_xml"
        assert CacheType.PLAN_MSSQL_TEXT.value == "plan_mssql_text"
        assert CacheType.PLAN_PG_TEXT.value == "plan_pg_text"
        assert CacheType.PLAN_PG_JSON.value == "plan_pg_json"
        assert CacheType.QUERY.value == "query"
        assert CacheType.LOGCFG.value == "logcfg"
        assert CacheType.REGRESSION.value == "regression"
