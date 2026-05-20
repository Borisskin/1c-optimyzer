"""Sprint 4 — Solution Generator placeholder.

Зарезервированный API контракт под Sprint 8-9 (AI-генератор обработок 1С
под конкретную базу через MCP BSL Atlas).

В Sprint 4 всегда возвращает 501 Not Implemented. Frontend кнопка
«Сгенерировать решение» не рендерится — backend контракт готов чтобы
Sprint 8 просто включил его без переделки aggregator/RPC.
"""

from __future__ import annotations

from typing import Any


class SolutionGenerator:
    def __init__(self) -> None:
        self.enabled = False  # Sprint 4: всегда False. Sprint 8: True при MCP integration.

    def generate_solution(
        self,
        finding_id: str,  # noqa: ARG002
        base_context: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "error": "Solution generator not yet implemented (planned for Sprint 8)",
            "status_code": 501,
        }
