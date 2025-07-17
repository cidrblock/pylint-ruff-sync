"""Test mypy overlap functionality."""

from pylint_ruff_sync.constants import MYPY_OVERLAP_RULES
from pylint_ruff_sync.mypy_overlap import MypyOverlapExtractor
from pylint_ruff_sync.rule import Rule, Rules, RuleSource


def test_mypy_overlap_rules_not_empty() -> None:
    """Test that mypy overlap rules set is not empty."""
    assert len(MYPY_OVERLAP_RULES) > 0


def test_mypy_overlap_rules_contains_expected() -> None:
    """Test that mypy overlap rules contains expected rules."""
    # Test a few known rules that should be in the overlap set
    expected_rules = {
        "E1101",  # no-member
        "E1102",  # not-callable
        "W0221",  # arguments-differ
    }

    for rule in expected_rules:
        assert rule in MYPY_OVERLAP_RULES, f"Rule {rule} should be in mypy overlap set"


def test_mypy_overlap_rules_excludes_expected() -> None:
    """Test that mypy overlap rules excludes rules that shouldn't overlap."""
    # Test a few rules that should NOT be in the overlap set
    excluded_rules = {
        "R0903",  # too-few-public-methods
        "C0103",  # invalid-name
    }

    for rule in excluded_rules:
        assert rule not in MYPY_OVERLAP_RULES, (
            f"Rule {rule} should not be in mypy overlap set"
        )


def test_mypy_overlap_extractor_init() -> None:
    """Test MypyOverlapExtractor initialization."""
    rules = Rules()
    extractor = MypyOverlapExtractor(rules=rules)
    assert extractor.rules is rules


def test_mypy_overlap_extractor_extract() -> None:
    """Test MypyOverlapExtractor.extract() method."""
    rules = Rules()

    # Add some test rules - mix of overlap and non-overlap
    overlap_rule = Rule(
        pylint_id="E1101",
        pylint_name="no-member",
        source=RuleSource.PYLINT_LIST,
    )
    non_overlap_rule = Rule(
        pylint_id="C0103",
        pylint_name="invalid-name",
        source=RuleSource.PYLINT_LIST,
    )

    rules.add_rule(rule=overlap_rule)
    rules.add_rule(rule=non_overlap_rule)

    # Extract mypy overlap information
    extractor = MypyOverlapExtractor(rules=rules)
    extractor.extract()

    # Check that overlap rule is marked correctly
    assert overlap_rule.is_mypy_overlap is True
    assert non_overlap_rule.is_mypy_overlap is False


def test_mypy_overlap_extractor_extract_empty_rules() -> None:
    """Test MypyOverlapExtractor.extract() with empty rules."""
    rules = Rules()

    extractor = MypyOverlapExtractor(rules=rules)
    extractor.extract()  # Should not raise any errors

    # Verify no rules were added
    assert not rules
