"""Sprint 4 — Главный entry point Query Analyzer'а.

`analyze_query(query_text)` объединяет findings из:
  - Native rule engine (Sprint 4 — основной источник)
  - BSL Language Server (Sprint 4 — placeholder, всегда [])

Дедупликация: если два findings от разных rules матчат **идентичный** range
с одинаковой темой (category), оставляем более специфичный (с не пустыми
тегами). Sprint 4 native-only — дедупликация работает между разными native
rules если они случайно матчат одну и ту же подстроку.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from optimyzer_backend.query_analyzer.bsl_ls_client import BSLLanguageServerClient
from optimyzer_backend.query_analyzer.native_rules import (
    Finding,
    NativeRule,
    analyze as native_analyze,
    load_native_rules,
)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


class QueryAnalyzer:
    """Singleton-friendly анализатор. Lazy load native rules."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self._native_rules: list[NativeRule] = []
        self._bsl_client = BSLLanguageServerClient()
        self.reload_rules()

    def reload_rules(self) -> None:
        self._native_rules = load_native_rules(self.rules_dir)

    @property
    def native_rules(self) -> list[NativeRule]:
        return self._native_rules

    @property
    def bsl_ls_available(self) -> bool:
        return self._bsl_client.available

    def analyze(self, query_text: str) -> dict[str, Any]:
        native = native_analyze(query_text, self._native_rules)
        # BSL LS placeholder — Sprint 4 всегда возвращает [].
        bsl_diags = self._bsl_client.analyze_query(query_text)
        bsl_findings = [_diag_to_finding(d) for d in bsl_diags]

        merged = _merge_and_dedupe(native + bsl_findings)
        merged.sort(key=lambda f: (f.line_start, f.col_start, _SEVERITY_ORDER.get(f.severity, 9)))

        summary = {
            "critical": sum(1 for f in merged if f.severity == "critical"),
            "warning": sum(1 for f in merged if f.severity == "warning"),
            "info": sum(1 for f in merged if f.severity == "info"),
        }

        return {
            "query_text": query_text,
            "findings": [f.to_dict() for f in merged],
            "bsl_ls_available": self.bsl_ls_available,
            "summary": summary,
            "rules_count": len(self._native_rules),
        }


def _diag_to_finding(d: Any) -> Finding:
    """Конверсия BSLDiagnostic → Finding. Заготовка под Sprint 5+."""
    return Finding(
        source="bsl-language-server",
        rule_id=f"BSL-LS-{d.code}",
        severity=_normalize_severity(d.severity),
        category="performance",
        line_start=d.line_start,
        line_end=d.line_end,
        col_start=d.col_start,
        col_end=d.col_end,
        message=d.message,
        explanation_md=d.message,
        tags=["bsl-language-server"],
    )


def _normalize_severity(s: str) -> str:
    s = s.lower()
    if s in ("error", "critical"):
        return "critical"
    if s in ("warning", "warn"):
        return "warning"
    return "info"


def _merge_and_dedupe(findings: list[Finding]) -> list[Finding]:
    """Убирает дубликаты по (line_start, line_end, col_start, col_end, category)
    оставляя более специфичный (native rule приоритетнее BSL LS).
    """
    by_key: dict[tuple[int, int, int, int, str], Finding] = {}
    for f in findings:
        key = (f.line_start, f.line_end, f.col_start, f.col_end, f.category)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = f
            continue
        # native приоритетнее BSL LS (русское объяснение по ЦУП)
        if existing.source == "bsl-language-server" and f.source == "native":
            by_key[key] = f
    return list(by_key.values())
