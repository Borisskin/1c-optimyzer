"""Тесты для templates и saved queries (Phases H + I)."""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.oql.templates import TEMPLATES
from optimyzer_backend.oql import parse_oql, validate, SQLCompiler
from optimyzer_backend.storage.sqlite_store import SqliteStore


# ---------- Templates ----------


def test_all_templates_parse_and_compile() -> None:
    """Каждый встроенный шаблон должен парситься, валидироваться и компилироваться."""
    for tpl in TEMPLATES:
        query = tpl["query"]
        ast = parse_oql(query)
        errors = validate(ast)
        assert errors == [], f"{tpl['id']}: validation failed: {errors}"
        compiler = SQLCompiler(active_archive_id="any")
        sql, _ = compiler.compile(ast)
        assert "FROM events" in sql, f"{tpl['id']}: missing FROM events"


def test_templates_have_required_fields() -> None:
    for tpl in TEMPLATES:
        for key in ("id", "label", "description", "category", "query"):
            assert key in tpl, f"template {tpl.get('id')} missing {key}"
        assert tpl["label"], f"empty label in {tpl['id']}"


def test_templates_ids_unique() -> None:
    ids = [t["id"] for t in TEMPLATES]
    assert len(ids) == len(set(ids))


def test_templates_count_at_least_8() -> None:
    # Spec phase H — 8 templates
    assert len(TEMPLATES) >= 8


# ---------- Saved queries ----------


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore(path=tmp_path / "test.sqlite")


def test_save_and_list(store: SqliteStore) -> None:
    new_id = store.save_query(name="мой запрос", query="events | take 10", description="тест")
    assert new_id > 0
    queries = store.list_saved_queries()
    assert len(queries) == 1
    q = queries[0]
    assert q["name"] == "мой запрос"
    assert q["query"] == "events | take 10"
    assert q["description"] == "тест"
    assert q["run_count"] == 0


def test_save_multiple_and_order(store: SqliteStore) -> None:
    a = store.save_query(name="A", query="events | take 1")
    b = store.save_query(name="B", query="events | take 2")
    queries = store.list_saved_queries()
    assert len(queries) == 2
    # newest first by created_at
    assert {q["id"] for q in queries} == {a, b}


def test_delete_saved_query(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="events")
    assert store.delete_saved_query(qid) is True
    assert store.list_saved_queries() == []
    # idempotent
    assert store.delete_saved_query(qid) is False


def test_rename_saved_query(store: SqliteStore) -> None:
    qid = store.save_query(name="OldName", query="events")
    assert store.rename_saved_query(qid, "NewName") is True
    queries = store.list_saved_queries()
    assert queries[0]["name"] == "NewName"


def test_mark_query_run(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="events")
    assert store.mark_query_run(qid) is True
    queries = store.list_saved_queries()
    q = queries[0]
    assert q["run_count"] == 1
    assert q["last_run_at"] is not None


def test_mark_query_run_increments_count(store: SqliteStore) -> None:
    qid = store.save_query(name="X", query="events")
    store.mark_query_run(qid)
    store.mark_query_run(qid)
    store.mark_query_run(qid)
    q = store.list_saved_queries()[0]
    assert q["run_count"] == 3


def test_recent_run_appears_first(store: SqliteStore) -> None:
    import time as _t

    qid_a = store.save_query(name="A", query="events | take 1")
    _t.sleep(0.01)
    qid_b = store.save_query(name="B", query="events | take 2")
    # Run A — should bump it to top
    _t.sleep(0.01)
    store.mark_query_run(qid_a)
    queries = store.list_saved_queries()
    assert queries[0]["id"] == qid_a


def test_save_with_no_description(store: SqliteStore) -> None:
    qid = store.save_query(name="NoDesc", query="events")
    q = store.list_saved_queries()[0]
    assert q["description"] is None
