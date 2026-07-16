"""BYOK: ключ Anthropic принадлежит пользователю и живёт только на его машине.

Раньше AI шёл через наш сервер (ADR-057): ключ лежал у нас, и каждый вызов
оплачивали мы. Это делало обязательным сервер, биллинг, квоты и охрану ключа.
Теперь наоборот — пользователь вводит свой ключ в настройках, вызовы идут
напрямую с его машины в Anthropic. Наш сервер в AI-пути не участвует вообще.

Ключ хранится в metadata.sqlite (APPDATA/1c-optimyzer) как обычная настройка.
Это plaintext на машине пользователя — стандартная практика для десктопного
BYOK; ключ не покидает его компьютер и никуда нами не отправляется.

Наружу ключ никогда не отдаётся целиком — только маска (sk-ant-...XYZW), чтобы
пользователь мог убедиться, что сохранил именно то, что хотел.
"""

from __future__ import annotations

import logging
from typing import Any

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.storage.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)

SETTING_KEY = "anthropic_api_key"
SETTING_MODEL = "anthropic_model"

_store: SqliteStore | None = None


def get_store() -> SqliteStore:
    global _store
    if _store is None:
        _store = SqliteStore()
    return _store


def get_stored_api_key() -> str | None:
    """Ключ пользователя из локальных настроек.

    Три состояния, и их важно различать:
      * None — настройка никогда не задавалась → разрешаем откат на ENV
        (нужно для разработки и тестов; у пользователя ENV пустой).
      * ""   — пользователь ЯВНО удалил ключ → AI выключен. Никакого отката
        на ENV: «удалил ключ» обязано означать «AI выключен», иначе клиент
        подхватил бы чужой ключ из окружения.
      * "sk-…" — ключ пользователя, используем его.
    """
    try:
        value = get_store().get_setting(SETTING_KEY)
    except Exception:  # noqa: BLE001 — настройки не должны ронять AI
        logger.exception("не удалось прочитать ключ из настроек")
        return None
    if value is None:
        return None
    return value.strip()


def get_stored_model() -> str | None:
    try:
        return (get_store().get_setting(SETTING_MODEL) or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


def mask_key(key: str) -> str:
    """sk-ant-api03-AbCdEf...WXYZ → sk-ant-…WXYZ. Целиком ключ не показываем."""
    if not key:
        return ""
    if len(key) <= 12:
        return "…" + key[-4:]
    return f"{key[:7]}…{key[-4:]}"


@rpc("ai_settings_get")
def ai_settings_get() -> dict[str, Any]:
    """Состояние BYOK-настройки для экрана настроек."""
    key = get_stored_api_key() or ""
    return {
        "ok": True,
        "has_key": bool(key),
        "key_masked": mask_key(key),
        "model": get_stored_model(),
    }


@rpc("ai_settings_set_key")
def ai_settings_set_key(api_key: str) -> dict[str, Any]:
    """Сохраняет ключ пользователя и пересоздаёт AI-клиент.

    Валидация намеренно мягкая (непустой + похож на ключ Anthropic): строгую
    проверку делает сам Anthropic при первом вызове, а мы не хотим блокировать
    пользователя из-за смены формата ключей на их стороне.
    """
    key = (api_key or "").strip()
    if not key:
        return {"ok": False, "error": "Ключ не может быть пустым"}
    if not key.startswith("sk-"):
        return {
            "ok": False,
            "error": "Похоже, это не ключ Anthropic — он должен начинаться с «sk-»",
        }

    get_store().set_setting(SETTING_KEY, key)
    _reset_ai_clients()
    logger.info("ключ Anthropic сохранён (%s)", mask_key(key))
    return {"ok": True, "has_key": True, "key_masked": mask_key(key)}


@rpc("ai_settings_clear_key")
def ai_settings_clear_key() -> dict[str, Any]:
    """Удаляет ключ — AI выключается, приложение продолжает работать."""
    get_store().set_setting(SETTING_KEY, "")
    _reset_ai_clients()
    logger.info("ключ Anthropic удалён из настроек")
    return {"ok": True, "has_key": False, "key_masked": ""}


def _reset_ai_clients() -> None:
    """Сбрасывает кешированные AI-клиенты, чтобы новый ключ применился сразу.

    Без этого пользователь сохранил бы ключ и всё равно видел «AI не настроен»
    до перезапуска приложения.
    """
    from optimyzer_backend.rpc import explainer_rpc

    explainer_rpc.reset_client()
