"""Backward-compat shim для Sprint 6 кода (Sprint 8 Phase C).

Реальная реализация переехала в optimyzer_backend.sql_antipatterns/.
Этот модуль остался как тонкая обёртка, чтобы старый код Sprint 6 не
сломался импортами `from optimyzer_backend.sql.antipatterns import ...`.

Архитектурное решение — ADR-045:
    - Новый код пишет: from optimyzer_backend.sql_antipatterns import detect_antipatterns
    - Старый код продолжает работать через этот shim (engine="mssql" по умолчанию)
"""

from __future__ import annotations

from optimyzer_backend.sql_antipatterns.engine import detect_antipatterns as _detect
from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
    TSqlAntipattern,
)


def detect_antipatterns(tsql: str) -> list[TSqlAntipattern]:
    """Legacy API Sprint 6 — анализирует T-SQL запрос с engine='mssql'.

    Для PG / нового кода используйте:
        from optimyzer_backend.sql_antipatterns import detect_antipatterns
        results = detect_antipatterns(sql, engine='postgres')
    """
    return _detect(tsql, engine="mssql")


__all__ = [
    "AntipatternSeverity",
    "SqlAntipattern",
    "TSqlAntipattern",
    "detect_antipatterns",
]
