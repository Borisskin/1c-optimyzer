"""Тесты для SqliteStore saved_queries API.

Унаследовано из ``test_templates_and_saved.py`` (Sprint 1). Templates-секция
удалена в Sprint 2 Phase A (OQL templates сняты); SQL-templates тесты
появятся в Phase F.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.storage.sqlite_store import SqliteStore


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore(path=tmp_path / "test.sqlite")


def test_save_and_list(store: SqliteStore) -> None:
    new_id = store.save_query(name="мой запрос", query="SELECT * FROM events LIMIT 10", description="тест")
    assert new_id > 0
    queries = store.list_saved_queries()
    assert len(queries) == 1
    q = queries[0]
    assert q["name"] == "мой запрос"
    assert q["query"] == "SELECT * FROM events LIMIT 10"
    assert q["description"] == "тест"
    assert q["run_count"] == 0


def test_save_multiple_and_order(store: SqliteStore) -> None:
    a = store.save_query(name="A", query="SELECT 1")
    b = store.save_query(name="B", query="SELECT 2")
    queries = store.list_saved_queries()
    assert len(queries) == 2
    assert {q["id"] for q in queries} == {a, b}


def test_delete_saved_query(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="SELECT 1")
    assert store.delete_saved_query(qid) is True
    assert store.list_saved_queries() == []
    assert store.delete_saved_query(qid) is False


def test_rename_saved_query(store: SqliteStore) -> None:
    qid = store.save_query(name="OldName", query="SELECT 1")
    assert store.rename_saved_query(qid, "NewName") is True
    queries = store.list_saved_queries()
    assert queries[0]["name"] == "NewName"


def test_mark_query_run(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="SELECT 1")
    assert store.mark_query_run(qid) is True
    queries = store.list_saved_queries()
    q = queries[0]
    assert q["run_count"] == 1
    assert q["last_run_at"] is not None


def test_mark_query_run_increments_count(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="SELECT 1")
    store.mark_query_run(qid)
    store.mark_query_run(qid)
    store.mark_query_run(qid)
    q = store.list_saved_queries()[0]
    assert q["run_count"] == 3


def test_recent_run_appears_first(store: SqliteStore) -> None:
    import time as _t

    qid_a = store.save_query(name="A", query="SELECT 1")
    _t.sleep(0.01)
    qid_b = store.save_query(name="B", query="SELECT 2")
    _t.sleep(0.01)
    store.mark_query_run(qid_a)
    queries = store.list_saved_queries()
    assert queries[0]["id"] == qid_a


def test_save_with_no_description(store: SqliteStore) -> None:
    qid = store.save_query(name="NoDesc", query="SELECT 1")
    q = store.list_saved_queries()[0]
    assert q["description"] is None
