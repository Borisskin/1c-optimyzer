"""/v1/webhooks/* — внешние webhooks (YooKassa)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.db import get_db
from services import payment_processor

logger = logging.getLogger("optimyzer.webhooks")

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def verify_yookassa_signature(request: Request, body_bytes: bytes) -> None:
    """Проверка подписи webhook.

    На момент написания YooKassa не подписывает webhook'и стандартно. Если включат —
    проверка через заголовок (точное имя зависит от их docs). Сейчас — заглушка
    которая просто пропускает (за безопасность отвечает фильтрация по IP YooKassa
    на nginx-уровне).
    """
    # TODO Phase 2.x: добавить IP allowlist для YooKassa CIDR
    _ = request, body_bytes
    return


@router.post("/yookassa", status_code=200)
async def yookassa_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Webhook от YooKassa.

    События:
    - payment.succeeded — основное (Credits/Pro активируются)
    - payment.canceled — Pending → Cancelled
    - refund.succeeded — refund issued
    """
    body_bytes = await request.body()
    verify_yookassa_signature(request, body_bytes)
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON") from exc

    event = payload.get("event")
    if not event:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing event field")

    logger.info("YooKassa webhook: event=%s", event)

    if event == "payment.succeeded":
        payment = payment_processor.handle_payment_succeeded(db, payload)
        return {"received": True, "payment_id": payment.id if payment else None}

    if event in ("payment.canceled", "payment.cancelled"):
        payment = payment_processor.handle_payment_failed(db, payload)
        return {"received": True, "payment_id": payment.id if payment else None}

    if event == "refund.succeeded":
        # TODO Phase 2.x: реализовать обработку refunds
        logger.info("Refund event received — manual handling required for now")
        return {"received": True, "note": "refund_event_logged"}

    logger.info("Unhandled YooKassa event: %s", event)
    return {"received": True, "note": "event_ignored"}
