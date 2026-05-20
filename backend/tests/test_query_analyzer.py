"""Sprint 4 — Query Analyzer unit tests.

Покрывает:
  - Native rule loader (загрузка markdown файлов с YAML frontmatter)
  - Native engine (matcher + line/col conversion)
  - Aggregator (объединение native + BSL LS placeholder, дедупликация, summary)
  - BSL LS client (placeholder — всегда disabled)
  - Solution generator (placeholder — всегда 501)
  - Cache (нормализация запроса + put/get)
  - RPC dispatch
  - Каждое native rule — positive + negative тест

AI rewriter live tests — в test_sprint4_real_data.py (требует ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from optimyzer_backend.query_analyzer.aggregator import QueryAnalyzer
from optimyzer_backend.query_analyzer.bsl_ls_client import (
    BSLDiagnostic,
    BSLLanguageServerClient,
)
from optimyzer_backend.query_analyzer.native_rules import (
    Finding,
    NativeRule,
    analyze as native_analyze,
    load_native_rules,
    _offset_to_line_col,
)
from optimyzer_backend.query_analyzer.query_cache import (
    QueryRewriteCache,
    QueryRewriteEntry,
    compute_cache_key,
    normalize_query,
)
from optimyzer_backend.query_analyzer.solution_generator import SolutionGenerator


# ---------- Helpers ----------


def _rules_dir() -> Path:
    """Каноничный путь к rules — `backend/query_analyzer_rules/`."""
    return Path(__file__).resolve().parents[1] / "query_analyzer_rules"


# ---------- Native loader ----------


class TestNativeRuleLoader:
    def test_loads_all_native_rules(self) -> None:
        rules = load_native_rules(_rules_dir())
        assert len(rules) >= 12, f"Ожидаем минимум 12 native rules, нашли {len(rules)}"

    def test_each_rule_has_required_fields(self) -> None:
        rules = load_native_rules(_rules_dir())
        for r in rules:
            assert r.id, f"Правило без id: {r.source_file}"
            assert r.severity in ("critical", "warning", "info"), f"{r.id}: bad severity {r.severity}"
            assert r.category in ("performance", "correctness", "style"), f"{r.id}: bad category"
            assert len(r.patterns) >= 1, f"{r.id}: нет patterns (regex невалиден?)"
            assert r.title, f"{r.id}: нет title"

    def test_rule_ids_are_unique(self) -> None:
        rules = load_native_rules(_rules_dir())
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids)), f"Дубли в id: {[i for i in ids if ids.count(i) > 1]}"

    def test_missing_dir_returns_empty(self) -> None:
        assert load_native_rules(Path("/no/such/dir")) == []

    def test_broken_rule_silently_skipped(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.md"
        bad.write_text("not a valid frontmatter file", encoding="utf-8")
        good = tmp_path / "good.md"
        good.write_text(
            "---\nid: test_rule\nseverity: warning\ncategory: performance\n"
            "patterns:\n  - '(?i)test'\n---\n# Test\n",
            encoding="utf-8",
        )
        rules = load_native_rules(tmp_path)
        assert len(rules) == 1
        assert rules[0].id == "test_rule"


# ---------- Native engine ----------


class TestNativeEngine:
    def test_empty_query_returns_no_findings(self) -> None:
        rules = load_native_rules(_rules_dir())
        assert native_analyze("", rules) == []

    def test_clean_query_returns_no_findings(self) -> None:
        rules = load_native_rules(_rules_dir())
        query = """
        ВЫБРАТЬ Док.Ссылка, Док.Дата
        ИЗ Документ.РеализацияТоваровУслуг КАК Док
        ГДЕ Док.Проведён = ИСТИНА
        УПОРЯДОЧИТЬ ПО Док.Дата УБЫВ
        """
        findings = native_analyze(query, rules)
        # Чистый запрос — могут быть info, но не должно быть critical
        critical = [f for f in findings if f.severity == "critical"]
        assert critical == [], f"Чистый запрос дал critical findings: {[f.rule_id for f in critical]}"


class TestOffsetToLineCol:
    def test_first_char(self) -> None:
        assert _offset_to_line_col("hello", 0) == (1, 1)

    def test_middle_of_line(self) -> None:
        assert _offset_to_line_col("hello world", 6) == (1, 7)

    def test_second_line(self) -> None:
        assert _offset_to_line_col("hello\nworld", 6) == (2, 1)

    def test_crlf_treated_as_one_separator(self) -> None:
        # offset после \r\n должен быть на line 2 col 1
        assert _offset_to_line_col("abc\r\ndef", 5) == (2, 1)

    def test_offset_at_end(self) -> None:
        # offset за пределами — clamp to last
        line, col = _offset_to_line_col("abc", 100)
        assert line == 1


# ---------- BSL LS placeholder ----------


class TestBSLLSPlaceholder:
    def test_always_unavailable_in_sprint4(self) -> None:
        client = BSLLanguageServerClient()
        assert client.available is False

    def test_analyze_returns_empty(self) -> None:
        client = BSLLanguageServerClient()
        assert client.analyze_query("ВЫБРАТЬ * ИЗ Тов") == []

    def test_diagnostic_dataclass_shape(self) -> None:
        d = BSLDiagnostic(
            line_start=1, line_end=2, col_start=1, col_end=5,
            severity="warning", code="XYZ", message="m",
        )
        assert d.source == "bsl-language-server"


# ---------- Aggregator ----------


class TestQueryAnalyzer:
    def test_loads_rules_on_init(self) -> None:
        analyzer = QueryAnalyzer(_rules_dir())
        assert len(analyzer.native_rules) >= 12
        assert analyzer.bsl_ls_available is False

    def test_analyze_empty_query(self) -> None:
        analyzer = QueryAnalyzer(_rules_dir())
        result = analyzer.analyze("")
        assert result["findings"] == []
        assert result["summary"]["critical"] == 0
        assert result["bsl_ls_available"] is False
        assert result["rules_count"] >= 12

    def test_analyze_bad_query_returns_findings(self) -> None:
        analyzer = QueryAnalyzer(_rules_dir())
        bad_query = """ВЫБРАТЬ *
        ИЗ Документ.А КАК А, Документ.Б КАК Б
        ГДЕ А.Артикул = "X" ИЛИ А.Артикул = "Y"
        """
        result = analyzer.analyze(bad_query)
        assert len(result["findings"]) >= 3, f"Ожидаем ≥3 findings, нашли {len(result['findings'])}"
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "select_star" in rule_ids
        assert "comma_join_implicit" in rule_ids

    def test_findings_sorted_by_position(self) -> None:
        analyzer = QueryAnalyzer(_rules_dir())
        query = """
        ВЫБРАТЬ * ИЗ Тов
        ГДЕ Артикул = "A" ИЛИ Артикул = "B"
        """
        result = analyzer.analyze(query)
        positions = [(f["line_start"], f["col_start"]) for f in result["findings"]]
        assert positions == sorted(positions), "findings должны быть отсортированы по позиции"

    def test_dedupe_same_range_same_category(self) -> None:
        """Если два rule матчат идентичный range — оставляем один."""
        from optimyzer_backend.query_analyzer.aggregator import _merge_and_dedupe
        f1 = Finding(
            source="native", rule_id="rule_a", severity="warning", category="performance",
            line_start=1, line_end=1, col_start=1, col_end=10,
            message="m", explanation_md="b",
        )
        f2 = Finding(
            source="bsl-language-server", rule_id="rule_b", severity="warning", category="performance",
            line_start=1, line_end=1, col_start=1, col_end=10,
            message="m", explanation_md="b",
        )
        merged = _merge_and_dedupe([f1, f2])
        assert len(merged) == 1
        assert merged[0].source == "native"  # native приоритетнее


# ---------- Individual rule tests (positive + negative) ----------


class TestVirtualTableInJoin:
    def test_matches_balance(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ИЗ Док.А КАК А ВНУТРЕННЕЕ СОЕДИНЕНИЕ РегистрНакопления.Тов.Остатки(&Д) КАК Б"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "virtual_table_in_join"]
        assert len(findings) >= 1

    def test_negative_no_virtual_table(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ИЗ Док.А КАК А ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Контрагенты КАК К"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "virtual_table_in_join"]
        assert findings == []


class TestSubqueryInJoin:
    def test_matches_subquery(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "СОЕДИНЕНИЕ (ВЫБРАТЬ Контрагент ИЗ Док.А) КАК Подз ПО Док.Кон = Подз.Кон"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "subquery_in_join"]
        assert len(findings) >= 1

    def test_negative_normal_join(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Контрагенты КАК К ПО А.Кон = К.Ссылка"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "subquery_in_join"]
        assert findings == []


class TestOrInWhere:
    def test_matches_or_in_where(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ Артикул = 'A' ИЛИ Артикул = 'B'"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "or_in_where"]
        assert len(findings) >= 1

    def test_negative_or_outside_where(self) -> None:
        rules = load_native_rules(_rules_dir())
        # ИЛИ есть, но нет ГДЕ
        q = "ВЫБРАТЬ Док.Ссылка ИЗ Документ.А"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "or_in_where"]
        assert findings == []


class TestInWithSubquery:
    def test_matches_in_subquery(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ Контрагент В (ВЫБРАТЬ Ссылка ИЗ Справочник.Клиенты)"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "in_with_subquery"]
        assert len(findings) >= 1

    def test_negative_in_list(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ Артикул В (&Артикул1, &Артикул2)"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "in_with_subquery"]
        assert findings == []


class TestNotInWithSubquery:
    def test_matches(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ Ссылка НЕ В (ВЫБРАТЬ Номенклатура ИЗ РегистрСведений.Цены)"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "not_in_with_subquery"]
        assert len(findings) >= 1
        assert findings[0].severity == "critical"


class TestVyrazitInWhere:
    def test_matches(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ ВЫРАЗИТЬ(Док.Контрагент КАК Справочник.Контрагенты).Наименование = 'X'"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "vyrazit_in_where"]
        assert len(findings) >= 1

    def test_negative_vyrazit_in_select(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ ВЫРАЗИТЬ(Док.Контрагент КАК Справочник.Контрагенты) ИЗ Док"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "vyrazit_in_where"]
        assert findings == []


class TestSelectDistinct:
    def test_matches_raznye(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ РАЗЛИЧНЫЕ Док.Ссылка ИЗ Док"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "select_distinct"]
        assert len(findings) >= 1


class TestUnionWithoutAll:
    def test_matches_obyedinit_without_vse(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ * ИЗ А ОБЪЕДИНИТЬ ВЫБРАТЬ * ИЗ Б"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "union_without_all"]
        assert len(findings) >= 1

    def test_negative_with_vse(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ * ИЗ А ОБЪЕДИНИТЬ ВСЕ ВЫБРАТЬ * ИЗ Б"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "union_without_all"]
        assert findings == []


class TestTempTableWithoutIndex:
    def test_matches_no_index(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = """ВЫБРАТЬ Ссылка ПОМЕСТИТЬ ВТ_Тест ИЗ Справочник.А
        ;
        ВЫБРАТЬ * ИЗ ВТ_Тест"""
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "temp_table_without_index"]
        assert len(findings) >= 1

    def test_negative_has_index(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = """ВЫБРАТЬ Ссылка ПОМЕСТИТЬ ВТ_Тест ИЗ Справочник.А
        ИНДЕКСИРОВАТЬ ПО Ссылка
        ;"""
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "temp_table_without_index"]
        assert findings == []


class TestSelectStar:
    def test_matches(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ * ИЗ Справочник.А"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "select_star"]
        assert len(findings) >= 1


class TestPervyeWithoutOrder:
    def test_matches(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ ПЕРВЫЕ 10 Док.Ссылка, Док.Дата ИЗ Документ.А КАК Док"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "pervye_without_order"]
        assert len(findings) >= 1

    def test_negative_with_order(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ВЫБРАТЬ ПЕРВЫЕ 10 Док.Ссылка ИЗ Документ.А КАК Док УПОРЯДОЧИТЬ ПО Док.Дата"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "pervye_without_order"]
        assert findings == []


class TestCommaJoinImplicit:
    def test_matches(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ИЗ Документ.А КАК А, Документ.Б КАК Б"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "comma_join_implicit"]
        assert len(findings) >= 1
        assert findings[0].severity == "critical"

    def test_negative_explicit_join(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ИЗ Документ.А КАК А ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.Б КАК Б ПО А.К = Б.К"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "comma_join_implicit"]
        assert findings == []


class TestFunctionInWhere:
    def test_matches_god(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ ГОД(Док.Дата) = 2024"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "function_in_where"]
        assert len(findings) >= 1

    def test_matches_vreg(self) -> None:
        rules = load_native_rules(_rules_dir())
        q = "ГДЕ ВРЕГ(Тов.Артикул) = 'A001'"
        findings = [f for f in native_analyze(q, rules) if f.rule_id == "function_in_where"]
        assert len(findings) >= 1


# ---------- Solution Generator placeholder ----------


class TestSolutionGenerator:
    def test_always_disabled_sprint4(self) -> None:
        gen = SolutionGenerator()
        assert gen.enabled is False

    def test_returns_501(self) -> None:
        gen = SolutionGenerator()
        result = gen.generate_solution("rule_id", {"some": "context"})
        assert result["ok"] is False
        assert result["status_code"] == 501
        assert "Sprint 8" in result["error"]


# ---------- Query rewrite cache ----------


class TestQueryRewriteCache:
    def test_normalize_collapses_whitespace(self) -> None:
        assert normalize_query("ВЫБРАТЬ   *  ИЗ\n\nТов") == "ВЫБРАТЬ * ИЗ Тов"

    def test_cache_key_stable(self) -> None:
        k1 = compute_cache_key("ВЫБРАТЬ *", ["a", "b"])
        k2 = compute_cache_key("ВЫБРАТЬ *", ["b", "a"])  # порядок findings не важен
        assert k1 == k2

    def test_cache_key_changes_with_query(self) -> None:
        k1 = compute_cache_key("ВЫБРАТЬ А", ["a"])
        k2 = compute_cache_key("ВЫБРАТЬ Б", ["a"])
        assert k1 != k2

    def test_put_and_get(self, tmp_path: Path) -> None:
        cache = QueryRewriteCache(tmp_path / "test.db")
        entry = QueryRewriteEntry(
            cache_key="abc123",
            query_hash="h1",
            findings_hash="h2",
            rewritten_query="ВЫБРАТЬ Ссылка ИЗ Тов",
            changes_json='[]',
            notes_for_developer=None,
            estimated_improvement="50x",
            model="claude-sonnet-4-6",
            tokens_in=100,
            tokens_out=200,
            created_at="",
        )
        cache.put(entry)
        got = cache.get("abc123")
        assert got is not None
        assert got.rewritten_query == "ВЫБРАТЬ Ссылка ИЗ Тов"
        assert got.tokens_in == 100

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        cache = QueryRewriteCache(tmp_path / "test.db")
        assert cache.get("nope") is None


# ---------- RPC integration ----------


class TestRPCIntegration:
    def test_analyze_rpc_returns_findings(self) -> None:
        from optimyzer_backend.rpc.dispatcher import Dispatcher
        from optimyzer_backend.rpc import query_analyzer_rpc  # noqa: F401 — registers RPCs

        disp = Dispatcher.default()
        resp = disp.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "query_analyzer.analyze",
            "params": {"query_text": "ВЫБРАТЬ * ИЗ Документ.А КАК А, Документ.Б КАК Б"},
        })
        assert resp is not None
        assert "result" in resp
        assert resp["result"]["ok"] is True
        assert len(resp["result"]["findings"]) >= 2

    def test_status_rpc(self) -> None:
        from optimyzer_backend.rpc.dispatcher import Dispatcher
        from optimyzer_backend.rpc import query_analyzer_rpc  # noqa: F401

        disp = Dispatcher.default()
        resp = disp.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "query_analyzer.status",
            "params": {},
        })
        assert resp is not None
        assert resp["result"]["ok"] is True
        assert resp["result"]["native_rules_count"] >= 12
        assert resp["result"]["bsl_ls_available"] is False

    def test_generate_solution_returns_501(self) -> None:
        from optimyzer_backend.rpc.dispatcher import Dispatcher
        from optimyzer_backend.rpc import query_analyzer_rpc  # noqa: F401

        disp = Dispatcher.default()
        resp = disp.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "query_analyzer.generate_solution",
            "params": {"finding_id": "x"},
        })
        assert resp is not None
        assert resp["result"]["status_code"] == 501

    def test_reload_rules_rpc(self) -> None:
        from optimyzer_backend.rpc.dispatcher import Dispatcher
        from optimyzer_backend.rpc import query_analyzer_rpc  # noqa: F401

        disp = Dispatcher.default()
        resp = disp.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "query_analyzer.reload_rules",
            "params": {},
        })
        assert resp is not None
        assert resp["result"]["ok"] is True
        assert resp["result"]["rules_count"] >= 12


# ---------- Performance ----------


class TestPerformance:
    def test_analyze_under_5_seconds(self) -> None:
        """DoD #24 — synthetic. На реальных запросах — в test_sprint4_real_data."""
        import time

        analyzer = QueryAnalyzer(_rules_dir())
        # Большой запрос с множеством антипаттернов
        big_query = "\n".join([
            "ВЫБРАТЬ *",
            "ИЗ Документ.А КАК А, Документ.Б КАК Б",
            "ГДЕ А.Артикул = 'X' ИЛИ А.Артикул = 'Y'",
            "  И ВЫРАЗИТЬ(А.Контрагент КАК Справочник.К).Наименование = 'Z'",
            "  И ГОД(А.Дата) = 2024",
            "  И А.Контрагент В (ВЫБРАТЬ Ссылка ИЗ Справочник.К)",
        ] * 20)

        start = time.monotonic()
        result = analyzer.analyze(big_query)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Анализ занял {elapsed:.2f}s, ожидаем <5s"
        assert len(result["findings"]) > 0
