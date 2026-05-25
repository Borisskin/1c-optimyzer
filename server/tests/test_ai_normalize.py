"""Sprint 9 Phase D — Unit tests для normalize_ai_enum.

Тестирует generic normalizer + конкретные mappings SEVERITY и IMPACT.
"""
from __future__ import annotations

import pytest

from services.ai_explainer import (
    IMPACT_MAPPING,
    SEVERITY_MAPPING,
    normalize_ai_enum,
)


# ---------------------------------------------------------------------------
# normalize_ai_enum: базовая логика
# ---------------------------------------------------------------------------


class TestNormalizeAiEnum:
    def test_known_value_exact_case(self) -> None:
        result = normalize_ai_enum("Critical", SEVERITY_MAPPING, "Info")
        assert result == "Critical"

    def test_known_value_lowercase(self) -> None:
        result = normalize_ai_enum("critical", SEVERITY_MAPPING, "Info")
        assert result == "Critical"

    def test_known_value_uppercase(self) -> None:
        result = normalize_ai_enum("CRITICAL", SEVERITY_MAPPING, "Info")
        assert result == "Critical"

    def test_known_value_mixed_case(self) -> None:
        result = normalize_ai_enum("Warning", SEVERITY_MAPPING, "Info")
        assert result == "Warning"

    def test_unknown_value_returns_default(self) -> None:
        result = normalize_ai_enum("Extreme", SEVERITY_MAPPING, "Info")
        assert result == "Info"

    def test_unknown_value_custom_default(self) -> None:
        result = normalize_ai_enum("Extreme", SEVERITY_MAPPING, "Warning")
        assert result == "Warning"

    def test_empty_string_returns_default(self) -> None:
        result = normalize_ai_enum("", SEVERITY_MAPPING, "Info")
        assert result == "Info"

    def test_whitespace_stripped(self) -> None:
        result = normalize_ai_enum("  critical  ", SEVERITY_MAPPING, "Info")
        assert result == "Critical"

    def test_non_string_none_returns_default(self) -> None:
        result = normalize_ai_enum(None, SEVERITY_MAPPING, "Info")  # type: ignore[arg-type]
        assert result == "Info"

    def test_non_string_int_returns_default(self) -> None:
        result = normalize_ai_enum(5, SEVERITY_MAPPING, "Info")  # type: ignore[arg-type]
        assert result == "Info"

    def test_non_string_list_returns_default(self) -> None:
        result = normalize_ai_enum(["Critical"], SEVERITY_MAPPING, "Info")  # type: ignore[arg-type]
        assert result == "Info"

    def test_non_string_bool_returns_default(self) -> None:
        result = normalize_ai_enum(True, SEVERITY_MAPPING, "Info")  # type: ignore[arg-type]
        assert result == "Info"


# ---------------------------------------------------------------------------
# SEVERITY_MAPPING: полные alias проверки
# ---------------------------------------------------------------------------


class TestSeverityMapping:
    """AI часто использует non-canonical значения — проверяем все aliases."""

    def test_high_maps_to_critical(self) -> None:
        """Bug #2 из Demo Session: AI вернул 'High' → Pydantic 422."""
        assert normalize_ai_enum("High", SEVERITY_MAPPING, "Info") == "Critical"

    def test_blocker_maps_to_critical(self) -> None:
        assert normalize_ai_enum("Blocker", SEVERITY_MAPPING, "Info") == "Critical"

    def test_error_maps_to_critical(self) -> None:
        assert normalize_ai_enum("Error", SEVERITY_MAPPING, "Info") == "Critical"

    def test_medium_maps_to_warning(self) -> None:
        assert normalize_ai_enum("Medium", SEVERITY_MAPPING, "Info") == "Warning"

    def test_moderate_maps_to_warning(self) -> None:
        assert normalize_ai_enum("Moderate", SEVERITY_MAPPING, "Info") == "Warning"

    def test_warn_maps_to_warning(self) -> None:
        assert normalize_ai_enum("Warn", SEVERITY_MAPPING, "Info") == "Warning"

    def test_low_maps_to_info(self) -> None:
        assert normalize_ai_enum("Low", SEVERITY_MAPPING, "Info") == "Info"

    def test_minor_maps_to_info(self) -> None:
        assert normalize_ai_enum("Minor", SEVERITY_MAPPING, "Info") == "Info"

    def test_informational_maps_to_info(self) -> None:
        assert normalize_ai_enum("Informational", SEVERITY_MAPPING, "Info") == "Info"

    def test_canonical_critical_preserved(self) -> None:
        assert normalize_ai_enum("Critical", SEVERITY_MAPPING, "Info") == "Critical"

    def test_canonical_warning_preserved(self) -> None:
        assert normalize_ai_enum("Warning", SEVERITY_MAPPING, "Info") == "Warning"

    def test_canonical_info_preserved(self) -> None:
        assert normalize_ai_enum("Info", SEVERITY_MAPPING, "Info") == "Info"

    def test_unknown_severity_falls_back_to_info(self) -> None:
        for unknown in ["Severe", "Fatal", "Urgent", "Catastrophic", "N/A", "none"]:
            assert normalize_ai_enum(unknown, SEVERITY_MAPPING, "Info") == "Info", f"failed for {unknown!r}"


# ---------------------------------------------------------------------------
# IMPACT_MAPPING
# ---------------------------------------------------------------------------


class TestImpactMapping:
    def test_critical_maps_to_critical(self) -> None:
        assert normalize_ai_enum("Critical", IMPACT_MAPPING, "Low") == "Critical"

    def test_high_maps_to_high(self) -> None:
        assert normalize_ai_enum("High", IMPACT_MAPPING, "Low") == "High"

    def test_moderate_maps_to_medium(self) -> None:
        assert normalize_ai_enum("Moderate", IMPACT_MAPPING, "Low") == "Medium"

    def test_medium_maps_to_medium(self) -> None:
        assert normalize_ai_enum("Medium", IMPACT_MAPPING, "Low") == "Medium"

    def test_minor_maps_to_low(self) -> None:
        assert normalize_ai_enum("Minor", IMPACT_MAPPING, "Low") == "Low"

    def test_unknown_impact_falls_back_to_low(self) -> None:
        assert normalize_ai_enum("Extreme", IMPACT_MAPPING, "Low") == "Low"
