"""Tests для credits_service и /v1/credits/*."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.credits import Credits, CreditsPackage
from services import credits_service
from tests.factories import access_cookies_for, make_user


def test_grant_package_creates_active_credits(db_session):
    user = make_user(db_session)
    pkg = credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    assert pkg.operations_total == 30
    assert pkg.operations_remaining == 30
    assert pkg.is_active is True


def test_consume_credit_decrements_remaining(db_session):
    user = make_user(db_session)
    credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    consumed = credits_service.consume_credit(db_session, user, amount=1)
    assert consumed is not None
    assert consumed.operations_used == 1


def test_consume_returns_none_when_empty(db_session):
    user = make_user(db_session)
    consumed = credits_service.consume_credit(db_session, user)
    assert consumed is None


def test_consume_uses_nearest_to_expiry_first(db_session):
    user = make_user(db_session)
    later = credits_service.grant_package(db_session, user, CreditsPackage.STANDARD)  # 30 days
    # Создаём пакет с меньшим expiry
    sooner = Credits(
        user_id=user.id,
        package=CreditsPackage.MINI,
        operations_total=30,
        operations_used=0,
        purchased_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=5),
        is_active=True,
    )
    db_session.add(sooner)
    db_session.commit()
    consumed = credits_service.consume_credit(db_session, user)
    assert consumed is not None
    assert consumed.id == sooner.id, "Должны сначала тратить тот что раньше истечёт"


def test_total_remaining_sums_active(db_session):
    user = make_user(db_session)
    credits_service.grant_package(db_session, user, CreditsPackage.MINI)      # 30
    credits_service.grant_package(db_session, user, CreditsPackage.STANDARD)  # 100
    assert credits_service.total_remaining(db_session, user) == 130


def test_expired_packages_excluded(db_session):
    user = make_user(db_session)
    pkg = credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    pkg.expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    assert credits_service.total_remaining(db_session, user) == 0


def test_deactivate_expired_marks_inactive(db_session):
    user = make_user(db_session)
    pkg = credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    pkg.expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    count = credits_service.deactivate_expired(db_session)
    assert count == 1
    db_session.refresh(pkg)
    assert pkg.is_active is False


# --- Router tests ---


def test_balance_endpoint_zero(client, db_session):
    user = make_user(db_session)
    resp = client.get("/v1/credits/balance", cookies=access_cookies_for(user))
    assert resp.status_code == 200
    assert resp.json()["operations_remaining"] == 0


def test_purchase_creates_payment_with_stub_yookassa(client, db_session):
    """В тесте YooKassa не настроен (см. conftest), поэтому create_payment
    возвращает stub confirmation_url. Тест проверяет что эндпоинт корректно
    создаёт Payment-запись и возвращает URL."""
    user = make_user(db_session)
    resp = client.post(
        "/v1/credits/purchase",
        json={"package": "mini"},
        cookies=access_cookies_for(user),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["package"] == "mini"
    assert body["amount_kopecks"] == 29900
    assert body["confirmation_url"].startswith("https://")
    assert body["payment_id"]
