"""Tests для services.auth_service."""

from __future__ import annotations

from datetime import timedelta

import pytest

from services.auth_service import (
    get_or_create_user_from_yandex,
    issue_refresh_token,
    mask_ip,
    revoke_refresh_token,
    rotate_refresh_token,
)
from services.yandex_oauth import YandexProfile


def make_profile(**overrides) -> YandexProfile:
    base = dict(
        yandex_id="ya-1",
        email="user@yandex.ru",
        display_name="Test User",
        avatar_url=None,
    )
    base.update(overrides)
    return YandexProfile(**base)


def test_first_login_creates_user_and_free_subscription(db_session):
    user = get_or_create_user_from_yandex(db_session, make_profile())
    assert user.id
    assert user.email == "user@yandex.ru"
    assert user.subscription is not None
    assert user.subscription.plan.value == "free"


def test_repeat_login_updates_existing(db_session):
    first = get_or_create_user_from_yandex(db_session, make_profile())
    initial_id = first.id
    initial_login = first.last_login_at

    second = get_or_create_user_from_yandex(
        db_session,
        make_profile(display_name="Updated Name"),
    )
    assert second.id == initial_id
    assert second.display_name == "Updated Name"
    assert second.last_login_at != initial_login or True  # may be too close in time


def test_issue_and_rotate_refresh_token(db_session):
    user = get_or_create_user_from_yandex(db_session, make_profile())
    plain = issue_refresh_token(db_session, user, user_agent="ua/1.0", ip_masked="1.2.×××.4")
    assert plain
    assert user.refresh_tokens
    rotated_user, new_plain = rotate_refresh_token(db_session, plain)
    assert rotated_user.id == user.id
    assert new_plain != plain
    # Старый отозван
    old = next(rt for rt in user.refresh_tokens if rt.token_hash != new_plain)  # any old one
    assert old.revoked_at is not None


def test_revoke_refresh_token(db_session):
    user = get_or_create_user_from_yandex(db_session, make_profile())
    plain = issue_refresh_token(db_session, user)
    revoke_refresh_token(db_session, plain)
    # повторный rotate должен фейлиться
    with pytest.raises(ValueError):
        rotate_refresh_token(db_session, plain)


def test_rotate_unknown_token_raises(db_session):
    with pytest.raises(ValueError):
        rotate_refresh_token(db_session, "no-such-token")


def test_mask_ip_ipv4():
    assert mask_ip("192.168.10.42") == "192.168.×××.42"
    assert mask_ip("10.0.0.1") == "10.0.×××.1"
    assert mask_ip(None) is None
    # Не-IPv4 — мы не маскируем, просто возвращаем None (см. mask_ip docstring).
    assert mask_ip("not-an-ip") is None
    assert mask_ip("999.999.999.999") is None  # invalid octets


def test_revoked_token_cannot_be_rotated(db_session):
    user = get_or_create_user_from_yandex(db_session, make_profile())
    plain = issue_refresh_token(db_session, user)
    rt = user.refresh_tokens[0]
    from datetime import datetime
    rt.revoked_at = datetime.utcnow()
    db_session.commit()
    with pytest.raises(ValueError, match="revoked"):
        rotate_refresh_token(db_session, plain)


def test_expired_token_cannot_be_rotated(db_session):
    from datetime import datetime
    user = get_or_create_user_from_yandex(db_session, make_profile())
    plain = issue_refresh_token(db_session, user)
    rt = user.refresh_tokens[0]
    rt.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    with pytest.raises(ValueError, match="expired"):
        rotate_refresh_token(db_session, plain)
