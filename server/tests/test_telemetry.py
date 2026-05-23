"""Tests для telemetry_service и роутеров."""

from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timedelta

from sqlalchemy import select

from models.telemetry import TelemetryEvent
from schemas.telemetry import TelemetryEventIn
from services import telemetry_service
from tests.factories import access_cookies_for, make_user


def _ev(**overrides) -> TelemetryEventIn:
    base = dict(
        device_fingerprint="a" * 16,
        app_version="0.6.0",
        platform="windows",
        category="behavior",
        event_type="screen_view",
        payload={"screen": "operations"},
        timestamp=datetime.utcnow(),
    )
    base.update(overrides)
    return TelemetryEventIn(**base)


# --- service ---


def test_record_batch_anonymous(db_session):
    n = telemetry_service.record_batch(db_session, [_ev(), _ev(event_type="ai_click")])
    assert n == 2
    rows = db_session.scalars(select(TelemetryEvent)).all()
    assert all(r.user_id is None for r in rows)


def test_record_batch_with_user_attributes_user_id(db_session):
    user = make_user(db_session)
    telemetry_service.record_batch(db_session, [_ev()], user=user)
    row = db_session.scalar(select(TelemetryEvent))
    assert row.user_id == user.id


def test_cleanup_old_events(db_session):
    # Один старый, один свежий.
    telemetry_service.record_batch(db_session, [_ev(timestamp=datetime.utcnow() - timedelta(days=100))])
    telemetry_service.record_batch(db_session, [_ev(timestamp=datetime.utcnow())])
    removed = telemetry_service.cleanup_old_events(db_session, max_age_days=90)
    assert removed == 1
    rows = db_session.scalars(select(TelemetryEvent)).all()
    assert len(rows) == 1


def test_summarize_groups_by_dimensions(db_session):
    telemetry_service.record_batch(
        db_session,
        [
            _ev(event_type="screen_view"),
            _ev(event_type="screen_view"),
            _ev(event_type="ai_click", category="conversion"),
        ],
    )
    summary = telemetry_service.summarize(db_session, period_days=7)
    assert summary.total_events == 3
    assert summary.unique_devices == 1
    by_type = {r.key: r.count for r in summary.by_event_type}
    assert by_type["screen_view"] == 2
    assert by_type["ai_click"] == 1


# --- /v1/telemetry/batch ---


def test_telemetry_batch_anonymous(client):
    resp = client.post(
        "/v1/telemetry/batch",
        json={
            "events": [
                {
                    "device_fingerprint": "fp-" + "x" * 20,
                    "app_version": "0.6.0",
                    "platform": "windows",
                    "category": "tech",
                    "event_type": "archive_loaded",
                    "payload": {"size_mb": 1024},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["accepted"] == 1


def test_telemetry_batch_with_auth_links_user(client, db_session):
    user = make_user(db_session)
    resp = client.post(
        "/v1/telemetry/batch",
        json={
            "events": [
                {
                    "device_fingerprint": "fp-" + "x" * 20,
                    "app_version": "0.6.0",
                    "platform": "macos",
                    "category": "behavior",
                    "event_type": "screen_view",
                    "payload": {"screen": "anatomy"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        },
        cookies=access_cookies_for(user),
    )
    assert resp.status_code == 200
    row = db_session.scalar(select(TelemetryEvent))
    assert row.user_id == user.id


# --- /v1/admin/telemetry/summary ---


def _admin_auth_header(username: str = "admin", password: str = "test-admin-password") -> dict[str, str]:
    creds = b64encode(f"{username}:{password}".encode()).decode()
    return {"authorization": f"Basic {creds}"}


def test_admin_summary_requires_basic_auth(client):
    resp = client.get("/v1/admin/telemetry/summary")
    assert resp.status_code == 401


def test_admin_summary_with_creds(client):
    # Сначала наполним telemetry
    client.post(
        "/v1/telemetry/batch",
        json={
            "events": [
                {
                    "device_fingerprint": "fp-" + "x" * 20,
                    "app_version": "0.6.0",
                    "platform": "windows",
                    "category": "behavior",
                    "event_type": "screen_view",
                    "payload": {},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        },
    )
    resp = client.get(
        "/v1/admin/telemetry/summary?period_days=30",
        headers=_admin_auth_header(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_events"] >= 1
    assert body["period_days"] == 30


def test_admin_summary_bad_password_401(client):
    resp = client.get(
        "/v1/admin/telemetry/summary",
        headers=_admin_auth_header(password="wrong"),
    )
    assert resp.status_code == 401
