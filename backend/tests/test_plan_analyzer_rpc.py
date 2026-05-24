"""Sprint 7 — RPC методы plan_analyzer.

Покрывает все 5 RPC:
    analyze_file        — error paths без planview binary (happy в e2e тесте)
    analyze_xml         — error paths
    status              — smoke
    list_tj_plans       — все ветки (no archive, empty, with plans)
    get_tj_plan         — happy + not_found
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest

from optimyzer_backend.rpc import plan_analyzer_rpc as par
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.storage import duckdb_store


# --- Fixtures ---


@pytest.fixture
def plans_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Создаёт DuckDB архив с 3 DBMSSQL событиями: 2 c plan_text, 1 без.

    Регистрирует connection в _ACTIVE_CONNECTIONS + _ARCHIVES чтобы list/get
    RPC видели его как ready.

    Yields archive_id.
    """
    archive_id = "test_plans_archive"
    db_path = tmp_path / f"{archive_id}.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(duckdb_store.SCHEMA_DDL)

    rows = [
        # (id, archive_id, ts, duration_us, event_type, session_id, user, context,
        #  context_norm, process, process_role, process_pid, sql_text,
        #  sql_text_normalized, sql_text_hash, plan_text, rows_read, rows_modified,
        #  extra, source_file, source_line_start)
        (
            1, archive_id, datetime(2026, 5, 24, 10, 0, 0), 500_000, "DBMSSQL", 1, "Admin",
            "Документ.A : 1", "Документ.A", "rphost", "rphost", 1234,
            "SELECT 1", "SELECT ?", "h1", "Compute Scalar", 0, 0,
            None, "f.log", 1,
        ),
        (
            2, archive_id, datetime(2026, 5, 24, 10, 5, 0), 1_200_000, "DBMSSQL", 1, "Admin",
            "Документ.B : 2", "Документ.B", "rphost", "rphost", 1234,
            "SELECT * FROM _Reference15", "SELECT * FROM _Reference15", "h2",
            "|--Clustered Index Seek(OBJECT:([_Reference15]))\n|     Estimated Rows = 100",
            0, 0, None, "f.log", 2,
        ),
        (
            3, archive_id, datetime(2026, 5, 24, 10, 10, 0), 100_000, "DBMSSQL", 1, "Admin",
            "Документ.C : 3", "Документ.C", "rphost", "rphost", 1234,
            "SELECT 2", "SELECT ?", "h3", None, 0, 0,  # NO plan_text
            None, "f.log", 3,
        ),
    ]
    cols = ", ".join(duckdb_store.EVENT_COLUMNS)
    placeholders = ", ".join(["?"] * len(duckdb_store.EVENT_COLUMNS))
    conn.executemany(f"INSERT INTO events ({cols}) VALUES ({placeholders})", rows)

    duckdb_store.register_active_connection(archive_id, conn)
    _ARCHIVES[archive_id] = {"status": "ready"}

    yield archive_id

    # Teardown
    _ARCHIVES.pop(archive_id, None)
    duckdb_store.unregister_active_connection(archive_id)
    conn.close()


# --- analyze_file / analyze_xml: error paths ---


def test_analyze_file_empty_path():
    resp = par.analyze_file_rpc("")
    assert resp["ok"] is False
    assert resp["error"] == "invalid_file_path"


def test_analyze_file_non_string():
    # mypy disabled — намеренно ломаем тип
    resp = par.analyze_file_rpc(None)  # type: ignore[arg-type]
    assert resp["ok"] is False
    assert resp["error"] == "invalid_file_path"


def test_analyze_file_not_found(tmp_path: Path):
    fake_path = tmp_path / "nonexistent.sqlplan"
    resp = par.analyze_file_rpc(str(fake_path))
    assert resp["ok"] is False
    assert resp["error"] == "file_not_found"


def test_analyze_xml_non_string():
    resp = par.analyze_xml_rpc(None)  # type: ignore[arg-type]
    assert resp["ok"] is False
    assert resp["error"] == "invalid_xml"


def test_analyze_xml_empty():
    resp = par.analyze_xml_rpc("   ")
    assert resp["ok"] is False
    assert resp["error"] == "empty_xml"


# --- status ---


def test_status_rpc_shape():
    resp = par.status_rpc()
    assert resp["ok"] is True
    assert "available" in resp
    assert "binary_path" in resp
    assert "version" in resp
    assert resp["rules_count"] == 30


