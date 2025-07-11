"""Tests for the main functionality of pylint-ruff-sync."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

from pylint_ruff_sync.main import (
    PylintExtractor,
    PylintRule,
    PyprojectUpdater,
    RuffPylintExtractor,
    _setup_argument_parser,
)

if TYPE_CHECKING:
    import pytest

# Constants
EXPECTED_RULES_COUNT = 2


def test_pylint_rule_init() -> None:
    """Test PylintRule initialization."""
    rule = PylintRule(code="C0103", name="invalid-name", description="Invalid name")
    assert rule.code == "C0103"
    assert rule.name == "invalid-name"
    assert rule.description == "Invalid name"


def test_pylint_rule_repr() -> None:
    """Test PylintRule string representation."""
    rule = PylintRule(code="C0103", name="invalid-name", description="Invalid name")
    assert repr(rule) == "PylintRule(code='C0103', name='invalid-name')"


def test_extract_implemented_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting implemented rules from GitHub issue.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    # Mock HTML response
    mock_response = Mock()
    mock_response.content = b"""
    <li class="task-list-item">
        <input type="checkbox" checked="checked">
        <code>rule-name</code>
        <code>C0103</code>
    </li>
    <li class="task-list-item">
        <input type="checkbox">
        <code>other-rule</code>
        <code>C0104</code>
    </li>
    """
    mock_response.raise_for_status.return_value = None

    def mock_requests_get(*_args: object, **_kwargs: object) -> Mock:
        return mock_response

    monkeypatch.setattr("requests.get", mock_requests_get)

    # Mock BeautifulSoup parsing
    mock_li = Mock()
    mock_li.attrs = {"class": ["task-list-item"]}

    # Create mock children - make children iterable and contain the mock elements
    mock_input = Mock()
    mock_input.name = "input"
    mock_input.attrs = {"checked": "checked"}

    mock_code1 = Mock()
    mock_code1.name = "code"
    mock_code1.text = "rule-name"

    mock_code2 = Mock()
    mock_code2.name = "code"
    mock_code2.text = "C0103"

    # Set up children as an iterable
    mock_li.children = [mock_input, mock_code1, mock_code2]

    def mock_soup_init(*_args: object, **_kwargs: object) -> Mock:
        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_li]
        return mock_soup

    monkeypatch.setattr("bs4.BeautifulSoup", mock_soup_init)

    extractor = RuffPylintExtractor()
    result = extractor.extract_implemented_rules()

    assert "C0103" in result
    assert len(result) == 1


def test_extract_all_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting all pylint rules.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    # Mock subprocess output
    mock_result = Mock()
    mock_result.stdout = """
    :invalid-name (C0103): *Invalid name*
    :missing-docstring (C0111): *Missing docstring*
    """

    def mock_subprocess_run(*_args: object, **_kwargs: object) -> Mock:
        return mock_result

    def mock_shutil_which(_cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)

    extractor = PylintExtractor()
    rules = extractor.extract_all_rules()

    assert len(rules) == EXPECTED_RULES_COUNT
    assert rules[0].code == "C0103"
    assert rules[0].name == "invalid-name"
    assert rules[1].code == "C0111"
    assert rules[1].name == "missing-docstring"


def test_update_pylint_config() -> None:
    """Test updating pylint configuration."""
    updater = PyprojectUpdater(config_file=Path("test.toml"))
    config: dict[str, object] = {}
    rules_to_enable = {"C0103", "C0111"}
    existing_disabled: set[str] = set()
    all_rules = [
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
        PylintRule(
            code="C0111", name="missing-docstring", description="Missing docstring"
        ),
    ]

    result = updater.update_pylint_config(
        config=config,
        rules_to_enable=rules_to_enable,
        existing_disabled=existing_disabled,
        all_rules=all_rules,
    )

    assert "tool" in result
    assert "pylint" in result["tool"]
    assert "messages_control" in result["tool"]["pylint"]
    assert result["tool"]["pylint"]["messages_control"]["enable"] == [
        "C0103",
        "C0111",
    ]
    assert result["tool"]["pylint"]["messages_control"]["disable"] == []


def test_main_argument_parsing() -> None:
    """Test that main function parses arguments correctly."""
    # Test that the argument parser is set up correctly by testing the dry run flag
    parser = _setup_argument_parser()

    # Test dry run argument
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True

    # Test verbose argument
    args = parser.parse_args(["--verbose"])
    assert args.verbose is True

    # Test config file argument
    args = parser.parse_args(["--config-file", "custom.toml"])
    assert args.config_file == Path("custom.toml")


def test_resolve_rule_identifiers() -> None:
    """Test resolving rule identifiers by code and name."""
    extractor = PylintExtractor()
    rules = [
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
        PylintRule(
            code="C0111", name="missing-docstring", description="Missing docstring"
        ),
        PylintRule(
            code="R0903",
            name="too-few-public-methods",
            description="Too few public methods",
        ),
    ]

    # Test resolving by code
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["C0103", "R0903"], all_rules=rules
    )
    assert result == {"C0103", "R0903"}

    # Test resolving by name
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["invalid-name", "missing-docstring"], all_rules=rules
    )
    assert result == {"C0103", "C0111"}

    # Test mixed codes and names
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["C0103", "missing-docstring"], all_rules=rules
    )
    assert result == {"C0103", "C0111"}

    # Test unknown rule
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["unknown-rule"], all_rules=rules
    )
    assert result == set()


def test_update_pylint_config_with_existing_disabled_rules() -> None:
    """Test updating pylint configuration respecting existing disabled rules."""
    updater = PyprojectUpdater(config_file=Path("test.toml"))

    # Config with some rules already disabled
    config: dict[str, object] = {
        "tool": {"pylint": {"messages_control": {"disable": ["R0903", "C0103"]}}}
    }

    # Rules that would normally be enabled (not implemented in ruff)
    rules_to_enable = {"C0103", "C0111", "R0124"}
    # Existing disabled rules resolved to codes
    existing_disabled = {"R0903", "C0103"}
    all_rules = [
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
        PylintRule(
            code="C0111", name="missing-docstring", description="Missing docstring"
        ),
        PylintRule(
            code="R0903",
            name="too-few-public-methods",
            description="Too few public methods",
        ),
        PylintRule(
            code="R0124",
            name="inconsistent-return-statements",
            description="Inconsistent return statements",
        ),
    ]

    result = updater.update_pylint_config(
        config=config,
        rules_to_enable=rules_to_enable,
        existing_disabled=existing_disabled,
        all_rules=all_rules,
    )

    # Should only enable rules that are not disabled in config
    # C0103 is disabled, so should not be enabled
    # C0111 and R0124 should be enabled
    expected_enable = {"C0111", "R0124"}
    assert (
        set(result["tool"]["pylint"]["messages_control"]["enable"]) == expected_enable
    )
    # Should preserve existing disabled rules in original format
    assert set(result["tool"]["pylint"]["messages_control"]["disable"]) == {
        "R0903",
        "C0103",
    }


def test_disabled_rule_by_name_not_enabled() -> None:
    """Test that rules disabled by name are not enabled by code.

    This verifies that suppressed-message (disabled by name) prevents
    I0020 (its code) from being enabled.
    """
    updater = PyprojectUpdater(config_file=Path("test.toml"))

    # Config with rule disabled by name
    config: dict[str, object] = {
        "tool": {"pylint": {"messages_control": {"disable": ["suppressed-message"]}}}
    }

    # Rules that would normally be enabled, including I0020 (suppressed-message)
    rules_to_enable = {"I0020", "C0111", "R0124"}
    # I0020 is the code for "suppressed-message", so it should be in existing_disabled
    existing_disabled = {"I0020"}
    all_rules = [
        PylintRule(
            code="I0020", name="suppressed-message", description="Suppressed message"
        ),
        PylintRule(
            code="C0111", name="missing-docstring", description="Missing docstring"
        ),
        PylintRule(
            code="R0124",
            name="inconsistent-return-statements",
            description="Inconsistent return statements",
        ),
    ]

    result = updater.update_pylint_config(
        config=config,
        rules_to_enable=rules_to_enable,
        existing_disabled=existing_disabled,
        all_rules=all_rules,
    )

    # I0020 should NOT be enabled because it's disabled by name as "suppressed-message"
    expected_enable = {"C0111", "R0124"}
    assert (
        set(result["tool"]["pylint"]["messages_control"]["enable"]) == expected_enable
    )
    # Should preserve the original disable format (by name)
    assert result["tool"]["pylint"]["messages_control"]["disable"] == [
        "suppressed-message"
    ]

    # Verify I0020 is not in the enable list
    assert "I0020" not in result["tool"]["pylint"]["messages_control"]["enable"]
