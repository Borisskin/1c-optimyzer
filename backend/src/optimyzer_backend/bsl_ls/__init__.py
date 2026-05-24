"""bsl-language-server adapter (Sprint 6).

Subprocess+WebSocket sidecar для семантического анализа SDBL запросов.

Использование:
    from optimyzer_backend.bsl_ls import get_client, AnalyzeRequest

    client = await get_client()
    result = await client.analyze_sdbl(
        AnalyzeRequest(query_sdbl="ВЫБРАТЬ * ИЗ Справочник.Контрагенты")
    )
    for diag in result.diagnostics:
        print(diag.code, diag.message)

Singleton: один процесс bsl-LS на весь backend (lazy-start при первом
обращении к QueryAnalyzer). Lifecycle: при exit backend — graceful shutdown.

Архитектура: см. docs/sales_sprint/SPRINT_6_PROMT.md §"PHASE B".
"""

from __future__ import annotations

from .client import BslLsClient, get_client, shutdown_client
from .lifecycle import BslLsLifecycle, BslLsPaths
from .models import (
    AnalyzeRequest,
    AnalyzeResult,
    Diagnostic,
    DiagnosticGroup,
    Position,
    Range,
    Severity,
)

__all__ = [
    "AnalyzeRequest",
    "AnalyzeResult",
    "BslLsClient",
    "BslLsLifecycle",
    "BslLsPaths",
    "Diagnostic",
    "DiagnosticGroup",
    "Position",
    "Range",
    "Severity",
    "get_client",
    "shutdown_client",
]
