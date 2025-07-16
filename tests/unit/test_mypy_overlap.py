"""Test module for mypy overlap functionality."""

from __future__ import annotations

from pylint_ruff_sync.mypy_overlap import (
    MYPY_OVERLAP_RULES,
    get_mypy_overlap_rules,
    is_mypy_overlap_rule,
)

# Expected number of mypy overlap rules based on antonagestam analysis
EXPECTED_MYPY_OVERLAP_COUNT = 78

# Minimum pylint rule code length (e.g., E001)
MIN_RULE_CODE_LENGTH = 4


def test_mypy_overlap_rules_constant() -> None:
    """Test the MYPY_OVERLAP_RULES constant."""
    # Should be a set
    assert isinstance(MYPY_OVERLAP_RULES, set)

    # Should contain the expected number of rules (78 as documented)
    assert len(MYPY_OVERLAP_RULES) == EXPECTED_MYPY_OVERLAP_COUNT

    # Should contain known mypy overlap rules
    assert "E1101" in MYPY_OVERLAP_RULES  # no-member
    assert "E1102" in MYPY_OVERLAP_RULES  # not-callable
    assert "E1120" in MYPY_OVERLAP_RULES  # no-value-for-parameter
    assert "E1128" in MYPY_OVERLAP_RULES  # assignment-from-none
    assert "W0221" in MYPY_OVERLAP_RULES  # arguments-differ

    # Should not contain rules that are not mypy overlap
    assert "R0903" not in MYPY_OVERLAP_RULES  # too-few-public-methods
    assert "C0103" not in MYPY_OVERLAP_RULES  # invalid-name


def test_get_mypy_overlap_rules() -> None:
    """Test the get_mypy_overlap_rules function."""
    rules = get_mypy_overlap_rules()

    # Should return a copy of the constant
    assert rules == MYPY_OVERLAP_RULES
    assert rules is not MYPY_OVERLAP_RULES  # Should be a copy

    # Modifying the returned set should not affect the original
    original_length = len(MYPY_OVERLAP_RULES)
    rules.add("TEST123")
    assert len(MYPY_OVERLAP_RULES) == original_length


def test_is_mypy_overlap_rule() -> None:
    """Test the is_mypy_overlap_rule function."""
    # Known mypy overlap rules should return True
    assert is_mypy_overlap_rule("E1101") is True  # no-member
    assert is_mypy_overlap_rule("E1102") is True  # not-callable
    assert is_mypy_overlap_rule("W0221") is True  # arguments-differ

    # Non-mypy overlap rules should return False
    assert is_mypy_overlap_rule("R0903") is False  # too-few-public-methods
    assert is_mypy_overlap_rule("C0103") is False  # invalid-name
    assert is_mypy_overlap_rule("INVALID") is False  # non-existent rule


def test_mypy_overlap_rules_format() -> None:
    """Test that all mypy overlap rules follow the correct format."""
    for rule_code in MYPY_OVERLAP_RULES:
        # Should be strings
        assert isinstance(rule_code, str)

        # Should follow pylint rule format (letter followed by digits)
        assert len(rule_code) >= MIN_RULE_CODE_LENGTH  # Minimum E001 format
        assert rule_code[0].isupper()  # First character should be uppercase letter
        assert rule_code[1:].isdigit()  # Rest should be digits


def test_mypy_overlap_categories() -> None:
    """Test that mypy overlap rules cover expected categories."""
    # Count rules by category (first letter)
    categories: dict[str, int] = {}
    for rule_code in MYPY_OVERLAP_RULES:
        category = rule_code[0]
        categories[category] = categories.get(category, 0) + 1

    # Should have Error rules (E)
    assert "E" in categories
    assert categories["E"] > 0

    # Should have Warning rules (W)
    assert "W" in categories
    assert categories["W"] > 0

    # May have Convention rules (C)
    # May have Refactor rules (R)

    # Should not have Fatal rules (F) as these are typically not mypy overlap
    assert "F" not in categories
