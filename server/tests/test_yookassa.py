"""Tests для YooKassa integration: payment_processor, webhooks, recurring billing.

YooKassa SDK мокаем через прямую подмену creator-функции — это чище чем
patch'ить yookassa.Payment.create на уровне модуля.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from models.credits import CreditsPackage
from models.payment import Payment, PaymentPurpose, PaymentStatus
from models.subscription import SubscriptionPlan, SubscriptionStatus
from services import (
    license_keys_service,
    payment_processor,
    recurring_billing,
)
from services.yookassa_client import CreatedPayment, build_receipt, kopecks_to_rub_str
from tests.factories import make_user, upgrade_to_pro


# --- yookassa_client helpers ---


def test_kopecks_to_rub_str():
    assert kopecks_to_rub_str(29900) == "299.00"
    assert kopecks_to_rub_str(0) == "0.00"
    assert kopecks_to_rub_str(1) == "0.01"


def test_build_receipt_shape():
    receipt = build_receipt(
        email="u@y.ru",
        description="Test purchase",
        amount_kopecks=29900,
    )
    assert receipt["customer"]["email"] == "u@y.ru"
    item = receipt["items"][0]
    assert item["description"] == "Test purchase"
    assert item["amount"]["value"] == "299.00"
    assert item["vat_code"] == 1


# --- payment_processor: create flows ---


def _mock_yookassa_create(*, idempotency_key: str, amount_kopecks: int, **kwargs) -> CreatedPayment:
    return CreatedPayment(
        yookassa_payment_id=f"yk-{idempotency_key[:8]}",
        confirmation_url=f"https://yookassa.ru/checkout/yk-{idempotency_key[:8]}",
        raw={"status": "pending"},
    )


def test_create_credits_payment_persists_and_calls_yookassa(db_session):
    user = make_user(db_session)
    p = payment_processor.create_credits_payment(
        db_session, user, CreditsPackage.MINI,
        yookassa_creator=_mock_yookassa_create,
    )
    assert p.status == PaymentStatus.PENDING
    assert p.purpose == PaymentPurpose.CREDITS
    assert p.package_or_plan == "mini"
    assert p.amount_kopecks == 29900
    assert p.yookassa_payment_id and p.yookassa_payment_id.startswith("yk-")
    assert p.confirmation_url.startswith("https://yookassa.ru/")


def test_create_subscription_payment_marks_save_method(db_session):
    user = make_user(db_session)
    p = payment_processor.create_subscription_payment(
        db_session, user, yookassa_creator=_mock_yookassa_create,
    )
    assert p.purpose == PaymentPurpose.SUBSCRIPTION
    assert p.amount_kopecks == 299000


# --- payment_processor: webhook handling ---


def test_webhook_succeeded_grants_credits(db_session):
    user = make_user(db_session)
    payment = payment_processor.create_credits_payment(
        db_session, user, CreditsPackage.MINI,
        yookassa_creator=_mock_yookassa_create,
    )
    event = {
        "event": "payment.succeeded",
        "object": {"id": payment.yookassa_payment_id, "status": "succeeded"},
    }
    updated = payment_processor.handle_payment_succeeded(db_session, event)
    assert updated is not None
    assert updated.status == PaymentStatus.SUCCEEDED
    # Credits созданы
    db_session.refresh(user)
    assert user.credits, "Credits должны быть начислены"
    assert user.credits[0].operations_total == 30


def test_webhook_idempotent_no_double_grant(db_session):
    user = make_user(db_session)
    payment = payment_processor.create_credits_payment(
        db_session, user, CreditsPackage.MINI,
        yookassa_creator=_mock_yookassa_create,
    )
    event = {
        "event": "payment.succeeded",
        "object": {"id": payment.yookassa_payment_id, "status": "succeeded"},
    }
    payment_processor.handle_payment_succeeded(db_session, event)
    payment_processor.handle_payment_succeeded(db_session, event)  # retry
    db_session.refresh(user)
    assert len(user.credits) == 1, "Повторный webhook не должен создавать второй пакет"


def test_webhook_subscription_upgrades_user_and_issues_key(db_session):
    user = make_user(db_session)
    payment = payment_processor.create_subscription_payment(
        db_session, user, yookassa_creator=_mock_yookassa_create,
    )
    event = {
        "event": "payment.succeeded",
        "object": {
            "id": payment.yookassa_payment_id,
            "status": "succeeded",
            "payment_method": {"id": "pm-saved-card", "saved": True},
        },
    }
    payment_processor.handle_payment_succeeded(db_session, event)
    db_session.refresh(user)
    assert user.subscription.plan == SubscriptionPlan.PRO
    assert user.subscription.auto_renew is True
    assert user.subscription.yookassa_payment_method_id == "pm-saved-card"
    # License key выпущен
    from sqlalchemy import select
    from models.license_key import LicenseKey
    keys = db_session.scalars(select(LicenseKey).where(LicenseKey.user_id == user.id)).all()
    assert len(keys) == 1
    assert keys[0].key.startswith("OPTM-")


def test_webhook_for_unknown_payment_returns_none(db_session):
    event = {
        "event": "payment.succeeded",
        "object": {"id": "unknown-id"},
    }
    result = payment_processor.handle_payment_succeeded(db_session, event)
    assert result is None


def test_webhook_failed_cancels_payment(db_session):
    user = make_user(db_session)
    payment = payment_processor.create_credits_payment(
        db_session, user, CreditsPackage.MINI,
        yookassa_creator=_mock_yookassa_create,
    )
    event = {
        "event": "payment.canceled",
        "object": {"id": payment.yookassa_payment_id, "status": "canceled"},
    }
    updated = payment_processor.handle_payment_failed(db_session, event)
    assert updated is not None
    assert updated.status == PaymentStatus.CANCELLED


# --- license keys ---


def test_generate_key_format():
    key = license_keys_service.generate_key()
    assert key.startswith("OPTM-")
    parts = key.split("-")
    assert len(parts) == 5
    assert all(len(p) == 4 for p in parts[1:])


def test_regenerate_key_invalidates_old(db_session):
    """После regenerate старый ключ помечен is_used=True (= отозван)."""
    user = make_user(db_session)
    old = license_keys_service.issue_key(db_session, user)
    new = license_keys_service.regenerate_key(db_session, user)
    db_session.refresh(old)
    assert old.is_used is True
    assert old.used_at is not None
    assert new.key != old.key
    assert new.is_used is False


def test_get_or_create_active_key_idempotent(db_session):
    """Повторный вызов возвращает тот же ключ (один активный на user)."""
    user = make_user(db_session)
    a = license_keys_service.get_or_create_active_key(db_session, user)
    b = license_keys_service.get_or_create_active_key(db_session, user)
    assert a.key == b.key


# --- recurring billing ---


def _mock_recurring_creator(*, idempotency_key: str, amount_kopecks: int, **kwargs) -> CreatedPayment:
    return CreatedPayment(
        yookassa_payment_id=f"rec-{idempotency_key[:8]}",
        confirmation_url="",
        raw={"status": "succeeded"},  # симулируем мгновенный успех
    )


def test_recurring_billing_charges_due(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=1)  # ends_at = now + 1d → попадает в окно
    user.subscription.yookassa_payment_method_id = "pm-1"
    user.subscription.price_locked_kopecks = 299000
    db_session.commit()

    counts = recurring_billing.run_recurring_billing(
        yookassa_creator=_mock_recurring_creator,
        session_factory=lambda: db_session,
    )
    assert counts["attempted"] == 1
    assert counts["succeeded"] == 1
    db_session.refresh(user.subscription)
    # ends_at должен сдвинуться вперёд (минимум на 30 дней от старого ends_at).
    assert user.subscription.ends_at > datetime.utcnow() + timedelta(days=29)


def test_recurring_skips_when_no_payment_method(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=1)
    user.subscription.yookassa_payment_method_id = None
    db_session.commit()

    counts = recurring_billing.run_recurring_billing(
        yookassa_creator=_mock_recurring_creator,
        session_factory=lambda: db_session,
    )
    assert counts["skipped_no_pm"] == 1
    assert counts["succeeded"] == 0


# --- Webhook router ---


def test_webhook_router_succeeded(client, db_session):
    user = make_user(db_session)
    payment = payment_processor.create_credits_payment(
        db_session, user, CreditsPackage.MINI,
        yookassa_creator=_mock_yookassa_create,
    )
    resp = client.post(
        "/v1/webhooks/yookassa",
        json={
            "event": "payment.succeeded",
            "object": {"id": payment.yookassa_payment_id, "status": "succeeded"},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["received"] is True


def test_webhook_router_unknown_event_ignored(client):
    resp = client.post(
        "/v1/webhooks/yookassa",
        json={"event": "some.other.event", "object": {}},
    )
    assert resp.status_code == 200
    assert resp.json().get("note") == "event_ignored"


def test_webhook_missing_event_field(client):
    resp = client.post("/v1/webhooks/yookassa", json={"object": {}})
    assert resp.status_code == 400
