"""Тесты RPC-методов bsl_ls.* + интеграция с Configuration (Sprint 6 Phase C)."""

from __future__ import annotations

import pytest

from optimyzer_backend.bsl_ls.lifecycle import BslLsBinariesNotFoundError, get_paths


def _binaries_available() -> bool:
    try:
        get_paths().validate()
        return True
    except BslLsBinariesNotFoundError:
        return False


class TestBslLsStatus:
    """status_rpc безопасен даже без JVM — только проверяет наличие бинарников."""

    def test_status_returns_ok(self) -> None:
        from optimyzer_backend.rpc.bsl_ls_rpc import status_rpc

        result = status_rpc()
        assert result["ok"] is True
        assert "binaries_available" in result
        assert "configuration_connected" in result
        assert result["bsl_ls_version"] == "0.29.0"

    def test_status_shows_binaries_state(self) -> None:
        from optimyzer_backend.rpc.bsl_ls_rpc import status_rpc

        result = status_rpc()
        if _binaries_available():
            assert result["binaries_available"] is True
            assert result["binaries_source"] in {
                "tauri-resource",
                "frontend-src-tauri",
                "research-fallback-jdk24",
                "research-fallback-system-java",
            }
        else:
            assert result["binaries_available"] is False
            assert result["binaries_error"] is not None


class TestBslLsAnalyzeBinariesMissing:
    """Когда бинарники недоступны — analyze возвращает структурированную ошибку."""

    def test_returns_binaries_missing_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from optimyzer_backend.rpc import bsl_ls_rpc

        # Forced fail get_paths.
        def _raise_no_binaries(**kwargs: object) -> None:
            raise BslLsBinariesNotFoundError("test: бинарники отсутствуют")

        monkeypatch.setattr(bsl_ls_rpc, "get_bsl_client_sync", _raise_no_binaries)
        result = bsl_ls_rpc.analyze_rpc("ВЫБРАТЬ 1")
        assert result["ok"] is False
        assert result["error"] == "bsl_ls_binaries_missing"
        assert "hint" in result


class TestBslLsAnalyzeValidation:
    def test_non_string_input_rejected(self) -> None:
        from optimyzer_backend.rpc.bsl_ls_rpc import analyze_rpc

        result = analyze_rpc(query_sdbl=42)  # type: ignore[arg-type]
        assert result["ok"] is False
        assert "string" in result["error"].lower()


class TestReloadConfigurationNoJvm:
    """reload_configuration без работающей JVM — no-op."""

    def test_no_jvm_returns_not_running(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        from optimyzer_backend.bsl_ls import client as bsl_client_module
        from optimyzer_backend.rpc.bsl_ls_rpc import reload_configuration_rpc

        # Гарантируем что singleton не активен.
        monkeypatch.setattr(bsl_client_module, "_client", None)
        # Мокаем configurationRoot — чтобы не вернулся "configuration_not_connected".
        monkeypatch.setattr(
            "optimyzer_backend.rpc.bsl_ls_rpc._get_configuration_root",
            lambda: "C:/fake/path",
        )
        result = reload_configuration_rpc()
        assert result["ok"] is True
        assert result["applied"] is False
        assert result["reason"] == "bsl_ls_not_running"

    def test_no_configuration_skips_reload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from optimyzer_backend.rpc.bsl_ls_rpc import reload_configuration_rpc

        monkeypatch.setattr(
            "optimyzer_backend.rpc.bsl_ls_rpc._get_configuration_root",
            lambda: None,
        )
        result = reload_configuration_rpc()
        assert result["ok"] is True
        assert result["applied"] is False
        assert result["reason"] == "configuration_not_connected"


class TestConfigurationStoreGetSourcePath:
    """Sprint 6 — get_source_path должен возвращать индексированный путь."""

    def test_returns_none_when_not_indexed(self, tmp_path: object) -> None:
        from optimyzer_backend.configuration_metadata.store import (
            ConfigurationMetadataStore,
        )

        store = ConfigurationMetadataStore(tmp_path / "test.db")  # type: ignore[operator]
        assert store.get_source_path() is None

    def test_returns_none_when_path_does_not_exist(self, tmp_path: object) -> None:
        from optimyzer_backend.configuration_metadata.store import (
            ConfigurationMetadataStore,
        )

        store = ConfigurationMetadataStore(tmp_path / "test.db")  # type: ignore[operator]
        store.set_meta("source_path", "/nonexistent/path")
        assert store.get_source_path() is None

    def test_returns_path_when_dir_exists(self, tmp_path: object) -> None:
        from optimyzer_backend.configuration_metadata.store import (
            ConfigurationMetadataStore,
        )

        store = ConfigurationMetadataStore(tmp_path / "test.db")  # type: ignore[operator]
        store.set_meta("source_path", str(tmp_path))  # type: ignore[arg-type]
        result = store.get_source_path()
        assert result is not None
        assert result == tmp_path  # type: ignore[comparison-overlap]


@pytest.mark.integration
@pytest.mark.skipif(not _binaries_available(), reason="bsl-LS binaries not installed")
class TestBslLsAnalyzeIntegration:
    """End-to-end через RPC: реальный JVM + analyze."""

    def test_analyze_via_rpc_returns_diagnostics(self) -> None:
        from optimyzer_backend.rpc.bsl_ls_rpc import analyze_rpc

        sdbl = (
            "ВЫБРАТЬ Док.Ссылка.Контрагент.Ссылка.Наименование "
            "ИЗ Документ.ПродажаТоваров КАК Док"
        )
        result = analyze_rpc(query_sdbl=sdbl)
        assert result["ok"] is True
        codes = {d["code"] for d in result["diagnostics"]}
        assert "RefOveruse" in codes or "QueryNestedFieldsByDot" in codes
        assert "grouped" in result
        assert "analysis_duration_ms" in result
