"""Test module for mypy overlap functionality."""

from __future__ import annotations

from pylint_ruff_sync.constants import MYPY_OVERLAP_RULES
from pylint_ruff_sync.mypy_overlap import (
    MypyOverlapExtractor,
    get_mypy_overlap_rules,
    is_mypy_overlap_rule,
)
from pylint_ruff_sync.rule import Rule, Rules, RuleSource

# Expected number of mypy overlap rules (update if rules change)
EXPECTED_MYPY_OVERLAP_COUNT = 78
# Minimum expected length for rule codes (e.g., "E1101" is 5 characters)
MIN_RULE_CODE_LENGTH = 4
# Minimum expected number of rule categories
MIN_EXPECTED_CATEGORIES = 3


def test_mypy_overlap_rules_constant() -> None:
    """Test the MYPY_OVERLAP_RULES constant."""
    # Test type and basic properties
    assert isinstance(MYPY_OVERLAP_RULES, set)

    # Test expected count (this may need updating if rules change)
    assert len(MYPY_OVERLAP_RULES) == EXPECTED_MYPY_OVERLAP_COUNT

    # Test some known overlap rules are included
    assert "E1101" in MYPY_OVERLAP_RULES  # no-member
    assert "E1102" in MYPY_OVERLAP_RULES  # not-callable
    assert "E1120" in MYPY_OVERLAP_RULES  # no-value-for-parameter
    assert "E1128" in MYPY_OVERLAP_RULES  # assignment-from-none
    assert "W0221" in MYPY_OVERLAP_RULES  # arguments-differ

    # Test some rules that should NOT be overlap rules
    assert "R0903" not in MYPY_OVERLAP_RULES  # too-few-public-methods
    assert "C0103" not in MYPY_OVERLAP_RULES  # invalid-name


def test_get_mypy_overlap_rules() -> None:
    """Test the get_mypy_overlap_rules function."""
    rules = get_mypy_overlap_rules()

    # Should return the same content as the constant
    assert rules == MYPY_OVERLAP_RULES
    assert rules is not MYPY_OVERLAP_RULES  # Should be a copy

    # Modifying returned set should not affect original
    original_length = len(MYPY_OVERLAP_RULES)
    rules.add("FAKE_RULE")
    assert len(MYPY_OVERLAP_RULES) == original_length


def test_is_mypy_overlap_rule() -> None:
    """Test the is_mypy_overlap_rule function."""
    # Test known overlap rules
    assert is_mypy_overlap_rule("E1101") is True  # no-member
    assert is_mypy_overlap_rule("E1102") is True  # not-callable
    assert is_mypy_overlap_rule("W0221") is True  # arguments-differ

    # Test known non-overlap rules
    assert is_mypy_overlap_rule("R0903") is False  # too-few-public-methods
    assert is_mypy_overlap_rule("C0103") is False  # invalid-name
    assert is_mypy_overlap_rule("INVALID") is False  # non-existent rule


def test_mypy_overlap_rules_format() -> None:
    """Test that all mypy overlap rules have the expected format."""
    for rule_code in MYPY_OVERLAP_RULES:
        # All rule codes should be strings of appropriate length
        assert isinstance(rule_code, str)
        assert len(rule_code) >= MIN_RULE_CODE_LENGTH
        # Should start with letter and contain digits
        assert rule_code[0].isalpha()
        assert any(char.isdigit() for char in rule_code)


def test_mypy_overlap_categories() -> None:
    """Test that mypy overlap rules cover expected categories."""
    categories = {rule_code[0] for rule_code in MYPY_OVERLAP_RULES}

    # Should include multiple categories (E, W, C, etc.)
    assert len(categories) >= MIN_EXPECTED_CATEGORIES
    assert "E" in categories  # Error rules
    assert "W" in categories  # Warning rules


def test_mypy_overlap_extractor_init() -> None:
    """Test MypyOverlapExtractor initialization."""
    rules = Rules()
    extractor = MypyOverlapExtractor(rules)
    assert extractor.rules is rules


def test_mypy_overlap_extractor_extract() -> None:
    """Test MypyOverlapExtractor extract method."""
    rules = Rules()

    # Add some test rules, including overlap and non-overlap rules
    rules.add_rule(
        Rule(
            pylint_id="E1101",  # Known overlap rule
            pylint_name="no-member",
            source=RuleSource.PYLINT_LIST,
        )
    )
    rules.add_rule(
        Rule(
            pylint_id="E1102",  # Known overlap rule
            pylint_name="not-callable",
            source=RuleSource.PYLINT_LIST,
        )
    )
    rules.add_rule(
        Rule(
            pylint_id="C0103",  # Not an overlap rule
            pylint_name="invalid-name",
            source=RuleSource.PYLINT_LIST,
        )
    )
    rules.add_rule(
        Rule(
            pylint_id="R0903",  # Not an overlap rule
            pylint_name="too-few-public-methods",
            source=RuleSource.PYLINT_LIST,
        )
    )

    # Initially, no rules should be marked as mypy overlap
    for rule in rules:
        assert rule.is_mypy_overlap is False

    # Extract mypy overlap information
    extractor = MypyOverlapExtractor(rules)
    extractor.extract()

    # Check that overlap rules are marked correctly
    e1101_rule = rules.get_by_identifier("E1101")
    e1102_rule = rules.get_by_identifier("E1102")
    c0103_rule = rules.get_by_identifier("C0103")
    r0903_rule = rules.get_by_identifier("R0903")

    assert e1101_rule is not None
    assert e1102_rule is not None
    assert c0103_rule is not None
    assert r0903_rule is not None

    assert e1101_rule.is_mypy_overlap is True
    assert e1102_rule.is_mypy_overlap is True
    assert c0103_rule.is_mypy_overlap is False
    assert r0903_rule.is_mypy_overlap is False


def test_mypy_overlap_extractor_empty_rules() -> None:
    """Test MypyOverlapExtractor with empty rules."""
    rules = Rules()
    extractor = MypyOverlapExtractor(rules)

    # Should not raise an error with empty rules
    extractor.extract()
    assert len(rules) == 0
