"""/v1/ai/* — AI orchestration (Sprint 6 Phase D).

В Sprint 6 — минимальный endpoint без auth/caching. Phase 1 INFRA добавит:
  - JWT auth с user_id
  - Caching (один и тот же запрос — один и тот же ответ)
  - Soft caps tracking
  - Multi-model routing (Sonnet/Opus в зависимости от tier)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from schemas.ai import (
    ExplainRequest,
    ExplainResponse,
    PlanExplainRequest,
    PlanExplainResponse,
)
from services.ai_explainer import (
    AiExplainerError,
    AiNotConfiguredError,
    explain_plan_query,
    explain_query,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ai", tags=["ai"])


@router.post("/explain", response_model=ExplainResponse)
async def post_explain(req: ExplainRequest) -> ExplainResponse:
    """Structured AI explanation поверх SDBL запроса + bsl-LS диагностик."""
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
async def post_explain_plan(req: PlanExplainRequest) -> PlanExplainResponse:
    """Sprint 7: Structured AI explanation поверх execution plan + PerformanceStudio warnings."""
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
