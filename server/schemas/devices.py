"""Pydantic схемы для /v1/devices/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    platform: str
    app_version: str
    activated_at: datetime
    last_seen_at: datetime
    last_ip_masked: str | None
    is_active: bool


class DevicesListResponse(BaseModel):
    devices: list[DeviceRead]
    limit: int


class DeviceActivateRequest(BaseModel):
    """POST /v1/devices/activate."""

    key: str
    fingerprint: str
    device_name: str
    platform: str
    app_version: str


class DeviceActivateResponse(BaseModel):
    """Возвращает device-specific tokens + контекст подписки."""

    access_token: str
    refresh_token: str
    user_email: str
    device_id: str
    device_name: str
    subscription_plan: str
    subscription_ends_at: datetime


class DeviceHeartbeatRequest(BaseModel):
    """POST /v1/devices/heartbeat — JWT + текущее состояние."""

    app_version: str | None = None


class DeviceHeartbeatResponse(BaseModel):
    subscription_plan: str
    subscription_ends_at: datetime
    ai_quota_remaining: int
    credits_remaining: int
