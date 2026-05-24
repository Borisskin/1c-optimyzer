"""RPC методы для bsl-LS adapter (Sprint 6 Phase C).

Public RPC:
    bsl_ls.analyze(query_sdbl, [enabled_rules])
        → диагностики bsl-language-server + группировка по Q6
        configurationRoot подтягивается автоматически из подключённой
        Configuration (configuration_metadata.api.get_default_store).

    bsl_ls.status()
        → доступность binaries, JVM running state, версия

    bsl_ls.reload_configuration()
        → передать configurationRoot в bsl-LS через workspace/didChangeConfiguration.
        Вызывается из configuration_rpc после индексации новой XML выгрузки.

Эти RPC заменят query_analyzer.analyze в Sprint 6 Phase E. Старый
query_analyzer_rpc остаётся работать до полного перехода UI.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from optimyzer_backend.bsl_ls import AnalyzeRequest
from optimyzer_backend.bsl_ls.lifecycle import BslLsBinariesNotFoundError, get_paths
from optimyzer_backend.bsl_ls.runtime import get_bsl_client_sync, run_async
from optimyzer_backend.configuration_metadata.api import get_default_store
from optimyzer_backend.rpc.dispatcher import rpc

logger = logging.getLogger(__name__)


def _get_configuration_root() -> Optional[str]:
    """Текущий configurationRoot для bsl-LS — из ConfigurationMetadataStore."""
    try:
        store = get_default_store()
        source = store.get_source_path()
        return str(source) if source else None
    except Exception as e:  # noqa: BLE001
        logger.warning("Не удалось прочитать source_path конфигурации: %s", e)
        return None


@rpc("bsl_ls.analyze")
def analyze_rpc(
    query_sdbl: str,
    enabled_rules: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Анализирует SDBL через bsl-LS (синхронный wrapper).

    Если конфигурация подключена — semantic rules активны (QueryToMissingMetadata).
    Если нет — только синтаксические.
    """
    if not isinstance(query_sdbl, str):
        return {"ok": False, "error": "query_sdbl must be string"}

    try:
        config_root = _get_configuration_root()
        client = get_bsl_client_sync(configuration_root=config_root)
    except BslLsBinariesNotFoundError as e:
        return {
            "ok": False,
            "error": "bsl_ls_binaries_missing",
            "details": str(e),
            "hint": "Запустите scripts/setup-bsl-ls-binaries.ps1 или переустановите Optimyzer",
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Ошибка инициализации bsl-LS")
        return {"ok": False, "error": "bsl_ls_init_failed", "details": str(e)}

    req = AnalyzeRequest(
        query_sdbl=query_sdbl,
        configuration_root=config_root,
        enabled_rules=enabled_rules,
    )
    try:
        result = run_async(client.analyze_sdbl(req), timeout=30)
    except TimeoutError as e:
        return {"ok": False, "error": "bsl_ls_timeout", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("Ошибка анализа SDBL")
        return {"ok": False, "error": "bsl_ls_analyze_failed", "details": str(e)}

    return {
        "ok": True,
        "diagnostics": [d.model_dump(mode="json") for d in result.diagnostics],
        "grouped": [g.model_dump(mode="json") for g in result.grouped],
        "parse_success": result.parse_success,
        "analysis_duration_ms": result.analysis_duration_ms,
        "bsl_ls_version": result.bsl_ls_version,
        "configuration_root": config_root,
        "configuration_connected": config_root is not None,
    }


@rpc("bsl_ls.status")
def status_rpc() -> dict[str, Any]:
    """Состояние bsl-LS: бинарники + JVM + текущая конфигурация."""
    binaries_available = False
    binaries_source: Optional[str] = None
    binaries_error: Optional[str] = None
    try:
        paths = get_paths()
        paths.validate()
        binaries_available = True
        binaries_source = paths.source
    except BslLsBinariesNotFoundError as e:
        binaries_error = str(e)

    config_root = _get_configuration_root()
    try:
        store = get_default_store()
        config_info = store.get_configuration_info() if store.is_indexed() else None
    except Exception:  # noqa: BLE001
        config_info = None

    return {
        "ok": True,
        "binaries_available": binaries_available,
        "binaries_source": binaries_source,
        "binaries_error": binaries_error,
        "configuration_connected": config_root is not None,
        "configuration_root": config_root,
        "configuration_info": config_info,
        "bsl_ls_version": "0.29.0",
    }


@rpc("bsl_ls.reload_configuration")
def reload_configuration_rpc() -> dict[str, Any]:
    """Уведомляет работающий bsl-LS sidecar о смене configurationRoot.

    Вызывается из configuration_rpc.connect_configuration после успешной
    индексации новой XML выгрузки. Если JVM не запущена — no-op (новый
    configRoot применится при следующем analyze).
    """
    config_root = _get_configuration_root()
    if config_root is None:
        return {"ok": True, "applied": False, "reason": "configuration_not_connected"}

    try:
        # Не делаем lazy-start — если JVM ещё не нужна, не запускаем.
        from optimyzer_backend.bsl_ls.client import _client as _existing_client

        if _existing_client is None:
            return {"ok": True, "applied": False, "reason": "bsl_ls_not_running"}

        async def _apply() -> None:
            await _existing_client.set_workspace_configuration(config_root)

        run_async(_apply(), timeout=10)
        return {"ok": True, "applied": True, "configuration_root": config_root}
    except Exception as e:  # noqa: BLE001
        logger.exception("reload_configuration failed")
        return {"ok": False, "error": str(e)}