# --- list_tj_plans ---


def test_list_tj_plans_archive_not_loaded():
    resp = par.list_tj_plans_rpc("does_not_exist")
    assert resp["ok"] is False
    assert resp["error"] == "archive_not_loaded"


def test_list_tj_plans_archive_not_ready():
    _ARCHIVES["pending_arc"] = {"status": "loading"}
    try:
        resp = par.list_tj_plans_rpc("pending_arc")
        assert resp["ok"] is False
        assert resp["error"] == "archive_not_ready"
    finally:
        _ARCHIVES.pop("pending_arc", None)


def test_list_tj_plans_returns_events_with_plan(plans_archive: str):
    resp = par.list_tj_plans_rpc(plans_archive)
    assert resp["ok"] is True
    assert resp["has_planSQLText"] is True
    assert resp["total"] == 2  # из 3 событий 2 имеют plan_text
    items = resp["items"]
    assert len(items) == 2
    # Сортировка по duration DESC NULLS LAST — event #2 (1.2s) первый
    assert items[0]["event_id"] == 2
    assert items[1]["event_id"] == 1
    # SQL preview обрезан до 200 символов (наши SQL короткие — целиком)
    assert "Reference15" in items[0]["sql_preview"]
    # Размер плана — длина text-плана в байтах
    assert items[0]["plan_size_bytes"] > 0
    # Context из context_normalized
    assert items[0]["context"] == "Документ.B"


def test_list_tj_plans_pagination(plans_archive: str):
    resp = par.list_tj_plans_rpc(plans_archive, limit=1, offset=0)
    assert len(resp["items"]) == 1
    assert resp["items"][0]["event_id"] == 2  # самый медленный

    resp = par.list_tj_plans_rpc(plans_archive, limit=1, offset=1)
    assert len(resp["items"]) == 1
    assert resp["items"][0]["event_id"] == 1


def test_list_tj_plans_has_planSQLText_false_when_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Архив без plan_text → has_planSQLText=False, banner в UI."""
    archive_id = "test_no_plans"
    db_path = tmp_path / f"{archive_id}.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(duckdb_store.SCHEMA_DDL)

    # 1 DBMSSQL без plan_text
    cols = ", ".join(duckdb_store.EVENT_COLUMNS)
    placeholders = ", ".join(["?"] * len(duckdb_store.EVENT_COLUMNS))
    conn.execute(
        f"INSERT INTO events ({cols}) VALUES ({placeholders})",
        [
            1, archive_id, datetime(2026, 5, 24, 10, 0, 0), 500_000, "DBMSSQL",
            None, None, None, None, "rphost", "rphost", 1234,
            "SELECT 1", None, None, None, None, None, None, "f.log", 1,
        ],
    )

    duckdb_store.register_active_connection(archive_id, conn)
    _ARCHIVES[archive_id] = {"status": "ready"}
    try:
        resp = par.list_tj_plans_rpc(archive_id)
        assert resp["ok"] is True
        assert resp["has_planSQLText"] is False
        assert resp["total"] == 0
        assert resp["items"] == []
    finally:
        _ARCHIVES.pop(archive_id, None)
        duckdb_store.unregister_active_connection(archive_id)
        conn.close()


# --- get_tj_plan ---


def test_get_tj_plan_happy(plans_archive: str):
    resp = par.get_tj_plan_rpc(plans_archive, 2)
    assert resp["ok"] is True
    assert resp["event_id"] == 2
    assert "Reference15" in resp["sql_text"]
    assert "Clustered Index Seek" in resp["plan_text"]
    assert resp["duration_us"] == 1_200_000
    assert resp["context"] == "Документ.B"
    assert resp["ts"].startswith("2026-05-24")


def test_get_tj_plan_event_not_found(plans_archive: str):
    resp = par.get_tj_plan_rpc(plans_archive, 99999)
    assert resp["ok"] is False
    assert resp["error"] == "event_not_found"


def test_get_tj_plan_no_plan_text(plans_archive: str):
    """Event #3 в fixture не имеет plan_text → специальная ошибка."""
    resp = par.get_tj_plan_rpc(plans_archive, 3)
    assert resp["ok"] is False
    assert resp["error"] == "no_plan_text"


def test_get_tj_plan_archive_not_loaded():
    resp = par.get_tj_plan_rpc("does_not_exist", 1)
    assert resp["ok"] is False
    assert resp["error"] == "archive_not_loaded"
