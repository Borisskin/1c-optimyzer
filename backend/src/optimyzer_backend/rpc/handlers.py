"""RPC-методы. Регистрируются через @rpc при импорте модуля."""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend import __version__
from optimyzer_backend.archive.extractor import extract_archive
from optimyzer_backend.parsers.tj_parser import parse_file
from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.storage.duckdb_store import DuckDBStore
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


@rpc("load_archive")
def load_archive(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Archive not found: {path}")

    archive_id = uuid.uuid4().hex
    size = p.stat().st_size

    state: dict[str, Any] = {
        "archive_id": archive_id,
        "path": str(p),
        "size_bytes": size,
        "status": "extracting",
        "progress": 0.0,
        "events_parsed": 0,
        "errors": [],
        "started_at": time.time(),
        "extract_dir": None,
        "store": None,
        "file_count": 0,
    }
    _ARCHIVES[archive_id] = state

    try:
        result = extract_archive(p, archive_id=archive_id)
        state["extract_dir"] = str(result.extract_dir)
        state["file_count"] = len(result.files)
        state["status"] = "parsing"
        state["progress"] = 0.1

        store = DuckDBStore(archive_id)
        store.open()
        state["store"] = store

        total_events = 0
        next_id = 1
        log_files = result.log_files
        for idx, lf in enumerate(log_files):
            try:
                events = list(parse_file(lf.abs_path))
                if events:
                    store.bulk_insert(events, start_id=next_id)
                    next_id += len(events)
                    total_events += len(events)
            except Exception as e:
                state["errors"].append(f"{lf.relative_path}: {type(e).__name__}: {e}")
            state["events_parsed"] = total_events
            state["progress"] = 0.1 + 0.85 * ((idx + 1) / max(len(log_files), 1))

        store.create_indexes()
        elapsed = time.time() - state["started_at"]
        state["status"] = "ready"
        state["progress"] = 1.0
        state["parsing_time_sec"] = elapsed
        state["loaded_at"] = datetime.utcnow().isoformat()

        _sqlite().upsert_recent_archive(
            archive_id=archive_id,
            path=str(p),
            size_bytes=size,
            events_count=total_events,
            parsing_time_sec=elapsed,
        )
    except Exception as e:
        state["status"] = "error"
        state["errors"].append(f"{type(e).__name__}: {e}")

    return _public_state(state)


@rpc("get_archive_status")
def get_archive_status(archive_id: str) -> dict[str, Any]:
    state = _ARCHIVES.get(archive_id)
    if state is None:
        raise ValueError(f"Unknown archive_id: {archive_id}")
    return _public_state(state)


@rpc("list_recent_archives")
def list_recent_archives() -> list[dict[str, Any]]:
    return _sqlite().list_recent_archives(limit=20)


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
        "size_bytes": state["size_bytes"],
        "file_count": state.get("file_count", 0),
        "status": state["status"],
        "progress": round(state.get("progress", 0.0), 3),
        "events_parsed": state.get("events_parsed", 0),
        "errors": list(state.get("errors", []))[:20],
        "parsing_time_sec": state.get("parsing_time_sec"),
        "loaded_at": state.get("loaded_at"),
    }
