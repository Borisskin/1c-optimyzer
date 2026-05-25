"""PG antipattern #3 — ILIKE без pg_trgm GIN индекса (heuristic).

Pattern: WHERE col ILIKE '%text%' (или leading %)
Severity: WARNING
1С-aware: False (1С обычно использует LIKE с case-insensitive collation через mchar)

ILIKE с wildcards не использует обычный b-tree индекс. Для эффективного
поиска нужен GIN индекс на gin_trgm_ops из расширения pg_trgm.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_ilike_without_trgm(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []

    # sqlglot представляет ILIKE как exp.ILike (или exp.Like с insensitive=True).
    ilike_class = getattr(exp, "ILike", None)
    candidates: list[exp.Expression] = []
    if ilike_class is not None:
        candidates.extend(ast.find_all(ilike_class))

    # Fallback: regex-style detection через exp.Like с флагом.
    for like in ast.find_all(exp.Like):
        if getattr(like, "args", {}).get("insensitive"):
            candidates.append(like)

    for ilike in candidates:
        pattern = ilike.args.get("expression")
        if not isinstance(pattern, exp.Literal):
            continue
        text = pattern.this if isinstance(pattern.this, str) else ""
        if "%" not in text:
            continue

        findings.append(
            SqlAntipattern(
                code="ilike_without_trgm",
                title="ILIKE с wildcard — нужен pg_trgm GIN",
                description=(
                    f"ILIKE '{text[:40]}' использует wildcard — обычный b-tree индекс "
                    "не помогает. Без расширения pg_trgm и GIN индекса PostgreSQL "
                    "будет делать Seq Scan."
                ),
                severity=AntipatternSeverity.WARNING,
                dialect="postgres",
                snippet=f"ILIKE '{text[:60]}'",
                rationale=(
                    "ILIKE требует case-insensitive сравнения. Без pg_trgm + GIN "
                    "индекса по выражению lower(col) gin_trgm_ops — будет Seq Scan."
                ),
                recommendation=(
                    "Создайте расширение: `CREATE EXTENSION pg_trgm;`\n"
                    "Затем индекс: `CREATE INDEX idx_col_trgm ON tbl USING GIN (col gin_trgm_ops);`"
                ),
            )
        )
        break
    return findings


__all__ = ["detect_ilike_without_trgm"]
