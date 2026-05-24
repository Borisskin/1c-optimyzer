"""Парсер LSP/bsl-LS JSON output в наши Pydantic-модели (Sprint 6 Phase B).

Два пути использования:
    1. parse_lsp_diagnostic(d) — из LSP publishDiagnostics notification
    2. group_overlapping(diags, snippets_for) — дедупликация по Q6

Severity mapping (Q7): LSP severity (1-4) + bsl-LS DiagnosticSeverity hint
(в .codeDescription.href или tags) → наша Severity enum.

LSP severity:
    1 = Error
    2 = Warning
    3 = Information
    4 = Hint
"""

from __future__ import annotations

from typing import Optional

from .models import Diagnostic, DiagnosticGroup, Position, Range, Severity


# Маппинг bsl-LS rule code → наша Severity (категоризация Q7).
# Все 19 SDBL правил с явной severity, не зависящей от LSP integer.
_RULE_SEVERITY: dict[str, Severity] = {
    # BLOCKER — синтаксис/метаданные сломаны
    "QueryParseError": Severity.BLOCKER,
    "QueryToMissingMetadata": Severity.BLOCKER,
    # CRITICAL — гарантированная проблема
    "VirtualTableCallWithoutParameters": Severity.CRITICAL,
    "FieldsFromJoinsWithoutIsNull": Severity.CRITICAL,
    # MAJOR — антипаттерны производительности
    "JoinWithSubQuery": Severity.MAJOR,
    "JoinWithVirtualTable": Severity.MAJOR,
    "RefOveruse": Severity.MAJOR,
    "QueryNestedFieldsByDot": Severity.MAJOR,
    "FullOuterJoinQuery": Severity.MAJOR,
    "UnionAll": Severity.MAJOR,
    "SelectTopWithoutOrderBy": Severity.MAJOR,
    "IncorrectUseLikeInQuery": Severity.MAJOR,
    "LogicalOrInJoinQuerySection": Severity.MAJOR,
    "LogicalOrInTheWhereSectionOfQuery": Severity.MAJOR,
    "SameMetadataObjectAndChildNames": Severity.MAJOR,
    "ForbiddenMetadataName": Severity.MAJOR,
    # MINOR / INFO — стиль (toggle в Settings, default off в UI слое)
    "AssignAliasFieldsInQuery": Severity.MINOR,
    "UsingLikeInQuery": Severity.MINOR,
    "MultilineStringInQuery": Severity.MINOR,
}


def _lsp_severity_to_domain(lsp_severity: Optional[int]) -> Severity:
    """LSP severity (1-4) → наша Severity (fallback если rule неизвестен)."""
    mapping = {
        1: Severity.CRITICAL,  # LSP Error
        2: Severity.MAJOR,  # LSP Warning
        3: Severity.MINOR,  # LSP Information
        4: Severity.INFO,  # LSP Hint
    }
    return mapping.get(lsp_severity or 2, Severity.MAJOR)


def _severity_from_string(s: Optional[str]) -> Optional[Severity]:
    """bsl-LS отдаёт severity строкой в JsonReporter ('Warning', 'Error') —
    конвертируем если LSP integer недоступен."""
    if not s:
        return None
    mapping = {
        "Error": Severity.CRITICAL,
        "Warning": Severity.MAJOR,
        "Information": Severity.MINOR,
        "Hint": Severity.INFO,
    }
    return mapping.get(s)


def parse_lsp_diagnostic(raw: dict, sdbl_text: Optional[str] = None) -> Diagnostic:
    """Парсит один LSP Diagnostic из bsl-LS publishDiagnostics.

    Args:
        raw: dict как пришёл из bsl-LS (LSP формат, см. JsonReporter).
        sdbl_text: если передан, заполняем snippet — подстрока из SDBL по range.

    Returns:
        Нормализованный Diagnostic.
    """
    code = str(raw.get("code", ""))
    range_raw = raw.get("range", {})
    rng = Range(
        start=Position(
            line=int(range_raw.get("start", {}).get("line", 0)),
            character=int(range_raw.get("start", {}).get("character", 0)),
        ),
        end=Position(
            line=int(range_raw.get("end", {}).get("line", 0)),
            character=int(range_raw.get("end", {}).get("character", 0)),
        ),
    )

    # Severity — приоритет: explicit rule mapping > LSP integer > string > MAJOR.
    severity = _RULE_SEVERITY.get(code)
    if severity is None:
        severity = _severity_from_string(raw.get("severity"))
    if severity is None:
        lsp_int = raw.get("severity") if isinstance(raw.get("severity"), int) else None
        severity = _lsp_severity_to_domain(lsp_int)

    href = None
    code_desc = raw.get("codeDescription")
    if isinstance(code_desc, dict):
        href = code_desc.get("href")

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    snippet = _extract_snippet(sdbl_text, rng) if sdbl_text else None

    return Diagnostic(
        code=code,
        code_description_href=href,
        message=str(raw.get("message", "")),
        range=rng,
        severity=severity,
        source=str(raw.get("source", "bsl-language-server")),
        tags=[str(t) for t in tags],
        snippet=snippet,
    )


def _extract_snippet(text: str, rng: Range) -> Optional[str]:
    """Достаёт текст SDBL по range. Если range вне границ — None."""
    lines = text.splitlines()
    if rng.start.line >= len(lines):
        return None
    if rng.start.line == rng.end.line:
        line = lines[rng.start.line]
        return line[rng.start.character : rng.end.character]
    # Multi-line range — собираем.
    parts: list[str] = [lines[rng.start.line][rng.start.character :]]
    for i in range(rng.start.line + 1, min(rng.end.line, len(lines))):
        parts.append(lines[i])
    if rng.end.line < len(lines):
        parts.append(lines[rng.end.line][: rng.end.character])
    return "\n".join(parts)


def group_overlapping(diagnostics: list[Diagnostic]) -> list[DiagnosticGroup]:
    """Группирует overlapping diagnostics в одну UI card (Q6).

    Алгоритм:
        1. Сортируем по start position.
        2. Идём по списку, накапливая текущую группу пока range пересекаются.
        3. На разрыве — закрываем группу и начинаем новую.

    Severity группы = max из всех severity.
    """
    if not diagnostics:
        return []

    sorted_diags = sorted(
        diagnostics,
        key=lambda d: (d.range.start.line, d.range.start.character),
    )

    groups: list[DiagnosticGroup] = []
    current: list[Diagnostic] = [sorted_diags[0]]
    current_range = sorted_diags[0].range

    def close_current() -> None:
        # max severity внутри группы.
        primary = max(current, key=lambda d: d.severity.order)
        # Сортируем коды/сообщения по severity убыванию для UI.
        ordered = sorted(current, key=lambda d: -d.severity.order)
        groups.append(
            DiagnosticGroup(
                range=current_range,
                severity=primary.severity,
                codes=[d.code for d in ordered],
                messages=[d.message for d in ordered],
                snippet=primary.snippet,
                primary=primary,
            )
        )

    for diag in sorted_diags[1:]:
        if current_range.overlaps(diag.range):
            current.append(diag)
            # Расширяем range группы — берём union.
            current_range = _union_range(current_range, diag.range)
        else:
            close_current()
            current = [diag]
            current_range = diag.range
    close_current()
    return groups


def _union_range(a: Range, b: Range) -> Range:
    """Минимальный range покрывающий оба."""
    if (a.start.line, a.start.character) <= (b.start.line, b.start.character):
        start = a.start
    else:
        start = b.start
    if (a.end.line, a.end.character) >= (b.end.line, b.end.character):
        end = a.end
    else:
        end = b.end
    return Range(start=start, end=end)
