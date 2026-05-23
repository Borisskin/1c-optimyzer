"""/v1/usage/* — track/check/summary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_device_user, get_current_user
from models.device import Device
from models.subscription import SubscriptionPlan
from models.user import User
from schemas.usage import (
    UsageCheckResponse,
    UsageSummaryResponse,
    UsageTrackRequest,
    UsageTrackResponse,
)
from services import credits_service, soft_caps, usage_service

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/check", response_model=UsageCheckResponse)
def check_can_run(
    cost: int = 1,
    auth: Annotated[tuple[User, str], Depends(get_current_device_user)] = ...,
    db: Annotated[Session, Depends(get_db)] = ...,
) -> UsageCheckResponse:
    """Desktop спрашивает: можно ли AI-операцию?"""
    user, _device_id = auth
    decision = soft_caps.decide(db, user, cost=cost)
    free_remaining = soft_caps.free_quota_remaining(db, user)
    credits_remaining = credits_service.total_remaining(db, user)
    pro_active = bool(user.subscription and user.subscription.is_pro_active)
    return UsageCheckResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        billed_against=decision.billed_against,
        options=list(decision.options),
        free_quota_remaining=free_remaining,
        credits_remaining=credits_remaining,
        pro_active=pro_active,
    )


@router.post("/track", response_model=UsageTrackResponse)
def track(
    payload: UsageTrackRequest,
    auth: Annotated[tuple[User, str], Depends(get_current_device_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UsageTrackResponse:
    """Desktop сообщает о выполненной операции (после неё)."""
    user, device_id = auth
    device = db.get(Device, device_id)
    try:
        record = usage_service.track(
            db,
            user,
            device=device,
            operation_type=payload.operation_type,
            archive_hash=payload.archive_hash,
            cost=payload.cost_credits,
            success=payload.success,
            ai_tokens_input=payload.ai_tokens_input,
            ai_tokens_output=payload.ai_tokens_output,
            ai_cost_usd=payload.ai_cost_usd,
        )
    except usage_service.UsageDeniedError as exc:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, str(exc)) from exc
    return UsageTrackResponse(
        usage_id=record.id,
        billed_against=record.billed_against,
    )


@router.get("/summary", response_model=UsageSummaryResponse)
def summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UsageSummaryResponse:
    """Cabinet тянет сводку для Overview / Usage страниц."""
    data = usage_service.summary_for_user(db, user)
    return UsageSummaryResponse(**data)
