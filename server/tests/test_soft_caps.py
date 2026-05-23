"""Tests для services.soft_caps — приоритеты Free/Pro/Credits."""

from __future__ import annotations

from datetime import datetime

from models.credits import CreditsPackage
from models.usage import Usage, UsageBilledAgainst, UsageOperationType
from services import credits_service, soft_caps
from tests.factories import make_user, upgrade_to_pro


def test_free_user_no_usage_can_run(db_session):
    user = make_user(db_session)
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.FREE_QUOTA


def test_free_user_at_limit_denied(db_session):
    user = make_user(db_session)
    # Симулируем 5 уже выполненных AI
    for _ in range(5):
        db_session.add(
            Usage(
                user_id=user.id,
                operation_type=UsageOperationType.AI_EXPLANATION,
                timestamp=datetime.utcnow(),
                cost_credits=1,
                billed_against=UsageBilledAgainst.FREE_QUOTA,
                success=True,
            )
        )
    db_session.commit()
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is False
    assert decision.reason == "free_limit_exceeded"
    assert "upgrade" in decision.options
    assert "buy_credits" in decision.options


def test_free_user_with_credits_uses_credits(db_session):
    user = make_user(db_session)
    credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.CREDITS_BALANCE


def test_pro_user_always_allowed(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.PRO_QUOTA


def test_pro_with_exhausted_free_still_allowed(db_session):
    user = make_user(db_session)
    upgrade_to_pro(db_session, user, days=30)
    # Не должно мешать что Free квота 0 — Pro же.
    for _ in range(10):
        db_session.add(
            Usage(
                user_id=user.id,
                operation_type=UsageOperationType.AI_EXPLANATION,
                timestamp=datetime.utcnow(),
                cost_credits=1,
                billed_against=UsageBilledAgainst.FREE_QUOTA,
                success=True,
            )
        )
    db_session.commit()
    decision = soft_caps.decide(db_session, user)
    assert decision.allowed is True
    assert decision.billed_against == UsageBilledAgainst.PRO_QUOTA


def test_credits_priority_for_free_user(db_session):
    """Free + Credits: используется Credits до исчерпания, потом Free."""
    user = make_user(db_session)
    credits_service.grant_package(db_session, user, CreditsPackage.MINI)
    d1 = soft_caps.decide(db_session, user)
    assert d1.billed_against == UsageBilledAgainst.CREDITS_BALANCE
