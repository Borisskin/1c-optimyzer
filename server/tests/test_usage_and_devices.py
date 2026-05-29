"""Tests для usage_service, device_service и роутеров."""

from __future__ import annotations

import pytest

from models.device import DevicePlatform
from models.usage import UsageBilledAgainst, UsageOperationType
from services import config_service, device_service, usage_service
from tests.factories import (
    access_cookies_for,
    device_token_for,
    make_user,
    upgrade_to_pro,
)


# --- device_service ---


def test_register_first_device(db_session):
    user = make_user(db_session)
    dev, created = device_service.register_or_update_device(
        db_session,
        user,
        fingerprint="fp-1",
        name="MacBook",
        platform=DevicePlatform.MACOS,
        app_version="0.5.0",
    )
    assert created is True
    assert dev.is_active is True


def test_register_same_fingerprint_updates_not_duplicate(db_session):
    user = make_user(db_session)
    device_service.register_or_update_device(
        db_session, user, fingerprint="fp-1", name="MacBook",
        platform=DevicePlatform.MACOS, app_version="0.5.0",
    )
    dev2, created = device_service.register_or_update_device(
        db_session, user, fingerprint="fp-1", name="MacBook Pro",
        platform=DevicePlatform.MACOS, app_version="0.5.1",
    )
    assert created is False
    assert dev2.name == "MacBook Pro"
    assert dev2.app_version == "0.5.1"
    assert len(device_service.list_active(db_session, user)) == 1


def test_free_user_device_limit_one(db_session):
    user = make_user(db_session)  # Free
    device_service.register_or_update_device(
        db_session, user, fingerprint="fp-1", name="A",
        platform=DevicePlatform.WINDOWS, app_version="0.5.0",
    )
    with pytest.raises(ValueError, match="Device limit"):
        device_service.register_or_update_device(
            db_session, user, fingerprint="fp-2", name="B",
            platform=DevicePlatform.WINDOWS, app_version="0.5.0",
        )


def test_pro_user_can_register_five(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    for i in range(5):
        device_service.register_or_update_device(
            db_session, user, fingerprint=f"fp-{i}", name=f"Dev {i}",
            platform=DevicePlatform.WINDOWS, app_version="0.5.0",
        )
    with pytest.raises(ValueError, match="Device limit"):
        device_service.register_or_update_device(
            db_session, user, fingerprint="fp-6", name="6th",
            platform=DevicePlatform.WINDOWS, app_version="0.5.0",
        )


def test_deactivate_device(db_session):
    user = make_user(db_session)
    dev, _ = device_service.register_or_update_device(
        db_session, user, fingerprint="fp-1", name="X",
        platform=DevicePlatform.LINUX, app_version="0.5.0",
    )
    device_service.deactivate(db_session, user, dev.id)
    assert len(device_service.list_active(db_session, user)) == 0


# --- usage_service ---


def test_track_free_user_first_time(db_session):
    user = make_user(db_session)
    dev, _ = device_service.register_or_update_device(
        db_session, user, fingerprint="fp", name="D",
        platform=DevicePlatform.LINUX, app_version="0.5.0",
    )
    record = usage_service.track(
        db_session, user,
        device=dev,
        operation_type=UsageOperationType.AI_EXPLANATION,
        archive_hash="abc",
    )
    assert record.billed_against == UsageBilledAgainst.FREE_QUOTA
    assert record.cost_credits == 1


def test_track_denied_when_quota_exhausted(db_session):
    # S13: деналы по лимиту работают в paid-режиме (discovery — безлимит).
    config_service.update_config(db_session, {"monetization_mode": "paid"})
    user = make_user(db_session)
    for _ in range(5):
        usage_service.track(
            db_session, user, device=None,
            operation_type=UsageOperationType.AI_EXPLANATION,
            archive_hash=None,
        )
    with pytest.raises(usage_service.UsageDeniedError):
        usage_service.track(
            db_session, user, device=None,
            operation_type=UsageOperationType.AI_EXPLANATION,
            archive_hash=None,
        )


def test_summary_returns_zero_for_new_user(db_session):
    user = make_user(db_session)
    summary = usage_service.summary_for_user(db_session, user)
    assert summary["ai_operations_count"] == 0
    assert summary["free_quota_used"] == 0
    assert summary["free_quota_limit"] == 5


# --- Router tests ---


def test_devices_list_endpoint(client, db_session):
    user = make_user(db_session)
    device_service.register_or_update_device(
        db_session, user, fingerprint="fp", name="My Mac",
        platform=DevicePlatform.MACOS, app_version="0.5.0",
    )
    resp = client.get("/v1/devices", cookies=access_cookies_for(user))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["devices"]) == 1
    assert body["limit"] == 1


def test_usage_track_via_device_jwt(client, db_session):
    user = make_user(db_session)
    dev, _ = device_service.register_or_update_device(
        db_session, user, fingerprint="fp", name="X",
        platform=DevicePlatform.WINDOWS, app_version="0.5.0",
    )
    token = device_token_for(user, dev.id)
    resp = client.post(
        "/v1/usage/track",
        json={"operation_type": "ai_explanation"},
        headers={"authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["billed_against"] == "free_quota"


def test_usage_check_for_free_user(client, db_session):
    user = make_user(db_session)
    dev, _ = device_service.register_or_update_device(
        db_session, user, fingerprint="fp", name="X",
        platform=DevicePlatform.WINDOWS, app_version="0.5.0",
    )
    token = device_token_for(user, dev.id)
    resp = client.get(
        "/v1/usage/check",
        headers={"authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is True
    assert body["free_quota_remaining"] == 5


def test_dashboard_summary(client, db_session):
    user = make_user(db_session)
    resp = client.get("/v1/dashboard/summary", cookies=access_cookies_for(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "user@yandex.ru"
    assert body["subscription"]["plan"] == "free"
    assert body["credits_remaining"] == 0
    assert body["devices_active"] == 0
