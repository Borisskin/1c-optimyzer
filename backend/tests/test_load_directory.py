"""Тесты RPC load_directory — async ingestion с progress notifications."""

from __future__ import annotations

import time
from pathlib import Path

from optimyzer_backend.rpc import handlers


SAMPLE_EVENT = b"47:02.139004-1,CALL,1,level=INFO,process=rmngr,OSThread=23464\n"


def _make_log(path: Path, copies: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(SAMPLE_EVENT * copies)
    return path


def _wait_ready(archive_id: str, timeout_sec: float = 30.0) -> dict:
    state = handlers.wait_for_archive(archive_id, timeout_sec=timeout_sec)
    return state


def test_load_directory_happy_path(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_28220" / "26051813.log", copies=10)
    _make_log(tmp_path / "rmngr_24128" / "26051813.log", copies=5)

    initial = handlers.load_directory(str(tmp_path))
    assert initial["status"] in ("discovering", "parsing", "ready")
    archive_id = initial["archive_id"]
    assert initial["source_type"] == "folder"

    state = _wait_ready(archive_id)
    assert state["status"] == "ready", state.get("errors")
    assert state["events_parsed"] == 15
    assert state["file_count"] == 2
    handlers.unload_archive(archive_id)


def test_load_directory_rejects_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    try:
        handlers.load_directory(str(missing))
    except FileNotFoundError:
        return
    raise AssertionError("FileNotFoundError expected")


def test_load_directory_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("hello")
    try:
        handlers.load_directory(str(file_path))
    except NotADirectoryError:
        return
    raise AssertionError("NotADirectoryError expected")


def test_load_directory_empty_folder_reports_error(tmp_path: Path) -> None:
    handlers.load_directory(str(tmp_path))
    # дать background треду время дойти до discovery error
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        states = list(handlers._ARCHIVES.values())
        latest = states[-1] if states else None
        if latest and latest["status"] in ("error", "ready"):
            break
        time.sleep(0.05)
    states = list(handlers._ARCHIVES.values())
    latest = states[-1]
    assert latest["status"] == "error"
    assert any("не найдены" in e for e in latest["errors"])
    handlers.unload_archive(latest["archive_id"])


def test_load_directory_persists_process_role(tmp_path: Path) -> None:
    _make_log(tmp_path / "1CV8C_12044" / "26051813.log", copies=3)
    _make_log(tmp_path / "rphost_28220" / "26051813.log", copies=4)

    initial = handlers.load_directory(str(tmp_path))
    archive_id = initial["archive_id"]
    state = _wait_ready(archive_id)
    assert state["status"] == "ready"

    store = state["status"]  # noqa: F841
    # читаем напрямую через DuckDBStore (через handlers preset query)
    from optimyzer_backend.storage.duckdb_store import DuckDBStore

    arch_state = handlers._ARCHIVES[archive_id]
    duck: DuckDBStore = arch_state["store"]
    roles = duck.open().execute(
        "SELECT DISTINCT process_role FROM events ORDER BY process_role"
    ).fetchall()
    assert roles == [("1cv8c",), ("rphost",)]
    handlers.unload_archive(archive_id)


def test_get_archive_status_after_load(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_1" / "26051813.log", copies=1)
    initial = handlers.load_directory(str(tmp_path))
    archive_id = initial["archive_id"]
    _wait_ready(archive_id)

    state = handlers.get_archive_status(archive_id)
    assert state["archive_id"] == archive_id
    assert state["status"] == "ready"
    handlers.unload_archive(archive_id)


def test_cancel_ingestion_stub_returns_not_implemented(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_1" / "26051813.log", copies=1)
    initial = handlers.load_directory(str(tmp_path))
    archive_id = initial["archive_id"]
    _wait_ready(archive_id)
    result = handlers.cancel_ingestion(archive_id)
    assert result["ok"] is False
    assert "sprint_2" in result["reason"]
    handlers.unload_archive(archive_id)


def test_cancel_ingestion_unknown_archive() -> None:
    result = handlers.cancel_ingestion("nonexistent")
    assert result["ok"] is False


def test_open_stored_archive_reattach_after_unload(tmp_path: Path) -> None:
    """Симулирует перезапуск приложения: load → unload → open_stored_archive.

    После unload архив остаётся в SQLite и .duckdb на диске, но не в
    _ARCHIVES. open_stored_archive должен вернуть его обратно в state со
    status='ready', с восстановленным DuckDBStore, чтобы SQL запросы
    работали без повторного парсинга.
    """
    _make_log(tmp_path / "rphost_28220" / "26051813.log", copies=10)

    initial = handlers.load_directory(str(tmp_path))
    archive_id = initial["archive_id"]
    state = _wait_ready(archive_id)
    assert state["status"] == "ready"
    assert state["events_parsed"] == 10

    # Закрываем (симулируем перезапуск приложения)
    handlers.unload_archive(archive_id)
    assert archive_id not in handlers._ARCHIVES

    # Reattach
    reopened = handlers.open_stored_archive(archive_id)
    assert reopened["archive_id"] == archive_id
    assert reopened["status"] == "ready"
    assert reopened["events_parsed"] == 10
    assert reopened["source_type"] == "folder"
    assert archive_id in handlers._ARCHIVES

    # Idempotent — повторный open возвращает тот же state
    reopened_again = handlers.open_stored_archive(archive_id)
    assert reopened_again["archive_id"] == archive_id

    # И теперь SQL Engine должен видеть данные через cursor от живого store
    from optimyzer_backend.sql.executor import SQLExecutor
    with SQLExecutor(archive_id) as ex:
        result = ex.execute("SELECT COUNT(*) AS n FROM events")
    assert result["rows"][0][0] == 10

    handlers.unload_archive(archive_id)


def test_open_stored_archive_unknown_id_raises() -> None:
    try:
        handlers.open_stored_archive("definitely_not_an_archive_id")
    except ValueError as exc:
        assert "не найден" in str(exc)
        return
    raise AssertionError("ValueError expected")
    assert result["reason"] == "unknown_archive"
