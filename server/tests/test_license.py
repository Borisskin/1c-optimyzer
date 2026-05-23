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


def test_activate_free_user_works(client, db_session):
    """Free юзер тоже может активировать desktop (per mandatory login решение).
    Раньше тут было 403 — теперь 200, но лимит устройств = 1 для Free."""
    user = make_user(db_session)  # Free
    key = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(key.key))
    assert resp.status_code == 200
    body = resp.json()
    assert body["subscription"]["plan"] == "free"
    assert body["subscription"]["pro_active"] is False


def test_activate_free_device_limit_409(client, db_session):
    """Free юзер: лимит 1 устройство — второй ключ → 409."""
    user = make_user(db_session)
    k1 = license_keys_service.issue_key(db_session, user)
    resp = client.post("/v1/license/activate", json=_activate_payload(k1.key))
    assert resp.status_code == 200
    k2 = license_keys_service.issue_key(db_session, user)
    resp = client.post(
        "/v1/license/activate",
        json=_activate_payload(k2.key, fp=f"second-device-{'y' * 48}"),
    )
    assert resp.status_code == 409


def test_issue_for_cabinet_requires_auth(client):
    resp = client.post("/v1/license/issue-for-cabinet")
    assert resp.status_code == 401


def test_issue_for_cabinet_returns_key(client, db_session):
    from tests.factories import access_cookies_for
    user = make_user(db_session)
    resp = client.post(
        "/v1/license/issue-for-cabinet",
        cookies=access_cookies_for(user),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"].startswith("OPTM-")
    assert body["deep_link"] == f"optimyzer://activate?key={body['key']}"


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
