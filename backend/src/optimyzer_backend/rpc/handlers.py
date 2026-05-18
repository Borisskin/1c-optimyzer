"""RPC-методы. Регистрируются через @rpc при импорте модуля."""

from __future__ import annotations

import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend import __version__
from optimyzer_backend.ingest import (
    FolderSource,
    IngestProgress,
    LogFile,
    LogSource,
    ProgressReporter,
    ZipSource,
    detect_encoding,
)
from optimyzer_backend.parsers.tj_parser import parse_log_file_streaming
from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.storage.duckdb_store import DuckDBStore, default_db_dir
from optimyzer_backend.storage.sqlite_store import SqliteStore

# ---------- In-memory state ----------

_ARCHIVES: dict[str, dict[str, Any]] = {}
_SQLITE: SqliteStore | None = None


def _sqlite() -> SqliteStore:
    global _SQLITE
    if _SQLITE is None:
        _SQLITE = SqliteStore()
    return _SQLITE


# ---------- Health & info ----------


@rpc("ping")
def ping() -> dict[str, Any]:
    return {"status": "ok", "version": __version__}


@rpc("get_app_info")
def get_app_info() -> dict[str, Any]:
    return {
        "backend_version": __version__,
        "python_version": sys.version.split()[0],
        "duckdb_version": duckdb.__version__,
        "platform": sys.platform,
    }


# ---------- Archive lifecycle ----------


def _start_async_ingestion(
    *,
    source_factory,
    archive_id: str,
    public_path: str,
    source_type: str,
) -> dict[str, Any]:
    """Общий entry point для load_directory / load_archive.

    Запускает фоновую обработку в отдельном thread, сразу возвращает state
    со status='discovering'. Прогресс эмитится через ProgressReporter.
    """
    state: dict[str, Any] = {
        "archive_id": archive_id,
        "path": public_path,
        "source_type": source_type,
        "size_bytes": 0,
        "status": "discovering",
        "progress": 0.0,
        "events_parsed": 0,
        "errors": [],
        "started_at": time.time(),
        "store": None,
        "file_count": 0,
        "thread": None,
    }
    _ARCHIVES[archive_id] = state

    thread = threading.Thread(
        target=_run_ingestion,
        kwargs={
            "state": state,
            "source_factory": source_factory,
        },
        daemon=True,
    )
    state["thread"] = thread
    thread.start()
    return _public_state(state)


def _run_ingestion(*, state: dict[str, Any], source_factory) -> None:
    """Фоновый ingestion: discover → parse → index. Прогресс через ProgressReporter."""
    archive_id = state["archive_id"]
    reporter = ProgressReporter(archive_id=archive_id)

    def progress(
        phase: str,
        files_done: int,
        files_total: int,
        bytes_done: int,
        bytes_total: int,
        events_inserted: int,
        current_file: str | None,
        force: bool = False,
        error_message: str | None = None,
    ) -> None:
        reporter.emit(
            IngestProgress(
                phase=phase,  # type: ignore[arg-type]
                files_done=files_done,
                files_total=files_total,
                bytes_done=bytes_done,
                bytes_total=bytes_total,
                events_inserted=events_inserted,
                current_file=current_file,
                error_message=error_message,
            ),
            force=force,
        )

    try:
        # === Discovery ===
        progress("discovering", 0, 0, 0, 0, 0, None, force=True)
        source: LogSource = source_factory()
        log_files: list[LogFile] = source.discover()
        bytes_total = sum(lf.size_bytes for lf in log_files)

        state["file_count"] = len(log_files)
        state["size_bytes"] = bytes_total

        if not log_files:
            state["status"] = "error"
            state["errors"].append("Лог-файлы не найдены в указанной папке")
            progress(
                "error", 0, 0, 0, 0, 0, None,
                force=True,
                error_message="Лог-файлы не найдены в указанной папке",
            )
            return

        # === Parsing + insertion ===
        state["status"] = "parsing"
        store = DuckDBStore(archive_id)
        store.open()
        state["store"] = store

        bytes_done = 0
        events_inserted = 0
        # In-file emit каждые N событий — чтобы UI-счётчик не замирал на
        # больших файлах. Throttle в ProgressReporter (250мс) защищает от флуда
        # при быстром парсинге.
        EMIT_EVERY_EVENTS = 1000

        with store.appender() as appender:
            for idx, lf in enumerate(log_files):
                encoding = detect_encoding(lf.path)
                events_in_file = 0
                try:
                    for event in parse_log_file_streaming(source, lf, encoding=encoding):
                        appender.append_event(event)
                        events_inserted += 1
                        events_in_file += 1
                        if events_in_file % EMIT_EVERY_EVENTS == 0:
                            state["events_parsed"] = events_inserted
                            progress(
                                "parsing",
                                files_done=idx,
                                files_total=len(log_files),
                                bytes_done=bytes_done,
                                bytes_total=bytes_total,
                                events_inserted=events_inserted,
                                current_file=lf.relative_path,
                            )
                except Exception as exc:
                    state["errors"].append(
                        f"{lf.relative_path}: {type(exc).__name__}: {exc}"
                    )

                bytes_done += lf.size_bytes
                state["events_parsed"] = events_inserted
                state["progress"] = bytes_done / max(bytes_total, 1)
                progress(
                    "parsing",
                    files_done=idx + 1,
                    files_total=len(log_files),
                    bytes_done=bytes_done,
                    bytes_total=bytes_total,
                    events_inserted=events_inserted,
                    current_file=lf.relative_path,
                )

        # === Indexing ===
        state["status"] = "indexing"
        progress(
            "indexing",
            files_done=len(log_files),
            files_total=len(log_files),
            bytes_done=bytes_total,
            bytes_total=bytes_total,
            events_inserted=events_inserted,
            current_file=None,
            force=True,
        )
        store.create_indexes()

        # === Done ===
        elapsed = time.time() - state["started_at"]
        state["status"] = "ready"
        state["progress"] = 1.0
        state["parsing_time_sec"] = elapsed
        state["loaded_at"] = datetime.utcnow().isoformat()

        _sqlite().upsert_recent_archive(
            archive_id=archive_id,
            path=state["path"],
            size_bytes=bytes_total,
            events_count=events_inserted,
            parsing_time_sec=elapsed,
        )

        progress(
            "done",
            files_done=len(log_files),
            files_total=len(log_files),
            bytes_done=bytes_total,
            bytes_total=bytes_total,
            events_inserted=events_inserted,
            current_file=None,
            force=True,
        )
    except Exception as exc:
        state["status"] = "error"
        state["errors"].append(f"{type(exc).__name__}: {exc}")
        progress(
            "error",
            files_done=0,
            files_total=state.get("file_count", 0),
            bytes_done=0,
            bytes_total=state.get("size_bytes", 0),
            events_inserted=state.get("events_parsed", 0),
            current_file=None,
            force=True,
            error_message=f"{type(exc).__name__}: {exc}",
        )
        # Cleanup partial DuckDB file
        try:
            DuckDBStore.delete_db_file(archive_id)
        except Exception:
            pass


