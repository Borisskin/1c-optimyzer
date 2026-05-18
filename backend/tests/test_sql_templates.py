"""Тесты SQL Templates library (Sprint 2 Phase F)."""

from __future__ import annotations

import pytest

from optimyzer_backend.sql.templates import TEMPLATES
from optimyzer_backend.sql.validator import validate_sql


def test_templates_have_required_fields() -> None:
    for tpl in TEMPLATES:
        for key in ("id", "category", "label", "description", "sql"):
            assert key in tpl, f"template {tpl.get('id')} missing {key}"
        assert tpl["label"], f"empty label in {tpl['id']}"
        assert tpl["sql"].strip(), f"empty sql in {tpl['id']}"


def test_templates_ids_unique() -> None:
    ids = [t["id"] for t in TEMPLATES]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"


def test_templates_count_at_least_10() -> None:
    assert len(TEMPLATES) >= 10


@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda t: t["id"])
def test_template_passes_validator(tpl: dict) -> None:
    ok, err = validate_sql(tpl["sql"])
    assert ok, f"{tpl['id']}: validator rejected: {err}"


def test_templates_grouped_by_categories() -> None:
    cats = {t["category"] for t in TEMPLATES}
    # Sprint 2 spec: performance / locks / errors / memory / stats
    assert {"performance", "locks", "errors", "stats"}.issubset(cats)
