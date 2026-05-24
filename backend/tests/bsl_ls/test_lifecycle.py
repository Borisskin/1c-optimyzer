"""Тесты lifecycle.py — get_paths fallback chain + port utilities."""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from optimyzer_backend.bsl_ls.lifecycle import (
    BSL_LS_JAR_NAME,
    BslLsBinariesNotFoundError,
    BslLsPaths,
    _pick_free_port,
    _port_is_free,
    get_paths,
)


class TestGetPaths:
    def test_explicit_paths_take_priority(self, tmp_path: Path) -> None:
        java = tmp_path / "java.exe"
        jar = tmp_path / "bsl.jar"
        java.write_text("fake")
        jar.write_text("fake")
        paths = get_paths(explicit_java=java, explicit_jar=jar)
        assert paths.java_executable == java
        assert paths.bsl_ls_jar == jar
        assert paths.source == "explicit"

    def test_explicit_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(BslLsBinariesNotFoundError):
            get_paths(
                explicit_java=tmp_path / "nonexistent.exe",
                explicit_jar=tmp_path / "nonexistent.jar",
            )

    def test_env_vars_used_when_no_explicit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        java = tmp_path / "java.exe"
        jar = tmp_path / "bsl.jar"
        java.write_text("fake")
        jar.write_text("fake")
        monkeypatch.setenv("BSL_LS_JAVA_EXECUTABLE", str(java))
        monkeypatch.setenv("BSL_LS_JAR_PATH", str(jar))
        paths = get_paths()
        assert paths.source == "tauri-resource"
        assert paths.java_executable == java
        assert paths.bsl_ls_jar == jar

    def test_env_vars_pointing_to_missing_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Env vars указывают на несуществующие — должен пойти fallback.
        monkeypatch.setenv("BSL_LS_JAVA_EXECUTABLE", "/nonexistent/java.exe")
        monkeypatch.setenv("BSL_LS_JAR_PATH", "/nonexistent/bsl.jar")
        # Должен попробовать frontend/src-tauri/binaries/ или research/ —
        # если они есть на машине разработчика, тест проходит. Иначе
        # raise BslLsBinariesNotFoundError (что тоже валидно — это тест что
        # fallback chain работает).
        try:
            paths = get_paths()
            assert paths.source != "tauri-resource"
        except BslLsBinariesNotFoundError:
            pass  # Ok — на CI без бинарников

    def test_dev_paths_when_present(self) -> None:
        """Если frontend/src-tauri/binaries/ существует — должен найти."""
        try:
            paths = get_paths()
        except BslLsBinariesNotFoundError:
            pytest.skip("Бинарники не установлены (запустите setup-bsl-ls-binaries.ps1)")
        assert paths.java_executable.is_file()
        assert paths.bsl_ls_jar.is_file()
        assert paths.source in {
            "tauri-resource",
            "frontend-src-tauri",
            "research-fallback-jdk24",
            "research-fallback-system-java",
        }


class TestPortUtilities:
    def test_pick_free_port_returns_int_in_valid_range(self) -> None:
        port = _pick_free_port()
        assert 1024 < port < 65536

    def test_port_is_free_true_for_random_port(self) -> None:
        port = _pick_free_port()
        assert _port_is_free(port)

    def test_port_is_free_false_when_bound(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            assert not _port_is_free(port)


class TestBslLsPaths:
    def test_validate_raises_on_missing_java(self, tmp_path: Path) -> None:
        jar = tmp_path / "bsl.jar"
        jar.write_text("fake")
        paths = BslLsPaths(
            java_executable=tmp_path / "missing.exe",
            bsl_ls_jar=jar,
            source="test",
        )
        with pytest.raises(BslLsBinariesNotFoundError, match="java"):
            paths.validate()

    def test_validate_raises_on_missing_jar(self, tmp_path: Path) -> None:
        java = tmp_path / "java.exe"
        java.write_text("fake")
        paths = BslLsPaths(
            java_executable=java,
            bsl_ls_jar=tmp_path / "missing.jar",
            source="test",
        )
        with pytest.raises(BslLsBinariesNotFoundError, match="jar"):
            paths.validate()
