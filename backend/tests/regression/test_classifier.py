"""Sprint 11 Phase E — Tests для classifier."""

from __future__ import annotations

import math

import pytest

from optimyzer_backend.regression.classifier import (
    ChangeType,
    Confidence,
    classify_match,
    confidence_from_count,
)
from optimyzer_backend.regression.operation_matcher import (
    OperationData,
    OperationFingerprint,
    OperationMatch,
)


def _make_op(
    name: str = "Документ.Реализация",
    p95: float = 1000.0,
    p50: float = 500.0,
    count: int = 10,
) -> OperationData:
    return OperationData(
        name=name,
        context="ctx",
        samples_count=count,
        p50_duration_ms=p50,
        p95_duration_ms=p95,
        fingerprint=OperationFingerprint(name=name, context_signature="sig"),
    )


def _matched(
    baseline_p95: float, current_p95: float, b_count: int = 10, c_count: int = 10
) -> OperationMatch:
    b = _make_op(p95=baseline_p95, count=b_count)
    c = _make_op(p95=current_p95, count=c_count)
    return OperationMatch(
        match_type="matched",
        baseline=b,
        current=c,
        fingerprint=b.fingerprint,
    )


def _new(current_p95: float = 1000.0, c_count: int = 10) -> OperationMatch:
    c = _make_op(p95=current_p95, count=c_count)
    return OperationMatch(
        match_type="new", baseline=None, current=c, fingerprint=c.fingerprint
    )


def _disappeared(
    baseline_p95: float = 1000.0, b_count: int = 10
) -> OperationMatch:
    b = _make_op(p95=baseline_p95, count=b_count)
    return OperationMatch(
        match_type="disappeared",
        baseline=b,
        current=None,
        fingerprint=b.fingerprint,
    )


class TestConfidenceFromCount:
    def test_high_confidence(self):
        assert confidence_from_count(20) == Confidence.HIGH
        assert confidence_from_count(100) == Confidence.HIGH

    def test_medium_confidence(self):
        assert confidence_from_count(5) == Confidence.MEDIUM
        assert confidence_from_count(19) == Confidence.MEDIUM

    def test_low_confidence(self):
        assert confidence_from_count(0) == Confidence.LOW
        assert confidence_from_count(4) == Confidence.LOW


class TestClassifyMatched:
    def test_regression_detected_at_threshold(self):
        # ratio = 2.0 exactly → REGRESSION
        result = classify_match(_matched(100, 200), threshold=2.0)
        assert result.change_type == ChangeType.REGRESSION
        assert result.p95_ratio == 2.0

    def test_regression_above_threshold(self):
        # ratio = 3 → REGRESSION
        result = classify_match(_matched(100, 300), threshold=2.0)
        assert result.change_type == ChangeType.REGRESSION
        assert result.p95_ratio == 3.0

    def test_improvement_at_threshold(self):
        # ratio = 0.5 → IMPROVEMENT
        result = classify_match(_matched(200, 100), threshold=2.0)
        assert result.change_type == ChangeType.IMPROVEMENT
        assert result.p95_ratio == 0.5

    def test_stable_within_threshold(self):
        # ratio = 1.5 → STABLE (between 0.5 and 2.0)
        result = classify_match(_matched(100, 150), threshold=2.0)
        assert result.change_type == ChangeType.STABLE
        assert result.p95_ratio == 1.5

    def test_stable_no_change(self):
        result = classify_match(_matched(100, 100), threshold=2.0)
        assert result.change_type == ChangeType.STABLE

    def test_zero_baseline_with_nonzero_current_is_regression(self):
        """baseline_p95 == 0 → ratio = inf → REGRESSION."""
        result = classify_match(_matched(0, 100), threshold=2.0)
        assert result.change_type == ChangeType.REGRESSION
        assert result.p95_ratio is None  # inf не сериализуется

    def test_zero_baseline_zero_current_is_stable(self):
        result = classify_match(_matched(0, 0), threshold=2.0)
        assert result.change_type == ChangeType.STABLE


class TestClassifyNew:
    def test_new_classified(self):
        result = classify_match(_new(current_p95=500.0, c_count=50))
        assert result.change_type == ChangeType.NEW
        assert result.current_p95_ms == 500.0
        assert result.current_count == 50
        assert result.baseline_p95_ms is None
        assert result.baseline_count is None


