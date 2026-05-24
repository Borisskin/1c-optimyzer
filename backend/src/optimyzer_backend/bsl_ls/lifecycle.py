"""Жизненный цикл bsl-LS WebSocket sidecar (Sprint 6 Phase B).

Запускает JVM с bsl-language-server в WebSocket режиме, мониторит здоровье,
auto-restart при крашах (max 3). Lazy-start — JVM запускается при первом
обращении к get_client().

Точка входа — get_paths() ищет бинарники в нескольких местах:
    1. Tauri resource dir (production) — переданный через env vars
       BSL_LS_JAVA_EXECUTABLE и BSL_LS_JAR_PATH
    2. frontend/src-tauri/binaries/ (dev mode) — относительно репо
    3. research/ (fallback при отсутствии binaries — для разработки adapter
       до tauri build)

Конструктивные решения:
    - WebSocket с lazy-start (Q3) — JVM живёт от первого использования
      до выхода backend
    - Health-check каждые 30 сек через ws.ping()
    - Auto-restart at crash, max_crashes=3, потом graceful fail
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Версии — синхронизированы с scripts/setup-bsl-ls-binaries.ps1.
BSL_LS_VERSION = "0.29.0"
BSL_LS_JAR_NAME = f"bsl-language-server-{BSL_LS_VERSION}-exec.jar"
# bsl-LS websocket режим: default port 8025 (Tomcat), endpoint path /lsp.
# CLI флаги: --server.port=<port> --app.websocket.lsp-path=<path>.
DEFAULT_PORT = 8025
WEBSOCKET_LSP_PATH = "/lsp"
SPAWN_TIMEOUT_S = 60.0  # Spring Boot + Tomcat cold-start ~5-15s
HEALTH_CHECK_INTERVAL_S = 30.0


class BslLsBinariesNotFoundError(RuntimeError):
    """bsl-LS binaries не найдены ни в одном из ожидаемых мест."""


class BslLsSpawnError(RuntimeError):
    """JVM не запустилась за SPAWN_TIMEOUT_S."""


class BslLsCrashLoop(RuntimeError):
    """JVM крашится непрерывно (max_crashes превышен)."""


@dataclass(frozen=True)
class BslLsPaths:
    """Resolved пути к Java executable и bsl-LS jar."""

    java_executable: Path
    bsl_ls_jar: Path
    source: str  # "tauri-resource" / "frontend-src-tauri" / "research-fallback"

    def validate(self) -> None:
        if not self.java_executable.is_file():
            raise BslLsBinariesNotFoundError(f"java.exe не найден: {self.java_executable}")
        if not self.bsl_ls_jar.is_file():
            raise BslLsBinariesNotFoundError(f"bsl-LS jar не найден: {self.bsl_ls_jar}")


def _repo_root() -> Path:
    """Корень репозитория (где лежит .git)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise BslLsBinariesNotFoundError(f"Не найден корень репозитория от {here}")


def get_paths(
    *,
    explicit_java: Optional[Path] = None,
    explicit_jar: Optional[Path] = None,
) -> BslLsPaths:
    """Ищем bundled бинарники с fallback цепочкой.

    Args:
        explicit_java: Если передано — используем без поиска (для тестов).
        explicit_jar: Аналогично.

    Returns:
        BslLsPaths с source описывающим где нашли.

    Raises:
        BslLsBinariesNotFoundError: ни одна стратегия не сработала.
    """
    if explicit_java is not None and explicit_jar is not None:
        paths = BslLsPaths(explicit_java, explicit_jar, "explicit")
        paths.validate()
        return paths

    # Стратегия 1: env vars (production — Tauri передаёт через get_bsl_ls_paths).
    env_java = os.environ.get("BSL_LS_JAVA_EXECUTABLE")
    env_jar = os.environ.get("BSL_LS_JAR_PATH")
    if env_java and env_jar:
        paths = BslLsPaths(Path(env_java), Path(env_jar), "tauri-resource")
        try:
            paths.validate()
            return paths
        except BslLsBinariesNotFoundError:
            logger.warning("env vars указывают на несуществующие файлы, пробуем fallback")

    # Стратегия 2: frontend/src-tauri/binaries/ (dev mode).
    repo = _repo_root()
    java_dev = repo / "frontend" / "src-tauri" / "binaries" / "jre-21" / "bin" / "java.exe"
    jar_dev = repo / "frontend" / "src-tauri" / "binaries" / "bsl-ls" / BSL_LS_JAR_NAME
    if java_dev.is_file() and jar_dev.is_file():
        return BslLsPaths(java_dev, jar_dev, "frontend-src-tauri")

    # Стратегия 3: research/ (fallback — для разработки до tauri build).
    java_res = repo / "research" / "jre-21-extracted"
    # Используем system java + research jar если есть.
    jar_research = repo / "research" / BSL_LS_JAR_NAME
    if jar_research.is_file():
        # System java?
        system_java = shutil.which("java")
        # JDK 24 на машине Сергея.
        jdk24 = Path("C:/Program Files/Java/jdk-24/bin/java.exe")
        if jdk24.is_file():
            return BslLsPaths(jdk24, jar_research, "research-fallback-jdk24")
        if system_java:
            return BslLsPaths(Path(system_java), jar_research, "research-fallback-system-java")

    raise BslLsBinariesNotFoundError(
        "bsl-LS binaries не найдены ни в Tauri resource, ни в frontend/src-tauri/binaries/, "
        "ни в research/. Запустите scripts/setup-bsl-ls-binaries.ps1."
    )


