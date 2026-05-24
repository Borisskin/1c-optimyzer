"""Тесты parser.py — парсинг LSP Diagnostic + дедупликация."""

from __future__ import annotations

import pytest

from optimyzer_backend.bsl_ls.models import (
    Diagnostic,
    Position,
    Range,
    Severity,
)
from optimyzer_backend.bsl_ls.parser import (
    _RULE_SEVERITY,
    _extract_snippet,
    group_overlapping,
    parse_lsp_diagnostic,
)


class TestParseLspDiagnostic:
    def test_basic_ref_overuse(self) -> None:
        raw = {
            "code": "RefOveruse",
            "codeDescription": {
                "href": "https://1c-syntax.github.io/bsl-language-server/diagnostics/RefOveruse"
            },
            "data": None,
            "message": 'Избавьтесь от получения поля "Ссылка" в запросе.',
            "range": {
                "end": {"character": 67, "line": 14},
                "start": {"character": 26, "line": 14},
            },
            "relatedInformation": None,
            "severity": "Warning",
            "source": "bsl-language-server",
            "tags": [],
        }
        d = parse_lsp_diagnostic(raw)
        assert d.code == "RefOveruse"
        assert d.severity == Severity.MAJOR
        assert d.range.start.line == 14
        assert d.range.start.character == 26
        assert d.range.end.character == 67
        assert "Ссылка" in d.message
        assert d.code_description_href is not None
        assert "RefOveruse" in d.code_description_href

    def test_severity_from_rule_overrides_lsp(self) -> None:
        # bsl-LS отдаёт VirtualTableCallWithoutParameters как "Error" (severity 1)
        # но мы маппим в CRITICAL по rule code.
        raw = {
            "code": "VirtualTableCallWithoutParameters",
            "message": "Виртуальная таблица без параметров",
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
            "severity": "Error",
        }
        d = parse_lsp_diagnostic(raw)
        assert d.severity == Severity.CRITICAL

    def test_unknown_rule_falls_back_to_lsp_severity_string(self) -> None:
        raw = {
            "code": "UnknownNewRuleFromUpstream",
            "message": "что-то",
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
            "severity": "Information",
        }
        d = parse_lsp_diagnostic(raw)
        assert d.severity == Severity.MINOR  # Information -> MINOR

    def test_all_19_sdbl_rules_have_severity_mapping(self) -> None:
        """Sanity: каждое из 19 правил из research report — в _RULE_SEVERITY."""
        expected = {
            # Blocker
            "QueryParseError",
            "QueryToMissingMetadata",
            # Critical
            "VirtualTableCallWithoutParameters",
            "FieldsFromJoinsWithoutIsNull",
            # Major
            "JoinWithSubQuery",
            "JoinWithVirtualTable",
            "RefOveruse",
            "QueryNestedFieldsByDot",
            "FullOuterJoinQuery",
            "UnionAll",
            "SelectTopWithoutOrderBy",
            "IncorrectUseLikeInQuery",
            "LogicalOrInJoinQuerySection",
            "LogicalOrInTheWhereSectionOfQuery",
            "SameMetadataObjectAndChildNames",
            "ForbiddenMetadataName",
            # Minor
            "AssignAliasFieldsInQuery",
            "UsingLikeInQuery",
            "MultilineStringInQuery",
        }
        missing = expected - set(_RULE_SEVERITY.keys())
        assert not missing, f"Не покрыты в _RULE_SEVERITY: {missing}"

    def test_snippet_extraction_single_line(self) -> None:
        text = "ВЫБРАТЬ Док.Ссылка.Контрагент.Ссылка.Наименование ИЗ Документ.Реализация"
        rng = Range(
            start=Position(line=0, character=8),
            end=Position(line=0, character=49),
        )
        snippet = _extract_snippet(text, rng)
        assert snippet == "Док.Ссылка.Контрагент.Ссылка.Наименование"

    def test_snippet_extraction_multi_line(self) -> None:
        text = "line0\nline1text\nline2"
        rng = Range(
            start=Position(line=0, character=3),
            end=Position(line=2, character=3),
        )
        snippet = _extract_snippet(text, rng)
        assert snippet == "e0\nline1text\nlin"


class TestGroupOverlapping:
    def _diag(self, code: str, severity: Severity, sl: int, sc: int, ec: int) -> Diagnostic:
        return Diagnostic(
            code=code,
            message=f"{code} msg",
            range=Range(
                start=Position(line=sl, character=sc),
                end=Position(line=sl, character=ec),
            ),
            severity=severity,
        )

    def test_empty(self) -> None:
        assert group_overlapping([]) == []

    def test_disjoint_diagnostics(self) -> None:
        d1 = self._diag("RuleA", Severity.MAJOR, 0, 0, 5)
        d2 = self._diag("RuleB", Severity.MINOR, 0, 10, 15)
        groups = group_overlapping([d1, d2])
        assert len(groups) == 2

    def test_overlapping_grouped_with_max_severity(self) -> None:
        # Тестовый кейс из research report: на одной строке RefOveruse (Major)
        # и QueryNestedFieldsByDot (Major). Они должны слиться в одну группу.
        d1 = self._diag("RefOveruse", Severity.MAJOR, 14, 26, 67)
        d2 = self._diag("QueryNestedFieldsByDot", Severity.MAJOR, 14, 26, 67)
        groups = group_overlapping([d1, d2])
        assert len(groups) == 1
        assert groups[0].severity == Severity.MAJOR
        assert set(groups[0].codes) == {"RefOveruse", "QueryNestedFieldsByDot"}

    def test_overlap_severity_max(self) -> None:
        d1 = self._diag("Minor", Severity.MINOR, 0, 0, 10)
        d2 = self._diag("Critical", Severity.CRITICAL, 0, 5, 15)
        groups = group_overlapping([d1, d2])
        assert len(groups) == 1
        assert groups[0].severity == Severity.CRITICAL
        assert groups[0].primary.code == "Critical"
        # Codes отсортированы по severity убыванию.
        assert groups[0].codes[0] == "Critical"

    def test_three_overlapping_form_one_group(self) -> None:
        d1 = self._diag("A", Severity.MAJOR, 0, 0, 10)
        d2 = self._diag("B", Severity.MINOR, 0, 5, 15)
        d3 = self._diag("C", Severity.CRITICAL, 0, 12, 20)  # пересекается с d2
        groups = group_overlapping([d1, d2, d3])
        # d1 пересекается с d2, d2 пересекается с d3 — все в одной группе.
        assert len(groups) == 1
        assert groups[0].severity == Severity.CRITICAL
