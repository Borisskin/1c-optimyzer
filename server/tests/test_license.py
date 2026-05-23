"""Tests для /v1/license/* endpoints."""

from __future__ import annotations

import pytest

from models.device import DevicePlatform
from services import license_keys_service
from tests.factories import (
    device_token_for,
    make_user,
    upgrade_to_pro,
)


def _activate_payload(key: str, fp: str = "abcdef0123456789" * 4) -> dict:
    """Fingerprint в проде — SHA-256 (64 chars). Тест юзает длинный realistic FP."""
    return {
        "key": key,
        "fingerprint": fp,
        "device_name": "Test Mac",
        "platform": "macos",
        "app_version": "0.5.0",
    }


def test_activate_happy_path(client, db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    key = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(key.key))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == user.email
    assert body["subscription"]["pro_active"] is True


def test_activate_unknown_key_404(client):
    resp = client.post("/v1/license/activate", json=_activate_payload("OPTM-XXXX-XXXX-XXXX-XXXX"))
    assert resp.status_code == 404


def test_activate_used_key_404(client, db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    key = license_keys_service.issue_key(db_session, user)
    # Используем ключ один раз
    client.post("/v1/license/activate", json=_activate_payload(key.key, fp=f"fingerprint-one-{'x' * 48}"))
    # Второй раз — 404
    resp = client.post("/v1/license/activate", json=_activate_payload(key.key, fp=f"fingerprint-two-{'x' * 48}"))
    assert resp.status_code == 404


def test_activate_inactive_subscription_403(client, db_session):
    user = make_user(db_session)  # Free
    key = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(key.key))
    assert resp.status_code == 403


def test_activate_device_limit_409_for_free(client, db_session):
    """Хотя у Free нет Pro key, всё равно протестируем 409 path с Pro юзером и лимитом 5."""
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    # Активируем 5 устройств (выпустим 5 ключей)
    keys = [license_keys_service.issue_key(db_session, user) for _ in range(5)]
    for i, k in enumerate(keys):
        resp = client.post("/v1/license/activate", json=_activate_payload(k.key, fp=f"fingerprint-{i:08d}-{'x' * 48}"))
        assert resp.status_code == 200
    # 6-й — лимит
    sixth = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(sixth.key, fp=f"fingerprint-six-{'x' * 48}"))
    assert resp.status_code == 409


def test_activate_reactivate_existing_fingerprint(client, db_session):
    """Если уже активирован с этим fingerprint — это переактивация, не лимит."""
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    k1 = license_keys_service.issue_key(db_session, user)
    client.post("/v1/license/activate", json=_activate_payload(k1.key, fp=f"fingerprint-same-{'x' * 48}"))
    k2 = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(k2.key, fp=f"fingerprint-same-{'x' * 48}"))
    assert resp.status_code == 200


def test_heartbeat_requires_device_jwt(client):
    resp = client.post("/v1/license/heartbeat", json={})
    assert resp.status_code == 401


def test_heartbeat_returns_state(client, db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    key = license_keys_service.issue_key(db_session, user)
    activate_resp = client.post("/v1/license/activate", json=_activate_payload(key.key))
    token = activate_resp.json()["access_token"]

    resp = client.post(
        "/v1/license/heartbeat",
        json={"app_version": "0.5.1"},
        headers={"authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subscription_plan"] == "pro"
    assert body["ai_quota_remaining"] == -1  # Pro = unlimited
