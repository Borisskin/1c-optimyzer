"""Тесты protocol.py — JSON-RPC envelopes + LSP constructors."""

from __future__ import annotations

from optimyzer_backend.bsl_ls import protocol


class TestMakeRequest:
    def test_basic(self) -> None:
        msg = protocol.make_request(42, "textDocument/didOpen", {"uri": "file:///x.bsl"})
        assert msg["jsonrpc"] == "2.0"
        assert msg["id"] == 42
        assert msg["method"] == "textDocument/didOpen"
        assert msg["params"]["uri"] == "file:///x.bsl"

    def test_no_params(self) -> None:
        msg = protocol.make_request(1, "shutdown")
        assert msg["params"] == {}


class TestMakeNotification:
    def test_no_id(self) -> None:
        msg = protocol.make_notification("initialized")
        assert "id" not in msg
        assert msg["method"] == "initialized"
        assert msg["jsonrpc"] == "2.0"


class TestMessageClassification:
    def test_is_response(self) -> None:
        assert protocol.is_response({"id": 1, "result": "ok"})
        assert not protocol.is_response({"method": "notify"})
        assert not protocol.is_response({"id": 1, "method": "server_request"})

    def test_is_notification(self) -> None:
        assert protocol.is_notification({"method": "publish"})
        assert not protocol.is_notification({"id": 1, "result": "ok"})

    def test_is_server_request(self) -> None:
        assert protocol.is_server_request({"id": 1, "method": "workspace/configuration"})
        assert not protocol.is_server_request({"method": "notify"})


class TestLspInitialize:
    def test_without_config_root(self) -> None:
        params = protocol.lsp_initialize("file:///workspace")
        assert params["rootUri"] == "file:///workspace"
        assert params["initializationOptions"] == {}

    def test_with_config_root(self) -> None:
        params = protocol.lsp_initialize("file:///workspace", "C:/BUFFER/SCHEME")
        assert params["initializationOptions"]["configurationRoot"] == "C:/BUFFER/SCHEME"

    def test_workspace_folders(self) -> None:
        params = protocol.lsp_initialize("file:///workspace")
        assert len(params["workspaceFolders"]) == 1
        assert params["workspaceFolders"][0]["uri"] == "file:///workspace"


class TestLspDidOpen:
    def test_default_language_id_bsl(self) -> None:
        params = protocol.lsp_did_open("file:///x.bsl", "code")
        td = params["textDocument"]
        assert td["uri"] == "file:///x.bsl"
        assert td["languageId"] == "bsl"
        assert td["version"] == 1
        assert td["text"] == "code"


class TestLspDidChangeConfiguration:
    def test_settings_has_config_root(self) -> None:
        params = protocol.lsp_did_change_configuration("D:/some/path")
        assert params["settings"]["configurationRoot"] == "D:/some/path"
