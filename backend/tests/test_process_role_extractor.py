"""Тесты process_role_extractor — discovery 2026-05-18 показал mixed-case префиксы."""

from __future__ import annotations

import pytest

from optimyzer_backend.ingest.process_role_extractor import extract_process_role


def test_extracts_lowercase_rphost() -> None:
    assert extract_process_role("rphost_28220") == ("rphost", 28220)


def test_extracts_uppercase_rphost() -> None:
    assert extract_process_role("RPHOST_28220") == ("rphost", 28220)


def test_extracts_mixed_case_1cv8c() -> None:
    # 1CV8C_12044 рядом с 1cv8c_23100 — реальный кейс из LOGS_INSPECTION.md
    assert extract_process_role("1CV8C_12044") == ("1cv8c", 12044)
    assert extract_process_role("1cv8c_23100") == ("1cv8c", 23100)


@pytest.mark.parametrize(
    "folder, expected",
    [
        ("rphost_28220", ("rphost", 28220)),
        ("rmngr_24128", ("rmngr", 24128)),
        ("ragent_28284", ("ragent", 28284)),
        ("1cv8c_12044", ("1cv8c", 12044)),
        ("1cv8s_1688", ("1cv8s", 1688)),
        ("1cv8_24120", ("1cv8", 24120)),
    ],
)
def test_extracts_all_six_roles(folder: str, expected: tuple[str, int]) -> None:
    assert extract_process_role(folder) == expected


def test_returns_unknown_for_arbitrary_folder() -> None:
    assert extract_process_role("logs") == ("unknown", None)
    assert extract_process_role("temp") == ("unknown", None)
    assert extract_process_role("backup") == ("unknown", None)


def test_returns_unknown_for_partial_match() -> None:
    # pid non-numeric
    assert extract_process_role("rphost_abc") == ("unknown", None)
    # без подчёркивания
    assert extract_process_role("rphost") == ("unknown", None)
    # unknown role
    assert extract_process_role("foobar_1234") == ("unknown", None)


def test_extracts_large_pid() -> None:
    assert extract_process_role("rphost_999999999") == ("rphost", 999999999)


def test_lowercase_role_in_result_regardless_of_input_case() -> None:
    role_upper, _ = extract_process_role("RAGENT_1")
    role_mixed, _ = extract_process_role("RmNgR_2")
    assert role_upper == "ragent"
    assert role_mixed == "rmngr"


def test_strips_whitespace() -> None:
    assert extract_process_role("  rphost_28220  ") == ("rphost", 28220)