@rpc("load_directory")
def load_directory(path: str) -> dict[str, Any]:
    """Primary способ загрузки в Module 1 — рекурсивный обход папки.

    Запускает background ingestion. Возвращает state со status='discovering'
    сразу, дальнейший прогресс эмитится через ``progress`` notifications.
    """
    folder = Path(path)
    if not folder.exists():
        raise FileNotFoundError(f"Папка не найдена: {path}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Не папка: {path}")

    archive_id = uuid.uuid4().hex
    return _start_async_ingestion(
        source_factory=lambda: FolderSource(folder),
        archive_id=archive_id,
        public_path=str(folder),
        source_type="folder",
    )


@rpc("load_archive")
def load_archive(path: str) -> dict[str, Any]:
    """Legacy ZIP entry point (ADR-010) — оставлен для backwards compat с Sprint 0 fixtures.

    UI Module 1 этим путём не пользуется; tests используют ZipSource напрямую
    либо через этот RPC.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Archive not found: {path}")

    archive_id = uuid.uuid4().hex
    return _start_async_ingestion(
        source_factory=lambda: ZipSource(p, archive_id=archive_id),
        archive_id=archive_id,
        public_path=str(p),
        source_type="archive",
    )


@rpc("cancel_ingestion")
def cancel_ingestion(archive_id: str) -> dict[str, Any]:
    """Stub: Sprint 2 будет настоящий cancellation token (ADR-012 deferred).

    Sprint 1 — RPC зарегистрирован, кнопка в UI disabled с tooltip.
    """
    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {"ok": False, "reason": "unknown_archive"}
    return {"ok": False, "reason": "not_implemented_until_sprint_2"}


@rpc("get_archive_status")
def get_archive_status(archive_id: str) -> dict[str, Any]:
    state = _ARCHIVES.get(archive_id)
    if state is None:
        raise ValueError(f"Unknown archive_id: {archive_id}")
    return _public_state(state)


@rpc("wait_for_archive")
def wait_for_archive(archive_id: str, timeout_sec: float = 600.0) -> dict[str, Any]:
    """Блокирующий wait — используется только в тестах / e2e flows.

    UI пользуется push-notifications, не этим методом.
    """
    state = _ARCHIVES.get(archive_id)
    if state is None:
        raise ValueError(f"Unknown archive_id: {archive_id}")
    thread: threading.Thread | None = state.get("thread")
    if thread is not None:
        thread.join(timeout=timeout_sec)
    return _public_state(state)


@rpc("list_recent_archives")
def list_recent_archives() -> list[dict[str, Any]]:
    return _sqlite().list_recent_archives(limit=20)


@rpc("list_stored_archives")
def list_stored_archives() -> dict[str, Any]:
    """Список архивов в SQLite + реальный размер .duckdb на диске.

    Возвращает {archives: [...], total_db_size_bytes: int}. Архивы без файла
    на диске (например, был удалён вручную) включаются с db_size_bytes=0
    и is_orphan=True.
    """
    records = _sqlite().list_recent_archives(limit=100)
    db_dir = default_db_dir()
    total_size = 0
    archives: list[dict[str, Any]] = []
    for rec in records:
        archive_id = rec["archive_id"]
        db_path = db_dir / f"{archive_id}.duckdb"
        try:
            size = db_path.stat().st_size
            is_orphan = False
        except FileNotFoundError:
            size = 0
            is_orphan = True
        total_size += size
        archives.append({
            **rec,
            "db_size_bytes": size,
            "is_loaded": archive_id in _ARCHIVES,
            "is_orphan": is_orphan,
        })
    return {"archives": archives, "total_db_size_bytes": total_size}


@rpc("delete_archive")
def delete_archive(archive_id: str) -> dict[str, Any]:
    """Полное удаление архива: in-memory state + .duckdb на диске + запись в SQLite."""
    state = _ARCHIVES.pop(archive_id, None)
    if state is not None:
        store: DuckDBStore | None = state.get("store")
        if store:
            try:
                store.close()
            except Exception:
                pass
    DuckDBStore.delete_db_file(archive_id)
    sqlite_removed = _sqlite().delete_recent_archive(archive_id)
    return {"ok": True, "sqlite_removed": sqlite_removed, "was_loaded": state is not None}


@rpc("delete_all_archives")
def delete_all_archives() -> dict[str, Any]:
    """Wipe всего хранилища: закрывает соединения, удаляет .duckdb файлы, чистит SQLite."""
    closed = 0
    for archive_id, state in list(_ARCHIVES.items()):
        store: DuckDBStore | None = state.get("store")
        if store:
            try:
                store.close()
                closed += 1
            except Exception:
                pass
        _ARCHIVES.pop(archive_id, None)

    db_dir = default_db_dir()
    files_deleted = 0
    if db_dir.exists():
        for f in db_dir.glob("*.duckdb"):
            try:
                f.unlink()
                files_deleted += 1
            except OSError:
                pass

    sqlite_removed = _sqlite().delete_all_recent_archives()
    return {
        "ok": True,
        "closed": closed,
        "files_deleted": files_deleted,
        "sqlite_removed": sqlite_removed,
    }


@rpc("unload_archive")
def unload_archive(archive_id: str) -> dict[str, Any]:
    state = _ARCHIVES.pop(archive_id, None)
    if state is None:
        return {"ok": False, "reason": "not_loaded"}
    store: DuckDBStore | None = state.get("store")
    if store:
        store.close()
    return {"ok": True}


# ---------- Queries (preset) ----------


@rpc("query_events_preset")
def query_events_preset(archive_id: str, preset: str, limit: int = 100) -> dict[str, Any]:
    state = _ARCHIVES.get(archive_id)
    if state is None or state.get("status") != "ready":
        raise ValueError(f"Archive {archive_id} not ready")
    store: DuckDBStore = state["store"]
    t0 = time.time()
    columns, rows = store.run_preset(preset, limit=limit)
    return {
        "columns": [{"name": n, "type": t} for n, t in columns],
        "rows": rows,
        "total_count": len(rows),
        "truncated": len(rows) >= limit,
        "executed_in_ms": (time.time() - t0) * 1000,
    }


@rpc("get_storage_stats")
def get_storage_stats(archive_id: str) -> dict[str, Any]:
    state = _ARCHIVES.get(archive_id)
    if state is None:
        raise ValueError(f"Unknown archive_id: {archive_id}")
    store: DuckDBStore | None = state.get("store")
    events_count = store.count_events() if store else 0
    db_size = store.db_size_bytes() if store else 0
    parsing_time = state.get("parsing_time_sec") or 0.001
    eps = events_count / parsing_time if parsing_time else 0
    return {
        "events_count": events_count,
        "db_size_bytes": db_size,
        "parsing_speed_eps": eps,
        "archive_metadata": {
            "path": state["path"],
            "size_bytes": state["size_bytes"],
            "file_count": state.get("file_count"),
            "loaded_at": state.get("loaded_at"),
        },
    }


# ---------- helpers ----------


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "archive_id": state["archive_id"],
        "path": state["path"],
        "source_type": state.get("source_type", "archive"),
        "size_bytes": state["size_bytes"],
        "file_count": state.get("file_count", 0),
        "status": state["status"],
        "progress": round(state.get("progress", 0.0), 3),
        "events_parsed": state.get("events_parsed", 0),
        "errors": list(state.get("errors", []))[:20],
        "parsing_time_sec": state.get("parsing_time_sec"),
        "loaded_at": state.get("loaded_at"),
    }
