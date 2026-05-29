"""Sprint 8 Phase C — главный dispatcher для SQL antipatterns engine.

Принимает SQL текст + engine ('mssql' | 'postgres') и возвращает список
обнаруженных SqlAntipattern. Парсит SQL через sqlglot с указанным dialect,
вызывает все детекторы для этого dialect, собирает результаты и сортирует
по severity.

Robustness: один сломанный detector не валит весь анализ (обёрнут в try/except).
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

import sqlglot

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres import (
    POSTGRES_DETECTORS,
    detect_1c_context,
)
from optimyzer_backend.sql_antipatterns.tsql import TSQL_DETECTORS

logger = logging.getLogger(__name__)

# Лимит размера SQL — защита от OOM на гигантских запросах (типичные 1С SQL < 10KB).
_MAX_SQL_LEN = 200_000  # 200KB

# Порядок severity для сортировки (CRITICAL первым).
_SEVERITY_ORDER = {
    AntipatternSeverity.CRITICAL: 0,
    AntipatternSeverity.BLOCKER: 1,
    AntipatternSeverity.MAJOR: 2,
    AntipatternSeverity.WARNING: 3,
    AntipatternSeverity.MINOR: 4,
    AntipatternSeverity.INFO: 5,
}


def detect_antipatterns(
    sql: str,
    engine: Literal["mssql", "postgres"] = "mssql",
    force_1c_context: Optional[bool] = None,
) -> list[SqlAntipattern]:
    """Анализирует SQL запрос и возвращает список обнаруженных антипаттернов.

    Args:
        sql: исходный SQL текст
        engine: 'mssql' (T-SQL диалект) или 'postgres' (PG диалект)
        force_1c_context: если задан — переопределяет heuristic для 1С-context.
                          None → автоматически detect_1c_context(sql)

    Returns:
        Список SqlAntipattern, отсортированный по severity (CRITICAL первым).
        Пустой если запрос чистый или пустой.
    """
    if not sql or not isinstance(sql, str):
        return []
    if len(sql) > _MAX_SQL_LEN:
        logger.warning(
            "SQL too long (%d > %d) — antipatterns analysis skipped", len(sql), _MAX_SQL_LEN
        )
        return []

    is_1c = (
        force_1c_context
        if force_1c_context is not None
        else detect_1c_context(sql)
    )

    # Парсинг — если упал, возвращаем parse_error как antipattern.
    # sqlglot использует dialect='tsql' для MSSQL — маппим публичное 'mssql'.
    sqlglot_dialect = "tsql" if engine == "mssql" else engine
    try:
        ast = sqlglot.parse_one(sql, dialect=sqlglot_dialect)
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        # НЕ светим sqlglot-детали в UI и НЕ помечаем как BLOCKER. 1С генерирует
        # специфичный T-SQL, который статический парсер sqlglot часто не разбирает
        # (на боевых данных это большинство запросов). Это ограничение статического
        # анализатора, а НЕ проблема запроса. RPC-слой вынесет это в отдельный флаг
        # parse_failed; здесь — мягкое INFO без технических подробностей sqlglot.
        logger.debug("sqlglot parse failed (dialect=%s): %s", sqlglot_dialect, e)
        return [
            SqlAntipattern(
                code="parse_error",
                title="Статический разбор недоступен",
                description=(
                    "Запрос использует синтаксис, который статический анализатор "
                    "не разобрал. Анализ плана и AI-разбор доступны."
                ),
                severity=AntipatternSeverity.INFO,
                dialect=engine,
                rationale="",
                recommendation="",
            )
        ]

    if ast is None:
        return []

    detectors = POSTGRES_DETECTORS if engine == "postgres" else TSQL_DETECTORS
    findings: list[SqlAntipattern] = []

    for detector in detectors:
        try:
            findings.extend(detector(ast, is_1c_context=is_1c))
        except Exception as e:  # noqa: BLE001
            # Robustness — один сломанный detector не должен валить весь анализ
            logger.warning(
                "Detector %s failed on SQL (first 100 chars: %r): %s",
                detector.__name__,
                sql[:100],
                e,
            )

    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
    return findings


__all__ = [
    "POSTGRES_DETECTORS",
    "TSQL_DETECTORS",
    "detect_antipatterns",
]
