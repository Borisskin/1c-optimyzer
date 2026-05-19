"""Sprint 3 Phase E — Rule-based explainer tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.explainer import ExplainerEngine, load_rules
from optimyzer_backend.explainer.rule_loader import _parse_yaml_subset


# ---------- YAML subset parser ----------


def test_yaml_subset_simple_mapping() -> None:
    out = _parse_yaml_subset("id: foo\npriority: 100")
    assert out["id"] == "foo"
    assert out["priority"] == 100


def test_yaml_subset_string_with_special_chars() -> None:
    out = _parse_yaml_subset('value: "(?i)deadlock|взаимоблок"')
    assert out["value"] == "(?i)deadlock|взаимоблок"


def test_yaml_subset_nested_list() -> None:
    yaml_text = "patterns:\n  - field: event_type\n    value: TDEADLOCK\n  - field: count\n    value: 2"
    out = _parse_yaml_subset(yaml_text)
    assert isinstance(out["patterns"], list)
    assert len(out["patterns"]) == 2
    assert out["patterns"][0]["field"] == "event_type"
    assert out["patterns"][1]["value"] == 2


def test_yaml_subset_bool_and_null() -> None:
    out = _parse_yaml_subset("a: true\nb: false\nc: null")
    assert out["a"] is True
    assert out["b"] is False
    assert out["c"] is None


# ---------- Rule loading ----------


@pytest.fixture
def real_rules() -> Path:
    """Папка с настоящими правилами Sprint 3."""
    # backend/tests/test_explainer.py → backend/explainers/
    return Path(__file__).resolve().parents[1] / "explainers"


def test_load_real_rules_directory(real_rules: Path) -> None:
    rules = load_rules(real_rules)
    assert len(rules) >= 8, f"Expected >=8 rules, got {len(rules)}"
    rule_ids = {r.id for r in rules}
    assert "deadlock_lock_escalation" in rule_ids
    assert "deadlock_different_order" in rule_ids
    assert "slow_op_heavy_sql" in rule_ids


def test_rules_sorted_by_priority_desc(real_rules: Path) -> None:
    rules = load_rules(real_rules)
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities, reverse=True)


def test_rule_has_title_and_body(real_rules: Path) -> None:
    rules = load_rules(real_rules)
    for r in rules:
        assert r.title, f"Rule {r.id} без title"
        assert r.body, f"Rule {r.id} без body"


def test_load_rules_skips_readme(real_rules: Path) -> None:
    rules = load_rules(real_rules)
    ids = {r.id for r in rules}
    assert "readme" not in ids
    assert "README" not in ids


def test_load_rules_empty_dir(tmp_path: Path) -> None:
    assert load_rules(tmp_path) == []


def test_load_rules_nonexistent_dir() -> None:
    assert load_rules(Path("/does/not/exist")) == []


# ---------- ExplainerEngine.classify ----------


@pytest.fixture
def engine(real_rules: Path) -> ExplainerEngine:
    return ExplainerEngine(real_rules)


def test_classify_deadlock_lock_escalation(engine: ExplainerEngine) -> None:
    """1 region, 2+ participants → deadlock_lock_escalation (priority 100)."""
    match = engine.classify(
        {
            "event_type": "TDEADLOCK",
            "regions_count": 1,
            "participants_count": 2,
            "first_region": "РегистрНакопления.Партии",
        },
        applies_to="deadlock",
    )
    assert match is not None
    assert match.rule_id == "deadlock_lock_escalation"
    # Template substitution
    assert "РегистрНакопления.Партии" in match.body
    assert "2 участника" in match.body


def test_classify_deadlock_different_order(engine: ExplainerEngine) -> None:
    """2+ regions, 2+ participants → deadlock_different_order (priority 90)."""
    match = engine.classify(
        {
            "event_type": "TDEADLOCK",
            "regions_count": 2,
            "participants_count": 2,
        },
        applies_to="deadlock",
    )
    assert match is not None
    assert match.rule_id == "deadlock_different_order"


def test_classify_deadlock_fallback_to_single_resource(engine: ExplainerEngine) -> None:
    """Только event_type=TDEADLOCK (без regions/participants) → fallback."""
    match = engine.classify(
        {"event_type": "TDEADLOCK"},
        applies_to="deadlock",
    )
    assert match is not None
    assert match.rule_id == "deadlock_single_resource"


def test_classify_no_match_returns_none(engine: ExplainerEngine) -> None:
    match = engine.classify(
        {"event_type": "UNKNOWN_TYPE"},
        applies_to="deadlock",
    )
    assert match is None


def test_classify_respects_applies_to_filter(engine: ExplainerEngine) -> None:
    """Если applies_to='operation', deadlock-правила не матчатся."""
    match = engine.classify(
        {"event_type": "TDEADLOCK"},
        applies_to="operation",
    )
    # No operation rules match raw TDEADLOCK event
    assert match is None


def test_classify_slow_op_heavy_sql(engine: ExplainerEngine) -> None:
    match = engine.classify(
        {
            "operation": "Документ.Реализация.МодульОбъекта",
            "sql_share": 0.7,
            "sql_share_pct": 70,
            "sql_duration_ms": 5000,
            "calls": 100,
            "avg_duration_ms": 70,
        },
        applies_to="slow_op",
    )
    assert match is not None
    assert match.rule_id == "slow_op_heavy_sql"
    assert "Документ.Реализация" in match.body
    assert "70" in match.body


def test_classify_slow_op_call_cascade(engine: ExplainerEngine) -> None:
    match = engine.classify(
        {
            "operation": "Справочник.Контрагенты.МодульМенеджера",
            "calls": 5000,
            "avg_duration_ms": 10,
            "sql_share": 0.0,
        },
        applies_to="slow_op",
    )
    assert match is not None
    assert match.rule_id == "slow_op_call_cascade"


def test_classify_lock_timeout(engine: ExplainerEngine) -> None:
    match = engine.classify({"event_type": "TLOCK"}, applies_to="lock")
    assert match is not None
    assert match.rule_id == "lock_timeout"


def test_classify_exception_deadlock_victim_via_regex(engine: ExplainerEngine) -> None:
    match = engine.classify(
        {"event_type": "EXCP", "descr": "Транзакция была прервана. Deadlock detected"},
        applies_to="exception",
    )
    assert match is not None
    assert match.rule_id == "exception_deadlock_victim"


def test_classify_exception_timeout_via_regex(engine: ExplainerEngine) -> None:
    match = engine.classify(
        {"event_type": "EXCP", "descr": "Превышено время ожидания блокировки"},
        applies_to="exception",
    )
    assert match is not None
    assert match.rule_id == "exception_timeout"


def test_acceptance_synthetic_deadlocks_all_classify(engine: ExplainerEngine) -> None:
    """DoD #22 (синтетическая версия): все 3 типа синтетических deadlock'ов
    классифицируются одним из rules."""
    # Type 1: lock escalation (1 region, 2 participants)
    m1 = engine.classify(
        {"event_type": "TDEADLOCK", "regions_count": 1, "participants_count": 2},
        applies_to="deadlock",
    )
    # Type 2: different order (2 regions, 2 participants)
    m2 = engine.classify(
        {"event_type": "TDEADLOCK", "regions_count": 2, "participants_count": 2},
        applies_to="deadlock",
    )
    # Type 3: single resource (только event_type)
    m3 = engine.classify({"event_type": "TDEADLOCK"}, applies_to="deadlock")

    matches = [m1, m2, m3]
    assert all(m is not None for m in matches), "Не все 3 типа classified"
    rule_ids = [m.rule_id for m in matches]  # type: ignore[union-attr]
    assert len(set(rule_ids)) == 3, f"Ожидалось 3 разных rule_id, получили {rule_ids}"


def test_reload_rules(engine: ExplainerEngine) -> None:
    initial_count = len(engine.rules)
    engine.reload_rules()
    assert len(engine.rules) == initial_count
