"""JWT для web-cabinet (access + refresh) и desktop (device JWT).

Используем HS256 — для нашего scale достаточно. RS256 имеет смысл если
будут отдельные сервисы которые верифицируют токены.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from api.settings import settings

TokenKind = Literal["access", "refresh", "device"]


class InvalidTokenError(Exception):
    """Токен поврёжден / подпись не совпадает / истёк."""


def create_access_token(*, user_id: str, extra_claims: dict | None = None) -> str:
    """Короткоживущий JWT для web-cabinet."""
    return _create_token(
        user_id=user_id,
        kind="access",
        ttl=timedelta(seconds=settings.jwt_access_ttl_seconds),
        extra_claims=extra_claims,
    )


def create_refresh_token(*, user_id: str) -> tuple[str, str, datetime]:
    """Refresh token + его хеш + expiry. В БД сохраняем хеш.

    `expires_at` — naive UTC, чтобы матчиться с SQLite (см. auth_service.utc_naive_now).
    """
    plain = secrets.token_urlsafe(48)
    token_hash = hash_token(plain)
    expires_at = datetime.utcnow() + timedelta(days=settings.jwt_refresh_ttl_days)
    return plain, token_hash, expires_at


def create_device_token(*, user_id: str, device_id: str) -> str:
    """Long-lived JWT для desktop активаций."""
    return _create_token(
        user_id=user_id,
        kind="device",
        ttl=timedelta(days=settings.jwt_device_ttl_days),
        extra_claims={"device_id": device_id},
    )


def decode_token(token: str, *, expected_kind: TokenKind | None = None) -> dict:
    """Расшифровать JWT, проверить подпись и истечение."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:  # noqa: BLE001
        raise InvalidTokenError(str(exc)) from exc

    if expected_kind and payload.get("kind") != expected_kind:
        raise InvalidTokenError(f"Expected token kind {expected_kind}, got {payload.get('kind')}")

    return payload


def hash_token(plain: str) -> str:
    """Деривация хеша для хранения refresh token в БД.

    Не bcrypt — нужно искать по точному совпадению, bcrypt slow для lookup.
    SHA-256 с длинным random токеном (48 байт) — достаточно.
    """
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _create_token(
    *,
    user_id: str,
    kind: TokenKind,
    ttl: timedelta,
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "sub": user_id,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
