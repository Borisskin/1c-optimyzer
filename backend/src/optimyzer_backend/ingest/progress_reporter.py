"""JSON-RPC notifications для прогресса ingestion (ADR-012).

Notification format (без id, fire-and-forget):
    {"jsonrpc":"2.0","method":"progress","params":{archive_id, phase, ...}}

Throttle до 4 emit/sec — иначе на высоком парсинг-rate stdout захлёбывается
и frontend получает stale UI updates.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import asdict
from typing import Any

from .source import IngestProgress


class ProgressReporter:
    """Throttled JSON-RPC notifications fire-and-forget."""

    def __init__(self, archive_id: str, throttle_ms: int = 250, sink: Any = None):
        self.archive_id = archive_id
        self.throttle_ms = throttle_ms
        self._last_emit = 0.0
        # sink: object with .write(str) + .flush() — для тестов; default = sys.stdout
        self._sink = sink if sink is not None else sys.stdout
        self._lock = threading.Lock()

    def emit(self, progress: IngestProgress, force: bool = False) -> None:
        now = time.monotonic() * 1000
        with self._lock:
            if not force and (now - self._last_emit) < self.throttle_ms:
                return
            self._last_emit = now

        payload = asdict(progress)
        payload["archive_id"] = self.archive_id
        notification = {
            "jsonrpc": "2.0",
            "method": "progress",
            "params": payload,
        }
        # ensure_ascii=False — русские строки в payload не должны кодироваться \uXXXX
        self._sink.write(json.dumps(notification, ensure_ascii=False) + "\n")
        self._sink.flush()
