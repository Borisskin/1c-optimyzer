"""/v1/auth/* — Yandex OAuth login, logout, me, refresh."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_client_ip, get_current_user
from api.settings import settings
from schemas.auth import MeResponse, RefreshResponse, UserPublic, YandexLoginResponse
from services.auth_service import (
    get_or_create_user_from_yandex,
    issue_refresh_token,
    mask_ip,
    revoke_refresh_token,
    rotate_refresh_token,
)
from services.jwt_service import create_access_token
from services.yandex_oauth import (
    YandexOAuthError,
    build_authorize_url,
    exchange_code_for_token,
    fetch_profile,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# Отдельный router без префикса — для OAuth landing-page'ей которые Yandex
# редиректит на «голый» путь (`http://localhost/success`), а не на API endpoint.
oauth_landing_router = APIRouter(tags=["auth"])

# Путь должен СОВПАДАТЬ с redirect_uri в .env и в настройках Yandex OAuth app.
# У Сергея: http://localhost/success → этот хэндлер (через Apache/nginx proxy
# на 127.0.0.1:8001/success).
OAUTH_LANDING_PATH = "/success"


# --- Cookies helpers ---

REFRESH_COOKIE = "optimyzer_refresh"
STATE_COOKIE = "optimyzer_oauth_state"


def _set_refresh_cookie(response: Response, refresh: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        path="/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/v1/auth")


# --- Endpoints ---


@router.get(
    "/yandex/login",
    response_model=YandexLoginResponse,
    summary="Сформировать URL для Yandex OAuth и state",
)
def yandex_login(response: Response) -> YandexLoginResponse:
    """Frontend дёргает этот endpoint, получает authorize_url и state,
    сохраняет state в localStorage, делает window.location = authorize_url.

    Альтернатива: можно сразу `RedirectResponse(authorize_url)`. Делаем JSON —
    фронту проще управлять flow и хранить state.
    """
    state = secrets.token_urlsafe(24)
    authorize_url = build_authorize_url(state=state)
    # Дублируем state в cookie для server-side проверки если фронт забудет.
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        path="/",
    )
    return YandexLoginResponse(authorize_url=authorize_url, state=state)


@oauth_landing_router.get(
    OAUTH_LANDING_PATH,
    summary="Yandex OAuth callback landing — обмен code на token, set-cookie, redirect в cabinet",
)
async def yandex_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    cookie_state: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
) -> Response:
    """Принимает redirect от oauth.yandex.ru на `/success`, возвращает редирект на cabinet.

    Yandex отправляет юзера на YANDEX_REDIRECT_URI (`http://localhost/success` в
    дев-сетапе Сергея) с параметрами `?code=...&state=...`. Apache/nginx на :80
    проксирует на наш FastAPI :8001, мы тут обменяем code на token, выпустим
    JWT, поставим cookies, и редирект в cabinet.
    """
    if error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Yandex denied: {error}")
    if not code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing code")
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state")

    try:
        access_token_yandex = await exchange_code_for_token(code)
        profile = await fetch_profile(access_token_yandex)
    except YandexOAuthError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Yandex error: {exc}") from exc

    user = get_or_create_user_from_yandex(db, profile)
    refresh_plain = issue_refresh_token(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_masked=mask_ip(get_client_ip(request)),
    )
    access = create_access_token(user_id=user.id)

    cabinet_origin = settings.cors_origins_list[0] if settings.cors_origins_list else "/"
    redirect_to = f"{cabinet_origin}/?just_logged_in=1"
    # Важно: cookies ставим на тот же Response, который возвращаем.
    # FastAPI `response: Response` параметр работает только если ты возвращаешь
    # обычный pydantic-ответ, а не Response-объект.
    redirect = RedirectResponse(url=redirect_to, status_code=302)
    redirect.delete_cookie(STATE_COOKIE, path="/")
    _set_refresh_cookie(redirect, refresh_plain)
    redirect.set_cookie(
        "access_token",
        access,
        max_age=settings.jwt_access_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        path="/",
    )
    return redirect


@router.post(
    "/logout",
    status_code=204,
    summary="Logout — отозвать refresh, очистить cookies",
)
def logout(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    if refresh:
        revoke_refresh_token(db, refresh)
    _clear_refresh_cookie(response)
    response.delete_cookie("access_token", path="/")
    response.status_code = 204
    return response


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Текущий юзер по access cookie/Bearer",
)
def me(user=Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserPublic.model_validate(user))


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Обновить access по refresh cookie",
)
def refresh(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> RefreshResponse:
    if not refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh cookie")
    try:
        user, new_refresh = rotate_refresh_token(db, refresh)
    except ValueError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    new_access = create_access_token(user_id=user.id)
    _set_refresh_cookie(response, new_refresh)
    response.set_cookie(
        "access_token",
        new_access,
        max_age=settings.jwt_access_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        path="/",
    )
    return RefreshResponse(access_token=new_access)
