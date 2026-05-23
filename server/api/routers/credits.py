"""/v1/credits/* — баланс, история, purchase."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from models.user import User
from schemas.credits import (
    CreditsBalanceResponse,
    CreditsHistoryItem,
    CreditsHistoryResponse,
    CreditsPackageRead,
    CreditsPurchaseRequest,
    CreditsPurchaseResponse,
)
from services import credits_service, payment_processor

router = APIRouter(prefix="/v1/credits", tags=["credits"])


@router.get("/balance", response_model=CreditsBalanceResponse)
def balance(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CreditsBalanceResponse:
    active = credits_service.list_active_packages(db, user)
    all_pkgs = credits_service.list_all_packages(db, user)
    total_purchased = sum(p.operations_total for p in all_pkgs)
    total_used = sum(p.operations_used for p in all_pkgs)
    return CreditsBalanceResponse(
        operations_remaining=credits_service.total_remaining(db, user),
        operations_total_purchased=total_purchased,
        operations_used_total=total_used,
        active_packages=[
            CreditsPackageRead.model_validate(
                {
                    "id": p.id,
                    "package": p.package.value,
                    "operations_total": p.operations_total,
                    "operations_used": p.operations_used,
                    "operations_remaining": p.operations_remaining,
                    "purchased_at": p.purchased_at,
                    "expires_at": p.expires_at,
                    "is_active": p.is_active,
                }
            )
            for p in active
        ],
    )


@router.get("/history", response_model=CreditsHistoryResponse)
def history(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CreditsHistoryResponse:
    rows = credits_service.list_all_packages(db, user)
    return CreditsHistoryResponse(
        items=[
            CreditsHistoryItem.model_validate(
                {
                    "id": p.id,
                    "package": p.package.value,
                    "operations_total": p.operations_total,
                    "operations_used": p.operations_used,
                    "purchased_at": p.purchased_at,
                    "expires_at": p.expires_at,
                    "is_active": p.is_active,
                }
            )
            for p in rows
        ],
    )


@router.post("/purchase", response_model=CreditsPurchaseResponse)
def purchase(
    request: CreditsPurchaseRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CreditsPurchaseResponse:
    """Создать YooKassa payment + Payment запись. Возвращает confirmation_url
    куда фронт редиректит юзера для оплаты."""
    try:
        payment = payment_processor.create_credits_payment(db, user, request.package)
    except Exception as exc:  # noqa: BLE001
        # YooKassa unavailable / credentials missing — даём осмысленную ошибку.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Payment service unavailable: {exc}",
        ) from exc
    return CreditsPurchaseResponse(
        payment_id=payment.id,
        confirmation_url=payment.confirmation_url or "",
        amount_kopecks=payment.amount_kopecks,
        package=request.package,
    )
