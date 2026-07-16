"""BYOK: ключ Anthropic принадлежит пользователю и не уходит с его машины.

Раньше AI шёл через наш сервер и оплачивался нашим ключом. Теперь пользователь
вводит свой ключ в настройках. Эти тесты фиксируют семантику, которую легко
сломать рефакторингом:

  * ключ пользователя ПОБЕЖДАЕТ ANTHROPIC_API_KEY из окружения;
  * явное удаление ключа выключает AI и НЕ откатывается на ENV
    (иначе «удалил ключ» тихо означало бы «использую чужой ключ»);
  * наружу ключ отдаётся только маской.
"""

from __future__ import annotations

import pytest

from optimyzer_backend.rpc import ai_settings_rpc, explainer_rpc

USER_KEY = "sk-ant-api03-USER-OWN-SECRET-1234WXYZ"
ENV_KEY = "sk-ant-ENV-KEY-MUST-NOT-BE-USED-9999"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Изолируем настройки: APPDATA во временную папку, клиенты сброшены."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ai_settings_rpc._store = None
    explainer_rpc.reset_client()
    yield
    ai_settings_rpc._store = None
    explainer_rpc.reset_client()


def test_key_absent_by_default() -> None:
    state = ai_settings_rpc.ai_settings_get()
    assert state["has_key"] is False
    assert state["key_masked"] == ""


def test_rejects_empty_and_garbage_keys() -> None:
    assert ai_settings_rpc.ai_settings_set_key("")["ok"] is False
    assert ai_settings_rpc.ai_settings_set_key("   ")["ok"] is False
    # Не похоже на ключ Anthropic — не молчим, а объясняем.
    bad = ai_settings_rpc.ai_settings_set_key("hello")
    assert bad["ok"] is False
    assert "sk-" in bad["error"]


def test_saved_key_is_never_returned_in_full() -> None:
    ai_settings_rpc.ai_settings_set_key(USER_KEY)
    state = ai_settings_rpc.ai_settings_get()
    assert state["has_key"] is True
    assert "USER-OWN-SECRET" not in str(state), "ключ не должен отдаваться целиком"
    assert state["key_masked"].startswith("sk-ant-")
    assert state["key_masked"].endswith("WXYZ")


def test_user_key_wins_over_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Главное свойство BYOK: используется ключ пользователя, а не чужой из ENV."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    ai_settings_rpc.ai_settings_set_key(USER_KEY)

    client = explainer_rpc.get_client()
    assert client.enabled is True
    assert client.api_key == USER_KEY
    assert client.api_key != ENV_KEY


def test_clearing_key_disables_ai_and_does_not_fall_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """«Удалил ключ» обязано значить «AI выключен», а не «взял ключ из ENV»."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    ai_settings_rpc.ai_settings_set_key(USER_KEY)
    assert explainer_rpc.get_client().enabled is True

    ai_settings_rpc.ai_settings_clear_key()

    client = explainer_rpc.get_client()
    assert client.enabled is False, "после удаления ключа AI должен быть выключен"
    assert client.api_key == ""


def test_key_change_applies_without_restart() -> None:
    """Сохранил ключ — AI работает сразу, без перезапуска приложения."""
    assert explainer_rpc.get_client().enabled is False or True  # прогреваем кеш клиента
    ai_settings_rpc.ai_settings_set_key(USER_KEY)
    assert explainer_rpc.get_client().api_key == USER_KEY


def test_mask_key_does_not_leak_middle() -> None:
    masked = ai_settings_rpc.mask_key(USER_KEY)
    assert "SECRET" not in masked
    assert masked == "sk-ant-…WXYZ"
    assert ai_settings_rpc.mask_key("") == ""
