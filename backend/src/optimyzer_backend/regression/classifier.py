"""Sprint 11 Phase E — Regression classifier.

Classify каждый OperationMatch в один из 5 change types + confidence
+ priority_score (для выбора top-N для AI explanation).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from optimyzer_backend.regression.operation_matcher import OperationMatch


class ChangeType(str, Enum):
    REGRESSION = "regression"  # стало хуже threshold
    IMPROVEMENT = "improvement"  # стало лучше threshold
    NEW = "new"  # новая операция
    DISAPPEARED = "disappeared"  # исчезла
    STABLE = "stable"  # в пределах threshold


class Confidence(str, Enum):
    HIGH = "high"  # 20+ samples в обоих
    MEDIUM = "medium"  # 5-20 samples
    LOW = "low"  # < 5 samples


@dataclass
class RegressionResult:
    """Classification одной операции."""

    operation_name: str
    context_signature: str
    change_type: ChangeType
    confidence: Confidence

    # Metrics (Optional — какие применимы зависит от change_type)
    baseline_p50_ms: Optional[float] = None
    baseline_p95_ms: Optional[float] = None
    baseline_count: Optional[int] = None
    current_p50_ms: Optional[float] = None
    current_p95_ms: Optional[float] = None
    current_count: Optional[int] = None

    # Ratios (None для NEW/DISAPPEARED, где нет comparison)
    p95_ratio: Optional[float] = None  # current/baseline
    count_ratio: Optional[float] = None

    # Priority score для top-N AI summary
    # Higher = больший приоритет для генерации AI explanation
    priority_score: float = 0.0


def confidence_from_count(count: int) -> Confidence:
    """Уровень confidence от количества samples в архиве."""
    if count >= 20:
        return Confidence.HIGH
    if count >= 5:
        return Confidence.MEDIUM
    return Confidence.LOW


def _min_confidence(a: Confidence, b: Confidence) -> Confidence:
    """Минимум из двух — для matched operations берём slowest evidence."""
    order = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
    return a if order[a] <= order[b] else b


def classify_match(
    match: OperationMatch, threshold: float = 2.0
) -> RegressionResult:
    """Classify match → RegressionResult.

    Args:
        match: OperationMatch от operation_matcher.match_operations
        threshold: >= 2.0 — regression detected. <= 1/threshold — improvement.
                   В пределах threshold — STABLE.

    Returns:
        RegressionResult с change_type + metrics + priority_score.
    """
    if threshold < 1.0:
        raise ValueError(f"threshold must be >= 1.0 (got {threshold})")

    fingerprint = match.fingerprint

    if match.match_type == "new":
        assert match.current is not None
        op = match.current
        confidence = confidence_from_count(op.samples_count)
        # NEW operations priority = p95 × log(count) — новые быстрые но частые > новых медленных но редких
        priority = op.p95_duration_ms * math.log(op.samples_count + 1)
        return RegressionResult(
            operation_name=op.name,
            context_signature=fingerprint.context_signature,
            change_type=ChangeType.NEW,
            confidence=confidence,
            current_p50_ms=op.p50_duration_ms,
            current_p95_ms=op.p95_duration_ms,
            current_count=op.samples_count,
            priority_score=priority,
        )

    if match.match_type == "disappeared":
        assert match.baseline is not None
        op = match.baseline
        confidence = confidence_from_count(op.samples_count)
        # DISAPPEARED priority — низкий (обычно не actionable, всё ушло само)
        priority = op.p95_duration_ms * math.log(op.samples_count + 1) * 0.1
        return RegressionResult(
            operation_name=op.name,
            context_signature=fingerprint.context_signature,
            change_type=ChangeType.DISAPPEARED,
            confidence=confidence,
            baseline_p50_ms=op.p50_duration_ms,
            baseline_p95_ms=op.p95_duration_ms,
            baseline_count=op.samples_count,
            priority_score=priority,
        )

    # matched
    assert match.baseline is not None and match.current is not None
    baseline = match.baseline
    current = match.current

    confidence = _min_confidence(
        confidence_from_count(baseline.samples_count),
        confidence_from_count(current.samples_count),
    )

    baseline_p95 = baseline.p95_duration_ms
    current_p95 = current.p95_duration_ms

    # Защита от деления на 0 (baseline_p95 == 0 — редко, но возможно)
    if baseline_p95 <= 0:
        # Если baseline нулевой, а current нет — это de facto regression
        if current_p95 > 0:
            ratio = float("inf")
            change_type = ChangeType.REGRESSION
        else:
            ratio = 1.0
            change_type = ChangeType.STABLE
    else:
        ratio = current_p95 / baseline_p95
        if ratio >= threshold:
            change_type = ChangeType.REGRESSION
        elif ratio <= 1.0 / threshold:
            change_type = ChangeType.IMPROVEMENT
        else:
            change_type = ChangeType.STABLE

    count_ratio = (
        current.samples_count / baseline.samples_count
        if baseline.samples_count > 0
        else None
    )

    # Priority — только для regressions. Improvements/stable = 0.
    # Formula: (ratio - 1) × log(count + 1) × current_p95
    # → ratio=3, count=100 — приоритет ~ 2 × 4.6 × current_p95 = 9.2 × current_p95
    if change_type == ChangeType.REGRESSION and ratio != float("inf"):
        priority = (ratio - 1.0) * math.log(current.samples_count + 1) * current_p95
    elif change_type == ChangeType.REGRESSION:  # ratio = inf
        # Very high priority — baseline=0 → current=X — clearly notable
        priority = current_p95 * math.log(current.samples_count + 1) * 10
    else:
        priority = 0.0

    return RegressionResult(
        operation_name=current.name,
        context_signature=fingerprint.context_signature,
        change_type=change_type,
        confidence=confidence,
        baseline_p50_ms=baseline.p50_duration_ms,
        baseline_p95_ms=baseline.p95_duration_ms,
        baseline_count=baseline.samples_count,
        current_p50_ms=current.p50_duration_ms,
        current_p95_ms=current.p95_duration_ms,
        current_count=current.samples_count,
        p95_ratio=ratio if ratio != float("inf") else None,
        count_ratio=count_ratio,
        priority_score=priority,
    )
