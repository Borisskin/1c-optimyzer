"""AI-функции в sidecar: вызовы идут с машины пользователя его ключом (BYOK).

Раньше это жило на нашем сервере (ADR-057): фронт ходил в api.optimyzer.pro,
ключ был наш, каждый вызов оплачивали мы. Сервер при этом так и не был
задеплоен — домен не резолвился, поэтому AI не работал вообще ни у кого.

Теперь оркестратор (optimyzer_backend.ai.explainer) — тот же самый код, но
исполняется локально, на ключе пользователя. Наш сервер в AI-пути не участвует.

Функции explainer'а асинхронные (наследие FastAPI), а RPC-диспетчер sidecar'а
синхронный, поэтому каждый вызов прогоняется через asyncio.run.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from optimyzer_backend.ai import explainer
from optimyzer_backend.ai.schemas import (
    ExplainRequest,
    LogcfgGenerateRequest,
    PlanExplainRequest,
    RegressionExplainRequest,
)
from optimyzer_backend.rpc.dispatcher import rpc

logger = logging.getLogger(__name__)


class AiNotConfiguredError(RuntimeError):
    """Ключ пользователя не задан — UI предлагает ввести его в настройках."""


def _run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Синхронно исполняет корутину explainer'а."""
    return asyncio.run(coro)


def _call(
    fn: Callable[[Any], Coroutine[Any, Any, Any]],
    req: Any,
    what: str,
) -> dict[str, Any]:
    """Общая обёртка: единый формат ответа и человеческие ошибки.

    Технические детали (модель, токены, стектрейсы) не отдаём в UI — только в
    лог; в интерфейсе продукта им не место.
    """
    from optimyzer_backend.ai.config import settings

    if not settings.anthropic_api_key:
        return {
            "ok": False,
            "error": "ai_not_configured",
            "message": (
                "AI не настроен: укажите свой ключ Anthropic в настройках "
                "приложения (Настройки → AI)."
            ),
        }
    try:
        result = _run(fn(req))
        return {"ok": True, "result": result.model_dump()}
    except Exception as e:  # noqa: BLE001 — любая ошибка AI не должна ронять sidecar
        logger.exception("AI %s failed", what)
        return {
            "ok": False,
            "error": "ai_failed",
            "message": f"Не удалось получить объяснение: {e}",
        }


@rpc("ai_explain")
def ai_explain(**payload: Any) -> dict[str, Any]:
    """Объяснение SDBL-запроса + диагностик bsl-LS."""
    return _call(explainer.explain_query, ExplainRequest(**payload), "explain")


@rpc("ai_explain_plan")
def ai_explain_plan(**payload: Any) -> dict[str, Any]:
    """Объяснение плана запроса (MSSQL / PostgreSQL)."""
    return _call(
        explainer.explain_plan_query, PlanExplainRequest(**payload), "explain_plan"
    )


@rpc("ai_explain_regression")
def ai_explain_regression(**payload: Any) -> dict[str, Any]:
    """Объяснение регрессии производительности между архивами."""
    return _call(
        explainer.explain_regression,
        RegressionExplainRequest(**payload),
        "explain_regression",
    )


@rpc("ai_generate_logcfg")
def ai_generate_logcfg(**payload: Any) -> dict[str, Any]:
    """Генерация logcfg.xml по описанию задачи на естественном языке."""
    return _call(
        explainer.generate_logcfg, LogcfgGenerateRequest(**payload), "generate_logcfg"
    )


@rpc("ai_status")
def ai_status() -> dict[str, Any]:
    """Готов ли AI к работе — для показа подсказки «введите ключ» в UI."""
    from optimyzer_backend.ai.config import settings

    return {
        "ok": True,
        "enabled": bool(settings.anthropic_api_key),
        "model": settings.ai_model,
    }
