"""Sprint 4 — Native rule engine для SDBL-запросов.

Загружает правила из markdown-файлов и матчит их против текста запроса
через regex. Каждый match становится Finding с line/col ranges.

Формат правила (.md):

    ---
    id: virtual_table_in_join
    severity: warning           # critical | warning | info
    category: performance       # performance | correctness | style
    match_type: regex_lines     # пока единственный тип
    patterns:
      - '(?im)ВНУТРЕННЕЕ\\s+СОЕДИНЕНИЕ\\s+\\S+\\.Остатки'
    tags: [tsup-2.13.4, expert-10]
    ---

    # Title

    Markdown body с объяснением и примером переписывания.

YAML subset parser переиспользуем из explainer.rule_loader — это даёт
консистентность и не плодит зависимостей.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from optimyzer_backend.explainer.rule_loader import _parse_yaml_subset

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class NativeRule:
    id: str
    severity: str  # "critical" | "warning" | "info"
    category: str  # "performance" | "correctness" | "style" | "semantic"
    patterns: list[re.Pattern[str]] = field(default_factory=list)
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    source_file: str = ""
    # Sprint 5 — semantic rules: список требований к контексту.
    # Если содержит "configuration_metadata" — rule запустится только если
    # подключён ConfigurationMetadataStore.
    requires: list[str] = field(default_factory=list)
    # Sprint 5 — имя функции-чекера в semantic_checks.SEMANTIC_CHECKS.
    # None → обычное regex-правило (Sprint 4 поведение).
    check_name: str | None = None


@dataclass
class Finding:
    """Один найденный антипаттерн в запросе. Координаты — 1-based, как у
    LSP / CodeMirror diagnostics: line_start <= line_end, col_start inclusive,
    col_end exclusive."""

    source: str  # "native" — пока единственный источник; зарезервировано под "bsl-language-server"
    rule_id: str
    severity: str
    category: str
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    message: str
    explanation_md: str
    tags: list[str] = field(default_factory=list)
    solution_template_id: str | None = None  # placeholder под Sprint 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "message": self.message,
            "explanation_md": self.explanation_md,
            "tags": self.tags,
            "solution_template_id": self.solution_template_id,
        }


def load_native_rules(rules_dir: Path) -> list[NativeRule]:
    """Загружает все *.md из rules_dir + подкаталогов.

    README.md в корне rules_dir пропускается (это документация формата).
    Сломанные правила (невалидный YAML, нет id) пропускаются молча,
    чтобы один битый файл не валил весь engine.
    """
    if not rules_dir.is_dir():
        return []
    rules: list[NativeRule] = []
    for md_path in sorted(rules_dir.rglob("*.md")):
        if md_path.name.lower() == "readme.md" and md_path.parent == rules_dir:
            continue
        try:
            rule = _parse_rule_file(md_path)
            if rule is not None:
                rules.append(rule)
        except Exception:
            continue
    return rules


def _parse_rule_file(path: Path) -> NativeRule | None:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    frontmatter = _parse_yaml_subset(match.group(1))
    body = match.group(2).lstrip()
    rule_id = frontmatter.get("id")
    if not rule_id:
        return None

    raw_patterns = frontmatter.get("patterns") or []
    compiled: list[re.Pattern[str]] = []
    if isinstance(raw_patterns, list):
        for p in raw_patterns:
            if not isinstance(p, str):
                continue
            try:
                compiled.append(re.compile(p))
            except re.error:
                continue

    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""

    tags_raw = frontmatter.get("tags") or []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []

    requires_raw = frontmatter.get("requires") or []
    requires = [str(r) for r in requires_raw] if isinstance(requires_raw, list) else []

    check_name_raw = frontmatter.get("check_name")
    check_name = str(check_name_raw) if check_name_raw else None

    return NativeRule(
        id=str(rule_id),
        severity=str(frontmatter.get("severity", "warning")),
        category=str(frontmatter.get("category", "performance")),
        patterns=compiled,
        title=title,
        body=body,
        tags=tags,
        source_file=str(path),
        requires=requires,
        check_name=check_name,
    )


def analyze(
    query_text: str,
    rules: list[NativeRule],
    config_store: "object | None" = None,  # ConfigurationMetadataStore | None
) -> list[Finding]:
    """Прогоняет query_text через каждое правило, возвращает findings.

    Sprint 5: rule с requires=[configuration_metadata] запускается только
    если передан config_store И он is_indexed(). Иначе — silent skip
    (не false positive, не warning). Rule с category=="semantic" вызывает
    semantic check вместо regex matching.

    Дедупликация одного и того же rule на одинаковом range — на стороне
    aggregator, а не здесь.
    """
    findings: list[Finding] = []
    if not query_text:
        return findings

    config_available = config_store is not None and getattr(
        config_store, "is_indexed", lambda: False
    )()

    # Импорт здесь — чтобы избежать circular import (semantic_checks
    # может импортировать analyze для подвыборки нативных rules).
    from optimyzer_backend.query_analyzer.semantic_checks import (
        run_semantic_check,
    )

    for rule in rules:
        # Skip rules чьи requires не выполнены (Sprint 5: silent skip)
        if "configuration_metadata" in rule.requires and not config_available:
            continue

        if rule.category == "semantic":
            if rule.check_name is None:
                continue  # некорректное rule, пропускаем
            findings.extend(
                run_semantic_check(query_text, rule, config_store)
            )
            continue

        # Обычные regex rules (Sprint 4 поведение)
        for pattern in rule.patterns:
            for m in pattern.finditer(query_text):
                ls, cs = _offset_to_line_col(query_text, m.start())
                le, ce = _offset_to_line_col(query_text, m.end())
                findings.append(
                    Finding(
                        source="native",
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        line_start=ls,
                        line_end=le,
                        col_start=cs,
                        col_end=ce,
                        message=rule.title or rule.id,
                        explanation_md=rule.body,
                        tags=list(rule.tags),
                    )
                )
    return findings


def _offset_to_line_col(text: str, offset: int) -> tuple[int, int]:
    """Конвертит абсолютный offset в (line, col), оба 1-based.

    Строки разделены `\\n` или `\\r\\n` (последний считается одним разделителем).
    """
    if offset <= 0:
        return 1, 1
    if offset > len(text):
        offset = len(text)
    prefix = text[:offset]
    # Нормализуем CRLF → LF чтобы счётчик строк не плыл
    prefix_norm = prefix.replace("\r\n", "\n").replace("\r", "\n")
    line_idx = prefix_norm.count("\n")
    last_nl = prefix_norm.rfind("\n")
    col = len(prefix_norm) - (last_nl + 1) if last_nl >= 0 else len(prefix_norm)
    return line_idx + 1, col + 1
