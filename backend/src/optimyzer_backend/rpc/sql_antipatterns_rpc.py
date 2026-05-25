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

from typing import Any, Optional

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.sql_antipatterns import detect_antipatterns
from optimyzer_backend.sql_antipatterns.postgres._helpers import detect_1c_context


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

    findings = detect_antipatterns(sql, engine=engine, force_1c_context=force_1c_context)  # type: ignore[arg-type]
    is_1c = (
        force_1c_context
        if force_1c_context is not None
        else detect_1c_context(sql)
    )

    return {
        "ok": True,
        "engine": engine,
        "is_1c_context": is_1c,
        "findings": [f.to_dict() for f in findings],
    }
