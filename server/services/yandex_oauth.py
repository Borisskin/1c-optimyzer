"""Yandex OAuth client.

Через httpx async. В тестах мокаем через respx.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from api.settings import settings


class YandexOAuthError(Exception):
    """Ошибка от Yandex или сетевая."""


@dataclass(slots=True)
class YandexProfile:
    """Минимальный набор полей из login.yandex.ru/info."""

    yandex_id: str
    email: str
    display_name: str | None
    avatar_url: str | None


def build_authorize_url(state: str) -> str:
    """Собрать URL для редиректа юзера на Yandex OAuth.

    Args:
        state: CSRF-anti-replay-токен — сохраняем в session/cookie,
            проверяем при callback.
    """
    params = {
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.yandex_redirect_uri,
        "state": state,
        # Yandex использует не scopes а явные разрешения в console.
        # Можно указать `scope` для дополнительных полей, но minimum работает.
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.yandex_oauth_authorize_url}?{query}"


async def exchange_code_for_token(code: str) -> str:
    """Обменять authorization code на access_token."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.yandex_client_id,
        "client_secret": settings.yandex_client_secret,
        "redirect_uri": settings.yandex_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(settings.yandex_oauth_token_url, data=data)
    if resp.status_code != 200:
        raise YandexOAuthError(f"Yandex token endpoint returned {resp.status_code}: {resp.text}")
    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise YandexOAuthError(f"No access_token in Yandex response: {payload}")
    return access_token


async def fetch_profile(access_token: str) -> YandexProfile:
    """Получить профиль пользователя через login.yandex.ru/info."""
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"format": "json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.yandex_user_info_url,
            headers=headers,
            params=params,
        )
    if resp.status_code != 200:
        raise YandexOAuthError(f"Yandex info endpoint returned {resp.status_code}: {resp.text}")
    data = resp.json()
    yandex_id = data.get("id")
    if not yandex_id:
        raise YandexOAuthError(f"No id in Yandex profile: {data}")
    email = (data.get("default_email") or "").lower().strip()
    if not email:
        raise YandexOAuthError("No default_email in Yandex profile — нужно дать разрешение")
    display_name = (
        data.get("real_name")
        or data.get("display_name")
        or data.get("login")
    )
    avatar_url: str | None = None
    avatar_id = data.get("default_avatar_id")
    if avatar_id and not data.get("is_avatar_empty"):
        avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200"
    return YandexProfile(
        yandex_id=str(yandex_id),
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
