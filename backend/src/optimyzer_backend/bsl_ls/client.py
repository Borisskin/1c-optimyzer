"""WebSocket клиент к bsl-LS sidecar (Sprint 6 Phase B).

Высокоуровневый API:
    client = await get_client()
    result = await client.analyze_sdbl(request)

Singleton — один экземпляр на процесс backend. Lazy-start: JVM поднимается
при первом обращении к get_client().

Реализует LSP поверх JSON-RPC 2.0 поверх WebSocket.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Optional

try:
    import websockets
    from websockets.asyncio.client import ClientConnection
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "websockets>=12 не установлен. Добавьте в backend/pyproject.toml dependencies."
    ) from e

from . import protocol
from .lifecycle import WEBSOCKET_LSP_PATH, BslLsLifecycle, BslLsPaths, get_paths
from .models import AnalyzeRequest, AnalyzeResult, Diagnostic
from .parser import group_overlapping, parse_lsp_diagnostic

logger = logging.getLogger(__name__)


# Singleton state.
_lock = asyncio.Lock()
_client: Optional["BslLsClient"] = None
_lifecycle: Optional[BslLsLifecycle] = None


class BslLsClient:
    """LSP-over-WebSocket client для bsl-language-server.

    Не используйте напрямую — через get_client(). Жизненный цикл управляется
    модульным singleton'ом, чтобы один backend = один JVM.
    """

    def __init__(self, lifecycle: BslLsLifecycle) -> None:
        self.lifecycle = lifecycle
        self.ws: Optional[ClientConnection] = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        # Накопленные diagnostics per file_uri (приходят как notifications).
        self._diagnostics_buffer: dict[str, list[dict]] = {}
        # Event per uri — set когда придёт publishDiagnostics (любой, даже пустой).
        self._diagnostics_received: dict[str, asyncio.Event] = {}
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._initialized = False
        self._configuration_root: Optional[str] = None
        # Persistent workspace dir — все temp .bsl файлы складываются сюда,
        # чтобы bsl-LS видел их как часть инициализированного workspace.
        self._workspace_dir: Optional[Path] = None

    # ---- connection lifecycle ----

    async def connect(self) -> None:
        """Подключается к запущенной JVM по WebSocket (Tomcat endpoint /lsp)."""
        url = f"ws://127.0.0.1:{self.lifecycle.port}{WEBSOCKET_LSP_PATH}"
        logger.debug("Connecting to bsl-LS at %s", url)
        self.ws = await websockets.connect(url, max_size=2**24)  # 16 MB max msg
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def disconnect(self) -> None:
        """Корректное закрытие WebSocket."""
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self.ws:
            try:
                await self.ws.close()
            except Exception:  # noqa: BLE001
                pass
            self.ws = None

    async def is_alive(self) -> bool:
        """Health check — ws ping."""
        if not self.ws:
            return False
        try:
            pong_waiter = await self.ws.ping()
            await asyncio.wait_for(pong_waiter, timeout=5)
            return True
        except Exception:  # noqa: BLE001
            return False

    # ---- LSP protocol ----

    async def initialize(self, configuration_root: Optional[str] = None) -> None:
        """LSP initialize → initialized notification.

        Создаёт persistent workspace dir и передаёт его как rootUri/workspaceFolders.
        bsl-LS требует чтобы анализируемые файлы лежали внутри workspace folder.
        """
        if self._initialized:
            # Если меняется configurationRoot — переинициализация через
            # workspace/didChangeConfiguration.
            if configuration_root and configuration_root != self._configuration_root:
                await self.set_workspace_configuration(configuration_root)
            return

        # Persistent workspace — живёт до shutdown.
        if self._workspace_dir is None:
            self._workspace_dir = Path(tempfile.mkdtemp(prefix="optimyzer-bsl-ls-ws-"))
        root_uri = self._workspace_dir.as_uri()
        await self._request(
            "initialize",
            protocol.lsp_initialize(root_uri, configuration_root),
        )
        await self._notify("initialized", {})
        self._initialized = True
        self._configuration_root = configuration_root

    async def set_workspace_configuration(self, configuration_root: str) -> None:
        """Переключает configurationRoot без полной переинициализации."""
        await self._notify(
            "workspace/didChangeConfiguration",
            protocol.lsp_did_change_configuration(configuration_root),
        )
        self._configuration_root = configuration_root

    async def analyze_sdbl(
        self,
        req: AnalyzeRequest,
        diagnostic_wait_s: float = 10.0,
    ) -> AnalyzeResult:
        """Анализирует SDBL текст через bsl-LS.

        Поток:
            1. Убедиться что initialized (с правильным configurationRoot)
            2. Пишем wrapped BSL в реальный temp .bsl файл (bsl-LS требует file:// URI)
            3. textDocument/didOpen — bsl-LS начнёт анализ
            4. Дождаться publishDiagnostics для этого file_uri
            5. textDocument/didClose + delete temp file
            6. Парсинг + группировка

        Args:
            req: запрос на анализ
            diagnostic_wait_s: сколько ждать диагностики (default 10s).

        Returns:
            AnalyzeResult со списком diagnostics и groups.
        """
        started = time.monotonic()
        if not self._initialized or req.configuration_root != self._configuration_root:
            await self.initialize(req.configuration_root)

        # Готовим wrapped BSL модуль (SDBL inside, с правильным `|` prefix).
        wrapped = _wrap_sdbl_as_bsl_module(req.query_sdbl)

        # Пишем в persistent workspace dir (создан в initialize).
        assert self._workspace_dir is not None, "workspace_dir not initialized"
        tmp_file = self._workspace_dir / f"query-{uuid.uuid4().hex[:12]}.bsl"
        # BSL файлы должны быть UTF-8 BOM (см. CLAUDE.md memory).
        bom = b"\xef\xbb\xbf"
        tmp_file.write_bytes(bom + wrapped.encode("utf-8"))
        file_uri = tmp_file.as_uri()
        try:
            self._diagnostics_buffer[file_uri] = []
            self._diagnostics_received[file_uri] = asyncio.Event()
            await self._notify("textDocument/didOpen", protocol.lsp_did_open(file_uri, wrapped))

            # Ждём publishDiagnostics для этого uri (event-based).
            diagnostics_raw = await self._wait_diagnostics(file_uri, diagnostic_wait_s)

            await self._notify("textDocument/didClose", protocol.lsp_did_close(file_uri))
        finally:
            # Cleanup buffer + event + temp file.
            self._diagnostics_buffer.pop(file_uri, None)
            self._diagnostics_received.pop(file_uri, None)
            try:
                tmp_file.unlink(missing_ok=True)
            except OSError:
                pass

        # Парсинг + группировка.
        diagnostics: list[Diagnostic] = [
            parse_lsp_diagnostic(d, sdbl_text=wrapped) for d in diagnostics_raw
        ]
        # Фильтруем по enabled_rules если передан.
        if req.enabled_rules is not None:
            allow = set(req.enabled_rules)
            diagnostics = [d for d in diagnostics if d.code in allow]
        grouped = group_overlapping(diagnostics)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        return AnalyzeResult(
            diagnostics=diagnostics,
            grouped=grouped,
            parse_success=not any(d.code == "QueryParseError" for d in diagnostics),
            analysis_duration_ms=elapsed_ms,
        )

    async def shutdown(self) -> None:
        """LSP shutdown → exit + cleanup workspace."""
        if self.ws and self._initialized:
            try:
                await self._request("shutdown", {}, timeout_s=5.0)
                await self._notify("exit", {})
            except Exception:  # noqa: BLE001
                pass
        await self.disconnect()
        # Удаляем persistent workspace dir.
        if self._workspace_dir is not None:
            import shutil

            try:
                shutil.rmtree(self._workspace_dir, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass
            self._workspace_dir = None

    # ---- internal: JSON-RPC + reader loop ----

    async def _request(
        self, method: str, params: dict, timeout_s: float = 30.0
    ) -> Any:
        """Отправляет request, ждёт response с тем же id."""
        if not self.ws:
            raise RuntimeError("WebSocket не подключён")
        self._request_id += 1
        rid = self._request_id
        fut: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut
        msg = protocol.make_request(rid, method, params)
        await self.ws.send(json.dumps(msg, ensure_ascii=False))
        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        finally:
            self._pending.pop(rid, None)

    async def _notify(self, method: str, params: dict) -> None:
        if not self.ws:
            raise RuntimeError("WebSocket не подключён")
        msg = protocol.make_notification(method, params)
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _wait_diagnostics(self, file_uri: str, timeout_s: float) -> list[dict]:
        """Ждёт publishDiagnostics для file_uri.

        Event-based: bsl-LS присылает publishDiagnostics РОВНО ОДИН РАЗ после
        анализа файла (даже если 0 diagnostics — пустой список). Мы ставим
        Event при receive и ждём его с таймаутом.

        Дополнительно: после первого notification ждём 200ms на случай
        дополнительных (защита от LSP race conditions).
        """
        event = self._diagnostics_received.get(file_uri)
        if event is None:
            return []
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            logger.warning("bsl-LS не прислал publishDiagnostics за %ss", timeout_s)
            return list(self._diagnostics_buffer.get(file_uri, []))
        # Дополнительные 200ms — на случай если будет ещё одна нотификация.
        await asyncio.sleep(0.2)
        return list(self._diagnostics_buffer.get(file_uri, []))

    async def _reader_loop(self) -> None:
        """Читает сообщения из WebSocket и диспатчит их."""
        assert self.ws is not None
        try:
            async for raw_msg in self.ws:
                try:
                    if isinstance(raw_msg, bytes):
                        raw_msg = raw_msg.decode("utf-8")
                    msg = json.loads(raw_msg)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Невалидный JSON от bsl-LS: %s", e)
                    continue
                self._dispatch(msg)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning("WebSocket reader loop упал: %s", e)

    def _dispatch(self, msg: dict) -> None:
        """Диспатчит response/notification/server-request."""
        if protocol.is_response(msg):
            rid = msg["id"]
            fut = self._pending.get(rid)
            if fut and not fut.done():
                if "error" in msg:
                    fut.set_exception(RuntimeError(str(msg["error"])))
                else:
                    fut.set_result(msg.get("result"))
            return

        if protocol.is_notification(msg):
            method = msg.get("method")
            params = msg.get("params", {})
            if method == "textDocument/publishDiagnostics":
                uri = params.get("uri", "")
                diags = params.get("diagnostics", [])
                if uri in self._diagnostics_buffer:
                    self._diagnostics_buffer[uri] = diags
                # Сигналим waiter что diagnostics получены (даже пустой список).
                ev = self._diagnostics_received.get(uri)
                if ev is not None:
                    ev.set()
            elif method == "window/logMessage":
                level = params.get("type", 4)
                text = params.get("message", "")
                logger.log(_lsp_log_level_to_python(level), "[bsl-LS] %s", text)
            # Иначе игнорируем (например window/showMessage).
            return

        if protocol.is_server_request(msg):
            # bsl-LS может слать workspace/configuration request — отвечаем
            # пустыми settings (мы передаём всё через initializationOptions).
            method = msg.get("method")
            rid = msg.get("id")
            if method == "workspace/configuration":
                # items: список запрашиваемых конфигов
                items = msg.get("params", {}).get("items", [])
                result = [{} for _ in items]
                response = {"jsonrpc": "2.0", "id": rid, "result": result}
                if self.ws:
                    asyncio.create_task(
                        self.ws.send(json.dumps(response, ensure_ascii=False))
                    )
            elif rid is not None and self.ws:
                # Отвечаем method not found.
                response = {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32601, "message": "method not found"},
                }
                asyncio.create_task(self.ws.send(json.dumps(response, ensure_ascii=False)))


def _lsp_log_level_to_python(lsp_level: int) -> int:
    """LSP MessageType → logging level."""
    import logging as _l

    return {
        1: _l.ERROR,  # Error
        2: _l.WARNING,  # Warning
        3: _l.INFO,  # Info
        4: _l.DEBUG,  # Log
    }.get(lsp_level, _l.DEBUG)


def _wrap_sdbl_as_bsl_module(sdbl: str) -> str:
    """Оборачивает голый SDBL в BSL-модуль чтобы bsl-LS его проанализировал.

    bsl-LS анализирует BSL файлы и находит SDBL внутри строковых литералов
    (через `Запрос.Текст = "..."`). Голый SDBL не анализируется.

    BSL multi-line string syntax: каждая строка после первой должна
    начинаться с `|`. Без этого парсер BSL даёт ParseError.
    """
    # Escape кавычек в SDBL (BSL escape — удвоение).
    escaped = sdbl.replace('"', '""')
    # Многострочный литерал — добавляем `|` к каждой строке кроме первой.
    lines = escaped.split("\n")
    if len(lines) == 1:
        bsl_string = f'"{lines[0]}"'
    else:
        first, *rest = lines
        formatted = [f'"{first}"'] + [f'\t\t|"{line}"' for line in rest[:-1]]
        # Последняя строка получает закрывающую кавычку, остальные — без неё.
        # На самом деле в BSL multiline: вся строка одна, продолжается `|`.
        # Правильный формат:
        #   "первая
        #   |вторая
        #   |третья"
        formatted = [f'"{first}']
        for line in rest:
            formatted.append(f"\t\t|{line}")
        formatted[-1] = formatted[-1] + '"'
        bsl_string = "\n".join(formatted)
    return (
        "Процедура АнализЗапроса() Экспорт\n"
        "\tЗапрос = Новый Запрос;\n"
        "\tЗапрос.Текст =\n"
        f"\t\t{bsl_string};\n"
        "КонецПроцедуры\n"
    )


# ---- module-level singleton ----


async def get_client(
    explicit_java: Optional[Path] = None,
    explicit_jar: Optional[Path] = None,
    configuration_root: Optional[str] = None,
) -> BslLsClient:
    """Возвращает singleton BslLsClient. Lazy-start JVM при первом вызове.

    Если JVM упал между вызовами — auto-restart.

    Args:
        explicit_java: переопределить путь к java.exe (для тестов).
        explicit_jar: переопределить путь к jar (для тестов).
        configuration_root: путь к XML конфигурации 1С — если меняется,
            client переинициализируется через workspace/didChangeConfiguration.
    """
    global _client, _lifecycle  # noqa: PLW0603
    async with _lock:
        if _client and _lifecycle and _lifecycle.is_running():
            if await _client.is_alive():
                if configuration_root != _client._configuration_root:
                    await _client.initialize(configuration_root)
                return _client
            # WebSocket мёртв но процесс жив — пересоединяемся.
            await _client.disconnect()
            await _client.connect()
            await _client.initialize(configuration_root)
            return _client

        # Cold start: жгём всё что было и запускаем заново.
        if _client:
            try:
                await _client.shutdown()
            except Exception:  # noqa: BLE001
                pass
        if _lifecycle:
            try:
                await _lifecycle.stop()
            except Exception:  # noqa: BLE001
                pass

        paths: BslLsPaths = get_paths(explicit_java=explicit_java, explicit_jar=explicit_jar)
        _lifecycle = BslLsLifecycle(paths)
        await _lifecycle.start()
        _client = BslLsClient(_lifecycle)
        await _client.connect()
        await _client.initialize(configuration_root)
        # Register atexit для graceful shutdown.
        atexit.register(_atexit_handler)
        return _client


async def shutdown_client() -> None:
    """Graceful shutdown singleton'а. Вызывается из atexit и в тестах."""
    global _client, _lifecycle  # noqa: PLW0603
    if _client:
        try:
            await _client.shutdown()
        except Exception:  # noqa: BLE001
            pass
        _client = None
    if _lifecycle:
        try:
            await _lifecycle.stop()
        except Exception:  # noqa: BLE001
            pass
        _lifecycle = None


def _atexit_handler() -> None:
    """Sync wrapper для atexit (нельзя async)."""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(shutdown_client())
        loop.close()
    except Exception:  # noqa: BLE001
        pass
