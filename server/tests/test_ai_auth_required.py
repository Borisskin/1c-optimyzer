"""Регрессия безопасности: /v1/ai/* не должны быть доступны анонимно.

История: эндпоинты /v1/ai/* были открыты наружу — единственной проверкой был
глобальный AI kill-switch. Любой, кто знал адрес api.optimyzer.pro, мог слать
запросы, и каждый вызов оплачивался нашим ANTHROPIC_API_KEY (сам ключ при этом
сервер не покидал — утечки ключа не было, но деньги тратились наши).

Эти тесты работают на ЧИСТОМ приложении, без dependency_overrides из conftest
(там авторизация намеренно подменена, чтобы тесты AI-логики не занимались
логином). Поэтому здесь create_app() вызывается напрямую.

НЕ ОСЛАБЛЯТЬ эти тесты. Если они начали падать — значит, кто-то снял
авторизацию с AI-роутера и открыл кошелёк наружу.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app

# Тело запроса не важно: авторизация проверяется до валидации схемы.
AI_ENDPOINTS = [
    ("/v1/ai/explain", {"query_sdbl": "ВЫБРАТЬ 1", "diagnostics": []}),
    ("/v1/ai/explain_plan", {"sql_text": "select 1", "plan_xml": "<x/>", "plan_format": "xml"}),
    ("/v1/ai/explain_regression", {}),
    ("/v1/ai/generate_logcfg", {}),
]


@pytest.fixture()
def raw_client() -> TestClient:
    """Клиент без подмен авторизации — имитирует чужого человека с curl."""
    return TestClient(create_app())


@pytest.mark.parametrize("path,body", AI_ENDPOINTS)
def test_anonymous_call_is_rejected(raw_client: TestClient, path: str, body: dict) -> None:
    """Аноним не должен иметь возможности потратить наш AI-бюджет."""
    resp = raw_client.post(path, json=body)
    assert resp.status_code == 401, (
        f"{path} доступен без авторизации (код {resp.status_code}) — "
        "любой может тратить наш ANTHROPIC_API_KEY"
    )


@pytest.mark.parametrize("path,body", AI_ENDPOINTS)
def test_garbage_bearer_token_is_rejected(
    raw_client: TestClient, path: str, body: dict
) -> None:
    """Подделанный/протухший токен не должен пропускаться."""
    resp = raw_client.post(
        path, json=body, headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert resp.status_code == 401


def test_daily_budget_guard_blocks_when_limit_reached(monkeypatch) -> None:
    """Предохранитель: сверх дневного потолка вызовы отклоняются (503).

    Второй рубеж после авторизации — на случай скомпрометированного аккаунта
    или зациклившегося клиента.
    """
    from api.routers import ai as ai_router

    monkeypatch.setattr(ai_router, "AI_DAILY_CALL_LIMIT", 0)
    monkeypatch.setattr(ai_router, "_budget_day", None)
    monkeypatch.setattr(ai_router, "_budget_calls", 0)

    with pytest.raises(Exception) as exc:
        ai_router._daily_budget_guard()
    assert "503" in str(exc.value) or "ai_daily_limit_reached" in str(exc.value)
