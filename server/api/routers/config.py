"""/v1/config (desktop тянет конфиг) + /v1/admin/config (управление, HTTP Basic).

Remote Config — ядро управления продуктом без релиза desktop (S13).
Desktop опрашивает GET /v1/config при старте и периодически; админка крутит
режим/лимиты/фичи/kill-switch через GET/PUT /v1/admin/config.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import require_admin
from schemas.config import RemoteConfigAdmin, RemoteConfigPublic, RemoteConfigUpdate
from services import config_service

# Desktop-facing (публичный) и admin-facing роутеры — оба с полными путями.
public_router = APIRouter(tags=["config"])
admin_config_router = APIRouter(tags=["admin", "config"])


@public_router.get("/v1/config", response_model=RemoteConfigPublic)
def get_public_config(db: Annotated[Session, Depends(get_db)]) -> RemoteConfigPublic:
    """Desktop тянет конфиг (при старте + раз в ~6 ч). Публичный, без авторизации.

    Конфиг глобальный (не per-user) — содержимое не приватно, поэтому device JWT
    не требуется (работает даже если токен истёк → graceful на desktop)."""
    data = config_service.get_effective_config(db)
    return RemoteConfigPublic(**config_service.to_public_dict(data))


@admin_config_router.get("/v1/admin/config", response_model=RemoteConfigAdmin)
def get_admin_config(
    _admin: Annotated[str, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> RemoteConfigAdmin:
    """Полный конфиг для админки."""
    cfg = config_service.get_config(db)
    return RemoteConfigAdmin(**config_service.to_admin_dict(cfg))


@admin_config_router.put("/v1/admin/config", response_model=RemoteConfigAdmin)
def put_admin_config(
    changes: RemoteConfigUpdate,
    _admin: Annotated[str, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> RemoteConfigAdmin:
    """Частичное обновление конфига. Инкрементит config_version."""
    if not changes.has_any():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Не передано ни одного поля для обновления.",
        )
    cfg = config_service.update_config(db, changes.model_dump(exclude_unset=True))
    return RemoteConfigAdmin(**config_service.to_admin_dict(cfg))
