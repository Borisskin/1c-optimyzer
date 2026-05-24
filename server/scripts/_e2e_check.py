"""End-to-end smoke check для cabinet + desktop activation flow.

Что делает:
  1. Создаёт (или находит) тестового user'а claude-e2e-test@gmail.com в SQLite DB сервера.
  2. Выпускает access_token cookie (как после Yandex OAuth callback).
  3. Запрашивает /v1/auth/me, /v1/dashboard/summary, /v1/license/my-key.
  4. Запрашивает /v1/license/regenerate-key → проверяет, что старый отозван.
  5. POST /v1/license/activate (desktop flow) с свежим ключом + fingerprint.
  6. POST /v1/license/heartbeat с device JWT.

Запускается как `python scripts/_e2e_check.py` из server/ с .venv активированной.
Выходит с кодом 0 если всё OK, 1 если что-то сломалось.
"""

from __future__ import annotations

import sys
import time
import urllib.request
import urllib.error
import json
from http.cookiejar import CookieJar

# Локальный server.
BASE = "http://127.0.0.1:8001"


def step(msg: str) -> None:
    print(f"\n[E2E] {msg}")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL {msg}")
    sys.exit(1)


def http(method: str, path: str, body: dict | None = None,
         cookies: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = BASE + path
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    if cookies:
        headers["cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8") or "{}"
            return r.status, json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8")
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, {"raw": text}


def main() -> None:
    # 1) DB-setup: создаём user через factory и выпускаем cookie.
    step("Создаём claude-e2e-test@gmail.com и выпускаем cookie")
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.db import SessionLocal
    from services import auth_service
    from services.yandex_oauth import YandexProfile
    from services.jwt_service import create_access_token

    db = SessionLocal()
    try:
        prof = YandexProfile(
            yandex_id="e2e-yandex-id",
            email="claude-e2e-test@gmail.com",
            display_name="E2E Tester",
            avatar_url=None,
        )
        user = auth_service.get_or_create_user_from_yandex(db, prof)
        db.commit()
        access_token = create_access_token(user_id=user.id)
        ok(f"user_id={user.id} email={user.email}")
    finally:
        db.close()

    cookies = {"access_token": access_token}

    # 2) /v1/auth/me
    step("GET /v1/auth/me (cookie)")
    code, body = http("GET", "/v1/auth/me", cookies=cookies)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    if body.get("user", {}).get("email") != "claude-e2e-test@gmail.com":
        fail(f"unexpected user: {body}")
    ok(f"email={body['user']['email']}")

    # 3) /v1/dashboard/summary
    step("GET /v1/dashboard/summary")
    code, body = http("GET", "/v1/dashboard/summary", cookies=cookies)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    if "credits_remaining" not in body or "subscription" not in body:
        fail(f"missing fields in summary: {body}")
    ok(f"plan={body['subscription']['plan']} credits={body['credits_remaining']} ai_ops={body['ai_operations_this_month']}")

    # 4) /v1/license/my-key (создаст ключ, если не было)
    step("GET /v1/license/my-key (1-й раз)")
    code, body = http("GET", "/v1/license/my-key", cookies=cookies)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    first_key = body.get("key")
    if not first_key or not first_key.startswith("OPTM-"):
        fail(f"bad key format: {body}")
    ok(f"key={first_key}")

    # 4b) Повторный вызов — тот же ключ (idempotent)
    step("GET /v1/license/my-key (2-й раз — должен быть тот же)")
    code, body = http("GET", "/v1/license/my-key", cookies=cookies)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    if body.get("key") != first_key:
        fail(f"key changed unexpectedly: was {first_key}, now {body.get('key')}")
    ok(f"key unchanged: {body['key']}")

    # 5) Regenerate
    step("POST /v1/license/regenerate-key")
    code, body = http("POST", "/v1/license/regenerate-key", cookies=cookies)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    second_key = body.get("key")
    if not second_key or second_key == first_key:
        fail(f"expected new key different from {first_key}, got {second_key}")
    ok(f"new key={second_key}")

    # 5b) Старый ключ больше не активируется
    step("POST /v1/license/activate СТАРЫМ ключом (должен быть 404)")
    code, body = http("POST", "/v1/license/activate", body={
        "key": first_key,
        "fingerprint": "a" * 64,
        "device_name": "E2E Old",
        "platform": "windows",
        "app_version": "0.5.0",
    })
    if code != 404:
        fail(f"expected 404 for revoked key, got {code}: {body}")
    ok("revoked key correctly rejected (404)")

    # 6) Активация новым ключом — desktop flow
    step("POST /v1/license/activate новым ключом")
    code, body = http("POST", "/v1/license/activate", body={
        "key": second_key,
        "fingerprint": "b" * 64,
        "device_name": "E2E Desktop",
        "platform": "windows",
        "app_version": "0.5.0",
    })
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    device_token = body.get("access_token")
    if not device_token:
        fail(f"no access_token in response: {body}")
    ok(f"device_token issued ({len(device_token)} chars) device_id={body['device'].get('id')}")

    # 7) Heartbeat
    step("POST /v1/license/heartbeat (device token)")
    code, body = http("POST", "/v1/license/heartbeat", body={"app_version": "0.5.0"}, token=device_token)
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    if "subscription_plan" not in body:
        fail(f"missing fields: {body}")
    ok(f"plan={body['subscription_plan']} ai_remaining={body['ai_quota_remaining']}")

    # 8) Yandex login URL (cabinet generates this for login button)
    step("GET /v1/auth/yandex/login")
    code, body = http("GET", "/v1/auth/yandex/login")
    if code != 200:
        fail(f"expected 200, got {code}: {body}")
    if "authorize_url" not in body or "client_id=" not in body["authorize_url"]:
        fail(f"bad authorize_url: {body}")
    ok(f"authorize_url contains client_id ({body['authorize_url'][:80]}...)")

    print("\n[E2E] ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
