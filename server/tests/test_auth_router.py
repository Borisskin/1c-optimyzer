"""Integration tests для /v1/auth/* — c FastAPI TestClient и mocked Yandex."""

from __future__ import annotations

import httpx
import respx


@respx.mock
def test_yandex_login_returns_url_and_sets_state_cookie(client):
    resp = client.get("/v1/auth/yandex/login")
    assert resp.status_code == 200
    body = resp.json()
    assert body["authorize_url"].startswith("https://oauth.yandex.ru/authorize?")
    assert body["state"]
    assert "optimyzer_oauth_state" in resp.cookies


@respx.mock
def test_yandex_callback_full_flow(client):
    # Сначала получить state
    login_resp = client.get("/v1/auth/yandex/login")
    state = login_resp.json()["state"]

    respx.post("https://oauth.yandex.ru/token").mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.abc"}),
    )
    respx.get("https://login.yandex.ru/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "yandex-007",
                "default_email": "bond@yandex.ru",
                "real_name": "James Bond",
                "is_avatar_empty": True,
            },
        ),
    )

    resp = client.get(
        "/v1/auth/yandex/callback",
        params={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    # cookies должны быть установлены
    assert "optimyzer_refresh" in resp.cookies
    assert "access_token" in resp.cookies


@respx.mock
def test_yandex_callback_rejects_state_mismatch(client):
    client.get("/v1/auth/yandex/login")  # sets state cookie
    resp = client.get(
        "/v1/auth/yandex/callback",
        params={"code": "x", "state": "bogus"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


@respx.mock
def test_me_requires_authentication(client):
    resp = client.get("/v1/auth/me")
    assert resp.status_code == 401


@respx.mock
def test_logout_clears_cookies(client):
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 204


@respx.mock
def test_full_login_me_logout_flow(client):
    # 1. login
    login = client.get("/v1/auth/yandex/login").json()
    state = login["state"]

    respx.post("https://oauth.yandex.ru/token").mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.x"}),
    )
    respx.get("https://login.yandex.ru/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "y-1",
                "default_email": "me@yandex.ru",
                "real_name": "Me",
                "is_avatar_empty": True,
            },
        ),
    )
    cb = client.get(
        "/v1/auth/yandex/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )
    assert cb.status_code == 302

    # 2. me
    me = client.get("/v1/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["user"]["email"] == "me@yandex.ru"

    # 3. logout
    logout = client.post("/v1/auth/logout")
    assert logout.status_code == 204
