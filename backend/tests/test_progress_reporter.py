"""Тесты ProgressReporter — throttled JSON-RPC notifications (ADR-012)."""

from __future__ import annotations

import io
import json
import time

from optimyzer_backend.ingest.progress_reporter import ProgressReporter
from optimyzer_backend.ingest.source import IngestProgress


def _progress(phase: str = "parsing", bytes_done: int = 100, events: int = 10) -> IngestProgress:
    return IngestProgress(
        phase=phase,  # type: ignore[arg-type]
        files_done=1,
        files_total=10,
        bytes_done=bytes_done,
        bytes_total=1000,
        events_inserted=events,
        current_file="rphost_1/26051813.log",
    )


def test_emit_writes_jsonrpc_notification() -> None:
    sink = io.StringIO()
    reporter = ProgressReporter(archive_id="abc123", throttle_ms=0, sink=sink)
    reporter.emit(_progress(), force=True)

    output = sink.getvalue().strip()
    msg = json.loads(output)
    assert msg["jsonrpc"] == "2.0"
    assert msg["method"] == "progress"
    assert "id" not in msg  # notification без id
    assert msg["params"]["archive_id"] == "abc123"
    assert msg["params"]["phase"] == "parsing"
    assert msg["params"]["bytes_done"] == 100
    assert msg["params"]["events_inserted"] == 10


def test_throttle_drops_too_frequent_calls() -> None:
    sink = io.StringIO()
    reporter = ProgressReporter(archive_id="x", throttle_ms=250, sink=sink)
    reporter.emit(_progress(bytes_done=10), force=True)
    reporter.emit(_progress(bytes_done=20))  # дропнется по throttle
    reporter.emit(_progress(bytes_done=30))  # дропнется по throttle

    lines = [line for line in sink.getvalue().splitlines() if line]
    assert len(lines) == 1


def test_force_bypasses_throttle() -> None:
    sink = io.StringIO()
    reporter = ProgressReporter(archive_id="x", throttle_ms=10_000, sink=sink)
    reporter.emit(_progress(bytes_done=10), force=True)
    reporter.emit(_progress(bytes_done=20), force=True)
    reporter.emit(_progress(bytes_done=30), force=True)

    lines = [line for line in sink.getvalue().splitlines() if line]
    assert len(lines) == 3


def test_emit_after_throttle_window_passes() -> None:
    sink = io.StringIO()
    reporter = ProgressReporter(archive_id="x", throttle_ms=50, sink=sink)
    reporter.emit(_progress(bytes_done=10), force=True)
    time.sleep(0.08)
    reporter.emit(_progress(bytes_done=20))

    lines = [line for line in sink.getvalue().splitlines() if line]
    assert len(lines) == 2


def test_emit_preserves_cyrillic_payload() -> None:
    sink = io.StringIO()
    reporter = ProgressReporter(archive_id="абв", throttle_ms=0, sink=sink)
    p = IngestProgress(
        phase="error",
        files_done=0,
        files_total=0,
        bytes_done=0,
        bytes_total=0,
        events_inserted=0,
        current_file=None,
        error_message="Лог-файлы не найдены",
    )
    reporter.emit(p, force=True)
    msg = json.loads(sink.getvalue())
    # ensure_ascii=False — кириллица читаемая в выводе
    assert "абв" in sink.getvalue()
    assert msg["params"]["error_message"] == "Лог-файлы не найдены"
