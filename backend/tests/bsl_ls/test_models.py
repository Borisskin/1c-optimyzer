"""Тесты Pydantic-моделей и Range.overlaps."""

from __future__ import annotations

import pytest

from optimyzer_backend.bsl_ls.models import (
    AnalyzeRequest,
    Diagnostic,
    Position,
    Range,
    Severity,
)


class TestSeverity:
    def test_order_blocker_highest(self) -> None:
        assert Severity.BLOCKER.order > Severity.CRITICAL.order
        assert Severity.CRITICAL.order > Severity.MAJOR.order
        assert Severity.MAJOR.order > Severity.MINOR.order
        assert Severity.MINOR.order > Severity.INFO.order

    def test_max_by_order(self) -> None:
        items = [Severity.INFO, Severity.BLOCKER, Severity.MAJOR]
        assert max(items, key=lambda s: s.order) is Severity.BLOCKER


class TestRangeOverlaps:
    def _r(self, sl: int, sc: int, el: int, ec: int) -> Range:
        return Range(start=Position(line=sl, character=sc), end=Position(line=el, character=ec))

    def test_disjoint_same_line(self) -> None:
        a = self._r(0, 0, 0, 5)
        b = self._r(0, 10, 0, 15)
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_adjacent_no_overlap(self) -> None:
        # [0,5) и [5,10) — не пересекаются (LSP half-open).
        a = self._r(0, 0, 0, 5)
        b = self._r(0, 5, 0, 10)
        assert not a.overlaps(b)

    def test_overlap_same_line(self) -> None:
        a = self._r(0, 0, 0, 10)
        b = self._r(0, 5, 0, 15)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_contains(self) -> None:
        big = self._r(0, 0, 5, 0)
        small = self._r(2, 0, 3, 0)
        assert big.overlaps(small)
        assert small.overlaps(big)

    def test_multi_line_overlap(self) -> None:
        a = self._r(0, 5, 2, 10)
        b = self._r(2, 5, 4, 0)  # начало b до конца a
        assert a.overlaps(b)


class TestDiagnostic:
    def test_minimal(self) -> None:
        d = Diagnostic(
            code="RefOveruse",
            message="Избавьтесь от .Ссылка",
            range=Range(
                start=Position(line=5, character=12),
                end=Position(line=5, character=35),
            ),
            severity=Severity.MAJOR,
        )
        assert d.code == "RefOveruse"
        assert d.source == "bsl-language-server"
        assert d.tags == []
        assert d.snippet is None


class TestAnalyzeRequest:
    def test_defaults(self) -> None:
        req = AnalyzeRequest(query_sdbl="ВЫБРАТЬ 1")
        assert req.configuration_root is None
        assert req.enabled_rules is None
        assert req.file_uri == "inmemory:///query.bsl"
