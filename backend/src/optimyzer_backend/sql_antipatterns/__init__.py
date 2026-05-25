"""Sprint 8 Phase C — Universal SQL Antipatterns Engine.

Расширение Sprint 6 T-SQL antipatterns на универсальный engine с поддержкой
обоих движков (MSSQL + PostgreSQL).

Архитектура (ADR-045):
    sql_antipatterns/
    ├── models.py            ← SqlAntipattern + AntipatternSeverity + TSqlAntipattern (alias)
    ├── engine.py            ← главный dispatcher detect_antipatterns(sql, engine=...)
    ├── tsql/                ← 9 MSSQL детекторов (перенесены из sql/antipatterns.py)
    ├── postgres/            ← 15 PG детекторов + 1С-context helper
    └── shared/              ← общие утилиты

Public API:
    detect_antipatterns(sql, engine='mssql'|'postgres', force_1c_context=None)
        → list[SqlAntipattern]

Backward compat:
    sql.antipatterns.detect_antipatterns(tsql) делегирует сюда engine='mssql'.
"""

from optimyzer_backend.sql_antipatterns.engine import (
    POSTGRES_DETECTORS,
    TSQL_DETECTORS,
    detect_antipatterns,
)
from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
    TSqlAntipattern,
)

__all__ = [
    "AntipatternSeverity",
    "POSTGRES_DETECTORS",
    "SqlAntipattern",
    "TSQL_DETECTORS",
    "TSqlAntipattern",
    "detect_antipatterns",
]
