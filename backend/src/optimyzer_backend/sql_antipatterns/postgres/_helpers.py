"""Helpers для PG детекторов.

ADR-046: 1С-context detection — regex heuristic. Если в SQL встречаются
типичные 1С таблицы (_reference\\d+, _document\\d+, _accumrg\\d+, ...) или
типы (mchar/mvarchar) — обрабатываем SQL как генерированный 1С и
исключаем некоторые false-positives.
"""

from __future__ import annotations

import re
from typing import Optional

from sqlglot import exp

# Типичные 1С-таблицы в PG (lowercase из-за PG case-folding) и MSSQL (с dbo. префиксом).
# Покрываем оба случая: чистый PG identifier И MSSQL-style dbo._reference15 / [_Reference15].
_1C_TABLE_PATTERN = re.compile(
    r"(?:\bdbo\.|\bdbo\.\[|\[|\b)_(?:reference|document|accumrg|accumrgt|inforg|enum|const|seq|chrc|node|fld|pkg|task|bp|crrd|crab|crref|accrg|accrged)\d+",
    re.IGNORECASE,
)
# Типы 1С PG extension: mchar, mvarchar, fulleq.
# Поддерживаем оба синтаксиса: `col::mchar` и `CAST(col AS mchar)`.
_1C_TYPE_PATTERN = re.compile(
    r"(?:::|\bAS\s+)(mchar|mvarchar|fulleq)\b", re.IGNORECASE
)


def detect_1c_context(sql: str) -> bool:
    """Heuristic: SQL содержит 1С-specific identifiers?

    Возвращает True если найдена хотя бы одна 1С таблица или тип mchar/mvarchar.
    Используется для exclusion false-positives — например implicit cast
    mchar/mvarchar для 1С это нормально, а в чистом PG — antipattern.
    """
    if not sql:
        return False
    return bool(_1C_TABLE_PATTERN.search(sql) or _1C_TYPE_PATTERN.search(sql))


def safe_sql(node: exp.Expression, limit: int = 200) -> Optional[str]:
    """Безопасно получает SQL текст ноды для PG dialect."""
    try:
        s = node.sql(dialect="postgres")
        return s[:limit] if len(s) > limit else s
    except Exception:  # noqa: BLE001
        return None


__all__ = ["detect_1c_context", "safe_sql"]
