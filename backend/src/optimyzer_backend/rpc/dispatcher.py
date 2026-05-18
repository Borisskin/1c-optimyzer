"""JSON-RPC 2.0 dispatcher. Регистрация методов через декоратор @rpc."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

_REGISTRY: dict[str, Callable[..., Any]] = {}


def rpc(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in _REGISTRY:
            raise RuntimeError(f"RPC method already registered: {name}")
        _REGISTRY[name] = fn
        return fn

    return deco


class Dispatcher:
    def __init__(self, methods: dict[str, Callable[..., Any]]) -> None:
        self._methods = methods

    @classmethod
    def default(cls) -> "Dispatcher":
        return cls(dict(_REGISTRY))

    def handle(self, req: dict) -> dict | None:
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if not isinstance(method, str):
            return self._error(-32600, "Invalid Request: method missing", rid)

        fn = self._methods.get(method)
        if fn is None:
            return self._error(-32601, f"Method not found: {method}", rid)

        try:
            if isinstance(params, dict):
                result = fn(**params)
            elif isinstance(params, list):
                result = fn(*params)
            else:
                return self._error(-32602, "Invalid params type", rid)
        except TypeError as e:
            return self._error(-32602, f"Invalid params: {e}", rid)
        except Exception as e:
            return self._error(
                -32000,
                f"{type(e).__name__}: {e}",
                rid,
                data={"traceback": traceback.format_exc()},
            )

        if rid is None:
            return None
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    @staticmethod
    def _error(code: int, message: str, rid: Any, data: Any = None) -> dict:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": rid, "error": err}
