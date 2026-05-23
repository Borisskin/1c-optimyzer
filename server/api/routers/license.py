"""/v1/license/* — активация и (для существующих device JWT) переактивация."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from api.db import get_db
from api.deps import get_client_ip, get_current_device_user, get_current_user
from models.desktop_session import DesktopSessionStatus
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
    desktop_session_service,
    device_service,
    license_keys_service,
    soft_caps,
)
from services.auth_service import mask_ip
from services.jwt_service import create_device_token

router = APIRouter(prefix="/v1/license", tags=["license"])


class IssueKeyForCabinetResponse(BaseModel):
    """POST /v1/license/issue-for-cabinet.

    Cabinet вызывает после OAuth login юзера чтобы получить activation key для
    desktop приложения. Юзер потом либо копирует ключ в desktop, либо открывает
    `optimyzer://activate?key=...` deep link.
    """

    key: str
    deep_link: str


# ---------- Device flow (init/confirm/poll) ----------


class DesktopInitRequest(BaseModel):
    fingerprint: str = Field(..., min_length=10, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., pattern="^(windows|macos|linux)$")
    app_version: str = Field(..., min_length=1, max_length=32)


class DesktopInitResponse(BaseModel):
    session_id: str
    expires_at: datetime
    cabinet_url: str  # куда desktop открывает browser


class DesktopConfirmRequest(BaseModel):
    session_id: str


class DesktopConfirmResponse(BaseModel):
    status: str  # confirmed | already
    device_name: str


class DesktopPollResponse(BaseModel):
    status: str  # pending | confirmed | expired | claimed | cancelled
    access_token: str | None = None
    user: UserContext | None = None
    device: DeviceContext | None = None
    subscription: SubscriptionContext | None = None


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


@router.post(
    "/desktop-init",
    response_model=DesktopInitResponse,
    summary="Desktop: создать pending сессию активации (device flow step 1)",
)
def desktop_init(
    payload: DesktopInitRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DesktopInitResponse:
    """Desktop вызывает при «Войти через Yandex» — БЕЗ auth.

    Создаём session_id. Desktop потом открывает browser на
    `<cabinet>/desktop-activate?session=<id>` и polling'ом ждёт confirm.
    """
    session = desktop_session_service.init_session(
        db,
        fingerprint=payload.fingerprint,
        device_name=payload.device_name,
        platform=payload.platform,
        app_version=payload.app_version,
    )
    cabinet_base = (
        settings.cors_origins_list[0] if settings.cors_origins_list else "http://localhost:5173"
    )
    return DesktopInitResponse(
        session_id=session.id,
        expires_at=session.expires_at,
        cabinet_url=f"{cabinet_base}/desktop-activate?session={session.id}",
    )


@router.post(
    "/desktop-confirm",
    response_model=DesktopConfirmResponse,
    summary="Cabinet: подтвердить сессию после OAuth login (device flow step 2)",
)
def desktop_confirm(
    payload: DesktopConfirmRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DesktopConfirmResponse:
    """Cabinet вызывает после login юзера — связываем session с user_id."""
    try:
        session = desktop_session_service.confirm_session(
            db,
            payload.session_id,
            user,
            ip=get_client_ip(request),
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except desktop_session_service.DeviceLimitReached as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Device limit reached: {exc.active_count}/{exc.limit}. "
            "Деактивируйте старое устройство.",
        ) from exc

    return DesktopConfirmResponse(
        status="confirmed" if session.status == DesktopSessionStatus.CONFIRMED else "already",
        device_name=session.device_name,
    )


@router.get(
    "/desktop-poll",
    response_model=DesktopPollResponse,
    summary="Desktop: poll статуса сессии (device flow step 3)",
)
def desktop_poll(
    session_id: Annotated[str, Field(min_length=10)],
    db: Annotated[Session, Depends(get_db)],
) -> DesktopPollResponse:
    """Desktop polling'ом каждые ~2 сек. Когда status=confirmed — отдаём токен,
    помечаем claimed. БЕЗ auth (session_id — секрет per-device, проверяется).
    """
    session = desktop_session_service.poll_session(db, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")

    if session.status != DesktopSessionStatus.CONFIRMED:
        return DesktopPollResponse(status=session.status.value)

    # confirmed — отдаём token и помечаем claimed.
    desktop_session_service.claim_session(db, session_id)
    user = session.user  # type: ignore[attr-defined]
    sub = user.subscription if user else None
    return DesktopPollResponse(
        status="confirmed",
        access_token=session.issued_access_token,
        user=UserContext(id=user.id, email=user.email, display_name=user.display_name),
        device=DeviceContext(id=session.device_id, name=session.device_name),
        subscription=SubscriptionContext(
            plan=sub.plan.value if sub else "free",
            ends_at=sub.ends_at if sub else session.expires_at,
            pro_active=sub.is_pro_active if sub else False,
        ),
    )


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
