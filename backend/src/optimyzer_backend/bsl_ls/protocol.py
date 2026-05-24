"""LSP / JSON-RPC protocol типы (Sprint 6 Phase B).

bsl-language-server в `websocket` режиме говорит на стандартном LSP над
JSON-RPC 2.0. Этот модуль определяет message envelopes — без зависимости
от Pydantic (чистый dict[str, Any]) для скорости и интероп с websockets.
"""

from __future__ import annotations

from typing import Any, Optional

JsonValue = Any  # для краткости — bsl-LS messages = nested dict/list/str/int


def make_request(request_id: int, method: str, params: Optional[dict] = None) -> dict:
    """JSON-RPC 2.0 request envelope."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


def make_notification(method: str, params: Optional[dict] = None) -> dict:
    """JSON-RPC 2.0 notification (нет id, ответ не ожидается)."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
    }


def is_response(msg: dict) -> bool:
    """True если msg — ответ на наш request (есть id, нет method)."""
    return "id" in msg and "method" not in msg


def is_notification(msg: dict) -> bool:
    """True если msg — нотификация от сервера (есть method, нет id)."""
    return "method" in msg and "id" not in msg


def is_server_request(msg: dict) -> bool:
    """True если msg — запрос от сервера (есть и method, и id)."""
    return "method" in msg and "id" in msg


# ---- LSP message constructors (часто используемые) ----


def lsp_initialize(root_uri: str, configuration_root: Optional[str] = None) -> dict:
    """LSP initialize params.

    `configurationRoot` передаётся в initializationOptions — bsl-LS специфика.
    """
    init_options: dict[str, Any] = {}
    if configuration_root:
        init_options["configurationRoot"] = configuration_root
    return {
        "processId": None,  # bsl-LS не зависит от parent process монитора
        "rootUri": root_uri,
        "capabilities": {
            "textDocument": {
                "publishDiagnostics": {"versionSupport": False},
                "synchronization": {"dynamicRegistration": False},
            },
            "workspace": {
                "configuration": True,
                "didChangeConfiguration": {"dynamicRegistration": True},
            },
        },
        "initializationOptions": init_options,
        "workspaceFolders": [{"uri": root_uri, "name": "optimyzer-workspace"}],
    }


def lsp_did_open(file_uri: str, text: str, language_id: str = "bsl") -> dict:
    return {
        "textDocument": {
            "uri": file_uri,
            "languageId": language_id,
            "version": 1,
            "text": text,
        }
    }


def lsp_did_close(file_uri: str) -> dict:
    return {"textDocument": {"uri": file_uri}}


def lsp_did_change_configuration(configuration_root: str) -> dict:
    """workspace/didChangeConfiguration с конфигурацией bsl-LS."""
    return {
        "settings": {
            "configurationRoot": configuration_root,
        }
    }
