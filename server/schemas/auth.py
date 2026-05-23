"""Pydantic-схемы для /v1/auth/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    """Безопасное представление User'а — без yandex_id, без is_active."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str | None
    avatar_url: str | None
    last_login_at: datetime | None


class AuthCallbackResponse(BaseModel):
    """Что возвращает callback после успешного OAuth."""

    user: UserPublic
    access_token: str
    # refresh_token приходит cookie'й, не в body


class MeResponse(BaseModel):
    """GET /v1/auth/me."""

    user: UserPublic


class RefreshResponse(BaseModel):
    """POST /v1/auth/refresh."""

    access_token: str


class YandexLoginResponse(BaseModel):
    """GET /v1/auth/yandex/login (если не редиректим, а возвращаем URL)."""

    authorize_url: str
    state: str = Field(description="Сохрани в localStorage, проверь при callback")
