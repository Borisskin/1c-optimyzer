"""Обработка платежей: создание + webhook.

Webhook от YooKassa приходит на /v1/webhooks/yookassa. Что мы делаем:
1. Верифицируем что событие — payment.succeeded (есть и другие, но они нам пока не нужны)
2. Находим Payment по yookassa_payment_id
3. Если status уже SUCCEEDED — это retry от YooKassa (idempotency!), возвращаем 200 без действий
4. Иначе: меняем status, applying business effect (выдача Credits / Pro подписки + ключа)
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.settings import settings
from models.credits import PACKAGE_CONFIG, CreditsPackage
from models.payment import Payment, PaymentPurpose, PaymentStatus
from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User
from services import credits_service, license_keys_service

if TYPE_CHECKING:
    from services.yookassa_client import CreatedPayment


PRO_PRICE_KOPECKS = 299000  # 2 990 ₽


def create_credits_payment(
    db: Session,
    user: User,
    package: CreditsPackage,
    *,
    yookassa_creator=None,
) -> Payment:
    """Создать Payment + соответствующий YooKassa payment для покупки Credits.

    Args:
        yookassa_creator: callable создающий платёж в YooKassa. По умолчанию —
            прямой вызов services.yookassa_client.create_payment. В тестах
            можно передать мок.
    """
    cfg = PACKAGE_CONFIG[package]
    idempotency_key = secrets.token_urlsafe(24)
    payment = Payment(
        user_id=user.id,
        idempotency_key=idempotency_key,
        purpose=PaymentPurpose.CREDITS,
        package_or_plan=package.value,
        amount_kopecks=cfg["price_kopecks"],
        currency="RUB",
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if yookassa_creator is None:
        from services.yookassa_client import create_payment as yookassa_create
        yookassa_creator = yookassa_create

    created: CreatedPayment = yookassa_creator(
        idempotency_key=idempotency_key,
        amount_kopecks=cfg["price_kopecks"],
        description=f"Optimyzer Credits {package.value.capitalize()} · {cfg['operations']} AI операций",
        user_email=user.email,
        metadata={
            "user_id": user.id,
            "payment_id": payment.id,
            "package": package.value,
            "purpose": "credits",
        },
        save_payment_method=False,
    )
    payment.yookassa_payment_id = created.yookassa_payment_id
    payment.confirmation_url = created.confirmation_url
    db.commit()
    db.refresh(payment)
    return payment


def create_subscription_payment(
    db: Session,
    user: User,
    *,
    yookassa_creator=None,
) -> Payment:
    """Создать Payment + YooKassa payment для первой покупки Pro.

    Save_payment_method=True — чтобы можно было recurring через cron.
    """
    idempotency_key = secrets.token_urlsafe(24)
    payment = Payment(
        user_id=user.id,
        idempotency_key=idempotency_key,
        purpose=PaymentPurpose.SUBSCRIPTION,
        package_or_plan="pro",
        amount_kopecks=PRO_PRICE_KOPECKS,
        currency="RUB",
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if yookassa_creator is None:
        from services.yookassa_client import create_payment as yookassa_create
        yookassa_creator = yookassa_create

    created: CreatedPayment = yookassa_creator(
        idempotency_key=idempotency_key,
        amount_kopecks=PRO_PRICE_KOPECKS,
        description="Optimyzer Pro · подписка на 1 месяц",
        user_email=user.email,
        metadata={
            "user_id": user.id,
            "payment_id": payment.id,
            "purpose": "subscription",
        },
        save_payment_method=True,
    )
    payment.yookassa_payment_id = created.yookassa_payment_id
    payment.confirmation_url = created.confirmation_url
    db.commit()
    db.refresh(payment)
    return payment


def handle_payment_succeeded(
    db: Session,
    yookassa_event: dict[str, Any],
) -> Payment | None:
    """Обработать webhook event `payment.succeeded`.

    Returns:
        Обновлённый Payment (или None если событие не для нас, не валидное).
    """
    obj = yookassa_event.get("object", {})
    yookassa_id = obj.get("id")
    if not yookassa_id:
        return None

    payment = db.scalar(select(Payment).where(Payment.yookassa_payment_id == yookassa_id))
    if payment is None:
        # Не наш платёж (либо webhook раньше create_payment). Логируем и игнорируем.
        return None

    # Idempotency: повторный webhook — просто 200.
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = datetime.utcnow()

    user = payment.user

    if payment.purpose == PaymentPurpose.CREDITS:
        try:
            package = CreditsPackage(payment.package_or_plan)
        except ValueError:
            payment.status = PaymentStatus.CANCELLED
            db.commit()
            return payment
        credits_service.grant_package(db, user, package)
    elif payment.purpose == PaymentPurpose.SUBSCRIPTION:
        _upgrade_user_to_pro(db, user, payment, obj)
        license_keys_service.issue_key(db, user, payment=payment)

    db.commit()
    db.refresh(payment)
    return payment


def handle_payment_failed(
    db: Session,
    yookassa_event: dict[str, Any],
) -> Payment | None:
    obj = yookassa_event.get("object", {})
    yookassa_id = obj.get("id")
    if not yookassa_id:
        return None
    payment = db.scalar(select(Payment).where(Payment.yookassa_payment_id == yookassa_id))
    if payment is None:
        return None
    if payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED):
        return payment
    payment.status = PaymentStatus.CANCELLED
    db.commit()
    db.refresh(payment)
    return payment


def _upgrade_user_to_pro(
    db: Session,
    user: User,
    payment: Payment,
    yookassa_object: dict[str, Any],
) -> Subscription:
    """Сделать первую активацию Pro или продлить существующую."""
    sub = user.subscription
    now = datetime.utcnow()
    if sub is None:
        sub = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            starts_at=now,
            ends_at=now + timedelta(days=30),
            auto_renew=True,
            early_adopter=False,
            price_locked_kopecks=payment.amount_kopecks,
        )
        db.add(sub)
    else:
        # Продление — если ends_at в будущем, прибавляем к нему; иначе от now.
        base = sub.ends_at if sub.ends_at > now else now
        sub.plan = SubscriptionPlan.PRO
        sub.status = SubscriptionStatus.ACTIVE
        sub.starts_at = sub.starts_at or now
        sub.ends_at = base + timedelta(days=30)
        sub.auto_renew = True
        if sub.price_locked_kopecks == 0:
            sub.price_locked_kopecks = payment.amount_kopecks
    # Сохраняем payment_method_id для recurring.
    payment_method = yookassa_object.get("payment_method") or {}
    pm_id = payment_method.get("id")
    if pm_id and payment_method.get("saved"):
        sub.yookassa_payment_method_id = pm_id
    db.commit()
    db.refresh(sub)
    return sub