class TestClassifyDisappeared:
    def test_disappeared_classified(self):
        result = classify_match(_disappeared(baseline_p95=300.0, b_count=20))
        assert result.change_type == ChangeType.DISAPPEARED
        assert result.baseline_p95_ms == 300.0
        assert result.baseline_count == 20
        assert result.current_p95_ms is None

    def test_disappeared_low_priority(self):
        """Disappeared имеет 0.1× priority от same metrics в NEW (обычно not actionable)."""
        d = classify_match(_disappeared(baseline_p95=1000.0, b_count=10))
        n = classify_match(_new(current_p95=1000.0, c_count=10))
        assert d.priority_score < n.priority_score


class TestConfidence:
    def test_matched_takes_min_confidence(self):
        """Если baseline=high (20+) и current=low (<5) — overall low (наименьшее evidence)."""
        result = classify_match(_matched(100, 200, b_count=100, c_count=2))
        assert result.confidence == Confidence.LOW

    def test_matched_both_high(self):
        result = classify_match(_matched(100, 200, b_count=50, c_count=50))
        assert result.confidence == Confidence.HIGH

    def test_matched_medium_high(self):
        result = classify_match(_matched(100, 200, b_count=10, c_count=50))
        assert result.confidence == Confidence.MEDIUM

    def test_new_confidence_from_current_count(self):
        result = classify_match(_new(c_count=100))
        assert result.confidence == Confidence.HIGH

    def test_disappeared_confidence_from_baseline_count(self):
        result = classify_match(_disappeared(b_count=2))
        assert result.confidence == Confidence.LOW


class TestPriorityScore:
    def test_stable_has_zero_priority(self):
        result = classify_match(_matched(100, 110))
        assert result.priority_score == 0.0

    def test_improvement_has_zero_priority(self):
        result = classify_match(_matched(100, 40))
        assert result.priority_score == 0.0

    def test_regression_priority_increases_with_ratio(self):
        r1 = classify_match(_matched(100, 200))  # 2×
        r2 = classify_match(_matched(100, 400))  # 4×
        assert r2.priority_score > r1.priority_score

    def test_regression_priority_increases_with_count(self):
        r_rare = classify_match(_matched(100, 300, b_count=5, c_count=5))
        r_freq = classify_match(_matched(100, 300, b_count=5, c_count=100))
        assert r_freq.priority_score > r_rare.priority_score

    def test_regression_priority_increases_with_current_p95(self):
        """Same ratio но больший absolute time → больший priority."""
        r_small = classify_match(_matched(50, 150))  # 3× от 50ms
        r_big = classify_match(_matched(1000, 3000))  # 3× от 1s
        assert r_big.priority_score > r_small.priority_score


class TestEdgeCases:
    def test_threshold_validation(self):
        with pytest.raises(ValueError):
            classify_match(_matched(100, 200), threshold=0.5)

    def test_threshold_3x(self):
        # ratio=2 при threshold=3 → STABLE
        result = classify_match(_matched(100, 200), threshold=3.0)
        assert result.change_type == ChangeType.STABLE
        # ratio=3 → REGRESSION exactly
        result = classify_match(_matched(100, 300), threshold=3.0)
        assert result.change_type == ChangeType.REGRESSION

    def test_count_ratio_computed(self):
        result = classify_match(_matched(100, 200, b_count=10, c_count=30))
        assert result.count_ratio == 3.0

    def test_count_ratio_none_when_baseline_zero(self):
        # Не реалистично через _matched (count=0 == redundant с new/disappeared),
        # но edge case проверяем:
        b = _make_op(count=0)
        c = _make_op(count=10)
        m = OperationMatch(match_type="matched", baseline=b, current=c, fingerprint=b.fingerprint)
        result = classify_match(m)
        assert result.count_ratio is None

    def test_operation_name_propagated(self):
        result = classify_match(_matched(100, 200))
        assert result.operation_name == "Документ.Реализация"

    def test_context_signature_propagated(self):
        result = classify_match(_matched(100, 200))
        assert result.context_signature == "sig"
