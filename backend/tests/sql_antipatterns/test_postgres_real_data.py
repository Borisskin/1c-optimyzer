"""Sprint 8 Phase C — Real PG data + edge cases для antipatterns engine.

Источник: tools/sprint8_discovery/pg_tj_samples/ — реальные запросы которые
1С отправляет в PostgreSQL (из tech journal events DBPOSTGRS).

Тестируем что:
  - 961 unique real SQL обрабатываются без crash
  - Edge cases (CTE, JSONB, LATERAL, UNION ALL, multi-statement) не валят парсер
  - Performance budget — 1000 queries за < 60 секунд
  - Robustness — invalid SQL обрабатывается graceful
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest

from optimyzer_backend.sql_antipatterns import detect_antipatterns

FIXTURES_PATH = (
    Path(__file__).parent / "fixtures_real_pg_queries.json"
)

# Real TJ events имеют такой формат:
#   Sql="SELECT ... FROM ...
#   p_0: 1N
#   p_1: 'value'"
# Параметры (p_N:) — НЕ часть SQL. Отрезаем чтобы парсер не путался.
_PARAMS_BOUNDARY = re.compile(r"\np_\d+:\s", re.MULTILINE)


def _clean_tj_sql(raw: str) -> str:
    """Убирает параметры (p_N: value) которые 1С добавляет после SQL в TJ."""
    parts = _PARAMS_BOUNDARY.split(raw, maxsplit=1)
    return parts[0].strip()


@pytest.fixture(scope="module")
def real_pg_queries() -> list[str]:
    """961 unique SQL запрос из реального 1С-PG ТЖ архива (без trailing params)."""
    if not FIXTURES_PATH.exists():
        pytest.skip(f"Fixtures file not found: {FIXTURES_PATH}")
    with FIXTURES_PATH.open(encoding="utf-8") as f:
        raw_queries = json.load(f)
    return [_clean_tj_sql(q) for q in raw_queries]


class TestRealPgQueries:
    """Real-data integration — все 961 запроса обрабатываются без crash."""

    def test_all_queries_processable(self, real_pg_queries: list[str]) -> None:
        """Все 961 запроса обрабатываются без exception (robustness)."""
        for i, sql in enumerate(real_pg_queries):
            try:
                result = detect_antipatterns(sql, engine="postgres")
            except Exception as e:
                pytest.fail(f"Query #{i} crashed: {e!r}\nSQL: {sql[:200]}")
            assert isinstance(result, list), f"Query #{i} returned non-list"

    def test_parse_success_rate_when_engine_matches(
        self, real_pg_queries: list[str]
    ) -> None:
        """T-SQL запросы (от MSSQL connector) парсятся как mssql ≥ 50%.

        Note: реальные TJ от 1С базы dbpostgrs_sample.log содержат MIX:
        - T-SQL `exec sp_executesql`, dbo., [brackets] (от MSSQL connector)
        - PG-style _reference15, ARRAY (от PG connector)

        Если SQL T-SQL по сигнатуре — будем парсить как mssql.
        Это даёт хороший integration test для обоих engine dispatch путей.
        """
        # Heuristic split — T-SQL обычно содержит exec / sp_ / dbo. / [bracket]
        tsql_markers = re.compile(
            r"exec sp_executesql|dbo\.|\b\[\w+\]\b|0x[0-9A-Fa-f]+",
            re.IGNORECASE,
        )
        tsql_queries = [q for q in real_pg_queries if tsql_markers.search(q)]
        if len(tsql_queries) < 10:
            pytest.skip("Not enough T-SQL queries in real-data sample")

        parse_errors = 0
        for sql in tsql_queries:
            findings = detect_antipatterns(sql, engine="mssql")
            if any(f.code == "parse_error" for f in findings):
                parse_errors += 1
        success_rate = 1 - (parse_errors / len(tsql_queries))
        # T-SQL запросы должны парсится как mssql с гораздо лучшим rate.
        assert success_rate >= 0.5, (
            f"T-SQL parse success rate {success_rate:.1%} ниже 50%. "
            f"Errors: {parse_errors}/{len(tsql_queries)}"
        )

    def test_no_crash_on_any_real_query(
        self, real_pg_queries: list[str]
    ) -> None:
        """ГЛАВНОЕ: ни один реальный запрос не должен крашить engine.

        Это robustness test — даже если запрос непарсимый, должен вернуть
        либо [], либо [parse_error]. Никаких exceptions.
        """
        crashes: list[tuple[int, str, str]] = []
        for engine in ("postgres", "mssql"):
            for i, sql in enumerate(real_pg_queries):
                try:
                    result = detect_antipatterns(sql, engine=engine)  # type: ignore[arg-type]
                    assert isinstance(result, list)
                except Exception as e:
                    crashes.append((i, engine, str(e)[:100]))
        assert not crashes, (
            f"Engine crashed on {len(crashes)} queries: {crashes[:5]}"
        )

    def test_1c_context_detected_in_real_queries(
        self, real_pg_queries: list[str]
    ) -> None:
        """≥ 5% реальных 1С-PG/MSSQL запросов распознаются как 1С context.

        Note: реальные TJ от 1С-PG базы имеют `_reference\\d+` / `_document\\d+`
        identifiers. Не все запросы 1С (системные могут быть SET / SHOW etc.),
        поэтому 5% — floor для robustness check.
        """
        from optimyzer_backend.sql_antipatterns.postgres._helpers import (
            detect_1c_context,
        )

        sample = [q for q in real_pg_queries if 50 < len(q) < 2000]
        if len(sample) < 50:
            pytest.skip("Not enough real queries in sample")
        in_1c = sum(1 for q in sample if detect_1c_context(q))
        ratio = in_1c / len(sample)
        assert ratio >= 0.05, (
            f"1С-context ratio {ratio:.1%} ниже 5% — heuristic не работает? "
            f"({in_1c}/{len(sample)})"
        )


class TestEdgeCases:
    """Edge cases — CTE, JSONB, LATERAL, multi-statement, comments etc."""

    def test_cte(self) -> None:
        sql = """
        WITH active_docs AS (
            SELECT _IDRRef FROM _Document201 WHERE _Posted = TRUE
        )
        SELECT * FROM active_docs LIMIT 100
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_with_recursive(self) -> None:
        sql = """
        WITH RECURSIVE tree AS (
            SELECT id, parent_id FROM nodes WHERE parent_id IS NULL
            UNION ALL
            SELECT n.id, n.parent_id FROM nodes n JOIN tree t ON n.parent_id = t.id
        )
        SELECT * FROM tree
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)
        # UNION ALL — не должно flag union_instead_of_union_all
        assert not any(f.code == "union_instead_of_union_all" for f in result)

    def test_window_function(self) -> None:
        sql = """
        SELECT _IDRRef, _Date, ROW_NUMBER() OVER (PARTITION BY _Owner ORDER BY _Date DESC) AS rn
        FROM _Document201
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_jsonb_operations(self) -> None:
        sql = """
        SELECT data->'name', data->>'email'
        FROM users
        WHERE data @> '{"active":true}'::jsonb
        AND data #> '{address,city}' = '"Moscow"'::jsonb
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)
        # JSONB — должен flag jsonb_without_gin
        assert any(f.code == "jsonb_without_gin" for f in result)

    def test_lateral_join(self) -> None:
        sql = """
        SELECT m.id, t.last_change
        FROM main m
        LEFT JOIN LATERAL (
            SELECT MAX(updated_at) AS last_change FROM tracker WHERE main_id = m.id
        ) t ON TRUE
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_union_all_chain(self) -> None:
        sql = """
        SELECT id FROM t1
        UNION ALL SELECT id FROM t2
        UNION ALL SELECT id FROM t3
        UNION ALL SELECT id FROM t4
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)
        assert not any(f.code == "union_instead_of_union_all" for f in result)

    def test_very_long_query(self) -> None:
        """Запрос ~5000 символов — должен обрабатываться без crash."""
        sql = "SELECT id FROM t WHERE x IN (" + ",".join(str(i) for i in range(500)) + ")"
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_query_with_line_comments(self) -> None:
        sql = """
        SELECT id, name
        -- этот комментарий должен быть проигнорирован
        FROM users
        WHERE active = TRUE -- ещё один inline comment
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_query_with_block_comments(self) -> None:
        sql = """
        /* multi-line
           block comment */
        SELECT /* inline */ id FROM users
        """
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_comments_only(self) -> None:
        sql = "-- just a comment\n/* nothing here */"
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)

    def test_empty_query(self) -> None:
        assert detect_antipatterns("", engine="postgres") == []

    def test_whitespace_only(self) -> None:
        result = detect_antipatterns("   \n\t  \n  ", engine="postgres")
        assert isinstance(result, list)

    def test_multi_statement(self) -> None:
        # sqlglot обычно парсит первый statement из multi.
        sql = "SELECT 1; SELECT 2; UPDATE t SET x = 1;"
        result = detect_antipatterns(sql, engine="postgres")
        assert isinstance(result, list)


