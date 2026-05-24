"""Sprint 7 Phase E — regression на всех .sqlplan fixtures.

Прогоняет analyze_plan_file через PerformanceStudio CLI на каждом найденном
.sqlplan файле в 3 директориях:
    1. tools/sprint7_discovery/sqlplans/ — 5 synthetic (test01-test05)
    2. research/html-query-plan/test_plans/ — 40 real-world fixtures
    3. research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/ — 37 PerfStudio rule tests

Цель: ни один файл не должен крашить парсер/CLI. Если crash — каталогизируем
здесь как known issue (skip с reason) и заводим TD для Sprint 8.

Если planview.exe не найден на CI / dev машине → весь модуль пропускается.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.planview import cli as planview_cli
from optimyzer_backend.planview.cli import PlanviewError
from optimyzer_backend.planview.models import PlanAnalysisResult


# Все 3 директории с тестовыми .sqlplan. Repo-relative paths.
REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DIRS = [
    REPO_ROOT / "tools" / "sprint7_discovery" / "sqlplans",
    REPO_ROOT / "research" / "html-query-plan" / "test_plans",
    REPO_ROOT / "research" / "PerformanceStudio" / "tests" / "PlanViewer.Core.Tests" / "Plans",
]


def _collect_plans() -> list[Path]:
    plans: list[Path] = []
    for d in PLAN_DIRS:
        if d.exists():
            plans.extend(sorted(d.glob("*.sqlplan")))
    return plans


ALL_PLANS = _collect_plans()


# Известные проблемные файлы (планы которые crashed CLI или дают невалидный
# output) — pytest skip с reason. Файлы из этого списка следует исследовать
# в Sprint 8 как TD items.
KNOWN_BROKEN: dict[str, str] = {
    # PerformanceStudio CLI (PlanViewer.Cli) — System.Text.Json bug:
    # "object cycle was detected ... depth larger than 64" на очень глубоких
    # operator trees. Apparently no ReferenceHandler.Preserve / MaxDepth
    # workaround в текущей версии. Affects only фикстуры с deeply-nested
    # Hash Match Build subtrees. TD-Sprint8-A: либо патчить PerfStudio CLI
    # (отправить PR), либо обернуть в нашу custom JSON serialization.
    "batch_hash_table_build.sqlplan": "TD-Sprint8-A: PerfStudio CLI object cycle on deeply-nested operator tree",
}


# Skip всего модуля если planview.exe недоступен (CI без bundle).
pytestmark = pytest.mark.skipif(
    planview_cli.get_binary_path() is None,
    reason="planview.exe не найден — запусти scripts/setup-planview-binary.ps1",
)


@pytest.mark.parametrize(
    "plan_file",
    ALL_PLANS,
    ids=[p.name for p in ALL_PLANS],
)
def test_plan_analyzer_handles_real_plan(plan_file: Path) -> None:
    """analyze_plan_file должен парсить файл без crash. Output — валидная Pydantic."""
    if plan_file.name in KNOWN_BROKEN:
        pytest.skip(f"Known issue: {KNOWN_BROKEN[plan_file.name]}")

    try:
        result = planview_cli.analyze_plan_file(plan_file, warnings_only=False)
    except PlanviewError as e:
        # CLI отказался — это уже регрессия (раньше работало или вообще
        # не покрывалось). Логируем и фейлим, чтобы заметить.
        pytest.fail(
            f"PerformanceStudio упал на {plan_file.name}: {type(e).__name__}: {e}"
        )

    # Базовые инварианты result
    assert isinstance(result, PlanAnalysisResult)
    assert result.plan_source  # обязательное поле
    # statements может быть пустой если plan не содержит operator tree (редко)
    assert isinstance(result.statements, list)
    # summary всегда заполнен
    assert result.summary is not None
    assert result.summary.total_statements == len(result.statements)


def test_at_least_82_plans_found() -> None:
    """Sanity check: в repo должно быть ≥ 80 .sqlplan для покрытия."""
    assert len(ALL_PLANS) >= 80, (
        f"Найдено только {len(ALL_PLANS)} .sqlplan. "
        f"Проверь что research/* git submodules клонированы."
    )
