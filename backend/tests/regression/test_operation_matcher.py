"""Sprint 11 Phase E — Tests для operation_matcher."""

from __future__ import annotations

import pytest

from optimyzer_backend.regression.operation_matcher import (
    OperationData,
    compute_fingerprint,
    match_operations,
)


class TestComputeFingerprint:
    def test_simple_name(self):
        fp = compute_fingerprint("Документ.Реализация.Записать", "")
        assert fp.name == "Документ.Реализация.Записать"
        assert fp.context_signature == ""

    def test_strips_whitespace_around_name(self):
        fp1 = compute_fingerprint("  Документ.Реализация  ", "")
        fp2 = compute_fingerprint("Документ.Реализация", "")
        assert fp1.name == fp2.name

    def test_takes_first_line_of_context(self):
        ctx = "Документ.Реализация\nдополнительная информация\nещё одна строка"
        fp = compute_fingerprint("X", ctx)
        assert "Документ.Реализация" in fp.context_signature
        assert "дополнительная" not in fp.context_signature

    def test_timestamp_normalized(self):
        ctx1 = "Документ № 123, 2026-05-20 14:30:00"
        ctx2 = "Документ № 456, 2026-05-21 09:15:30"
        # Different doc number AND timestamp — оба нормализованы → matching
        fp1 = compute_fingerprint("X", ctx1)
        fp2 = compute_fingerprint("X", ctx2)
        assert fp1.signature() == fp2.signature()

    def test_uuid_normalized(self):
        ctx1 = "Объект: a1b2c3d4-1234-5678-9abc-def012345678"
        ctx2 = "Объект: 99999999-0000-1111-2222-333333333333"
        fp1 = compute_fingerprint("X", ctx1)
        fp2 = compute_fingerprint("X", ctx2)
        assert fp1.signature() == fp2.signature()

    def test_user_normalized(self):
        ctx1 = "Пользователь = Иванов И.И., Сеанс = 42"
        ctx2 = "Пользователь = Петров П.П., Сеанс = 100"
        fp1 = compute_fingerprint("X", ctx1)
        fp2 = compute_fingerprint("X", ctx2)
        assert fp1.signature() == fp2.signature()

    def test_session_normalized(self):
        ctx1 = "Сеанс = 42"
        ctx2 = "Сеанс = 1024"
        fp1 = compute_fingerprint("X", ctx1)
        fp2 = compute_fingerprint("X", ctx2)
        assert fp1.signature() == fp2.signature()

    def test_different_operations_distinct(self):
        fp1 = compute_fingerprint("Документ.Реализация", "")
        fp2 = compute_fingerprint("Документ.Поступление", "")
        assert fp1.signature() != fp2.signature()

    def test_different_business_context_distinct(self):
        """Different context (не runtime) → different signature."""
        fp1 = compute_fingerprint("Обработка.Печать", "Печать кассовых чеков")
        fp2 = compute_fingerprint("Обработка.Печать", "Печать накладных")
        assert fp1.signature() != fp2.signature()

    def test_long_context_capped(self):
        long_ctx = "A" * 500
        fp = compute_fingerprint("X", long_ctx)
        assert len(fp.context_signature) <= 200

    def test_empty_context(self):
        fp = compute_fingerprint("X", "")
        assert fp.context_signature == ""

    def test_none_name_handled(self):
        fp = compute_fingerprint("", "context")
        assert fp.name == ""

    def test_whitespace_collapsed(self):
        ctx1 = "Документ    с   множеством   пробелов"
        ctx2 = "Документ с множеством пробелов"
        fp1 = compute_fingerprint("X", ctx1)
        fp2 = compute_fingerprint("X", ctx2)
        assert fp1.signature() == fp2.signature()


class TestMatchOperations:
    def _op(self, name: str, context: str = "", count: int = 10) -> OperationData:
        return OperationData(
            name=name,
            context=context,
            samples_count=count,
            p50_duration_ms=100.0,
            p95_duration_ms=200.0,
        )

    def test_empty_archives(self):
        results = match_operations([], [])
        assert results == []

    def test_all_matched(self):
        baseline = [self._op("A"), self._op("B")]
        current = [self._op("A"), self._op("B")]
        results = match_operations(baseline, current)
        assert len(results) == 2
        assert all(r.match_type == "matched" for r in results)

    def test_all_new(self):
        results = match_operations([], [self._op("A"), self._op("B")])
        assert len(results) == 2
        assert all(r.match_type == "new" for r in results)

    def test_all_disappeared(self):
        results = match_operations([self._op("A"), self._op("B")], [])
        assert len(results) == 2
        assert all(r.match_type == "disappeared" for r in results)

    def test_mixed(self):
        baseline = [self._op("A"), self._op("B")]
        current = [self._op("B"), self._op("C")]
        results = match_operations(baseline, current)
        types = {r.match_type for r in results}
        assert types == {"matched", "new", "disappeared"}
        # B matched, C new, A disappeared
        assert len(results) == 3

    def test_baseline_current_preserved(self):
        b = self._op("A", count=5)
        c = self._op("A", count=15)
        results = match_operations([b], [c])
        assert len(results) == 1
        match = results[0]
        assert match.match_type == "matched"
        assert match.baseline is b
        assert match.current is c

    def test_runtime_diff_still_matched(self):
        """Same operation с разными runtime detail → still matched (fingerprint normalizes)."""
        baseline_ctx = "Документ № 123, 2026-05-20 14:30:00"
        current_ctx = "Документ № 999, 2026-05-25 09:00:00"
        b = self._op("Документ.Реализация", baseline_ctx)
        c = self._op("Документ.Реализация", current_ctx)
        results = match_operations([b], [c])
        assert len(results) == 1
        assert results[0].match_type == "matched"

    def test_different_business_context_separate_match(self):
        """Same operation_name, разный business context → different operations."""
        b1 = self._op("Обработка.Печать", "Печать кассовых чеков")
        b2 = self._op("Обработка.Печать", "Печать накладных")
        # current — только первая
        c1 = self._op("Обработка.Печать", "Печать кассовых чеков")
        results = match_operations([b1, b2], [c1])
        types = sorted(r.match_type for r in results)
        # 1 matched + 1 disappeared (b2)
        assert types == ["disappeared", "matched"]
