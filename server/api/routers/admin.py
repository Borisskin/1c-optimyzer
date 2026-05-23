"""/v1/admin/* — только для Сергея. HTTP Basic auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import require_admin
from schemas.telemetry import TelemetrySummary
from services import telemetry_service

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/telemetry/summary", response_model=TelemetrySummary)
def telemetry_summary(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[str, Depends(require_admin)],
    period_days: int = Query(default=30, ge=1, le=365),
) -> TelemetrySummary:
    return telemetry_service.summarize(db, period_days=period_days)