class TestPerformance:
    """Performance budget — engine должен оставаться быстрым."""

    def test_single_query_under_100ms(self) -> None:
        """Один запрос ~200 символов — < 100ms на full 15 detectors."""
        sql = (
            "SELECT _IDRRef, _Description, _Code FROM _Reference15 "
            "WHERE _Fld11355 = '\\x12345678'::bytea "
            "AND _Description::mvarchar LIKE '%test%' "
            "ORDER BY _Code LIMIT 100 OFFSET 5000"
        )
        # Прогрев
        detect_antipatterns(sql, engine="postgres")
        start = time.perf_counter()
        for _ in range(10):
            detect_antipatterns(sql, engine="postgres")
        elapsed_ms = (time.perf_counter() - start) * 100  # avg per call
        assert elapsed_ms < 100, (
            f"Average detection time {elapsed_ms:.1f}ms > 100ms budget"
        )

    def test_1000_queries_under_60_seconds(self, real_pg_queries: list[str]) -> None:
        """1000 real queries за < 60 секунд (даже на медленной CI)."""
        sample = real_pg_queries[:1000] if len(real_pg_queries) >= 1000 else real_pg_queries
        if len(sample) < 100:
            pytest.skip("Need at least 100 real queries for perf test")
        start = time.perf_counter()
        for sql in sample:
            detect_antipatterns(sql, engine="postgres")
        elapsed = time.perf_counter() - start
        # 60 секунд это очень щедро — для 961 запросов реально должно быть < 5
        assert elapsed < 60, (
            f"{len(sample)} queries за {elapsed:.1f}s > 60s budget"
        )
