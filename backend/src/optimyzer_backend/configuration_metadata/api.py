"""High-level API для configuration metadata (Sprint 5 Phase A).

Singleton-helper для query analyzer и RPC методов. Поддерживает
переопределение пути к БД через env `OPTIMYZER_CONFIG_DB_PATH`.

Использование::

    from optimyzer_backend.configuration_metadata.api import get_default_store

    store = get_default_store()  # ConfigurationMetadataStore
    if store.is_indexed():
        ...
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from optimyzer_backend.configuration_metadata.store import (
    ConfigurationMetadataStore,
)


_DEFAULT_DB_FILENAME = "config_metadata.db"
_lock = threading.Lock()
_singleton: ConfigurationMetadataStore | None = None
_singleton_db_path: Path | None = None


def get_default_db_path() -> Path:
    """Возвращает путь к default SQLite-файлу с конфигурационным индексом.

    Можно переопределить через env `OPTIMYZER_CONFIG_DB_PATH`.
    """
    env_path = os.environ.get("OPTIMYZER_CONFIG_DB_PATH")
    if env_path:
        return Path(env_path)
    # backend/data/config_metadata.db — рядом с explainer_cache.db
    # backend/src/optimyzer_backend/configuration_metadata/api.py
    #   parents[0] = configuration_metadata
    #   parents[3] = backend
    return Path(__file__).resolve().parents[3] / "data" / _DEFAULT_DB_FILENAME


def get_default_store() -> ConfigurationMetadataStore:
    """Singleton ConfigurationMetadataStore по default-пути.

    При первом вызове создаёт store (и инициализирует schema если БД новая).
    Повторные вызовы возвращают тот же экземпляр.

    Если default-путь поменялся (например через env), singleton
    пересоздаётся под новый путь.
    """
    global _singleton, _singleton_db_path
    target_path = get_default_db_path()
    with _lock:
        if _singleton is None or _singleton_db_path != target_path:
            _singleton = ConfigurationMetadataStore(target_path)
            _singleton_db_path = target_path
        return _singleton


def reset_default_store_for_tests() -> None:
    """Сбросить singleton (только для тестов)."""
    global _singleton, _singleton_db_path
    with _lock:
        _singleton = None
        _singleton_db_path = None
