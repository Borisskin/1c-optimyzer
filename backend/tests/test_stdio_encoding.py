"""Регресс: sidecar должен писать ответы в stdout как UTF-8 независимо от кодировки
консоли Windows (cp1251/cp866). Символ '×' (U+00D7) и кириллица не входят в cp1251 —
раньше это роняло процесс с UnicodeEncodeError в цикле перезапусков.
"""

from __future__ import annotations

import io
import json

from optimyzer_backend.__main__ import _force_utf8_stdio, _write


def _cp1251_stdout(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1251", newline="")
    monkeypatch.setattr("sys.stdout", stream)
    return raw


def test_write_non_cp1251_chars_does_not_crash(monkeypatch):
    raw = _cp1251_stdout(monkeypatch)
    _force_utf8_stdio()  # как в main(): переводим stdio на UTF-8

    payload = {"jsonrpc": "2.0", "id": 1, "result": {"sql": "SELECT 2 × 2 -- тест кириллица"}}
    _write(payload)  # не должно бросать UnicodeEncodeError

    line = raw.getvalue().decode("utf-8").strip()
    assert json.loads(line) == payload


def test_write_falls_back_to_buffer_without_reconfigure(monkeypatch):
    """Даже если stdio не перевели на UTF-8, _write не должен падать — есть страховка
    через запись UTF-8 байтов в буфер напрямую."""
    raw = _cp1251_stdout(monkeypatch)  # НЕ вызываем _force_utf8_stdio

    payload = {"jsonrpc": "2.0", "id": 2, "result": {"v": "×—°"}}
    _write(payload)

    line = raw.getvalue().decode("utf-8").strip()
    assert json.loads(line) == payload
