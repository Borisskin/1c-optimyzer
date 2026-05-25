"""Sprint 9 Phase E.1 — Performance baseline tests для SQL antipatterns engine.

Устанавливает performance targets для критических операций.
Помечены @pytest.mark.performance — запускаются по умолчанию.

Targets (ADR-052):
  - query < 1 KB  → < 50 ms
  - query < 10 KB → < 200 ms
  - query < 100 KB → < 1 sec
  - 30 queries    → < 1 sec throughput
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from optimyzer_backend.sql_antipatterns import detect_antipatterns
from optimyzer_backend.rpc.sql_antipatterns_rpc import _unwrap_sp_executesql

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "real_world"
MSSQL_FIXTURE = FIXTURES_DIR / "mssql_sp_executesql" / "queries.json"
PG_FIXTURE = FIXTURES_DIR / "pg_queries" / "queries.json"

pytestmark = pytest.mark.performance


# ---------------------------------------------------------------------------
# Latency targets
# ---------------------------------------------------------------------------


class TestAntipatternsLatency:
    """Latency targets для individual query analysis."""

    def test_small_mssql_query_under_50ms(self) -> None:
        """Простой MSSQL SELECT < 1 KB должен выполняться < 50 ms."""
        sql = "SELECT TOP 100 T1._IDRRef, T1._Code, T1._Description FROM dbo._Reference15 T1 WHERE T1._Fld1236 = 'ACTIVE'"
        start = time.perf_counter()
        detect_antipatterns(sql, engine="mssql")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Small MSSQL query took {elapsed_ms:.1f} ms (target < 50 ms)"

    def test_small_pg_query_under_50ms(self) -> None:
        """Простой PG SELECT < 1 KB должен выполняться < 50 ms."""
        sql = "SELECT t1._idrref, t1._code, t1._description FROM _reference15 t1 WHERE t1._fld1236 = $1"
        start = time.perf_counter()
        detect_antipatterns(sql, engine="postgres")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Small PG query took {elapsed_ms:.1f} ms (target < 50 ms)"

    def test_medium_query_under_200ms(self) -> None:
        """Средний запрос ~5 KB должен выполняться < 200 ms."""
        # Генерируем ~5 KB запрос
        parts = []
        for i in range(20):
            parts.append(
                f"SELECT T{i}._IDRRef, T{i}._Code, T{i}._Description "
                f"FROM dbo._Reference{i+10} T{i} WHERE T{i}._Fld{i+100} = 'VALUE_{i}'"
            )
        sql = " UNION ALL ".join(parts)
        start = time.perf_counter()
        detect_antipatterns(sql, engine="mssql")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 200, f"Medium query took {elapsed_ms:.1f} ms (target < 200 ms)"

    def test_unwrap_sp_executesql_under_1ms(self) -> None:
        """sp_executesql unwrap — regex операция, должна быть < 1 ms."""
        sql = "exec sp_executesql N'SELECT TOP 1000 T1._IDRRef, T1._Code FROM dbo._Reference15 T1 WHERE T1._Fld1234 = @P1', N'@P1 nvarchar(128)', N'TEST'"
        start = time.perf_counter()
        for _ in range(100):  # 100 вызовов
            _unwrap_sp_executesql(sql)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_call_ms = elapsed_ms / 100
        assert per_call_ms < 1.0, f"unwrap takes {per_call_ms:.3f} ms per call (target < 1 ms)"


# ---------------------------------------------------------------------------
# Throughput targets
# ---------------------------------------------------------------------------


class TestAntipatternsThoughput:
    """Throughput: 30 queries / second baseline."""

    @pytest.fixture(scope="class")
    def mssql_query_strings(self) -> list[str]:
        if not MSSQL_FIXTURE.exists():
            pytest.skip(f"Fixture not found: {MSSQL_FIXTURE}")
        data = json.loads(MSSQL_FIXTURE.read_text(encoding="utf-8"))
        return [item.get("sql", item) if isinstance(item, dict) else str(item) for item in data]

    def test_throughput_30_mssql_queries_under_1s(self, mssql_query_strings: list[str]) -> None:
        """30 реальных MSSQL запросов должны обрабатываться < 1 секунды."""
        queries = mssql_query_strings[:30]
        if len(queries) < 30:
            pytest.skip(f"Not enough queries: {len(queries)}")

        start = time.perf_counter()
        for sql in queries:
            detect_antipatterns(sql, engine="mssql")
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"30 MSSQL queries took {elapsed:.2f}s (target < 1s)"
        qps = len(queries) / elapsed
        # Log throughput (pytest -s покажет)
        print(f"\n[Performance] MSSQL throughput: {qps:.1f} queries/sec")

    def test_throughput_10_pg_queries_under_500ms(self) -> None:
        """10 реальных PG запросов должны обрабатываться < 500 ms."""
        if not PG_FIXTURE.exists():
            pytest.skip(f"Fixture not found: {PG_FIXTURE}")
        data = json.loads(PG_FIXTURE.read_text(encoding="utf-8"))
        queries: list[str] = [str(q) for q in data if q][:10]
        if not queries:
            pytest.skip("No PG queries in fixture")

        start = time.perf_counter()
        for sql in queries:
            detect_antipatterns(sql, engine="postgres")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"10 PG queries took {elapsed_ms:.0f}ms (target < 500ms)"


# ---------------------------------------------------------------------------
# No-regression: repeated calls are stable
# ---------------------------------------------------------------------------


class TestPerformanceStability:
    """Производительность не деградирует при повторных вызовах (нет memory leak, нет cache explosion)."""

    def test_repeated_calls_not_slower(self) -> None:
        """5-й вызов не должен быть значительно медленнее 1-го."""
        sql = "SELECT T1._IDRRef, T1._Code FROM dbo._Reference15 T1 WHERE T1._Fld1234 LIKE '%test%'"
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            detect_antipatterns(sql, engine="mssql")
            timings.append((time.perf_counter() - start) * 1000)

        first = timings[0]
        last = timings[-1]
        # Последний вызов не должен быть > 3x медленнее первого
        assert last < first * 3 + 5, f"Performance degraded: first={first:.1f}ms, last={last:.1f}ms"
