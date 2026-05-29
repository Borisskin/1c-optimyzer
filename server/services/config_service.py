"""Remote Config — чтение/запись серверного конфига управления desktop (S13).

- `get_config(db)` — ORM-объект singleton (создаёт с дефолтами при первом обращении).
- `get_effective_config(db)` — снимок-dict с TTL-кешем для горячих путей
  (`soft_caps.decide`, kill-switch в `/v1/ai/*`).
- `update_config(db, changes)` — частичное обновление + инкремент версии + сброс кеша.

Дефолт — discovery: всё бесплатно, лимиты безлимитные (None), рабочие фичи включены.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.remote_config import MonetizationMode, RemoteConfig

# --- Дефолты (используются при создании singleton и для заполнения пропусков) ---

DEFAULT_LIMITS: dict[str, Any] = {
    "ai_per_day": None,      # None = безлимит (discovery)
    "ai_per_month": None,
    "per_type": {},          # {"plan": int|None, "query": int|None, ...}
}

DEFAULT_FEATURE_FLAGS: dict[str, bool] = {
    "tj_analysis": True,
    "plans": True,
    "logcfg": True,
    "regressions": True,
    "query_analyzer": False,  # скрыт в продукте (см. App.tsx) — выключен по умолчанию
    "sql_console": True,
}

DEFAULT_AI_MODEL_PER_TYPE: dict[str, str] = {}   # пусто = встроенные дефолты ai_explainer
DEFAULT_PROMPT_VERSIONS: dict[str, str] = {}     # пусто = константы PROMPT_VERSION_* в коде

# Поля, которые получает desktop (без серверных деталей: модель/версии промптов).
PUBLIC_KEYS = ("monetization_mode", "ai_kill_switch", "limits", "feature_flags", "config_version")

# --- TTL-кеш снимка (горячие пути не должны бить БД на каждый AI-вызов) ---

_CACHE: dict[str, Any] = {"data": None, "exp": 0.0}
_CACHE_TTL = 30.0  # секунд


def _load_or_create(db: Session) -> RemoteConfig:
    cfg = db.scalars(select(RemoteConfig)).first()
    if cfg is None:
        cfg = RemoteConfig(
            monetization_mode=MonetizationMode.DISCOVERY,
            ai_kill_switch=False,
            limits=dict(DEFAULT_LIMITS),
            feature_flags=dict(DEFAULT_FEATURE_FLAGS),
            ai_model_per_type=dict(DEFAULT_AI_MODEL_PER_TYPE),
            prompt_versions=dict(DEFAULT_PROMPT_VERSIONS),
            config_version=1,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def get_config(db: Session) -> RemoteConfig:
    """ORM-объект singleton (для admin GET/PUT). Без кеша."""
    return _load_or_create(db)


def to_admin_dict(cfg: RemoteConfig) -> dict[str, Any]:
    """Полный конфиг для админки (пропуски в JSON заполняются дефолтами)."""
    mode = cfg.monetization_mode
    return {
        "monetization_mode": mode.value if hasattr(mode, "value") else str(mode),
        "ai_kill_switch": bool(cfg.ai_kill_switch),
        "limits": {**DEFAULT_LIMITS, **(cfg.limits or {})},
        "feature_flags": {**DEFAULT_FEATURE_FLAGS, **(cfg.feature_flags or {})},
        "ai_model_per_type": {**DEFAULT_AI_MODEL_PER_TYPE, **(cfg.ai_model_per_type or {})},
        "prompt_versions": {**DEFAULT_PROMPT_VERSIONS, **(cfg.prompt_versions or {})},
        "config_version": int(cfg.config_version),
        "updated_at": cfg.updated_at,
    }


def to_public_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Подмножество для desktop из admin-снимка."""
    return {k: data[k] for k in PUBLIC_KEYS}


def get_effective_config(db: Session) -> dict[str, Any]:
    """Снимок-dict конфига с TTL-кешем — для горячих путей (decide / AI kill-switch)."""
    now = time.monotonic()
    cached = _CACHE["data"]
    if cached is not None and now < _CACHE["exp"]:
        return cached
    data = to_admin_dict(_load_or_create(db))
    _CACHE["data"] = data
    _CACHE["exp"] = now + _CACHE_TTL
    return data


def invalidate_cache() -> None:
    """Сбросить кеш снимка (вызывается после update_config; полезно в тестах)."""
    _CACHE["data"] = None
    _CACHE["exp"] = 0.0


def is_discovery(db: Session) -> bool:
    return get_effective_config(db).get("monetization_mode") == MonetizationMode.DISCOVERY.value


def is_ai_kill_switch_on(db: Session) -> bool:
    return bool(get_effective_config(db).get("ai_kill_switch"))


def update_config(db: Session, changes: dict[str, Any]) -> RemoteConfig:
    """Частичное обновление. JSON-поля мёржатся поверх существующих (PUT не стирает
    то, что не передали). monetization_mode/ai_kill_switch — заменяются. Версия +1."""
    cfg = _load_or_create(db)

    mode = changes.get("monetization_mode")
    if mode is not None:
        cfg.monetization_mode = MonetizationMode(mode)

    if changes.get("ai_kill_switch") is not None:
        cfg.ai_kill_switch = bool(changes["ai_kill_switch"])

    for jkey in ("limits", "feature_flags", "ai_model_per_type", "prompt_versions"):
        val = changes.get(jkey)
        if val is not None:
            # reassign новым dict — SQLAlchemy отследит изменение JSON-колонки
            setattr(cfg, jkey, {**(getattr(cfg, jkey) or {}), **val})

    cfg.config_version = int(cfg.config_version) + 1
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    invalidate_cache()
    return cfg
