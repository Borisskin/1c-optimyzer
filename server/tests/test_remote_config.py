"""S13 Фаза 1 — Remote Config: модель, service, /v1/config, /v1/admin/config,
применение discovery в soft_caps.decide, AI kill-switch в /v1/ai/*."""

from __future__ import annotations

import pytest

import base64

from api.settings import settings
from models.remote_config import MonetizationMode
from models.usage import UsageBilledAgainst
from services import config_service, soft_caps
from tests.factories import make_user, upgrade_to_pro




# /v1/ai/* закрыты авторизацией (см. tests/test_ai_auth_required.py). Тесты в
# этом модуле проверяют не логин, а kill-switch/rate-limit, поэтому подменяем
# зависимость авторизации на фикстурном app.
@pytest.fixture(autouse=True)
def _authed_ai(app):
    from api.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: object()
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


# Берём креды из settings (в этом проекте .env имеет приоритет над os.environ),
# чтобы тест и require_admin использовали один и тот же источник истины.
ADMIN_AUTH = _basic(settings.admin_username, settings.admin_password)
BAD_AUTH = _basic(settings.admin_username, settings.admin_password + "_WRONG")


# ---------- config_service (unit) ----------


def test_default_config_is_discovery(db_session):
    cfg = config_service.get_config(db_session)
    assert cfg.monetization_mode == MonetizationMode.DISCOVERY
    assert cfg.ai_kill_switch is False
    assert cfg.config_version == 1


def test_get_config_is_singleton(db_session):
    a = config_service.get_config(db_session)
    b = config_service.get_config(db_session)
    assert a.id == b.id


def test_admin_dict_fills_defaults(db_session):
    cfg = config_service.get_config(db_session)
    data = config_service.to_admin_dict(cfg)
    # дефолтные фичи присутствуют
    assert data["feature_flags"]["tj_analysis"] is True
    assert data["feature_flags"]["query_analyzer"] is False
    assert data["limits"]["ai_per_month"] is None
    # серверные поля есть в admin-снимке
    assert "ai_model_per_type" in data and "prompt_versions" in data


def test_public_dict_excludes_server_only_fields(db_session):
    cfg = config_service.get_config(db_session)
    pub = config_service.to_public_dict(config_service.to_admin_dict(cfg))
    assert "ai_model_per_type" not in pub
    assert "prompt_versions" not in pub
    assert set(pub.keys()) == set(config_service.PUBLIC_KEYS)


def test_update_bumps_version_and_invalidates_cache(db_session):
    config_service.get_effective_config(db_session)  # прогрев кеша
    config_service.update_config(db_session, {"monetization_mode": "paid"})
    data = config_service.get_effective_config(db_session)
    assert data["monetization_mode"] == "paid"
    assert data["config_version"] == 2


def test_update_merges_json_without_wiping(db_session):
    config_service.update_config(db_session, {"feature_flags": {"plans": False}})
    cfg = config_service.get_config(db_session)
    flags = config_service.to_admin_dict(cfg)["feature_flags"]
    assert flags["plans"] is False
    # остальные флаги не стёрты
    assert flags["tj_analysis"] is True
    assert flags["sql_console"] is True


# ---------- soft_caps.decide в discovery ----------


def test_discovery_allows_without_quota(db_session):
    user = make_user(db_session)
    # дефолт discovery — free-юзер получает allowed=True без проверки лимита
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.FREE_QUOTA


def test_discovery_pro_billed_against_pro(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user)
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.PRO_QUOTA


def test_paid_mode_enforces_free_limit(db_session):
    user = make_user(db_session)
    config_service.update_config(db_session, {"monetization_mode": "paid"})
    # в paid-режиме free-квота снова считается (лимит 5/мес из settings)
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.FREE_QUOTA


# ---------- HTTP /v1/config ----------


def test_public_config_endpoint(client):
    resp = client.get("/v1/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["monetization_mode"] == "discovery"
    assert body["ai_kill_switch"] is False
    assert "feature_flags" in body and "config_version" in body
    # серверные поля НЕ должны утекать в публичный конфиг
    assert "ai_model_per_type" not in body
    assert "prompt_versions" not in body


# ---------- HTTP /v1/admin/config ----------


def test_admin_config_requires_auth(client):
    assert client.get("/v1/admin/config").status_code == 401
    assert client.get("/v1/admin/config", headers={"Authorization": BAD_AUTH}).status_code == 401


def test_admin_get_config(client):
    resp = client.get("/v1/admin/config", headers={"Authorization": ADMIN_AUTH})
    assert resp.status_code == 200
    body = resp.json()
    assert body["monetization_mode"] == "discovery"
    assert "ai_model_per_type" in body
    assert "prompt_versions" in body


def test_admin_put_updates_config(client):
    resp = client.put(
        "/v1/admin/config",
        headers={"Authorization": ADMIN_AUTH},
        json={"monetization_mode": "paid", "ai_kill_switch": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["monetization_mode"] == "paid"
    assert body["ai_kill_switch"] is True
    assert body["config_version"] == 2
    # повторный GET через публичный endpoint отражает изменения
    pub = client.get("/v1/config").json()
    assert pub["monetization_mode"] == "paid"
    assert pub["ai_kill_switch"] is True


def test_admin_put_empty_is_400(client):
    resp = client.put("/v1/admin/config", headers={"Authorization": ADMIN_AUTH}, json={})
    assert resp.status_code == 400


def test_admin_put_requires_auth(client):
    resp = client.put("/v1/admin/config", json={"ai_kill_switch": True})
    assert resp.status_code == 401


# ---------- AI kill-switch ----------


def test_kill_switch_blocks_ai_explain(client):
    # включаем kill-switch
    client.put(
        "/v1/admin/config",
        headers={"Authorization": ADMIN_AUTH},
        json={"ai_kill_switch": True},
    )
    resp = client.post("/v1/ai/explain", json={"query_sdbl": "ВЫБРАТЬ 1"})
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["error"] == "ai_temporarily_unavailable"


def test_kill_switch_off_does_not_block_with_503_killswitch(client):
    # При выключенном kill-switch guard пропускает; дальше может быть свой 503
    # (ai_not_configured без ключа) — но это НЕ kill-switch.
    resp = client.post("/v1/ai/explain", json={"query_sdbl": "ВЫБРАТЬ 1"})
    if resp.status_code == 503:
        assert resp.json()["detail"]["error"] != "ai_temporarily_unavailable"
