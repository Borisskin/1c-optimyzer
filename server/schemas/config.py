"""Pydantic схемы для /v1/config (desktop) и /v1/admin/config (управление)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MonetizationModeLit = Literal["discovery", "paid", "mixed"]


class RemoteConfigPublic(BaseModel):
    """GET /v1/config — то, что получает desktop (без серверных деталей)."""

    monetization_mode: MonetizationModeLit
    ai_kill_switch: bool
    limits: dict
    feature_flags: dict
    config_version: int


class RemoteConfigAdmin(RemoteConfigPublic):
    """GET /v1/admin/config — полный конфиг для админки."""

    ai_model_per_type: dict
    prompt_versions: dict
    updated_at: datetime | None = None


class RemoteConfigUpdate(BaseModel):
    """PUT /v1/admin/config — частичное обновление (все поля опциональны)."""

    monetization_mode: MonetizationModeLit | None = None
    ai_kill_switch: bool | None = None
    limits: dict | None = None
    feature_flags: dict | None = None
    ai_model_per_type: dict | None = None
    prompt_versions: dict | None = None

    model_config = {"extra": "forbid"}

    # Хотя бы одно поле должно быть передано — иначе PUT бессмыслен.
    def has_any(self) -> bool:
        return any(
            v is not None
            for v in (
                self.monetization_mode,
                self.ai_kill_switch,
                self.limits,
                self.feature_flags,
                self.ai_model_per_type,
                self.prompt_versions,
            )
        )
