"""Sprint 11 Phase E — RPC handler для performance regression analysis."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from optimyzer_backend.regression import (
    ChangeType,
    classify_match,
    match_operations,
)
from optimyzer_backend.regression.data_loader import load_operations
from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.sql.executor import SQLExecutionError


def _both_ready(baseline_id: str, current_id: str) -> dict[str, Any] | None:
    """Проверка что оба архива готовы (ingestion завершена)."""
    for label, aid in [("baseline", baseline_id), ("current", current_id)]:
        state = _ARCHIVES.get(aid)
        if state is None:
            return {"ok": False, "error": f"Архив {label} не загружен: {aid}"}
        if state.get("status") != "ready":
            return {
                "ok": False,
                "error": f"Архив {label} не готов (status={state.get('status')})",
            }
    return None


def _result_to_dict(r) -> dict[str, Any]:
    """Convert RegressionResult dataclass → dict для JSON RPC."""
    d = asdict(r)
    # change_type/confidence — enums → strings
    d["change_type"] = r.change_type.value
    d["confidence"] = r.confidence.value
    return d


@rpc("regression.compute")
def compute_regression(
    baseline_archive_id: str,
    current_archive_id: str,
    threshold: float = 2.0,
    min_samples: int = 5,
    top_n: int = 50,
) -> dict[str, Any]:
    """Sprint 11 Phase E — Performance regression analysis между двумя архивами.

    Args:
        baseline_archive_id: ID более раннего архива (до изменения).
        current_archive_id: ID более позднего архива (после изменения).
        threshold: regression detected если current_p95 >= baseline_p95 × threshold.
                   Default 2.0× (стало в 2 раза медленнее).
        min_samples: min samples в любом из архивов для включения в результат.
                     Default 5 — фильтр шума от редких операций.
        top_n: сколько top результатов вернуть на категорию (regressions,
               improvements, new, disappeared). Default 50.

    Returns:
        {
          "ok": True,
          "summary": {total_matched, total_regressions, ...},
          "regressions": [...top_n sorted by priority_score desc],
          "improvements": [...top_n sorted by ratio asc — biggest improvement first],
          "new": [...top_n sorted by priority],
          "disappeared": [...top_n],
          "stable_count": N,  # просто число (детали не возвращаем — много)
        }
    """
    err = _both_ready(baseline_archive_id, current_archive_id)
    if err:
        return err

    try:
        baseline_ops = load_operations(baseline_archive_id)
        current_ops = load_operations(current_archive_id)
    except SQLExecutionError as exc:
        return {"ok": False, "error": str(exc), "details": "SQL execution failed"}

    matches = match_operations(baseline_ops, current_ops)
    results = [classify_match(m, threshold=threshold) for m in matches]

    # Filter — если ни один из counts не достигает min_samples → skip (low signal)
    if min_samples > 0:
        results = [
            r
            for r in results
            if (r.baseline_count or 0) >= min_samples
            or (r.current_count or 0) >= min_samples
        ]

    # Group by change type + sort + limit
    by_type: dict[str, list] = {ct.value: [] for ct in ChangeType}
    for r in results:
        by_type[r.change_type.value].append(r)

    # Sort regressions по priority_score (биггест regression первый)
    by_type[ChangeType.REGRESSION.value].sort(
        key=lambda r: -r.priority_score
    )
    # Improvements — по ratio asc (наибольшее улучшение = меньшее ratio)
    by_type[ChangeType.IMPROVEMENT.value].sort(
        key=lambda r: r.p95_ratio if r.p95_ratio is not None else 1.0
    )
    # New — по priority_score desc (самые "значимые" новые)
    by_type[ChangeType.NEW.value].sort(key=lambda r: -r.priority_score)
    # Disappeared — по приоритету (что пропало)
    by_type[ChangeType.DISAPPEARED.value].sort(
        key=lambda r: -r.priority_score
    )

    summary = {
        "total_operations_matched": len(
            [m for m in matches if m.match_type == "matched"]
        ),
        "total_regressions": len(by_type[ChangeType.REGRESSION.value]),
        "total_improvements": len(by_type[ChangeType.IMPROVEMENT.value]),
        "total_new": len(by_type[ChangeType.NEW.value]),
        "total_disappeared": len(by_type[ChangeType.DISAPPEARED.value]),
        "total_stable": len(by_type[ChangeType.STABLE.value]),
        "threshold": threshold,
        "min_samples": min_samples,
    }

    return {
        "ok": True,
        "summary": summary,
        "regressions": [
            _result_to_dict(r)
            for r in by_type[ChangeType.REGRESSION.value][:top_n]
        ],
        "improvements": [
            _result_to_dict(r)
            for r in by_type[ChangeType.IMPROVEMENT.value][:top_n]
        ],
        "new": [
            _result_to_dict(r) for r in by_type[ChangeType.NEW.value][:top_n]
        ],
        "disappeared": [
            _result_to_dict(r)
            for r in by_type[ChangeType.DISAPPEARED.value][:top_n]
        ],
        "stable_count": len(by_type[ChangeType.STABLE.value]),
    }
