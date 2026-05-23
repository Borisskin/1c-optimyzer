"""Pydantic схемы для /v1/credits/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.credits import CreditsPackage


class CreditsPackageInfo(BaseModel):
    """Метаданные пакета — для покупки."""

    package: CreditsPackage
    operations: int
    price_rub: float
    ttl_days: int


class CreditsBalanceResponse(BaseModel):
    """GET /v1/credits/balance."""

    operations_remaining: int = Field(description="Суммарный остаток по активным пакетам")
    operations_total_purchased: int = Field(description="Всего куплено за всё время")
    operations_used_total: int = Field(description="Всего потрачено за всё время")
    active_packages: list["CreditsPackageRead"]


class CreditsPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    package: str
    operations_total: int
    operations_used: int
    operations_remaining: int
    purchased_at: datetime
    expires_at: datetime
    is_active: bool


class CreditsHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    package: str
    operations_total: int
    operations_used: int
    purchased_at: datetime
    expires_at: datetime
    is_active: bool


class CreditsHistoryResponse(BaseModel):
    items: list[CreditsHistoryItem]


class CreditsPurchaseRequest(BaseModel):
    """POST /v1/credits/purchase."""

    package: CreditsPackage


class CreditsPurchaseResponse(BaseModel):
    """Возвращает confirmation_url для YooKassa checkout."""

    payment_id: str
    confirmation_url: str
    amount_kopecks: int
    package: CreditsPackage


CreditsBalanceResponse.model_rebuild()
