"""Sprint 4 — BSL Language Server client (placeholder).

В Sprint 4 принято архитектурное решение НЕ использовать BSL Language Server
для анализа SDBL-запросов (см. ADR-025 и docs/BSL_LS_GAP_ANALYSIS.md).

Этот модуль оставлен как **placeholder с зарезервированным API контрактом**:
если в будущем (Sprint 5+) появится потребность анализировать `.bsl` файлы
с embedded `Запрос.Текст = "..."`, тут уже будет точка интеграции.

В Sprint 4 `BSLLanguageServerClient.available` всегда False, `analyze_query`
возвращает пустой список.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BSLDiagnostic:
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    severity: str
    code: str
    message: str
    source: str = "bsl-language-server"


class BSLLanguageServerClient:
    """Placeholder client. Sprint 4: всегда disabled. Sprint 5+: при включении
    интегрируется как Java sidecar (subprocess) для анализа BSL-модулей.

    API контракт зарезервирован чтобы Sprint 5+ не переделывал aggregator/RPC.
    """

    def __init__(self, jar_path: str | None = None) -> None:
        self._jar_path = jar_path
        # Sprint 4: hard-disabled. См. ADR-025 — pivot to native-only.
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def analyze_query(self, query_text: str, *, timeout: float = 30.0) -> list[BSLDiagnostic]:  # noqa: ARG002
        return []
