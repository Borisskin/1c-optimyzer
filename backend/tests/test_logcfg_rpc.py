"""Sprint 10 Phase A — тесты logcfg.detect_platform RPC.

Тесты мокируют файловую систему и сокет через unittest.mock.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from optimyzer_backend.rpc.logcfg_rpc import _probe_tcp, detect_platform_rpc


class TestDetectPlatformRpc:
    def test_single_version_found(self, tmp_path: Path) -> None:
        """Одна версия найдена → confidence=high."""
        ver_dir = tmp_path / "8.3.24.1461"
        ver_dir.mkdir()

        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ):
            result = detect_platform_rpc()

        assert result["version"] == "8.3.24"
        assert result["confidence"] == "high"
        assert "8.3.24" in result["all_found"]

    def test_multiple_versions_returns_highest(self, tmp_path: Path) -> None:
        """Несколько версий → возвращается самая свежая."""
        for ver in ("8.3.20.1000", "8.3.24.1461", "8.3.22.2101"):
            (tmp_path / ver).mkdir()

        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ):
            result = detect_platform_rpc()

        assert result["version"] == "8.3.24"
        assert result["confidence"] == "high"
        assert len(result["all_found"]) == 3

    def test_no_versions_agent_alive(self, tmp_path: Path) -> None:
        """Нет папок версий, но Server Agent отвечает → confidence=medium."""
        # Пустая папка — нет версий.
        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ), patch(
            "optimyzer_backend.rpc.logcfg_rpc._probe_tcp",
            return_value=True,
        ):
            result = detect_platform_rpc()

        assert result["version"] == "8.3.24"
        assert result["confidence"] == "medium"
        assert result["all_found"] == []

    def test_nothing_found_fallback(self, tmp_path: Path) -> None:
        """Ни папок, ни агента → fallback confidence=low."""
        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ), patch(
            "optimyzer_backend.rpc.logcfg_rpc._probe_tcp",
            return_value=False,
        ):
            result = detect_platform_rpc()

        assert result["version"] == "8.3.24"
        assert result["confidence"] == "low"

    def test_base_path_not_exists(self, tmp_path: Path) -> None:
        """Папка установки не существует → не падаем, fallback."""
        non_existent = tmp_path / "does_not_exist"

        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [non_existent],
        ), patch(
            "optimyzer_backend.rpc.logcfg_rpc._probe_tcp",
            return_value=False,
        ):
            result = detect_platform_rpc()

        assert result["confidence"] == "low"

    def test_ignores_non_version_dirs(self, tmp_path: Path) -> None:
        """Директории не соответствующие паттерну версии игнорируются."""
        (tmp_path / "8.3.24.1461").mkdir()
        (tmp_path / "common").mkdir()
        (tmp_path / "data").mkdir()
        (tmp_path / "8.3").mkdir()  # неполная версия

        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ):
            result = detect_platform_rpc()

        assert result["version"] == "8.3.24"
        assert len(result["all_found"]) == 1

    def test_version_format_major_minor_patch(self, tmp_path: Path) -> None:
        """Возвращается только 3-компонентная версия (без Build)."""
        (tmp_path / "8.3.24.1461").mkdir()

        with patch(
            "optimyzer_backend.rpc.logcfg_rpc._1C_INSTALL_PATHS",
            [tmp_path],
        ):
            result = detect_platform_rpc()

        parts = result["version"].split(".")
        assert len(parts) == 3, f"Ожидалось 3 части, получили: {result['version']}"


class TestProbeTcp:
    def test_probe_tcp_failure(self) -> None:
        """Недоступный порт → False, не выбрасывает исключение."""
        # Порт 19999 обычно не занят.
        result = _probe_tcp("localhost", 19999, timeout=0.1)
        assert result is False

    def test_probe_tcp_invalid_host(self) -> None:
        """Несуществующий хост → False, не выбрасывает исключение."""
        result = _probe_tcp("this.host.does.not.exist.invalid", 1541, timeout=0.1)
        assert result is False
