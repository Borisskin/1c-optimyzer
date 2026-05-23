"""Pydantic схемы для /v1/license/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.device import DevicePlatform


class LicenseActivateRequest(BaseModel):
    """POST /v1/license/activate."""

    key: str = Field(min_length=10, description="OPTM-XXXX-XXXX-XXXX-XXXX")
    fingerprint: str = Field(min_length=8, max_length=128)
    device_name: str = Field(min_length=1, max_length=255)
    platform: DevicePlatform
    app_version: str = Field(min_length=1, max_length=32)


class DeviceContext(BaseModel):
    id: str
    name: str


class UserContext(BaseModel):
    id: str
    email: str
    display_name: str | None


class SubscriptionContext(BaseModel):
    plan: str
    ends_at: datetime
    pro_active: bool


class LicenseActivateResponse(BaseModel):
    """Активация прошла — выдаём device JWT."""

    access_token: str
    user: UserContext
    device: DeviceContext
    subscription: SubscriptionContext


class LicenseActivateConflictResponse(BaseModel):
    """409 — лимит устройств превышен. Юзер должен выбрать что деактивировать."""

    detail: str
    active_devices: list["ActiveDeviceInfo"]


class ActiveDeviceInfo(BaseModel):
    id: str
    name: str
    platform: str
    last_seen_at: datetime


LicenseActivateConflictResponse.model_rebuild()
