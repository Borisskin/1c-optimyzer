"""/v1/telemetry/* — приём batch'ей от desktop."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from api.db import get_db
from api.settings import settings
from models.user import User
from schemas.telemetry import TelemetryBatchRequest, TelemetryBatchResponse
from services import telemetry_service
from services.jwt_service import InvalidTokenError, decode_token

router = APIRouter(prefix="/v1/telemetry", tags=["telemetry"])


def _try_resolve_user(
    db: Session,
    authorization: str | None,
    access_cookie: str | None,
) -> User | None:
    """Optional auth — telemetry от Free юзеров идёт без user_id (anonymous)."""
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif access_cookie:
        token = access_cookie
    if not token:
        return None
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.get(User, user_id)


@router.post("/batch", response_model=TelemetryBatchResponse)
def batch(
    body: TelemetryBatchRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> TelemetryBatchResponse:
    _ = request  # Reserved for future IP-based rate limiting / geo.
    user = _try_resolve_user(db, authorization, access_token)
    accepted = telemetry_service.record_batch(db, body.events, user=user)
    return TelemetryBatchResponse(accepted=accepted)


# Hint for IDE / OpenAPI: rate-limited через slowapi default (см. main.py)
_ = settings  # noqa: unused — placeholder для будущего конфигурируемого limit
