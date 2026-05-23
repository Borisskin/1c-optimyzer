"""/v1/devices/* — список и деактивация устройств web-кабинетом.

Активация и heartbeat — для desktop (отдельный router в Phase 1.5).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from models.user import User
from schemas.devices import DeviceRead, DevicesListResponse
from services import device_service

router = APIRouter(prefix="/v1/devices", tags=["devices"])


@router.get("", response_model=DevicesListResponse)
def list_devices(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DevicesListResponse:
    devices = device_service.list_active(db, user)
    return DevicesListResponse(
        devices=[DeviceRead.model_validate(d) for d in devices],
        limit=device_service.get_device_limit(user),
    )


@router.post("/{device_id}/deactivate", response_model=DeviceRead)
def deactivate(
    device_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeviceRead:
    try:
        dev = device_service.deactivate(db, user, device_id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return DeviceRead.model_validate(dev)
