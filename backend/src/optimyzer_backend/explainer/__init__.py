"""Sprint 3 — explainer engine.

Hybrid classifier:
    - rule_loader: читает explainers/*.md → markdown с YAML frontmatter.
    - classifier: pattern matching, возвращает первое matching правило.
    - claude_client: AI-генерация conversational объяснения (Phase F).

Public API:
    from optimyzer_backend.explainer import ExplainerEngine, RuleMatch
"""

from optimyzer_backend.explainer.classifier import ExplainerEngine, RuleMatch
from optimyzer_backend.explainer.rule_loader import Rule, load_rules

__all__ = ["ExplainerEngine", "RuleMatch", "Rule", "load_rules"]
