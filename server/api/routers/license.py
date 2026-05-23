"""/v1/license/* — активация и (для существующих device JWT) переактивация."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from api.db import get_db
from api.deps import get_client_ip, get_current_device_user, get_current_user
from models.user import User
from schemas.devices import DeviceHeartbeatRequest, DeviceHeartbeatResponse
from schemas.license import (
    ActiveDeviceInfo,
    DeviceContext,
    LicenseActivateRequest,
    LicenseActivateResponse,
    SubscriptionContext,
    UserContext,
)
from services import (
    credits_service,
    device_service,
    email_lookup_service,
    license_keys_service,
    soft_caps,
)
from services.auth_service import mask_ip
from services.jwt_service import create_device_token

router = APIRouter(prefix="/v1/license", tags=["license"])


class LookupByEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    fingerprint: str = Field(..., min_length=10, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., pattern="^(windows|macos|linux)$")
    app_version: str = Field(..., min_length=1, max_length=32)


class IssueKeyForCabinetResponse(BaseModel):
    """POST /v1/license/issue-for-cabinet.

    Cabinet вызывает после OAuth login юзера чтобы получить activation key для
    desktop приложения. Юзер потом либо копирует ключ в desktop, либо открывает
    `optimyzer://activate?key=...` deep link.
    """

    key: str
    deep_link: str




@router.post(
    "/lookup-by-email",
    response_model=LicenseActivateResponse,
    responses={409: {"description": "Лимит устройств превышен"}},
    summary="Email-only вход для desktop (без OAuth)",
)
def lookup_by_email(
    payload: LookupByEmailRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LicenseActivateResponse:
    """Desktop: юзер ввёл email → находим/создаём user → device JWT + подписка.

    Без верификации email (по решению Сергея: простой UX > security здесь).
    Если email уже привязан к Pro через cabinet OAuth — отдаём Pro.
    Иначе создаём новый Free аккаунт.
    """
    user = email_lookup_service.get_or_create_user_by_email(db, payload.email)
    try:
        device = email_lookup_service.attach_device_to_user(
            db,
            user,
            fingerprint=payload.fingerprint,
            device_name=payload.device_name,
            platform=payload.platform,
            app_version=payload.app_version,
            ip_masked=mask_ip(get_client_ip(request)),
        )
    except email_lookup_service.DeviceLimitReached as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Этот email уже привязан к {exc.active_count}/{exc.limit} устройствам. "
            "Деактивируйте старое устройство в личном кабинете.",
        ) from exc

    token = create_device_token(user_id=user.id, device_id=device.id)
    sub = user.subscription
    return LicenseActivateResponse(
        access_token=token,
        user=UserContext(id=user.id, email=user.email, display_name=user.display_name),
        device=DeviceContext(id=device.id, name=device.name),
        subscription=SubscriptionContext(
            plan=sub.plan.value if sub else "free",
            ends_at=sub.ends_at if sub else device.last_seen_at,
            pro_active=sub.is_pro_active if sub else False,
        ),
    )


@router.post(
    "/activate",
    response_model=LicenseActivateResponse,
    responses={
        409: {"description": "Лимит устройств превышен"},
        404: {"description": "Ключ не найден или уже использован"},
        403: {"description": "Подписка Pro неактивна"},
    },
)
def activate(
    payload: LicenseActivateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LicenseActivateResponse:
    """Обмен activation key + fingerprint на device JWT."""
    key_record = license_keys_service.lookup_key(db, payload.key)
    if key_record is None or key_record.is_used:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License key not found or already used")

    user: User = key_record.user
    sub = user.subscription
    # Free юзеры тоже могут активировать desktop — им просто выдаётся device JWT
    # без Pro-привилегий (soft cap = 5 AI/мес на user_id вместо безлимита).
    # Раньше тут было `if sub.plan != PRO → 403`, но это блокирует mandatory
    # login для Free, что противоречит решению Сергея от 23.05.2026
    # (полная блокировка приложения без активации).
    if not sub:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "User has no subscription record — обратитесь в поддержку",
        )

    # Проверяем лимит ДО создания/обновления device — если уже превышен, шлём 409.
    existing_with_fp = next(
        (d for d in device_service.list_active(db, user) if d.fingerprint == payload.fingerprint),
        None,
    )
    if existing_with_fp is None:
        active = device_service.list_active(db, user)
        if len(active) >= device_service.get_device_limit(user):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "detail": (
                        f"Device limit reached: {len(active)}/{device_service.get_device_limit(user)}."
                        " Деактивируйте старое устройство в личном кабинете."
                    ),
                    "active_devices": [
                        ActiveDeviceInfo(
                            id=d.id,
                            name=d.name,
                            platform=d.platform.value,
                            last_seen_at=d.last_seen_at,
                        ).model_dump(mode="json")
                        for d in active
                    ],
                },
            )

    ip_masked = mask_ip(get_client_ip(request))
    device, _ = device_service.register_or_update_device(
        db,
        user,
        fingerprint=payload.fingerprint,
        name=payload.device_name,
        platform=payload.platform,
        app_version=payload.app_version,
        ip_masked=ip_masked,
    )
    license_keys_service.consume_key(db, payload.key, device_id=device.id)

    token = create_device_token(user_id=user.id, device_id=device.id)
    return LicenseActivateResponse(
        access_token=token,
        user=UserContext(id=user.id, email=user.email, display_name=user.display_name),
        device=DeviceContext(id=device.id, name=device.name),
        subscription=SubscriptionContext(
            plan=sub.plan.value,
            ends_at=sub.ends_at,
            pro_active=sub.is_pro_active,
        ),
    )


@router.post(
    "/issue-for-cabinet",
    response_model=IssueKeyForCabinetResponse,
    summary="Выдать activation key для desktop приложения (cabinet only)",
)
def issue_for_cabinet(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> IssueKeyForCabinetResponse:
    """Cabinet → POST → получает свежий activation key для текущего юзера.

    Юзер потом либо копирует key в desktop, либо открывает
    `optimyzer://activate?key=...` (deep link который Tauri ловит).
    Key — одноразовый, привязан к user_id. На стороне desktop'а нужно
    POST'нуть его на `/v1/license/activate` с fingerprint своего устройства.
    """
    record = license_keys_service.issue_key(db, user)
    deep_link = f"optimyzer://activate?key={record.key}"
    return IssueKeyForCabinetResponse(key=record.key, deep_link=deep_link)


@router.post("/heartbeat", response_model=DeviceHeartbeatResponse)
def heartbeat(
    payload: DeviceHeartbeatRequest,
    auth: Annotated[tuple[User, str], Depends(get_current_device_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeviceHeartbeatResponse:
    """Desktop стучится сюда каждые 24 часа.

    Возвращает текущий статус, чтобы desktop мог обновить кеш.
    """
    user, device_id = auth
    device = db.get(__import__("models.device", fromlist=["Device"]).Device, device_id)
    if device is None or not device.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device deactivated")

    device_service.heartbeat(db, device, app_version=payload.app_version)

    sub = user.subscription
    pro_active = bool(sub and sub.is_pro_active)
    ai_remaining = soft_caps.free_quota_remaining(db, user) if not pro_active else -1
    return DeviceHeartbeatResponse(
        subscription_plan=sub.plan.value if sub else "free",
        subscription_ends_at=sub.ends_at if sub else datetime.utcnow(),
        ai_quota_remaining=ai_remaining,
        credits_remaining=credits_service.total_remaining(db, user),
    )
