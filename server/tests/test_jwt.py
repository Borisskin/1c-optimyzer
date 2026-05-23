"""Unit tests для services.jwt_service."""

from __future__ import annotations

import time

import pytest

from services.jwt_service import (
    InvalidTokenError,
    create_access_token,
    create_device_token,
    create_refresh_token,
    decode_token,
    hash_token,
)


def test_access_token_roundtrip():
    token = create_access_token(user_id="user-123")
    payload = decode_token(token, expected_kind="access")
    assert payload["sub"] == "user-123"
    assert payload["kind"] == "access"
    assert payload["exp"] > payload["iat"]


def test_access_token_rejected_as_device():
    token = create_access_token(user_id="user-123")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_kind="device")


def test_device_token_carries_device_id():
    token = create_device_token(user_id="user-1", device_id="dev-42")
    payload = decode_token(token, expected_kind="device")
    assert payload["sub"] == "user-1"
    assert payload["device_id"] == "dev-42"
    assert payload["kind"] == "device"


def test_tampered_signature_rejected():
    token = create_access_token(user_id="u")
    # Меняем bytes в середине signature — гарантированно invalid.
    parts = token.split(".")
    sig = parts[2]
    # Заменим первый char signature на любой другой (HS256 — 256 bit signature,
    # base64url decode'нется в 32 байта; первый char точно participatuet).
    tampered_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    tampered = ".".join([parts[0], parts[1], tampered_sig])
    with pytest.raises(InvalidTokenError):
        decode_token(tampered)


def test_refresh_token_returns_plain_hash_and_expiry():
    plain, hashed, expires_at = create_refresh_token(user_id="u")
    assert len(plain) > 40
    assert hashed == hash_token(plain)
    assert expires_at.timestamp() > time.time()


def test_hash_token_is_deterministic():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
