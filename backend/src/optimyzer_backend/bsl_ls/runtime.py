"""Async runtime для bsl-LS клиента (Sprint 6 Phase C).

backend RPC дispatcher — синхронный, но bsl-LS клиент — async (websockets).
Мостим их через persistent event loop в отдельном thread.

Использование (из sync RPC):
    from optimyzer_backend.bsl_ls.runtime import run_async, get_bsl_client_sync

    client = get_bsl_client_sync()  # singleton, lazy-start
    result = run_async(client.analyze_sdbl(req))

Lifecycle: loop стартует при первом вызове, живёт до atexit. При завершении
делает graceful shutdown_client + закрывает loop.
"""

from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
import logging
import threading
from typing import Any, Awaitable, Optional, TypeVar

from .client import BslLsClient, get_client, shutdown_client

logger = logging.getLogger(__name__)

T = TypeVar("T")

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_ready = threading.Event()
_lock = threading.Lock()


def _start_loop() -> None:
    """Спавнит фоновый thread с persistent event loop."""
    global _loop, _loop_thread
    with _lock:
        if _loop is not None:
            return

        def _run() -> None:
            global _loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _loop = loop
            _loop_ready.set()
            try:
                loop.run_forever()
            finally:
                loop.close()

        _loop_thread = threading.Thread(
            target=_run, name="bsl-ls-runtime", daemon=True
        )
        _loop_thread.start()
        _loop_ready.wait(timeout=5)
        if _loop is None:
            raise RuntimeError("bsl-ls runtime loop не стартовал")
        atexit.register(_shutdown_loop)


def run_async(coro: Awaitable[T], timeout: Optional[float] = 60.0) -> T:
    """Выполняет coroutine в фоновом loop, блокирующе ждёт результат.

    Args:
        coro: coroutine для выполнения.
        timeout: max сек ожидания, None = бесконечно.

    Returns:
        Результат coroutine.

    Raises:
        TimeoutError если не успели за timeout.
        Любые exceptions из coro прокидываются.
    """
    _start_loop()
    assert _loop is not None
    fut = asyncio.run_coroutine_threadsafe(coro, _loop)
    try:
        return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        fut.cancel()
        raise TimeoutError(f"bsl-LS coroutine не завершилась за {timeout}s")


def get_bsl_client_sync(configuration_root: Optional[str] = None) -> BslLsClient:
    """Sync wrapper над async get_client().

    Args:
        configuration_root: путь к XML конфигурации 1С (для семантического анализа).

    Returns:
        BslLsClient singleton.
    """
    return run_async(get_client(configuration_root=configuration_root), timeout=120)


def _shutdown_loop() -> None:
    """atexit: graceful shutdown bsl-LS + остановка loop."""
    global _loop, _loop_thread
    if _loop is None:
        return
    try:
        fut = asyncio.run_coroutine_threadsafe(shutdown_client(), _loop)
        try:
            fut.result(timeout=15)
        except Exception:  # noqa: BLE001
            pass
        _loop.call_soon_threadsafe(_loop.stop)
        if _loop_thread:
            _loop_thread.join(timeout=5)
    except Exception:  # noqa: BLE001
        pass
    finally:
        _loop = None
        _loop_thread = None
