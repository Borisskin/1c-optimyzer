"""Yandex OAuth client tests — мокаем httpx через respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from services.yandex_oauth import (
    YandexOAuthError,
    build_authorize_url,
    exchange_code_for_token,
    fetch_profile,
)


def test_build_authorize_url_contains_required_params():
    url = build_authorize_url(state="xyz")
    assert url.startswith("https://oauth.yandex.ru/authorize?")
    assert "client_id=test-client-id" in url
    assert "state=xyz" in url
    assert "response_type=code" in url
    assert "redirect_uri=http%3A%2F%2Ftestserver%2Foauth%2Fcallback" in url or "redirect_uri=http://testserver/oauth/callback" in url


@pytest.mark.asyncio
@respx.mock
async def test_exchange_code_for_token_happy_path():
    respx.post("https://oauth.yandex.ru/token").mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.abc", "token_type": "bearer"}),
    )
    token = await exchange_code_for_token("the-code")
    assert token == "ya29.abc"


@pytest.mark.asyncio
@respx.mock
async def test_exchange_code_for_token_error_response():
    respx.post("https://oauth.yandex.ru/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"}),
    )
    with pytest.raises(YandexOAuthError):
        await exchange_code_for_token("bad-code")


@pytest.mark.asyncio
@respx.mock
async def test_exchange_code_for_token_missing_access_token():
    respx.post("https://oauth.yandex.ru/token").mock(
        return_value=httpx.Response(200, json={"token_type": "bearer"}),
    )
    with pytest.raises(YandexOAuthError):
        await exchange_code_for_token("the-code")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_profile_happy_path():
    respx.get("https://login.yandex.ru/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "1234567",
                "default_email": "User@Yandex.Ru",
                "real_name": "Сергей Иванов",
                "display_name": "sergey",
                "default_avatar_id": "avatar-id-xyz",
                "is_avatar_empty": False,
            },
        ),
    )
    profile = await fetch_profile("ya29.token")
    assert profile.yandex_id == "1234567"
    # Email нормализован в lowercase.
    assert profile.email == "user@yandex.ru"
    assert profile.display_name == "Сергей Иванов"
    assert profile.avatar_url and "avatar-id-xyz" in profile.avatar_url


@pytest.mark.asyncio
@respx.mock
async def test_fetch_profile_without_avatar_returns_none():
    respx.get("https://login.yandex.ru/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "1234567",
                "default_email": "u@y.ru",
                "login": "u",
                "is_avatar_empty": True,
            },
        ),
    )
    profile = await fetch_profile("ya29.token")
    assert profile.avatar_url is None
    assert profile.display_name == "u"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_profile_without_email_raises():
    respx.get("https://login.yandex.ru/info").mock(
        return_value=httpx.Response(200, json={"id": "1", "default_email": ""}),
    )
    with pytest.raises(YandexOAuthError):
        await fetch_profile("ya29.token")
