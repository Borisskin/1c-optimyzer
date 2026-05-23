"""Sprint 5 Phase C — RPC методы для управления подключённой XML-выгрузкой
конфигурации 1С.

Public RPC:
    configuration.connect(path: str)
        → индексирует выгрузку (или возвращает already_indexed по hash)

    configuration.status()
        → {connected, source_path, indexed_at, object_count, by_kind,
           configuration: {name, synonym_ru, vendor, version}}

    configuration.disconnect()
        → очищает индекс (но не удаляет SQLite файл)

    configuration.reindex()
        → принудительная переиндексация текущего source (если он сохранён)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimyzer_backend.configuration_metadata.api import get_default_store
from optimyzer_backend.rpc.dispatcher import rpc


def _store_configuration_view(store) -> dict[str, str]:
    """Достаёт конфигурационные метаданные из store.meta как dict."""
    return {
        "name": store.get_meta("config_name") or "",
        "synonym_ru": store.get_meta("config_synonym_ru") or "",
        "vendor": store.get_meta("config_vendor") or "",
        "version": store.get_meta("config_version") or "",
    }


@rpc("configuration.connect")
def configuration_connect_rpc(path: str) -> dict[str, Any]:
    """Подключает XML выгрузку конфигурации.

    Параметры:
        path — абсолютный путь к корню выгрузки (где лежит Configuration.xml).

    Returns:
        {ok: True, status: "indexed"|"already_indexed", object_count, by_kind,
         configuration: {name, synonym_ru, vendor, version}, indexed_at}
        или
        {ok: False, error: "..."}
    """
    if not isinstance(path, str) or not path.strip():
        return {"ok": False, "error": "path must be a non-empty string"}
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"Путь не существует: {path}"}
    if not p.is_dir():
        return {"ok": False, "error": f"Путь не является папкой: {path}"}
    if not (p / "Configuration.xml").is_file():
        return {
            "ok": False,
            "error": "В указанной папке нет Configuration.xml — это не выгрузка 1С",
        }

    store = get_default_store()
    try:
        result = store.index_configuration(p)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "status": result["status"],
        "object_count": result["object_count"],
        "by_kind": result.get("by_kind") or {},
        "configuration": result.get("configuration") or _store_configuration_view(store),
        "indexed_at": store.get_meta("indexed_at") or "",
        "source_path": str(p),
    }


@rpc("configuration.status")
def configuration_status_rpc() -> dict[str, Any]:
    """Текущий статус подключённой конфигурации.

    Если конфигурация не подключена — `connected: false` и больше ничего.
    """
    store = get_default_store()
    if not store.is_indexed():
        return {"ok": True, "connected": False}
    return {
        "ok": True,
        "connected": True,
        "source_path": store.get_meta("source_path") or "",
        "indexed_at": store.get_meta("indexed_at") or "",
        "object_count": store.count_objects(),
        "by_kind": store.stats_by_kind(),
        "configuration": _store_configuration_view(store),
    }


@rpc("configuration.disconnect")
def configuration_disconnect_rpc() -> dict[str, Any]:
    """Отключает конфигурацию: очищает SQLite индекс.

    После disconnect query_analyzer.analyze автоматически перестанет
    запускать semantic rules (silent skip).
    """
    store = get_default_store()
    store.clear()
    return {"ok": True}


@rpc("configuration.reindex")
def configuration_reindex_rpc() -> dict[str, Any]:
    """Принудительная переиндексация текущего источника.

    Использует source_path из meta — то есть подразумевается что
    configuration.connect был хотя бы раз вызван. Если нет — error.
    """
    store = get_default_store()
    source = store.get_meta("source_path")
    if not source:
        return {
            "ok": False,
            "error": "Конфигурация не подключена — нечего переиндексировать. Сначала configuration.connect.",
        }
    p = Path(source)
    if not p.exists() or not (p / "Configuration.xml").is_file():
        return {
            "ok": False,
            "error": f"Источник недоступен: {source}",
        }
    # Принудительный re-index: сбрасываем хеш чтобы пройти invalidation
    store.set_meta("source_hash", "FORCED_REINDEX")
    try:
        result = store.index_configuration(p)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "status": result["status"],
        "object_count": result["object_count"],
        "by_kind": result.get("by_kind") or {},
        "configuration": result.get("configuration") or _store_configuration_view(store),
        "indexed_at": store.get_meta("indexed_at") or "",
    }
