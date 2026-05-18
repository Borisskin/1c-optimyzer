"""SQL Engine (Sprint 2 Phase B).

Заменяет OQL DSL Sprint 1: pre-built views (Phase D) + raw SQL для power users.
Выполняет только SELECT (ADR-019) — validator блокирует DDL/DML на parse stage,
а read-only DuckDB connection даёт defense-in-depth.
"""

from optimyzer_backend.sql.executor import SQLExecutionError, SQLExecutor
from optimyzer_backend.sql.schema_introspection import get_schema
from optimyzer_backend.sql.validator import SQLValidationError, validate_sql

__all__ = [
    "SQLExecutor",
    "SQLExecutionError",
    "validate_sql",
    "SQLValidationError",
    "get_schema",
]
