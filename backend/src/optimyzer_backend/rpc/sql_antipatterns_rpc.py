"""Sprint 8 Phase C — RPC для SQL antipatterns engine.

Public RPC:
    sql_antipatterns.detect(sql, engine, force_1c_context=None)
        → {ok, findings: [...], engine, is_1c_context}

Используется из:
    - PlanAnalyzer (frontend): автодетект engine из ТЖ + dropdown для manual SQL
    - Можно вызывать из любого экрана где появляется SQL текст

Engine values:
    'mssql'    — T-SQL детекторы (9 правил Sprint 6)
    'postgres' — PG детекторы (15 правил Sprint 8 Phase C)
"""

from __future__ import annotations

import re
from typing import Any, Optional

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.sql_antipatterns import detect_antipatterns
from optimyzer_backend.sql_antipatterns.postgres._helpers import detect_1c_context

# 1С на MSSQL всегда оборачивает SQL в sp_executesql:
#   {call sp_executesql(N'SELECT ...', N'@P1 nvarchar(128)', N'%')}
#   exec sp_executesql N'SELECT ...', N'@P1 nvarchar(128)', @P1=N'%'
# Извлекаем первый аргумент (сам SQL) перед парсингом.
_SP_EXECUTESQL_RE = re.compile(
    r"""
    (?:
        \{call\s+sp_executesql\s*\(\s*   # ODBC: {call sp_executesql(
        |
        (?:exec(?:ute)?\s+)?sp_executesql\s+   # T-SQL: exec sp_executesql
    )
    N'((?:[^']|'')*)'   # первый аргумент: N'<sql>'
    (?:\s*,|\s*\)|\s*$)  # дальше запятая или закрывающая скобка или конец
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)


def _unwrap_sp_executesql(sql: str) -> str:
    """Извлекает тело SQL из exec sp_executesql / {call sp_executesql(...)}.

    1С всегда передаёт запросы через sp_executesql — без этого sqlglot
    получает обёртку вместо реального SQL и выдаёт parse_error БЛОКЕР.
    """
    stripped = sql.strip()
    m = _SP_EXECUTESQL_RE.match(stripped)
    if m:
        return m.group(1).replace("''", "'")
    return sql


@rpc("sql_antipatterns.detect")
def detect_rpc(
    sql: str,
    engine: str = "mssql",
    force_1c_context: Optional[bool] = None,
) -> dict[str, Any]:
    """Анализирует SQL и возвращает обнаруженные антипаттерны.

    Args:
        sql: SQL текст (T-SQL или PG)
        engine: 'mssql' | 'postgres'
        force_1c_context: переопределяет heuristic detect_1c_context.
                          None → авто-detection.

    Returns:
        {
            "ok": True,
            "engine": "mssql" | "postgres",
            "is_1c_context": bool,
            "findings": [
                {
                    "code": "offset_without_limit",
                    "title": "...",
                    "description": "...",
                    "severity": "Warning",
                    "dialect": "postgres",
                    "is_1c_context_only": False,
                    "snippet": "OFFSET 100",
                    "rationale": "...",
                    "recommendation": "...",
                },
                ...
            ]
        }
    """
    if not isinstance(sql, str):
        return {"ok": False, "error": "sql must be string"}

    if engine not in ("mssql", "postgres"):
        return {"ok": False, "error": f"engine must be 'mssql' or 'postgres', got {engine!r}"}

    # 1С на MSSQL всегда оборачивает запросы в sp_executesql — извлекаем тело.
    effective_sql = _unwrap_sp_executesql(sql) if engine == "mssql" else sql

    findings = detect_antipatterns(effective_sql, engine=engine, force_1c_context=force_1c_context)  # type: ignore[arg-type]
    is_1c = (
        force_1c_context
        if force_1c_context is not None
        else detect_1c_context(effective_sql)
    )

    # parse_error — это не антипаттерн, а сигнал что статический парсер sqlglot не
    # разобрал запрос (частое на специфичном T-SQL от 1С — ~80%+ боевых запросов).
    # Выносим в отдельный флаг parse_failed и убираем из findings, чтобы UI не
    # показывал это как «найденную проблему» с техническими деталями sqlglot.
    parse_failed = any(f.code == "parse_error" for f in findings)
    findings = [f for f in findings if f.code != "parse_error"]

    return {
        "ok": True,
        "engine": engine,
        "is_1c_context": is_1c,
        "parse_failed": parse_failed,
        "findings": [f.to_dict() for f in findings],
    }
