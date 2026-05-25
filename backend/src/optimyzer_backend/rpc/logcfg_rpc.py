"""Sprint 10: logcfg.* RPC методы для TJ Config Builder.

logcfg.detect_platform — определение версии платформы 1С на локальной машине.
Результат используется для pre-fill поля «Версия 1С» в AI Wizard.
"""

from __future__ import annotations

import logging
import re
import socket
from pathlib import Path

from optimyzer_backend.rpc.dispatcher import rpc

logger = logging.getLogger(__name__)

# Стандартные пути установки 1С на Windows.
_1C_INSTALL_PATHS = [
    Path("C:/Program Files/1cv8"),
    Path("C:/Program Files (x86)/1cv8"),
]

# Формат версии: Major.Minor.Patch.Build (например 8.3.24.1461).
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

# Порт 1С Server Agent по умолчанию.
_SERVER_AGENT_PORT = 1541


@rpc("logcfg.detect_platform")
def detect_platform_rpc() -> dict:
    """Определяет версию платформы 1С на локальной машине.

    Стратегии (в порядке приоритета):
      1. Folder scan: C:/Program Files/1cv8/<version>/ — наиболее надёжный.
      2. Server Agent probe: localhost:1541 TCP — если агент запущен.
      3. Fallback: 8.3.24 с confidence=low.

    Returns:
        {"version": "8.3.24", "confidence": "high" | "medium" | "low",
         "all_found": ["8.3.24", ...]}
    """
    # Стратегия 1: сканируем папки установки.
    found_versions: list[str] = []
    for base_path in _1C_INSTALL_PATHS:
        if not base_path.exists():
            continue
        try:
            for entry in base_path.iterdir():
                if entry.is_dir() and _VERSION_RE.match(entry.name):
                    found_versions.append(entry.name)
        except PermissionError:
            logger.debug("Нет доступа к %s", base_path)

    if found_versions:
        # Сортируем семантически — берём самую свежую версию.
        def _ver_key(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split("."))

        found_versions.sort(key=_ver_key, reverse=True)
        highest = found_versions[0]
        # Возвращаем только Major.Minor.Patch (без Build).
        short = ".".join(highest.split(".")[:3])
        logger.info("1С платформа найдена: %s (все: %s)", short, found_versions)
        return {
            "version": short,
            "confidence": "high",
            "all_found": [".".join(v.split(".")[:3]) for v in found_versions],
        }

    # Стратегия 2: TCP probe на порт Server Agent.
    agent_alive = _probe_tcp("localhost", _SERVER_AGENT_PORT, timeout=0.5)
    if agent_alive:
        logger.info("1С Server Agent отвечает на порту %d, но версию не определили", _SERVER_AGENT_PORT)
        return {
            "version": "8.3.24",
            "confidence": "medium",
            "all_found": [],
        }

    # Fallback.
    logger.info("Платформа 1С не найдена на локальной машине — fallback 8.3.24")
    return {
        "version": "8.3.24",
        "confidence": "low",
        "all_found": [],
    }


def _probe_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    """Проверяет доступность TCP-порта. True если соединение установлено."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
