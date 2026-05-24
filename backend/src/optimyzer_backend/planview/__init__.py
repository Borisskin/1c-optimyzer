"""PerformanceStudio CLI wrapper (Sprint 7 Phase A).

Обёртка над `planview.exe` от PerformanceStudio (Erik Darling Data, MIT) —
analyzer execution plans MS SQL Server с 30 antipattern rules.

Bundled binary: `frontend/src-tauri/binaries/planview/planview.exe`
В dev-mode fallback на собранный планview в research/.

Public API:
    cli.analyze_plan_file(path) -> PlanAnalysisResult
    cli.analyze_plan_xml(xml) -> PlanAnalysisResult
    cli.is_available() -> bool
    cli.get_binary_path() -> Path | None
"""

from __future__ import annotations

from .models import (
    MemoryGrantResult,
    MissingIndexResult,
    OperatorResult,
    PlanAnalysisResult,
    PlanAnalysisSummary,
    QueryTimeResult,
    StatementResult,
    WarningResult,
)

__all__ = [
    "MemoryGrantResult",
    "MissingIndexResult",
    "OperatorResult",
    "PlanAnalysisResult",
    "PlanAnalysisSummary",
    "QueryTimeResult",
    "StatementResult",
    "WarningResult",
]
