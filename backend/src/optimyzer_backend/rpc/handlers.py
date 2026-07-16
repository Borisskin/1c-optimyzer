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
        "cancel_event": threading.Event(),
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


class _IngestionCancelled(Exception):
    """Поднимается из ingestion loop при срабатывании cancel_event.

    Обрабатывается в _run_ingestion: устанавливает status='cancelled',
    закрывает store, удаляет partial .duckdb файл с диска.
    """


def _no_logs_message(source: Any) -> str:
    """Человеческое объяснение, почему discovery ничего не дал.

    Голое «Лог-файлы не найдены» вводит в заблуждение, когда папка выбрана
    верно, но ТЖ ничего не записал: logcfg настроен на события, которых за
    период не было, — файлы создаются пустыми и отбраковываются. Пользователи
    в этом случае думают, что сломалось приложение, и переустанавливают его.
    """
    stats = getattr(source, "scan_stats", None) or {}
    empty = stats.get("empty", 0)
    not_tj = stats.get("not_tj", 0)
    matched = stats.get("name_matched", 0)

    if matched and empty == matched:
        return (
            f"Найдено файлов ТЖ: {matched}, но все они пустые. "
            "Технологический журнал создал файлы, но не записал ни одного события — "
            "скорее всего, в logcfg.xml заданы события, которых за этот период не было "
            "(например, только долгие запросы к СУБД). Проверьте настройки logcfg.xml "
            "и период сбора."
        )
    if matched and empty:
        return (
            f"Подходящих лог-файлов не найдено: из {matched} файлов ТЖ "
            f"{empty} пустых, {not_tj} не похожи на технологический журнал. "
            "Проверьте logcfg.xml и период сбора."
        )
    if not_tj:
        return (
            f"В папке найдено файлов с именем вида ГГММДДЧЧ.log: {matched}, "
            "но они не похожи на технологический журнал (не распознан формат событий). "
            "Убедитесь, что указана папка с логами ТЖ."
        )
    return (
        "Лог-файлы не найдены в указанной папке. Ожидаются файлы вида ГГММДДЧЧ.log "
        "во вложенных папках процессов (например, rphost_1234). "
        "Обычно нужно указать корневую папку каталога ТЖ."
    )


