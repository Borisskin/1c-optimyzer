"""/v1/subscriptions/* — управление подпиской."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from models.user import User
from schemas.subscriptions import (
    SubscriptionCurrentResponse,
    SubscriptionMutationResponse,
    SubscriptionRead,
)
from services import subscription_service

router = APIRouter(prefix="/v1/subscriptions", tags=["subscriptions"])


@router.get("/current", response_model=SubscriptionCurrentResponse)
def current(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionCurrentResponse:
    sub = subscription_service.get_or_create_subscription(db, user)
    return SubscriptionCurrentResponse(subscription=SubscriptionRead.model_validate(sub))


@router.post("/cancel", response_model=SubscriptionMutationResponse)
def cancel(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionMutationResponse:
    try:
        sub = subscription_service.cancel_subscription(db, user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return SubscriptionMutationResponse(
        subscription=SubscriptionRead.model_validate(sub),
        message="Подписка отменена. Доступ сохранится до конца оплаченного периода.",
    )


@router.post("/reactivate", response_model=SubscriptionMutationResponse)
def reactivate(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionMutationResponse:
    try:
        sub = subscription_service.reactivate_subscription(db, user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return SubscriptionMutationResponse(
        subscription=SubscriptionRead.model_validate(sub),
        message="Авто-продление включено.",
    )
