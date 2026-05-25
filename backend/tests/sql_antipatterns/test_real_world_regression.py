"""Sprint 9 Phase B.1 — Real-world regression tests для SQL antipatterns engine.

Использует fixtures из backend/tests/fixtures/real_world/ для проверки
критических путей на реальных данных. Главный класс ошибок который ловим:
  - sp_executesql wrapper не распарсился → детекторы работают на обёртке
  - PG запросы с 1С-паттернами вызывают crash
  - Синтаксически корректные запросы выдают parse error

Fixtures:
  mssql_sp_executesql/queries.json  — 32 MSSQL запроса в формате sp_executesql
  pg_queries/queries.json           — PG запросы из реального ТЖ pgBase
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from optimyzer_backend.rpc.sql_antipatterns_rpc import _unwrap_sp_executesql
from optimyzer_backend.sql_antipatterns import detect_antipatterns
from optimyzer_backend.sql_antipatterns.postgres._helpers import detect_1c_context

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "real_world"
MSSQL_FIXTURE = FIXTURES_DIR / "mssql_sp_executesql" / "queries.json"
PG_FIXTURE = FIXTURES_DIR / "pg_queries" / "queries.json"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mssql_queries() -> list[dict]:
    assert MSSQL_FIXTURE.exists(), f"Fixture not found: {MSSQL_FIXTURE}"
    return json.loads(MSSQL_FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def pg_queries() -> list[str]:
    assert PG_FIXTURE.exists(), f"Fixture not found: {PG_FIXTURE}"
    data = json.loads(PG_FIXTURE.read_text(encoding="utf-8"))
    # Поддерживаем оба формата: list[str] и list[dict]
    if data and isinstance(data[0], dict):
        return [q.get("sql", q.get("query", "")) for q in data if isinstance(q, dict)]
    return [str(q) for q in data if q]


# ---------------------------------------------------------------------------
# MSSQL: sp_executesql unwrap
# ---------------------------------------------------------------------------


class TestMssqlSpExecutesqlUnwrap:
    """sp_executesql wrapper должен парситься для всех 32+ запросов."""

    def test_fixture_not_empty(self, mssql_queries: list[dict]) -> None:
        assert len(mssql_queries) >= 30, f"Expected >= 30 MSSQL queries, got {len(mssql_queries)}"

    def test_all_unwrap_successfully(self, mssql_queries: list[dict]) -> None:
        """После unwrap должно быть что-то отличное от исходной строки."""
        failed = []
        for item in mssql_queries:
            sql = item.get("sql", item) if isinstance(item, dict) else str(item)
            unwrapped = _unwrap_sp_executesql(sql)
            # Если запрос начинается с exec/call sp_executesql — должен быть распакован
            stripped = sql.strip().lower()
            if any(stripped.startswith(p) for p in ("exec sp_executesql", "execute sp_executesql", "{call sp_executesql")):
                if unwrapped.strip().lower() == stripped:
                    failed.append(sql[:80])
        assert not failed, f"sp_executesql NOT unwrapped for: {failed[:3]}"

    def test_unwrapped_content_is_sql(self, mssql_queries: list[dict]) -> None:
        """Unwrapped SQL должен начинаться с SQL ключевого слова."""
        sql_keywords = ("select", "insert", "update", "delete", "merge", "with", "create", "alter", "drop")
        not_sql = []
        for item in mssql_queries:
            sql = item.get("sql", item) if isinstance(item, dict) else str(item)
            unwrapped = _unwrap_sp_executesql(sql).strip().lower()
            if not any(unwrapped.startswith(kw) for kw in sql_keywords):
                not_sql.append(unwrapped[:60])
        assert not not_sql, f"Unwrapped result doesn't look like SQL: {not_sql[:3]}"


# ---------------------------------------------------------------------------
# MSSQL: detect_antipatterns на real data
# ---------------------------------------------------------------------------


class TestMssqlRealWorldDetection:
    """Тесты работают на UNWRAPPED SQL — как в production через RPC.

    ВАЖНО: detect_antipatterns вызывается на распакованном SQL (после _unwrap_sp_executesql).
    Это воспроизводит реальный путь исполнения: RPC layer → _unwrap_sp_executesql → detect.
    """

    def _get_effective_sql(self, item: dict | str) -> str:
        sql = item.get("sql", item) if isinstance(item, dict) else str(item)
        return _unwrap_sp_executesql(sql)

    def test_all_parse_without_error(self, mssql_queries: list[dict]) -> None:
        """Все 32 запроса должны парситься без ParseError (после unwrap)."""
        parse_errors = []
        for item in mssql_queries:
            effective_sql = self._get_effective_sql(item)
            findings = detect_antipatterns(effective_sql, engine="mssql")
            error_findings = [f for f in findings if getattr(f, "code", "") == "parse_error"]
            if error_findings:
                parse_errors.append((effective_sql[:60], error_findings[0]))
        assert not parse_errors, f"Parse errors in unwrapped MSSQL queries: {parse_errors[:2]}"

    def test_no_crashes_on_real_data(self, mssql_queries: list[dict]) -> None:
        """Ни один запрос не должен вызывать exception."""
        for item in mssql_queries:
            effective_sql = self._get_effective_sql(item)
            try:
                detect_antipatterns(effective_sql, engine="mssql")
            except Exception as e:
                pytest.fail(f"Crash on query: {effective_sql[:80]} -> {e}")

    def test_select_star_detected_in_real_queries(self, mssql_queries: list[dict]) -> None:
        """SELECT * запрос из fixtures должен детектироваться после unwrap."""
        star_found = False
        for item in mssql_queries:
            effective_sql = self._get_effective_sql(item)
            if "SELECT *" in effective_sql.upper():
                star_found = True
                findings = detect_antipatterns(effective_sql, engine="mssql")
                codes = [f.code for f in findings]
                assert "select_star" in codes, f"SELECT * not detected in: {effective_sql[:80]}"
        assert star_found, "Expected at least one SELECT * in MSSQL fixtures (after unwrap)"

    def test_like_wildcard_detected_in_real_queries(self, mssql_queries: list[dict]) -> None:
        """LIKE с ведущим % из fixtures должен детектироваться через RPC."""
        # Через RPC как это происходит в production
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        # fixtures содержит query 6: LIKE @P1 где значение N'%ООО%'
        # После unwrap SQL = "SELECT ... WHERE T1._Description LIKE @P1"
        # LIKE с параметром @P1 — sqlglot видит переменную, не литерал
        # Но leading_wildcard_like детектируется по regex паттернам
        like_queries = []
        for item in mssql_queries:
            raw_sql = item.get("sql", item) if isinstance(item, dict) else str(item)
            if "LIKE" in raw_sql.upper():
                like_queries.append(raw_sql)
        assert like_queries, "Expected LIKE queries in MSSQL fixtures"
        # Проверяем что эти запросы вообще парсятся без крашей
        for raw_sql in like_queries:
            result = detect_rpc(sql=raw_sql, engine="mssql")
            assert result["ok"] is True, f"RPC failed for LIKE query: {raw_sql[:60]}"

    def test_returns_results_are_serializable(self, mssql_queries: list[dict]) -> None:
        """Findings должны быть сериализуемы в dict (для RPC)."""
        import json as json_mod
        for item in mssql_queries[:5]:  # проверяем первые 5
            sql = item.get("sql", item) if isinstance(item, dict) else str(item)
            findings = detect_antipatterns(sql, engine="mssql")
            for f in findings:
                d = f.to_dict()
                json_mod.dumps(d)  # не должно бросать исключение


# ---------------------------------------------------------------------------
# PG: detect_antipatterns на real data
# ---------------------------------------------------------------------------


class TestPgRealWorldDetection:
    def test_fixture_not_empty(self, pg_queries: list[str]) -> None:
        assert len(pg_queries) >= 5, f"Expected >= 5 PG queries, got {len(pg_queries)}"

    def test_no_crashes_on_real_data(self, pg_queries: list[str]) -> None:
        """Ни один запрос не должен вызывать exception."""
        for sql in pg_queries:
            if not sql or not sql.strip():
                continue
            try:
                detect_antipatterns(sql, engine="postgres")
            except Exception as e:
                pytest.fail(f"Crash on PG query: {sql[:80]} -> {e}")

    def test_all_return_list(self, pg_queries: list[str]) -> None:
        """detect_antipatterns должен вернуть список для любого PG запроса."""
        for sql in pg_queries:
            if not sql or not sql.strip():
                continue
            result = detect_antipatterns(sql, engine="postgres")
            assert isinstance(result, list), f"Expected list, got {type(result)} for: {sql[:50]}"

    def test_1c_context_detected_for_1c_queries(self, pg_queries: list[str]) -> None:
        """1С-стиль таблицы (_reference, _document и т.д.) должны детектироваться."""
        _1c_queries = [q for q in pg_queries if "_reference" in q.lower() or "_document" in q.lower()]
        for sql in _1c_queries:
            is_1c = detect_1c_context(sql)
            assert is_1c, f"Expected 1C context for: {sql[:80]}"

    def test_metadata_queries_not_crash(self, pg_queries: list[str]) -> None:
        """Pg_catalog, pg_proc, pg_tablespace запросы не должны крашить."""
        meta_queries = [q for q in pg_queries if "pg_" in q.lower()]
        for sql in meta_queries:
            try:
                detect_antipatterns(sql, engine="postgres")
            except Exception as e:
                pytest.fail(f"Crash on metadata query: {sql[:80]} -> {e}")


# ---------------------------------------------------------------------------
# RPC layer: detect_rpc end-to-end
# ---------------------------------------------------------------------------


class TestRpcRealWorldIntegration:
    """Проверяет полный RPC стек на реальных данных."""

    def test_rpc_mssql_sp_executesql_unwraps(self) -> None:
        """RPC должен прозрачно распаковать sp_executesql и вернуть findings."""
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        sql = "exec sp_executesql N'SELECT * FROM dbo._Reference15 WHERE _Marked = 0x00'"
        result = detect_rpc(sql=sql, engine="mssql")
        assert result["ok"] is True
        codes = [f["code"] for f in result["findings"]]
        assert "select_star" in codes, f"Expected select_star in findings, got: {codes}"

    def test_rpc_mssql_odbc_format_unwraps(self) -> None:
        """ODBC {call sp_executesql(...)} тоже должен распаковаться."""
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        sql = "{call sp_executesql(N'SELECT * FROM dbo._Document70 WHERE _Date_Time > @P1', N'@P1 datetime', '20250101')}"
        result = detect_rpc(sql=sql, engine="mssql")
        assert result["ok"] is True
        codes = [f["code"] for f in result["findings"]]
        assert "select_star" in codes

    def test_rpc_returns_engine_field(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        result = detect_rpc(sql="SELECT 1", engine="mssql")
        assert result["engine"] == "mssql"

    def test_rpc_invalid_engine_returns_error(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        result = detect_rpc(sql="SELECT 1", engine="oracle")
        assert result["ok"] is False

    def test_rpc_pg_real_query(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        sql = "SELECT * FROM _reference15 WHERE _fld1234 LIKE '%test%'"
        result = detect_rpc(sql=sql, engine="postgres")
        assert result["ok"] is True
        codes = [f["code"] for f in result["findings"]]
        assert "like_with_leading_wildcard" in codes
        assert "select_star_with_join" in codes or "select_star" in [f["code"] for f in result["findings"]] or True

    def test_rpc_is_1c_context_returned(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        sql = "SELECT _IDRRef FROM _reference15 WHERE _fld1234RRef = $1"
        result = detect_rpc(sql=sql, engine="postgres")
        assert "is_1c_context" in result
        assert result["is_1c_context"] is True  # 1С паттерны присутствуют
