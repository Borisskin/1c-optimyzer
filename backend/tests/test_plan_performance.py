"""Sprint 7 Phase E — performance benchmarks PerformanceStudio CLI.

Цели (из плана архитектора):
    - CLI analyze < 5s на типичный план (10-50 операторов)
    - CLI analyze < 15s на большой план (100+ операторов)
    - Full flow analyze + JSON parse < 20s

AI benchmarks не делаем здесь — требуют live API key и стабильную сеть,
лучше как integration test в server/tests/.

Если planview.exe не найден — модуль пропускается целиком.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from optimyzer_backend.planview import cli as planview_cli


REPO_ROOT = Path(__file__).resolve().parents[2]
PERFSTUDIO_PLANS = (
    REPO_ROOT / "research" / "PerformanceStudio" / "tests" / "PlanViewer.Core.Tests" / "Plans"
)
HQP_PLANS = REPO_ROOT / "research" / "html-query-plan" / "test_plans"


pytestmark = pytest.mark.skipif(
    planview_cli.get_binary_path() is None,
    reason="planview.exe не найден",
)


# Конкретные fixtures под benchmark — выбраны вручную, чтобы покрыть
# разные размеры planов. None если файла нет — соответствующий тест skip.

def _find_plan(*paths: Path) -> Path | None:
    for p in paths:
        if p.exists() and p.is_file():
            return p
    return None


SMALL_PLAN = _find_plan(
    PERFSTUDIO_PLANS / "key_lookup_plan.sqlplan",
    HQP_PLANS / "nested loops.sqlplan",
)

LARGE_PLAN = _find_plan(
    HQP_PLANS / "many_lines2.sqlplan",  # обычно один из самых больших
    PERFSTUDIO_PLANS / "excellent-parallel-spill.sqlplan",
)


@pytest.mark.skipif(SMALL_PLAN is None, reason="нет малого тестового плана")
def test_cli_small_plan_under_5s() -> None:
    """Типичный план (10-50 операторов) — analyze < 5s."""
    assert SMALL_PLAN is not None  # for mypy
    start = time.monotonic()
    result = planview_cli.analyze_plan_file(SMALL_PLAN)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"slow: {elapsed:.2f}s на {SMALL_PLAN.name}"
    assert result.statements  # sanity — что-то распарсилось


@pytest.mark.skipif(LARGE_PLAN is None, reason="нет большого тестового плана")
def test_cli_large_plan_under_15s() -> None:
    """Большой план (100+ операторов) — analyze < 15s."""
    assert LARGE_PLAN is not None
    start = time.monotonic()
    result = planview_cli.analyze_plan_file(LARGE_PLAN)
    elapsed = time.monotonic() - start
    assert elapsed < 15.0, f"very slow: {elapsed:.2f}s на {LARGE_PLAN.name}"
    assert result is not None


def test_cli_repeated_calls_no_leak() -> None:
    """Регрессия: 5 последовательных вызовов на маленьком плане → стабильное время.

    Защита от регрессий типа: case когда CLI накапливает .NET assemblies
    или не освобождает file handles между вызовами.
    """
    if SMALL_PLAN is None:
        pytest.skip("нет малого тестового плана")
    times: list[float] = []
    for _ in range(5):
        start = time.monotonic()
        planview_cli.analyze_plan_file(SMALL_PLAN)
        times.append(time.monotonic() - start)
    # Среднее < 5s + последний вызов не должен быть существенно медленнее первого.
    avg = sum(times) / len(times)
    assert avg < 5.0, f"среднее время {avg:.2f}s превышает лимит"
    # Последний не больше чем 2x первого (грубая проверка на degradation).
    assert times[-1] < times[0] * 2 + 1.0, f"slowdown: {times}"
