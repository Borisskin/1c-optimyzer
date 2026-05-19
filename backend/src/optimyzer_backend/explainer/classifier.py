"""Sprint 3 Phase E — pattern matcher.

ExplainerEngine.classify(features, applies_to) → первое matching правило,
с rendered template (`{{var}}` → значение из features).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from optimyzer_backend.explainer.rule_loader import Rule, RulePattern, load_rules


@dataclass
class RuleMatch:
    rule_id: str
    title: str
    body: str  # markdown body после template substitution
    applies_to: str
    priority: int


class ExplainerEngine:
    """Загружает правила и матчит их к feature dict."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self._rules: list[Rule] = []
        self.reload_rules()

    def reload_rules(self) -> None:
        self._rules = load_rules(self.rules_dir)

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    def classify(
        self,
        features: dict[str, Any],
        *,
        applies_to: str | None = None,
    ) -> RuleMatch | None:
        """Найти первое matching правило (sorted by priority DESC)."""
        for rule in self._rules:
            if applies_to is not None and rule.applies_to != applies_to:
                continue
            if all(_match_pattern(p, features) for p in rule.patterns):
                rendered = _render_template(rule.body, features)
                return RuleMatch(
                    rule_id=rule.id,
                    title=rule.title,
                    body=rendered,
                    applies_to=rule.applies_to,
                    priority=rule.priority,
                )
        return None


def _match_pattern(pat: RulePattern, features: dict[str, Any]) -> bool:
    if pat.field not in features:
        return False
    actual = features[pat.field]
    op = pat.operator
    expected = pat.value
    if op == "==":
        return _eq(actual, expected)
    if op == "!=":
        return not _eq(actual, expected)
    if op == ">=":
        return _gte(actual, expected)
    if op == "<=":
        return _lte(actual, expected)
    if op == ">":
        return _gt(actual, expected)
    if op == "<":
        return _lt(actual, expected)
    if op == "in":
        return isinstance(expected, list) and actual in expected
    if op == "contains":
        return isinstance(actual, (str, list)) and expected in actual
    if op == "matches":
        return isinstance(actual, str) and re.search(str(expected), actual) is not None
    return False


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _gte(a: Any, b: Any) -> bool:
    try:
        return float(a) >= float(b)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _lte(a: Any, b: Any) -> bool:
    try:
        return float(a) <= float(b)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _gt(a: Any, b: Any) -> bool:
    try:
        return float(a) > float(b)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _lt(a: Any, b: Any) -> bool:
    try:
        return float(a) < float(b)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


_TEMPLATE_RE = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _render_template(body: str, features: dict[str, Any]) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if "." in key:
            # Dotted access: features.foo.bar
            parts = key.split(".")
            val: Any = features
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            return _stringify(val)
        return _stringify(features.get(key))

    return _TEMPLATE_RE.sub(replacer, body)


def _stringify(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, (list, tuple)):
        return ", ".join(_stringify(x) for x in v)
    return str(v)
