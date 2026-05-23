"""Tests для /v1/subscriptions/* и services.subscription_service."""

from __future__ import annotations

import pytest

from services import subscription_service
from tests.factories import access_cookies_for, make_user, upgrade_to_pro


def test_get_or_create_subscription_returns_free_for_new_user(db_session):
    user = make_user(db_session)
    sub = subscription_service.get_or_create_subscription(db_session, user)
    assert sub.plan.value == "free"
    assert sub.status.value == "active"
    assert sub.auto_renew is False


def test_cancel_free_subscription_raises(db_session):
    user = make_user(db_session)
    with pytest.raises(ValueError):
        subscription_service.cancel_subscription(db_session, user)


def test_cancel_pro_subscription_disables_auto_renew(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    sub = subscription_service.cancel_subscription(db_session, user)
    assert sub.auto_renew is False
    assert sub.status.value == "cancelled"


def test_reactivate_after_cancel_works(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    subscription_service.cancel_subscription(db_session, user)
    sub = subscription_service.reactivate_subscription(db_session, user)
    assert sub.auto_renew is True
    assert sub.status.value == "active"


def test_reactivate_expired_raises(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=-1)  # уже истёк
    with pytest.raises(ValueError, match="expired"):
        subscription_service.reactivate_subscription(db_session, user)


# --- Router tests ---


def test_current_endpoint_returns_free(client, db_session):
    user = make_user(db_session)
    resp = client.get("/v1/subscriptions/current", cookies=access_cookies_for(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["subscription"]["plan"] == "free"


def test_cancel_endpoint_for_pro(client, db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    resp = client.post("/v1/subscriptions/cancel", cookies=access_cookies_for(user))
    assert resp.status_code == 200
    assert resp.json()["subscription"]["auto_renew"] is False
    assert "отменена" in resp.json()["message"].lower()


def test_endpoints_require_auth(client):
    assert client.get("/v1/subscriptions/current").status_code == 401
    assert client.post("/v1/subscriptions/cancel").status_code == 401
