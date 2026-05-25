"""PG antipattern #2 — Large OFFSET pagination (deep paging).

Pattern: OFFSET N где N > 1000
Severity: WARNING (CRITICAL если N > 10000)
1С-aware: False

Глубокое OFFSET pagination — классическая проблема PG. Сканирование
всех пропускаемых строк делает время линейно зависимым от offset.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)

_DEEP_PAGINATION = 1_000
_VERY_DEEP_PAGINATION = 10_000


def _extract_offset_int(offset_node: exp.Expression) -> int | None:
    """Пытаемся извлечь числовой offset (literal). Параметризованный → None."""
    if offset_node is None:
        return None
    expr = offset_node.expression if isinstance(offset_node, exp.Offset) else offset_node
    if isinstance(expr, exp.Literal) and expr.is_int:
        try:
            return int(expr.this)
        except (ValueError, TypeError):
            return None
    return None


def detect_large_offset_pagination(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for offset_node in ast.find_all(exp.Offset):
        value = _extract_offset_int(offset_node)
        if value is None or value < _DEEP_PAGINATION:
            continue

        if value >= _VERY_DEEP_PAGINATION:
            severity = AntipatternSeverity.CRITICAL
            extra = " Время выполнения растёт линейно — pagination становится непригодным."
        else:
            severity = AntipatternSeverity.WARNING
            extra = ""

        findings.append(
            SqlAntipattern(
                code="large_offset_pagination",
                title=f"Большое OFFSET значение ({value})",
                description=(
                    f"OFFSET {value} означает что PostgreSQL прочитает и отбросит "
                    f"{value} строк прежде чем начнёт возвращать результат." + extra
                ),
                severity=severity,
                dialect="postgres",
                snippet=f"OFFSET {value}",
                rationale=(
                    "PostgreSQL не имеет 'index skip' для OFFSET — каждая строка "
                    "до offset должна быть прочитана, проверена и отброшена."
                ),
                recommendation=(
                    "Используйте keyset pagination: вместо `OFFSET 50000 LIMIT 100` "
                    "сохраните `last_id` предыдущей страницы и используйте "
                    "`WHERE id > :last_id ORDER BY id LIMIT 100`."
                ),
            )
        )
        break
    return findings


__all__ = ["detect_large_offset_pagination"]