def _pick_free_port() -> int:
    """Возвращает свободный TCP порт (для случая когда 7777 занят)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_is_free(port: int) -> bool:
    """Проверяет, свободен ли порт на 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


async def _wait_port_open(port: int, timeout_s: float) -> None:
    """Ждёт пока порт станет доступен для подключения (= JVM поднялась)."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            return
        except (ConnectionRefusedError, OSError):
            await asyncio.sleep(0.5)
    raise BslLsSpawnError(f"JVM не открыла порт {port} за {timeout_s}s")


class BslLsLifecycle:
    """Управление JVM-процессом bsl-LS.

    Не используется напрямую — через BslLsClient в client.py.
    """

    def __init__(
        self,
        paths: BslLsPaths,
        port: Optional[int] = None,
        max_crashes: int = 3,
    ) -> None:
        self.paths = paths
        self._configured_port = port  # если None — выбираем динамически
        self.port = port or DEFAULT_PORT
        self.process: Optional[subprocess.Popen[bytes]] = None
        self.crash_count = 0
        self.max_crashes = max_crashes

    async def start(self) -> None:
        """Поднимает JVM. Идемпотентно — если уже работает, возвращает сразу."""
        if self.is_running():
            logger.debug("bsl-LS уже запущен (pid=%s, port=%s)", self.process.pid, self.port)
            return

        # Выбираем порт: если DEFAULT_PORT занят (другой процесс) — берём случайный.
        port = self._configured_port or DEFAULT_PORT
        if not _port_is_free(port):
            port = _pick_free_port()
            logger.info("Default port %s занят, использую %s", DEFAULT_PORT, port)
        self.port = port

        cmd = [
            str(self.paths.java_executable),
            "-jar",
            str(self.paths.bsl_ls_jar),
            "websocket",
            f"--server.port={self.port}",
            f"--app.websocket.lsp-path={WEBSOCKET_LSP_PATH}",
        ]
        logger.info("Запускаю bsl-LS: port=%s, source=%s", self.port, self.paths.source)
        # Для Windows — без CREATE_NEW_CONSOLE флага, наследуем stdio.
        creationflags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            # CREATE_NO_WINDOW — чтобы не вылазило окно при запуске из Tauri.
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )
        try:
            await _wait_port_open(self.port, SPAWN_TIMEOUT_S)
        except BslLsSpawnError:
            await self.stop()
            raise
        logger.info("bsl-LS запущен (pid=%s)", self.process.pid)

    def is_running(self) -> bool:
        """True если процесс жив (по poll())."""
        return self.process is not None and self.process.poll() is None

    async def restart(self) -> None:
        """Останавливает и перезапускает JVM. Счётчик crash инкрементируется."""
        self.crash_count += 1
        if self.crash_count > self.max_crashes:
            raise BslLsCrashLoop(
                f"bsl-LS упал {self.max_crashes} раз подряд — отказываюсь рестартовать"
            )
        logger.warning("Restarting bsl-LS (попытка %s/%s)", self.crash_count, self.max_crashes)
        await self.stop()
        await asyncio.sleep(2)
        await self.start()

    async def stop(self) -> None:
        """Graceful shutdown JVM. Если не отвечает — kill."""
        if self.process is None:
            return
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("bsl-LS не остановился за 10s, kill")
                self.process.kill()
                self.process.wait(timeout=5)
        except Exception as e:  # noqa: BLE001
            logger.warning("Ошибка при остановке bsl-LS: %s", e)
        finally:
            self.process = None
