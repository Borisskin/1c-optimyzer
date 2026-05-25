"""PG antipattern #13 — ORDER BY RANDOM() LIMIT N.

Pattern: ORDER BY RANDOM() | ORDER BY random() (с/без LIMIT)
Severity: WARNING (CRITICAL если LIMIT отсутствует или большой)
1С-aware: False

Full table scan + sort всей таблицы. Очень медленно для больших таблиц.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def _expression_is_random(expr: exp.Expression) -> bool:
    """Проверяет — это функция RANDOM() / random() / RAND()?"""
    # sqlglot has dedicated exp.Rand class для PG random()/MSSQL RAND()
    if hasattr(exp, "Rand") and isinstance(expr, getattr(exp, "Rand")):
        return True
    if isinstance(expr, exp.Func):
        try:
            name = expr.sql_name().upper()
        except Exception:  # noqa: BLE001
            name = type(expr).__name__.upper()
        if name in ("RANDOM", "RAND"):
            return True
    if isinstance(expr, exp.Anonymous):
        name = (expr.name or "").upper()
        if name in ("RANDOM", "RAND"):
            return True
    return False


def detect_order_by_random_with_limit(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for order in ast.find_all(exp.Order):
        order_expressions = order.args.get("expressions") or []
        has_random = False
        for o in order_expressions:
            target = o.this if isinstance(o, exp.Ordered) else o
            # ищем RANDOM в дереве выражения order
            for desc in target.walk():
                node = desc[0] if isinstance(desc, tuple) else desc
                if _expression_is_random(node):
                    has_random = True
                    break
            if has_random:
                break
        if not has_random:
            continue

        # Проверим LIMIT в parent SELECT
        parent_select = order.parent
        while parent_select is not None and not isinstance(parent_select, exp.Select):
            parent_select = parent_select.parent

        severity = AntipatternSeverity.CRITICAL
        if parent_select is not None and parent_select.args.get("limit") is not None:
            severity = AntipatternSeverity.WARNING

        findings.append(
            SqlAntipattern(
                code="order_by_random_with_limit",
                title="ORDER BY RANDOM() — full sort случайной таблицы",
                description=(
                    "ORDER BY RANDOM() требует Seq Scan всей таблицы + Sort. "
                    "Очень медленно на больших таблицах — независимо от LIMIT, "
                    "PostgreSQL сначала вычислит RANDOM() для каждой строки и "
                    "отсортирует, и только потом возьмёт первые N."
                ),
                severity=severity,
                dialect="postgres",
                snippet="ORDER BY RANDOM()",
                rationale=(
                    "Нет способа использовать индекс для случайного порядка — "
                    "сортировка обязательна, и она по полному датасету."
                ),
                recommendation=(
                    "Используйте `TABLESAMPLE BERNOULLI (1)` для быстрой случайной "
                    "выборки, либо ID-based random: "
                    "`WHERE id = (SELECT id FROM tbl OFFSET floor(random()*N) LIMIT 1)`."
                ),
            )
        )
        break
    return findings


__all__ = ["detect_order_by_random_with_limit"]
