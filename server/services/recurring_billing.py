"""Cron-задача для recurring Pro платежей.

Каждый день в 03:00 МСК (через APScheduler):
- Найти все подписки с auto_renew=True И ends_at ≤ now + 1 day
- Для каждой — создать новый YooKassa payment через сохранённый payment_method_id
- Успех: продлеваем ends_at на 30 дней
- Неуспех: переводим в PAST_DUE, шлём email юзеру, ждём 7 дней, потом CANCELLED
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import SessionLocal
from models.payment import Payment, PaymentPurpose, PaymentStatus
from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from services.payment_processor import PRO_PRICE_KOPECKS

logger = logging.getLogger("optimyzer.billing")


def run_recurring_billing(
    yookassa_creator=None,
    *,
    session_factory=None,
) -> dict[str, int]:
    """Запустить цикл расчётов. Возвращает счётчики для логов/мониторинга.

    Args:
        session_factory: callable, возвращающая Session. По умолчанию SessionLocal.
            В тестах подменяется на lambda: test_session чтобы не открывать новый.
    """
    if yookassa_creator is None:
        from services.yookassa_client import create_recurring_payment
        yookassa_creator = create_recurring_payment
    if session_factory is None:
        session_factory = SessionLocal

    counts = {"attempted": 0, "succeeded": 0, "failed": 0, "skipped_no_pm": 0, "cancelled_past_due": 0}
    db: Session = session_factory()
    try:
        now = datetime.utcnow()
        due_threshold = now + timedelta(days=1)
        active_due = db.scalars(
            select(Subscription).where(
                Subscription.plan == SubscriptionPlan.PRO,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.auto_renew.is_(True),
                Subscription.ends_at <= due_threshold,
            )
        ).all()

        for sub in active_due:
            counts["attempted"] += 1
            if not sub.yookassa_payment_method_id:
                counts["skipped_no_pm"] += 1
                logger.warning("Sub %s missing payment_method_id; skipping", sub.id)
                continue
            try:
                _charge_one(db, sub, yookassa_creator)
                counts["succeeded"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Recurring charge failed for sub %s: %s", sub.id, exc)
                sub.status = SubscriptionStatus.PAST_DUE
                db.commit()
                counts["failed"] += 1

        # Истёкшие PAST_DUE дольше 7 дней → CANCELLED.
        past_due_threshold = now - timedelta(days=7)
        stale = db.scalars(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.PAST_DUE,
                Subscription.updated_at <= past_due_threshold,
            )
        ).all()
        for sub in stale:
            sub.status = SubscriptionStatus.CANCELLED
            sub.auto_renew = False
            counts["cancelled_past_due"] += 1
        db.commit()
    finally:
        # Если внешний код передал свою session — не закрываем (он сам управит lifecycle).
        if session_factory is SessionLocal:
            db.close()
    logger.info("Recurring billing tick: %s", counts)
    return counts


def _charge_one(db: Session, sub: Subscription, yookassa_creator) -> Payment:
    idempotency_key = secrets.token_urlsafe(24)
    payment = Payment(
        user_id=sub.user_id,
        idempotency_key=idempotency_key,
        purpose=PaymentPurpose.SUBSCRIPTION,
        package_or_plan="pro",
        amount_kopecks=sub.price_locked_kopecks or PRO_PRICE_KOPECKS,
        currency="RUB",
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    created = yookassa_creator(
        idempotency_key=idempotency_key,
        payment_method_id=sub.yookassa_payment_method_id,
        amount_kopecks=payment.amount_kopecks,
        description="Optimyzer Pro · продление на 1 месяц",
        user_email=sub.user.email,
        metadata={
            "user_id": sub.user_id,
            "payment_id": payment.id,
            "purpose": "subscription_renewal",
        },
    )
    payment.yookassa_payment_id = created.yookassa_payment_id
    # Если YooKassa сразу подтвердил списание (recurring without 3DS, обычно).
    raw_status = created.raw.get("status") if isinstance(created.raw, dict) else None
    if raw_status == "succeeded":
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.utcnow()
        # Продлеваем подписку.
        base = sub.ends_at if sub.ends_at > datetime.utcnow() else datetime.utcnow()
        sub.ends_at = base + timedelta(days=30)
        sub.status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(payment)
    return payment
