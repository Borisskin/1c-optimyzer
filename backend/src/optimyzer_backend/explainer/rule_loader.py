"""Sprint 3 Phase E — markdown rule loader.

Каждое правило — отдельный .md файл с YAML frontmatter:

    ---
    id: deadlock_parallel_posting
    applies_to: deadlock
    priority: 100
    patterns:
      - field: event_type
        value: TDEADLOCK
      - field: participants_count
        operator: ">="
        value: 2
    ---

    # Title

    Markdown body. Поддерживает плейсхолдеры `{{var}}` которые заполняются
    classifier-ом при формировании RuleMatch.

Frontmatter parsing — без зависимости от PyYAML (минимальный YAML subset:
mappings, sequences, scalars, ничего изысканного).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RulePattern:
    field: str
    operator: str = "=="  # ==, !=, >=, <=, matches (regex), in, contains
    value: Any = None


@dataclass
class Rule:
    id: str
    applies_to: str  # 'deadlock' / 'operation' / 'session' / 'lock' / 'exception' / 'slow_op'
    priority: int = 0
    patterns: list[RulePattern] = field(default_factory=list)
    title: str = ""
    body: str = ""  # markdown body с плейсхолдерами
    source_file: str = ""


def load_rules(rules_dir: Path) -> list[Rule]:
    """Загружает все *.md файлы из rules_dir + рекурсивно из подкаталогов.

    README.md в корне rules_dir игнорируется (это документация формата).
    Правила сортируются по priority DESC (выше — сначала проверяется).
    """
    if not rules_dir.is_dir():
        return []
    rules: list[Rule] = []
    for md_path in sorted(rules_dir.rglob("*.md")):
        if md_path.name.lower() == "readme.md" and md_path.parent == rules_dir:
            continue
        try:
            rule = _parse_rule_file(md_path)
            if rule is not None:
                rules.append(rule)
        except Exception:
            # Поломанный rule не должен крашить весь engine
            continue
    rules.sort(key=lambda r: (-r.priority, r.id))
    return rules


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_rule_file(path: Path) -> Rule | None:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    frontmatter = _parse_yaml_subset(match.group(1))
    body = match.group(2).lstrip()
    rule_id = frontmatter.get("id")
    applies_to = frontmatter.get("applies_to")
    if not rule_id or not applies_to:
        return None
    # Title — первая # строка из body
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    patterns_raw = frontmatter.get("patterns") or []
    patterns: list[RulePattern] = []
    if isinstance(patterns_raw, list):
        for p in patterns_raw:
            if not isinstance(p, dict):
                continue
            patterns.append(
                RulePattern(
                    field=str(p.get("field", "")),
                    operator=str(p.get("operator", "==")),
                    value=p.get("value"),
                )
            )
    return Rule(
        id=str(rule_id),
        applies_to=str(applies_to),
        priority=int(frontmatter.get("priority", 0)),
        patterns=patterns,
        title=title,
        body=body,
        source_file=str(path),
    )


# ---------- minimal YAML subset parser ----------
# Поддерживаем: mappings вложенные, sequences ('- ...'), scalars (str/int/bool/null).
# Достаточно для наших frontmatter правил, без зависимости от PyYAML.


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    pos = 0
    result, _ = _parse_block(lines, pos, indent=0)
    return result if isinstance(result, dict) else {}


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar(value: str) -> Any:
    s = value.strip()
    if s == "" or s == "null" or s == "~":
        return None
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    # Inline list [a, b, c] — Sprint 5: парсим как list[scalar].
    # Поддерживает строки (с/без кавычек), числа, bool.
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        # Простой split по запятым (не учитывает вложенные [] — для нас этого достаточно).
        items = [item.strip() for item in inner.split(",")]
        return [_parse_scalar(item) for item in items if item]
    # Quoted string
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    # Try int
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    """Parses block-level scalar, mapping or sequence at given indent.

    Returns (parsed_value, next_pos).
    """
    pos = start
    # Skip blank
    while pos < len(lines) and (not lines[pos].strip() or lines[pos].lstrip().startswith("#")):
        pos += 1
    if pos >= len(lines):
        return None, pos

    line = lines[pos]
    cur_indent = _line_indent(line)
    if cur_indent < indent:
        return None, pos

    if line.lstrip().startswith("- "):
        # Sequence at this indent
        seq: list[Any] = []
        while pos < len(lines):
            l = lines[pos]
            if not l.strip() or l.lstrip().startswith("#"):
                pos += 1
                continue
            if _line_indent(l) < indent:
                break
            if not l.lstrip().startswith("- "):
                break
            content = l.lstrip()[2:]  # after "- "
            if ":" in content and not content.startswith(("'", '"')):
                # Inline mapping inside sequence item — collect on same line + nested deeper lines
                # We treat the rest as a single mapping entry; the parser supports
                # multi-key items by parsing successive 'key: value' on same indent inside the item.
                # Easiest: synthesize a virtual block starting at this line by replacing "- " with "  "
                # then parse mapping.
                lines_view = list(lines)
                lines_view[pos] = (" " * (cur_indent + 2)) + content
                item, pos = _parse_block(lines_view, pos, indent=cur_indent + 2)
            else:
                item = _parse_scalar(content)
                pos += 1
            seq.append(item)
        return seq, pos

    # Otherwise mapping at this indent
    mapping: dict[str, Any] = {}
    while pos < len(lines):
        l = lines[pos]
        if not l.strip() or l.lstrip().startswith("#"):
            pos += 1
            continue
        l_indent = _line_indent(l)
        if l_indent < indent:
            break
        if l_indent > indent:
            # Should have been consumed by recursive call
            pos += 1
            continue
        stripped = l.strip()
        if stripped.startswith("- "):
            # Sequence at same indent inside mapping isn't valid here — caller expected mapping
            break
        if ":" not in stripped:
            break
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Value is on next line(s) — nested block
            pos += 1
            value, pos = _parse_block(lines, pos, indent=indent + 2)
            mapping[key] = value
        else:
            mapping[key] = _parse_scalar(rest)
            pos += 1
    return mapping, pos
