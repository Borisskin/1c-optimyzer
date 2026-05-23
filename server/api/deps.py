"""Общие FastAPI dependencies."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from api.db import get_db
from api.settings import settings
from models.user import User
from services.jwt_service import InvalidTokenError, decode_token

# --- HTTP Basic для admin endpoints ---

basic_auth = HTTPBasic()


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(basic_auth)],
) -> str:
    """Защита /v1/admin/*."""
    correct_user = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_pass = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# --- JWT для web-cabinet ---


def _extract_access_token(
    request: Request,
    authorization: str | None,
    access_token_cookie: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if access_token_cookie:
        return access_token_cookie
    return None


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    """Достать юзера по Bearer access token (или access_token cookie)."""
    token = _extract_access_token(request, authorization, access_token)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing access token")
    try:
        payload = decode_token(token, expected_kind="access")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_current_device_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> tuple[User, str]:
    """Для desktop endpoints — достать (user, device_id) из device JWT."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing device token")
    token = authorization[7:].strip()
    try:
        payload = decode_token(token, expected_kind="device")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user_id = payload.get("sub")
    device_id = payload.get("device_id")
    if not user_id or not device_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject or device_id")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user, device_id


# --- Утилиты ---


def get_client_ip(request: Request) -> str | None:
    """Извлечь IP с учётом прокси (X-Forwarded-For), в dev возвращает client.host."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None
