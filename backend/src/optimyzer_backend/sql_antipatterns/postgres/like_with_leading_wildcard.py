"""PG antipattern #4 — LIKE с leading wildcard.

Pattern: LIKE '%text' или LIKE '%text%'
Severity: WARNING
1С-aware: True (1С генерирует такое для частичного поиска,
            severity снижается до INFO в 1С-context)

Невозможен b-tree index seek — нужен либо Seq Scan, либо trgm/FTS.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_like_with_leading_wildcard(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for like in ast.find_all(exp.Like):
        # Пропускаем ILIKE (отдельный детектор)
        if getattr(like, "args", {}).get("insensitive"):
            continue
        pattern = like.args.get("expression")
        if not isinstance(pattern, exp.Literal):
            continue
        text = pattern.this if isinstance(pattern.this, str) else ""
        if not text.startswith("%"):
            continue

        severity = AntipatternSeverity.INFO if is_1c_context else AntipatternSeverity.WARNING
        note = (
            " (1С-context: типично для поиска по подстроке — рассмотрите pg_trgm)"
            if is_1c_context
            else ""
        )

        findings.append(
            SqlAntipattern(
                code="like_with_leading_wildcard",
                title="LIKE с ведущим % (Seq Scan)",
                description=(
                    f"LIKE '{text[:40]}' начинается с %. PostgreSQL не может "
                    f"использовать b-tree индекс — будет Seq Scan." + note
                ),
                severity=severity,
                dialect="postgres",
                is_1c_context_only=False,
                snippet=f"LIKE '{text[:60]}'",
                rationale=(
                    "B-tree индекс упорядочен по префиксу. Leading % требует "
                    "проверки каждой строки в таблице."
                ),
                recommendation=(
                    "Если поиск по подстроке нужен — установите pg_trgm: "
                    "`CREATE INDEX ... USING GIN (col gin_trgm_ops);`\n"
                    "Если только префиксный поиск — переформулируйте на LIKE 'text%'."
                ),
            )
        )
        break
    return findings


__all__ = ["detect_like_with_leading_wildcard"]
