"""PG antipattern #6 — JSONB операции без GIN индекса (heuristic, INFO).

Pattern: WHERE col @> '...' | col -> 'key' | col ->> 'key' = '...'
Severity: INFO (мы не знаем есть ли индекс — только намёк)
1С-aware: False

JSONB без GIN индекса = Seq Scan. Мы не имеем доступа к схеме чтобы
проверить наличие индекса, поэтому это намёк а не ошибка.
"""

from __future__ import annotations

import re

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)

# Regex для JSONB операторов (sqlglot не всегда классифицирует их идеально).
_JSONB_OPS = re.compile(r"(@>|<@|\?\||\?&|\?|->>?|#>>?|#-|@\?|@@)", re.IGNORECASE)


def detect_jsonb_without_gin(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    try:
        sql_text = ast.sql(dialect="postgres")
    except Exception:  # noqa: BLE001
        return findings

    if not _JSONB_OPS.search(sql_text):
        return findings

    findings.append(
        SqlAntipattern(
            code="jsonb_without_gin",
            title="JSONB операции — проверьте наличие GIN индекса",
            description=(
                "В запросе используются JSONB операторы (@>, ->, ->>, #>...). "
                "Без GIN индекса на этой JSONB колонке PostgreSQL будет делать "
                "Seq Scan. Проверьте наличие индекса в схеме."
            ),
            severity=AntipatternSeverity.INFO,
            dialect="postgres",
            snippet=None,
            rationale=(
                "JSONB операторы containment/path требуют GIN индекс с jsonb_ops "
                "или jsonb_path_ops opclass для эффективного поиска."
            ),
            recommendation=(
                "Если есть селективная JSONB колонка — создайте GIN индекс: "
                "`CREATE INDEX idx_col_gin ON tbl USING GIN (json_col jsonb_path_ops);`"
            ),
        )
    )
    return findings


__all__ = ["detect_jsonb_without_gin"]
