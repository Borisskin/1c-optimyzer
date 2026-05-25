"""Модели данных для sql_antipatterns engine (Sprint 8 Phase C).

ADR-045: единая модель SqlAntipattern для обоих движков. TSqlAntipattern
оставлен как alias для backward compat с Sprint 6 кодом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class AntipatternSeverity(str, Enum):
    """Универсальная severity для обоих движков.

    Sprint 6 (MSSQL) использовал: BLOCKER / CRITICAL / MAJOR / MINOR.
    Sprint 8 Phase C добавил PG c упрощённой схемой: CRITICAL / WARNING / INFO.

    Compat-mapping для CRITICAL/MAJOR/MINOR из старого T-SQL кода:
        BLOCKER → CRITICAL  (нет парсера → нечего смотреть, критично)
        CRITICAL → CRITICAL
        MAJOR    → WARNING
        MINOR    → INFO
    """

    # PG-стиль (рекомендуемое для нового кода)
    CRITICAL = "Critical"
    WARNING = "Warning"
    INFO = "Info"

    # Sprint 6 T-SQL legacy названия (сохраняем чтобы старые тесты прошли)
    BLOCKER = "Blocker"
    MAJOR = "Major"
    MINOR = "Minor"


@dataclass(frozen=True)
class SqlAntipattern:
    """Один обнаруженный антипаттерн.

    Возвращается всеми detector'ами обоих движков. Поле dialect позволяет
    UI/AI prompt различать MSSQL и PG контексты.
    """

    code: str  # уникальный код правила, например "offset_without_limit"
    title: str  # короткое название (русский)
    description: str  # развёрнутое объяснение проблемы
    severity: AntipatternSeverity
    dialect: Literal["mssql", "postgres"] = "mssql"
    is_1c_context_only: bool = False  # обнаружен только в 1С-context
    snippet: Optional[str] = None  # часть SQL с проблемой
    rationale: str = ""  # почему это antipattern (для AI prompt)
    recommendation: str = ""  # что делать (для UI hint)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "dialect": self.dialect,
            "is_1c_context_only": self.is_1c_context_only,
            "snippet": self.snippet,
            "rationale": self.rationale,
            "recommendation": self.recommendation,
        }


# ----------------------------------------------------------------------------
# Backward compat alias для Sprint 6 T-SQL кода.
# Старый код импортировал TSqlAntipattern из sql.antipatterns — оставляем
# имя как alias, в реальности это та же SqlAntipattern.
# ----------------------------------------------------------------------------

TSqlAntipattern = SqlAntipattern


__all__ = [
    "AntipatternSeverity",
    "SqlAntipattern",
    "TSqlAntipattern",
]
