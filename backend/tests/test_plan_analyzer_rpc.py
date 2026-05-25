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
        #  extra, source_file, source_line_start, engine)
        # Sprint 8 Phase B — добавлен engine column в EVENT_COLUMNS (22 fields total).
        (
            1, archive_id, datetime(2026, 5, 24, 10, 0, 0), 500_000, "DBMSSQL", 1, "Admin",
            "Документ.A : 1", "Документ.A", "rphost", "rphost", 1234,
            "SELECT 1", "SELECT ?", "h1", "Compute Scalar", 0, 0,
            None, "f.log", 1, "mssql",
        ),
        (
            2, archive_id, datetime(2026, 5, 24, 10, 5, 0), 1_200_000, "DBMSSQL", 1, "Admin",
            "Документ.B : 2", "Документ.B", "rphost", "rphost", 1234,
            "SELECT * FROM _Reference15", "SELECT * FROM _Reference15", "h2",
            "|--Clustered Index Seek(OBJECT:([_Reference15]))\n|     Estimated Rows = 100",
            0, 0, None, "f.log", 2, "mssql",
        ),
        (
            3, archive_id, datetime(2026, 5, 24, 10, 10, 0), 100_000, "DBMSSQL", 1, "Admin",
            "Документ.C : 3", "Документ.C", "rphost", "rphost", 1234,
            "SELECT 2", "SELECT ?", "h3", None, 0, 0,  # NO plan_text
            None, "f.log", 3, "mssql",
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

    # 1 DBMSSQL без plan_text (22 fields включая engine — Sprint 8 Phase B).
    cols = ", ".join(duckdb_store.EVENT_COLUMNS)
    placeholders = ", ".join(["?"] * len(duckdb_store.EVENT_COLUMNS))
    conn.execute(
        f"INSERT INTO events ({cols}) VALUES ({placeholders})",
        [
            1, archive_id, datetime(2026, 5, 24, 10, 0, 0), 500_000, "DBMSSQL",
            None, None, None, None, "rphost", "rphost", 1234,
            "SELECT 1", None, None, None, None, None, None, "f.log", 1, "mssql",
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


# ============================================================
# Sprint 8 Phase B — mixed MSSQL/PG archive + engine filter
# ============================================================


@pytest.fixture
def mixed_engine_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Архив с 1 DBMSSQL + 2 DBPOSTGRS событиями с planом.

    Используется для тестов engine filter в list_tj_plans и engine field
    в get_tj_plan ответе.
    """
    archive_id = "test_mixed_engine"
    db_path = tmp_path / f"{archive_id}.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(duckdb_store.SCHEMA_DDL)

    rows = [
        (
            10, archive_id, datetime(2026, 5, 25, 14, 0, 0), 300_000, "DBMSSQL",
            1, "Admin", "Документ.X : 1", "Документ.X", "rphost", "rphost", 1234,
            "SELECT 1", "SELECT ?", "h10", "Compute Scalar", 0, 0,
            None, "f.log", 1, "mssql",
        ),
        (
            20, archive_id, datetime(2026, 5, 25, 14, 5, 0), 500_000, "DBPOSTGRS",
            2, "BVS", "Документ.Y : 2", "Документ.Y", "rphost", "rphost", 1234,
            "SELECT count(*) FROM _document201", "SELECT count(*) FROM _document201", "h20",
            "Aggregate  (cost=10.5..10.5 rows=1 width=8)\n  -> Seq Scan on _document201\nPlanning Time: 0.1 ms\nExecution Time: 0.5 ms",
            0, 0, None, "f.log", 2, "postgres",
        ),
        (
            30, archive_id, datetime(2026, 5, 25, 14, 10, 0), 800_000, "DBPOSTGRS",
            2, "BVS", "Документ.Z : 3", "Документ.Z", "rphost", "rphost", 1234,
            "SELECT * FROM _reference15 WHERE _fld11355 = 1",
            "SELECT * FROM _reference15 WHERE _fld11355 = ?", "h30",
            "Index Scan using _reference15_pk on _reference15  (cost=0.42..8.5 rows=1)\nPlanning Time: 0.2 ms\nExecution Time: 0.8 ms",
            0, 0, None, "f.log", 3, "postgres",
        ),
    ]
    cols = ", ".join(duckdb_store.EVENT_COLUMNS)
    placeholders = ", ".join(["?"] * len(duckdb_store.EVENT_COLUMNS))
    conn.executemany(f"INSERT INTO events ({cols}) VALUES ({placeholders})", rows)

    duckdb_store.register_active_connection(archive_id, conn)
    _ARCHIVES[archive_id] = {"status": "ready"}

    yield archive_id

    _ARCHIVES.pop(archive_id, None)
    duckdb_store.unregister_active_connection(archive_id)
    conn.close()


def test_list_tj_plans_returns_both_engines(mixed_engine_archive: str):
    """Без фильтра — возвращаются и MSSQL и PG planы."""
    resp = par.list_tj_plans_rpc(mixed_engine_archive)
    assert resp["ok"] is True
    assert resp["total"] == 3  # 1 mssql + 2 postgres
    engines = {it["engine"] for it in resp["items"]}
    assert engines == {"mssql", "postgres"}


def test_list_tj_plans_counts_by_engine(mixed_engine_archive: str):
    """counts_by_engine показывает разбивку для UI filter toggle."""
    resp = par.list_tj_plans_rpc(mixed_engine_archive)
    assert resp["ok"] is True
    counts = resp["counts_by_engine"]
    assert counts.get("mssql") == 1
    assert counts.get("postgres") == 2


def test_list_tj_plans_filter_postgres(mixed_engine_archive: str):
    """engine='postgres' возвращает только PG planы."""
    resp = par.list_tj_plans_rpc(mixed_engine_archive, engine="postgres")
    assert resp["ok"] is True
    assert resp["total"] == 2
    assert all(it["engine"] == "postgres" for it in resp["items"])


def test_list_tj_plans_filter_mssql(mixed_engine_archive: str):
    """engine='mssql' возвращает только MSSQL planы."""
    resp = par.list_tj_plans_rpc(mixed_engine_archive, engine="mssql")
    assert resp["ok"] is True
    assert resp["total"] == 1
    assert all(it["engine"] == "mssql" for it in resp["items"])


def test_list_tj_plans_invalid_engine_filter_ignored(mixed_engine_archive: str):
    """Невалидный engine ('oracle', 'foo') игнорируется — все planы возвращаются.

    Защита от случайных API misuse — лучше показать всё чем сломать UI.
    """
    resp = par.list_tj_plans_rpc(mixed_engine_archive, engine="oracle")
    assert resp["ok"] is True
    assert resp["total"] == 3


def test_get_tj_plan_returns_postgres_engine(mixed_engine_archive: str):
    """get_tj_plan ответ содержит engine='postgres' для DBPOSTGRS event."""
    resp = par.get_tj_plan_rpc(mixed_engine_archive, 20)
    assert resp["ok"] is True
    assert resp["engine"] == "postgres"
    assert "Seq Scan" in resp["plan_text"]
    assert "Planning Time" in resp["plan_text"]


def test_get_tj_plan_returns_mssql_engine(mixed_engine_archive: str):
    """get_tj_plan ответ содержит engine='mssql' для DBMSSQL event."""
    resp = par.get_tj_plan_rpc(mixed_engine_archive, 10)
    assert resp["ok"] is True
    assert resp["engine"] == "mssql"