def _run_ingestion(*, state: dict[str, Any], source_factory) -> None:
    """Фоновый ingestion: discover → parse → index. Прогресс через ProgressReporter.

    Поддерживает cooperative cancellation через state['cancel_event']:
    проверяется между файлами и каждые CANCEL_CHECK_EVERY_EVENTS внутри
    больших файлов. При cancel — graceful stop, удаление .duckdb.
    """
    archive_id = state["archive_id"]
    reporter = ProgressReporter(archive_id=archive_id)
    cancel_event: threading.Event = state["cancel_event"]
    CANCEL_CHECK_EVERY_EVENTS = 5000

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
            message = _no_logs_message(source)
            state["status"] = "error"
            state["errors"].append(message)
            progress(
                "error", 0, 0, 0, 0, 0, None,
                force=True,
                error_message=message,
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
                if cancel_event.is_set():
                    raise _IngestionCancelled()
                encoding = detect_encoding(lf.path)
                events_in_file = 0
                try:
                    for event in parse_log_file_streaming(source, lf, encoding=encoding):
                        appender.append_event(event)
                        events_inserted += 1
                        events_in_file += 1
                        if events_in_file % CANCEL_CHECK_EVERY_EVENTS == 0 and cancel_event.is_set():
                            raise _IngestionCancelled()
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
                except _IngestionCancelled:
                    raise
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
    except _IngestionCancelled:
        state["status"] = "cancelled"
        state["errors"].append("Загрузка отменена пользователем")
        # Закрываем store перед удалением .duckdb — Windows держит lock.
        store_ref: DuckDBStore | None = state.get("store")
        if store_ref is not None:
            try:
                store_ref.close()
            except Exception:
                pass
            state["store"] = None
        try:
            DuckDBStore.delete_db_file(archive_id)
        except Exception:
            pass
        progress(
            "cancelled",
            files_done=0,
            files_total=state.get("file_count", 0),
            bytes_done=0,
            bytes_total=state.get("size_bytes", 0),
            events_inserted=state.get("events_parsed", 0),
            current_file=None,
            force=True,
            error_message="Загрузка отменена пользователем",
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


def _stable_archive_id_for_path(public_path: str) -> str:
    """Возвращает archive_id для пути: переиспользует ID если такой path
    уже был загружен раньше, иначе генерирует новый UUID.

    Это нужно чтобы ключи AI-кеша (sha256(archive_id|kind|target)) переживали
    повторную загрузку одной и той же папки. Без этого каждый reload папки
    делал старые AI-объяснения недоступными: запись в explainer_cache.db
    оставалась, но привязана к UUID который больше нигде не используется.

    Side-effects: если ID переиспользуется и старый .duckdb файл существует,
    он удаляется — данные будут перепарсены с нуля (содержимое папки могло
    измениться).
    """
    existing = _sqlite().find_archive_id_by_path(public_path)
    if existing is None:
        return uuid.uuid4().hex
    # Перед re-ingest нужно удалить старый .duckdb (если он есть на диске).
    # Если он сейчас открыт другим архивом из _ARCHIVES — закрываем сначала.
    open_state = _ARCHIVES.pop(existing, None)
    if open_state is not None:
        store = open_state.get("store")
        if store is not None:
            try:
                store.close()
            except Exception:
                pass
    try:
        DuckDBStore.delete_db_file(existing)
    except Exception:
        pass
    return existing


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

    public_path = str(folder)
    archive_id = _stable_archive_id_for_path(public_path)
    return _start_async_ingestion(
        source_factory=lambda: FolderSource(folder),
        archive_id=archive_id,
        public_path=public_path,
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

    public_path = str(p)
    archive_id = _stable_archive_id_for_path(public_path)
    return _start_async_ingestion(
        source_factory=lambda: ZipSource(p, archive_id=archive_id),
        archive_id=archive_id,
        public_path=public_path,
        source_type="archive",
    )


@rpc("cancel_ingestion")
def cancel_ingestion(archive_id: str) -> dict[str, Any]:
    """Cooperative cancel: устанавливает cancel_event, ingestion thread
    его подхватывает между файлами / каждые 5000 событий, raises
    _IngestionCancelled, делает graceful cleanup (close store + delete db).

    Возвращает {ok: True, status: 'cancelling'} даже если thread ещё
    работает — UI узнает о финальном 'cancelled' через progress event.
    """
    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {"ok": False, "reason": "unknown_archive"}
    cancel_event: threading.Event | None = state.get("cancel_event")
    if cancel_event is None:
        return {"ok": False, "reason": "no_cancel_event"}
    if state.get("status") in ("ready", "error", "cancelled"):
        return {"ok": False, "reason": "already_finished", "status": state["status"]}
    cancel_event.set()
    return {"ok": True, "status": "cancelling"}


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


@rpc("open_stored_archive")
def open_stored_archive(archive_id: str) -> dict[str, Any]:
    """Reattach уже-распарсенный архив из SQLite-истории к текущей session.

    Без этого после перезапуска приложения пользователю пришлось бы заново
    парсить ту же папку с логами. Здесь же мы только открываем существующий
    .duckdb файл (моментально) и регистрируем archive в in-memory state,
    чтобы SQL Console и view-экраны могли с ним работать.

    Idempotent: если архив уже загружен — возвращает текущий public state.
    """
    existing = _ARCHIVES.get(archive_id)
    if existing is not None:
        return _public_state(existing)

    records = _sqlite().list_recent_archives(limit=200)
    record = next((r for r in records if r["archive_id"] == archive_id), None)
    if record is None:
        raise ValueError(f"Архив не найден в истории: {archive_id}")

    db_path = default_db_dir() / f"{archive_id}.duckdb"
    if not db_path.exists():
        raise FileNotFoundError(
            f"База архива не найдена на диске: {db_path.name}. "
            "Возможно, файл был удалён вручную — используйте 'Загрузить новую папку'."
        )

    store = DuckDBStore(archive_id)
    store.open()

    path_str = record["path"]
    source_type = "folder" if Path(path_str).is_dir() else "archive"

    state: dict[str, Any] = {
        "archive_id": archive_id,
        "path": path_str,
        "source_type": source_type,
        "size_bytes": record["size_bytes"] or 0,
        "status": "ready",
        "progress": 1.0,
        "events_parsed": record["events_count"] or 0,
        "errors": [],
        "started_at": time.time(),
        "store": store,
        "file_count": 0,
        "thread": None,
        "parsing_time_sec": record["parsing_time_sec"],
        "loaded_at": record["loaded_at"],
    }
    _ARCHIVES[archive_id] = state
    return _public_state(state)


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


# ---------- Saved queries ----------


@rpc("list_saved_queries")
def list_saved_queries() -> list[dict[str, Any]]:
    return _sqlite().list_saved_queries()


@rpc("save_query")
def save_query(name: str, query: str, description: str | None = None) -> dict[str, Any]:
    if not name.strip():
        raise ValueError("Имя сохранённого запроса не должно быть пустым")
    if not query.strip():
        raise ValueError("Запрос не должен быть пустым")
    new_id = _sqlite().save_query(name=name.strip(), query=query, description=description)
    return {"id": new_id}


@rpc("delete_saved_query")
def delete_saved_query(id: int) -> dict[str, Any]:
    return {"ok": _sqlite().delete_saved_query(id)}


@rpc("rename_saved_query")
def rename_saved_query(id: int, new_name: str) -> dict[str, Any]:
    if not new_name.strip():
        raise ValueError("Новое имя не должно быть пустым")
    return {"ok": _sqlite().rename_saved_query(id, new_name.strip())}


@rpc("mark_query_run")
def mark_query_run(id: int) -> dict[str, Any]:
    return {"ok": _sqlite().mark_query_run(id)}


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
