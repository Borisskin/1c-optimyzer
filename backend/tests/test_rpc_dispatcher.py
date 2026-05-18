"""Тесты для JSON-RPC dispatcher: routing, error codes."""

from __future__ import annotations

from optimyzer_backend.rpc.dispatcher import Dispatcher


def test_dispatcher_routes_method():
    disp = Dispatcher({"echo": lambda **kw: kw})
    resp = disp.handle({"jsonrpc": "2.0", "id": 1, "method": "echo", "params": {"x": 1}})
    assert resp == {"jsonrpc": "2.0", "id": 1, "result": {"x": 1}}


def test_dispatcher_method_not_found():
    disp = Dispatcher({})
    resp = disp.handle({"jsonrpc": "2.0", "id": 7, "method": "nope"})
    assert resp["error"]["code"] == -32601


def test_dispatcher_invalid_params_type():
    disp = Dispatcher({"echo": lambda **kw: kw})
    resp = disp.handle({"jsonrpc": "2.0", "id": 1, "method": "echo", "params": "not-an-object"})
    assert resp["error"]["code"] == -32602


def test_dispatcher_invalid_request_missing_method():
    disp = Dispatcher({})
    resp = disp.handle({"jsonrpc": "2.0", "id": 1})
    assert resp["error"]["code"] == -32600


def test_dispatcher_handles_handler_exception():
    def boom(**kw):
        raise RuntimeError("kaboom")

    disp = Dispatcher({"boom": boom})
    resp = disp.handle({"jsonrpc": "2.0", "id": 1, "method": "boom", "params": {}})
    assert resp["error"]["code"] == -32000
    assert "kaboom" in resp["error"]["message"]


def test_dispatcher_notification_returns_none():
    """Запрос без id (notification) — ответа быть не должно."""
    disp = Dispatcher({"echo": lambda **kw: kw})
    resp = disp.handle({"jsonrpc": "2.0", "method": "echo", "params": {}})
    assert resp is None
