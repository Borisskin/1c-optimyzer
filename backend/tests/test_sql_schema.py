"""Тесты schema introspection (Sprint 2 Phase B)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from optimyzer_backend.sql.schema_introspection import get_schema


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "schema_test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE events (id BIGINT, ts TIMESTAMP, payload JSON)")
    conn.execute("CREATE TABLE meta (key VARCHAR, value VARCHAR)")
    conn.close()
    return db_path


def test_get_schema_returns_all_tables(seeded_db: Path) -> None:
    schema = get_schema("any", db_path=seeded_db)
    assert set(schema.keys()) == {"events", "meta"}


def test_get_schema_column_metadata(seeded_db: Path) -> None:
    schema = get_schema("any", db_path=seeded_db)
    events = schema["events"]
    names = [c["name"] for c in events]
    assert names == ["id", "ts", "payload"]
    types = {c["name"]: c["type"] for c in events}
    assert "BIGINT" in types["id"].upper()
    assert "TIMESTAMP" in types["ts"].upper()


def test_missing_db_returns_empty_dict(tmp_path: Path) -> None:
    assert get_schema("missing", db_path=tmp_path / "nope.duckdb") == {}


def test_schema_preserves_column_order(seeded_db: Path) -> None:
    schema = get_schema("any", db_path=seeded_db)
    assert [c["name"] for c in schema["events"]] == ["id", "ts", "payload"]
