"""/v1/ai/* — AI orchestration (Sprint 6 Phase D + Sprint 11 caching).

Sprint 11 добавил:
  - Caching (один и тот же запрос → cached response, без повторного AI call)
  - Force Refresh с rate limiting (5 min per-item + 10/hour per-session)
  - /force_refresh_status endpoint для UI countdown

Phase 1 INFRA позже добавит:
  - JWT auth с user_id
  - Soft caps tracking
  - Multi-model routing (Sonnet/Opus в зависимости от tier)
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from schemas.ai import (
    ExplainRequest,
    ExplainResponse,
    LogcfgGenerateRequest,
    LogcfgGenerateResponse,
    PlanExplainRequest,
    PlanExplainResponse,
    RegressionExplainRequest,
    RegressionExplainResponse,
)
from services import config_service
from services.ai_explainer import (
    AiExplainerError,
    AiNotConfiguredError,
    explain_plan_query,
    explain_query,
    explain_regression,
    generate_logcfg,
)
from services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# ВАЖНО (безопасность/деньги): все /v1/ai/* требуют авторизации.
#
# До этого эндпоинты были открыты: единственной проверкой был глобальный
# kill-switch, поэтому любой, кто знает адрес api.optimyzer.pro, мог слать
# запросы и тратить наш ANTHROPIC_API_KEY. Сам ключ при этом никогда не
# покидал сервер (утечки ключа не было), но расход оплачивали мы.
#
# get_current_user отдаёт 401 без валидного Bearer access token, что полностью
# исключает анонимные вызовы. Дополнительно — потолок трат (_daily_budget_guard)
# как предохранитель на случай скомпрометированного аккаунта.
#
# ---------------------------------------------------------------------------
# Предохранитель по тратам: глобальный дневной потолок AI-вызовов.
#
# Второй рубеж после авторизации. Авторизация отсекает анонимов, но не спасёт,
# если аккаунт скомпрометирован или свой же клиент зациклится в ретраях.
# Потолок ограничивает максимальный дневной ущерб фиксированной суммой.
# ---------------------------------------------------------------------------

AI_DAILY_CALL_LIMIT = int(os.environ.get("OPTIMYZER_AI_DAILY_CALL_LIMIT", "500"))

_budget_lock = threading.Lock()
_budget_day: date | None = None
_budget_calls: int = 0


def _daily_budget_guard() -> None:
    """Считает AI-вызовы за сутки (UTC) и отклоняет всё сверх лимита.

    Кэш-хиты сюда тоже попадают — это осознанно: лимит грубый и защищает
    кошелёк, а не оптимизирует UX. Порог задаётся OPTIMYZER_AI_DAILY_CALL_LIMIT.
    """
    global _budget_day, _budget_calls
    today = datetime.now(timezone.utc).date()
    with _budget_lock:
        if _budget_day != today:
            _budget_day = today
            _budget_calls = 0
        if _budget_calls >= AI_DAILY_CALL_LIMIT:
            logger.error(
                "AI дневной потолок исчерпан: %s вызовов (лимит %s). "
                "Запросы отклоняются до конца суток UTC.",
                _budget_calls,
                AI_DAILY_CALL_LIMIT,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "ai_daily_limit_reached",
                    "message": "AI-функции временно недоступны. Попробуйте завтра.",
                },
            )
        _budget_calls += 1


router = APIRouter(
    prefix="/v1/ai",
    tags=["ai"],
    dependencies=[Depends(get_current_user), Depends(_daily_budget_guard)],
)


def ai_enabled_guard(db: Annotated[Session, Depends(get_db)]) -> None:
    """S13 — глобальный AI kill-switch из Remote Config. Если включён, AI-вызовы
    мягко отклоняются (503), не ломая остальной продукт. Авторитетная проверка
    на сервере (desktop дополнительно прячет кнопки по конфигу)."""
    if config_service.is_ai_kill_switch_on(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "ai_temporarily_unavailable",
                "message": "AI-функции временно недоступны. Попробуйте позже.",
            },
        )


# ============================================================================
# Sprint 11 Phase D — Force Refresh rate limiting helpers
# ============================================================================


def _check_force_refresh_or_raise(force_refresh: bool, cache_key_hint: str) -> None:
    """Если force_refresh — проверить rate limiter и raise 429 если cooldown.

    cache_key_hint — мы НЕ знаем cache_key ДО вызова (он вычисляется внутри
    ai_explainer). Используем эвристический key из request payload как proxy —
    для force refresh цель — защитить от спам-кликов на одной AI карточке,
    поэтому per-payload key достаточно.
    """
    if not force_refresh:
        return
    limiter = get_rate_limiter()
    status_obj = limiter.check_and_record(cache_key_hint)
    if not status_obj.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "force_refresh_rate_limited",
                "reason": status_obj.reason,
                "per_item_remaining_seconds": status_obj.per_item_remaining_seconds,
                "per_session_used": status_obj.per_session_used,
                "per_session_limit": status_obj.per_session_limit,
                "per_session_remaining_seconds": status_obj.per_session_remaining_seconds,
                "message": (
                    "Force refresh заблокирован cooldown'ом. "
                    "AI ответы при одинаковых данных стабильны."
                ),
            },
        )


# ============================================================================
# Sprint 11 Phase D — Force Refresh Status endpoint
# ============================================================================


class ForceRefreshStatusResponse(BaseModel):
    """Статус force refresh для конкретного cache_key (UI countdown)."""

    allowed: bool
    per_item_remaining_seconds: int
    per_session_used: int
    per_session_limit: int
    per_session_remaining_seconds: int


@router.get(
    "/force_refresh_status/{cache_key}", response_model=ForceRefreshStatusResponse
)
async def get_force_refresh_status(cache_key: str) -> ForceRefreshStatusResponse:
    """UI запрашивает каждые 5 сек чтобы обновить countdown на кнопке."""
    limiter = get_rate_limiter()
    s = limiter.check(cache_key)
    return ForceRefreshStatusResponse(
        allowed=s.allowed,
        per_item_remaining_seconds=s.per_item_remaining_seconds,
        per_session_used=s.per_session_used,
        per_session_limit=s.per_session_limit,
        per_session_remaining_seconds=s.per_session_remaining_seconds,
    )


@router.post("/explain", response_model=ExplainResponse)
async def post_explain(
    req: ExplainRequest,
    _guard: Annotated[None, Depends(ai_enabled_guard)],
) -> ExplainResponse:
    """Structured AI explanation поверх SDBL запроса + bsl-LS диагностик."""
    # Sprint 11 — Force refresh rate limiting. Используем hash(sdbl) как proxy.
    _check_force_refresh_or_raise(req.force_refresh, f"explain:{hash(req.query_sdbl)}")
    try:
        return await explain_query(req)
    except AiNotConfiguredError as e:
        logger.warning("AI endpoint вызван без ANTHROPIC_API_KEY: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_not_configured", "message": str(e)},
        )
    except AiExplainerError as e:
        logger.exception("AI explain failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_orchestration_failed", "message": str(e)},
        )


@router.post("/explain_plan", response_model=PlanExplainResponse)
async def post_explain_plan(
    req: PlanExplainRequest,
    _guard: Annotated[None, Depends(ai_enabled_guard)],
) -> PlanExplainResponse:
    """Sprint 7: Structured AI explanation поверх execution plan + PerformanceStudio warnings."""
    _check_force_refresh_or_raise(
        req.force_refresh, f"plan:{req.engine}:{hash(req.plan_xml)}"
    )
    try:
        return await explain_plan_query(req)
    except AiNotConfiguredError as e:
        logger.warning("AI explain_plan вызван без ANTHROPIC_API_KEY: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_not_configured", "message": str(e)},
        )
    except AiExplainerError as e:
        logger.exception("AI explain_plan failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_orchestration_failed", "message": str(e)},
        )


@router.post("/explain_regression", response_model=RegressionExplainResponse)
async def post_explain_regression(
    req: RegressionExplainRequest,
    _guard: Annotated[None, Depends(ai_enabled_guard)],
) -> RegressionExplainResponse:
    """Sprint 11 Phase F — короткое AI объяснение регрессии операции."""
    _check_force_refresh_or_raise(
        req.force_refresh,
        f"regression:{hash(req.operation_name)}:{hash(req.context_signature)}",
    )
    try:
        return await explain_regression(req)
    except AiNotConfiguredError as e:
        logger.warning("AI explain_regression вызван без ANTHROPIC_API_KEY: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_not_configured", "message": str(e)},
        )
    except AiExplainerError as e:
        logger.exception("AI explain_regression failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_orchestration_failed", "message": str(e)},
        )


@router.post("/generate_logcfg", response_model=LogcfgGenerateResponse)
async def post_generate_logcfg(
    req: LogcfgGenerateRequest,
    _guard: Annotated[None, Depends(ai_enabled_guard)],
) -> LogcfgGenerateResponse:
    """Sprint 10: Генерация настройки logcfg.xml через Haiku по описанию проблемы производительности."""
    _check_force_refresh_or_raise(
        req.force_refresh, f"logcfg:{hash(req.problem_description)}"
    )
    try:
        return await generate_logcfg(req)
    except AiNotConfiguredError as e:
        logger.warning("AI generate_logcfg вызван без ANTHROPIC_API_KEY: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_not_configured", "message": str(e)},
        )
    except AiExplainerError as e:
        logger.exception("AI generate_logcfg failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_orchestration_failed", "message": str(e)},
        )
