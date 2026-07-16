"""Sprint 3 Phase E/F — explainer RPC methods.

Public RPC:
    explainer_classify(archive_id, anatomy_kind, target_id, features)
        → instant rule-based RuleMatch | None

    explainer_ai(archive_id, anatomy_kind, target_id, anatomy_data,
                 rule_id?, rule_body?, force_refresh=False)
        → AI explanation, кеш-aware. Может занимать 3-15 сек.

    explainer_status()
        → {"enabled": bool, "model": str, "cache_entries": int, "rules_count": int}

    explainer_reload_rules()
        → {"ok": True, "rules_count": int}

Frontend паттерн (Phase F UX):
    1. Сразу вызывает explainer_classify (instant) → показывает rule-based.
    2. Параллельно вызывает explainer_ai → через 3-15 сек дополняет / замещает.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimyzer_backend.explainer import ExplainerEngine
from optimyzer_backend.explainer.cache import ExplainerCache, make_cache_key
from optimyzer_backend.explainer.claude_client import ClaudeExplainerClient
from optimyzer_backend.rpc.dispatcher import rpc


# ---------- Singletons (lazy-init) ----------

_engine: ExplainerEngine | None = None
_client: ClaudeExplainerClient | None = None
_cache: ExplainerCache | None = None


def _rules_dir() -> Path:
    # backend/explainers — рядом с pyproject.toml
    return Path(__file__).resolve().parents[3] / "explainers"


def _cache_path() -> Path:
    # data/explainer_cache.db — отдельная БД, не смешиваем с app metadata
    return Path(__file__).resolve().parents[3] / "data" / "explainer_cache.db"


def get_engine() -> ExplainerEngine:
    global _engine
    if _engine is None:
        _engine = ExplainerEngine(_rules_dir())
    return _engine


def get_client() -> ClaudeExplainerClient:
    """AI-клиент на ключе ПОЛЬЗОВАТЕЛЯ (BYOK).

    Приоритет: ключ из настроек приложения → затем ENV (dev). Наш сервер и наш
    ключ в этой цепочке не участвуют — см. ai_settings_rpc.
    """
    global _client
    if _client is None:
        # Локальный импорт: ai_settings_rpc импортирует этот модуль для сброса
        # клиента, а импорт на уровне модуля дал бы цикл.
        from optimyzer_backend.rpc.ai_settings_rpc import (
            get_stored_api_key,
            get_stored_model,
        )

        user_key = get_stored_api_key()
        # None → настройка не задавалась, отдаём None и клиент возьмёт ENV (dev).
        # "" → пользователь явно удалил ключ: передаём пустую строку как явный
        #      override, чтобы AI выключился, а не подхватил ключ из окружения.
        _client = ClaudeExplainerClient(api_key=user_key, model=get_stored_model())
    return _client


def reset_client() -> None:
    """Сбрасывает кеш клиента — вызывается после смены ключа в настройках."""
    global _client
    _client = None


def get_cache() -> ExplainerCache:
    global _cache
    if _cache is None:
        _cache = ExplainerCache(_cache_path())
    return _cache


# ---------- RPC handlers ----------


@rpc("explainer_classify")
def explainer_classify(
    archive_id: str,  # noqa: ARG001 — пока не используется но останется в API
    anatomy_kind: str,
    target_id: str,  # noqa: ARG001 — пока не используется
    features: dict[str, Any],
) -> dict[str, Any]:
    engine = get_engine()
    match = engine.classify(features, applies_to=anatomy_kind)
    if match is None:
        return {"ok": True, "matched": False}
    return {
        "ok": True,
        "matched": True,
        "rule_id": match.rule_id,
        "title": match.title,
        "body": match.body,
        "priority": match.priority,
    }


@rpc("explainer_ai")
def explainer_ai(
    archive_id: str,
    anatomy_kind: str,
    target_id: str,
    anatomy_data: dict[str, Any],
    rule_id: str | None = None,
    rule_body: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache = get_cache()
    cache_key = make_cache_key(archive_id, anatomy_kind, target_id)

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return {
                "ok": True,
                "text": cached.ai_text,
                "from_cache": True,
                "model": cached.model,
                "tokens_in": cached.tokens_in,
                "tokens_out": cached.tokens_out,
                "created_at": cached.created_at,
            }

    client = get_client()
    result = client.generate(
        anatomy_kind=anatomy_kind,
        anatomy_data=anatomy_data,
        rule_context=rule_body,
    )

    if not result.ok:
        return {
            "ok": False,
            "error": result.error,
            "enabled": client.enabled,
        }

    cache.put(
        cache_key=cache_key,
        archive_id=archive_id,
        anatomy_kind=anatomy_kind,
        target_id=str(target_id),
        rule_id=rule_id,
        ai_text=result.text,
        model=result.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
    )

    return {
        "ok": True,
        "text": result.text,
        "from_cache": False,
        "model": result.model,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "elapsed_ms": result.elapsed_ms,
    }


@rpc("explainer_check_cache")
def explainer_check_cache(
    archive_id: str,
    anatomy_kind: str,
    target_id: str,
) -> dict[str, Any]:
    """Read-only проверка кеша AI-объяснения. НЕ вызывает Claude API.

    Frontend дёргает этот метод на mount ExplainerCard, чтобы сразу
    показать уже сгенерированное объяснение (без кнопки и без повторной
    траты токенов). Если в кеше пусто — возвращает found=False, тогда
    UI показывает кнопку «Сгенерировать».
    """
    cached = get_cache().get(make_cache_key(archive_id, anatomy_kind, target_id))
    if cached is None:
        return {"ok": True, "found": False}
    return {
        "ok": True,
        "found": True,
        "text": cached.ai_text,
        "model": cached.model,
        "tokens_in": cached.tokens_in,
        "tokens_out": cached.tokens_out,
        "created_at": cached.created_at,
    }


@rpc("explainer_status")
def explainer_status() -> dict[str, Any]:
    client = get_client()
    engine = get_engine()
    cache = get_cache()
    return {
        "ok": True,
        "ai_enabled": client.enabled,
        "model": client.model if client.enabled else None,
        "rules_count": len(engine.rules),
        "cache_entries": cache.stats()["entries"],
    }


@rpc("explainer_reload_rules")
def explainer_reload_rules() -> dict[str, Any]:
    engine = get_engine()
    engine.reload_rules()
    return {"ok": True, "rules_count": len(engine.rules)}


# ---------- Dev-tools (admin) RPCs — не для обычного UI ----------


@rpc("explainer_cache_list")
def explainer_cache_list(limit: int = 500) -> dict[str, Any]:
    """Список всех cached AI explanations — для dev-tools screen."""
    return {"ok": True, "entries": get_cache().list_all(limit=limit)}


@rpc("explainer_cache_clear_all")
def explainer_cache_clear_all() -> dict[str, Any]:
    """Полная очистка кеша. Destructive — вызывает повторные API calls
    при следующем открытии anatomy views."""
    removed = get_cache().clear_all()
    return {"ok": True, "removed": removed}


@rpc("explainer_cache_clear_archive")
def explainer_cache_clear_archive(archive_id: str) -> dict[str, Any]:
    """Очистить кеш для конкретного архива."""
    removed = get_cache().evict_archive(archive_id)
    return {"ok": True, "removed": removed}


@rpc("explainer_cache_delete_entry")
def explainer_cache_delete_entry(cache_key: str) -> dict[str, Any]:
    """Удалить одну entry по cache_key (для точечной перегенерации)."""
    deleted = get_cache().delete(cache_key)
    return {"ok": True, "deleted": deleted}
