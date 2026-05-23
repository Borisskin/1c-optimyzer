"""/v1/subscriptions/* — управление подпиской."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from models.user import User
from schemas.subscriptions import (
    SubscriptionCurrentResponse,
    SubscriptionMutationResponse,
    SubscriptionRead,
)
from services import payment_processor, subscription_service

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


class SubscriptionPurchaseResponse(BaseModel):
    """POST /v1/subscriptions/purchase — для покупки/продления Pro."""

    payment_id: str
    confirmation_url: str
    amount_kopecks: int


@router.post("/purchase", response_model=SubscriptionPurchaseResponse)
def purchase_pro(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionPurchaseResponse:
    """Создать YooKassa payment для Pro (с save_payment_method для recurring).

    Это для нового юзера или для юзера который отменил и хочет вернуться.
    """
    try:
        payment = payment_processor.create_subscription_payment(db, user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Payment service unavailable: {exc}",
        ) from exc
    return SubscriptionPurchaseResponse(
        payment_id=payment.id,
        confirmation_url=payment.confirmation_url or "",
        amount_kopecks=payment.amount_kopecks,
    )
