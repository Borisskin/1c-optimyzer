"""Sprint 8 Phase B — integration test для re_explain_safe против реальной pgBase.

Gated: запускается только если ENV `OPTIMYZER_PGBASE_AVAILABLE=1`
(используется на машине Сергея где есть pgBase + postgres/1111 user).

CI / fresh dev machines пропускают этот тест без падения.
"""

from __future__ import annotations

import os
from pathlib import Path

import keyring
import pytest

from optimyzer_backend.pg.connections import PgConnectionStore
from optimyzer_backend.pg.re_explain import re_explain_safe, ping_connection
from optimyzer_backend.pg.safety import UnsafeQueryError


# Условие skip всего модуля если pgBase недоступен.
pytestmark = pytest.mark.skipif(
    os.environ.get("OPTIMYZER_PGBASE_AVAILABLE") != "1",
    reason="Set OPTIMYZER_PGBASE_AVAILABLE=1 to enable real pgBase tests",
)


# Test creds — используем default postgres/1111 как на dev машине Сергея.
PG_HOST = os.environ.get("OPTIMYZER_PG_HOST", "localhost")
PG_PORT = int(os.environ.get("OPTIMYZER_PG_PORT", "5432"))
PG_DATABASE = os.environ.get("OPTIMYZER_PG_DATABASE", "pgBase")
PG_USERNAME = os.environ.get("OPTIMYZER_PG_USERNAME", "postgres")
PG_PASSWORD = os.environ.get("OPTIMYZER_PG_PASSWORD", "1111")


@pytest.fixture
def store(tmp_path: Path) -> PgConnectionStore:
    return PgConnectionStore(db_path=tmp_path / "test_metadata.sqlite")


@pytest.fixture
def saved_connection(store: PgConnectionStore) -> int:
    """Сохраняет connection в store + keychain (используется realный OS keychain)."""
    conn = store.add(
        name="Test pgBase",
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        username=PG_USERNAME,
        password=PG_PASSWORD,
    )
    yield conn.id
    # Cleanup keychain entry.
    try:
        store.delete(conn.id)
    except Exception:
        pass


# ============================================================
# test_connection — простой ping
# ============================================================


async def test_real_connection_works():
    """Реальный test_connection возвращает version=PostgreSQL..."""
    result = await ping_connection(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        username=PG_USERNAME,
        password=PG_PASSWORD,
    )
    assert result["ok"] is True
    assert "version" in result
    assert "PostgreSQL" in result["version"]


async def test_real_connection_bad_password():
    """Неверный пароль → ok=False с invalid_password."""
    result = await ping_connection(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        username=PG_USERNAME,
        password="absolutely-wrong-password",
    )
    assert result["ok"] is False
    assert result["error"] in ("invalid_password", "invalid_auth", "unexpected")


async def test_real_connection_bad_database():
    """База не существует → ok=False с database_not_found."""
    result = await ping_connection(
        host=PG_HOST,
        port=PG_PORT,
        database="this-db-definitely-does-not-exist",
        username=PG_USERNAME,
        password=PG_PASSWORD,
    )
    assert result["ok"] is False
    assert result["error"] in ("database_not_found", "unexpected")


# ============================================================
# re_explain_safe — реальный EXPLAIN
# ============================================================


async def test_re_explain_simple_select(
    store: PgConnectionStore, saved_connection: int
):
    """re-EXPLAIN простого SELECT возвращает JSON план с Plan/Planning Time/Execution Time."""
    plan = await re_explain_safe(
        sql="SELECT 1 AS value",
        connection_id=saved_connection,
        store=store,
    )
    # Plan — список с одним dict.
    assert isinstance(plan, list)
    assert len(plan) >= 1
    root = plan[0]
    assert "Plan" in root
    # ANALYZE даёт Execution Time.
    assert "Execution Time" in root or "Planning Time" in root


async def test_re_explain_with_real_pg_table(
    store: PgConnectionStore, saved_connection: int
):
    """re-EXPLAIN запроса к pg_catalog таблице (всегда есть)."""
    plan = await re_explain_safe(
        sql="SELECT datname FROM pg_database WHERE datistemplate = false",
        connection_id=saved_connection,
        store=store,
    )
    assert isinstance(plan, list)
    root = plan[0]
    assert "Plan" in root
    # Проверим что Plan содержит Node Type (basic schema PG EXPLAIN JSON).
    assert "Node Type" in root["Plan"]


async def test_re_explain_unsafe_query_rejected(
    store: PgConnectionStore, saved_connection: int
):
    """INSERT в re_explain_safe → UnsafeQueryError, до connect к PG не доходит."""
    with pytest.raises(UnsafeQueryError):
        await re_explain_safe(
            sql="INSERT INTO some_table VALUES (1)",
            connection_id=saved_connection,
            store=store,
        )


async def test_re_explain_marks_used(
    store: PgConnectionStore, saved_connection: int
):
    """После успешного re-EXPLAIN last_used_at должен быть обновлён."""
    before = store.get(saved_connection)
    assert before is not None
    assert before.last_used_at is None

    await re_explain_safe(
        sql="SELECT 1",
        connection_id=saved_connection,
        store=store,
    )

    after = store.get(saved_connection)
    assert after is not None
    assert after.last_used_at is not None


async def test_re_explain_applies_1c_settings(
    store: PgConnectionStore, saved_connection: int
):
    """re_explain_safe должен применять SET enable_mergejoin=off (1С-настройки).

    Это гарантирует что план будет похож на тот что выдаёт сам 1С (а не PG
    с default-настройками). Проверяем что plan не использует Merge Join
    для двух больших таблиц (PG бы выбрал Merge, но мы запретили).

    Делаем JOIN двух pg_class копий — он точно должен использовать Hash Join
    (или Nested Loop), но не Merge Join.
    """
    plan = await re_explain_safe(
        sql="""
        SELECT a.relname, b.relname
        FROM pg_class a JOIN pg_class b ON a.oid = b.oid
        LIMIT 10
        """,
        connection_id=saved_connection,
        store=store,
    )
    # Inspect plan tree — recursively check that no Merge Join is present.
    def _check_no_merge(node: dict) -> bool:
        if node.get("Node Type") == "Merge Join":
            return False
        for child in node.get("Plans", []):
            if not _check_no_merge(child):
                return False
        return True

    root = plan[0]["Plan"]
    assert _check_no_merge(root), (
        f"План использует Merge Join несмотря на enable_mergejoin=off: {plan}"
    )
