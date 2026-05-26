"""Sprint 11 Phase E — Performance Regression Tracking.

Сравнивает две архивные базы операций (TJ events) на operation-level:
- Matched: одинаковая операция в обоих архивах
- Regression: current_p95 > baseline_p95 × threshold
- Improvement: current_p95 < baseline_p95 / threshold
- New: операция только в current
- Disappeared: операция только в baseline
- Stable: в пределах threshold

Confidence:
- High: 20+ samples в обоих
- Medium: 5-20 samples
- Low: < 5 samples

Priority score для приоритизации AI summary:
  (p95_ratio - 1) × log(count + 1) × current_p95
"""

from optimyzer_backend.regression.classifier import (
    ChangeType,
    Confidence,
    RegressionResult,
    classify_match,
    confidence_from_count,
)
from optimyzer_backend.regression.operation_matcher import (
    OperationData,
    OperationFingerprint,
    OperationMatch,
    compute_fingerprint,
    match_operations,
)

__all__ = [
    "ChangeType",
    "Confidence",
    "OperationData",
    "OperationFingerprint",
    "OperationMatch",
    "RegressionResult",
    "classify_match",
    "compute_fingerprint",
    "confidence_from_count",
    "match_operations",
]
