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
    rule = PylintRule("C0103", "invalid-name", "Invalid name")
    assert rule.code == "C0103"
    assert rule.name == "invalid-name"
    assert rule.description == "Invalid name"


def test_pylint_rule_repr() -> None:
    """Test PylintRule string representation."""
    rule = PylintRule("C0103", "invalid-name", "Invalid name")
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
    updater = PyprojectUpdater(Path("test.toml"))
    config: dict[str, object] = {}
    rules_to_enable = {"C0103", "C0111"}

    result = updater.update_pylint_config(config, rules_to_enable)

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
        PylintRule("C0103", "invalid-name", "Invalid name"),
        PylintRule("C0111", "missing-docstring", "Missing docstring"),
        PylintRule("R0903", "too-few-public-methods", "Too few public methods"),
    ]

    # Test resolving by code
    result = extractor.resolve_rule_identifiers(["C0103", "R0903"], rules)
    assert result == {"C0103", "R0903"}

    # Test resolving by name
    result = extractor.resolve_rule_identifiers(
        ["invalid-name", "missing-docstring"], rules
    )
    assert result == {"C0103", "C0111"}

    # Test mixed codes and names
    result = extractor.resolve_rule_identifiers(["C0103", "missing-docstring"], rules)
    assert result == {"C0103", "C0111"}

    # Test unknown rule
    result = extractor.resolve_rule_identifiers(["unknown-rule"], rules)
    assert result == set()


def test_update_pylint_config_with_existing_disabled_rules() -> None:
    """Test updating pylint configuration respecting existing disabled rules."""
    updater = PyprojectUpdater(Path("test.toml"))

    # Config with some rules already disabled
    config: dict[str, object] = {
        "tool": {"pylint": {"messages_control": {"disable": ["R0903", "C0103"]}}}
    }

    # Rules that would normally be enabled (not implemented in ruff)
    rules_to_enable = {"C0103", "C0111", "R0124"}

    result = updater.update_pylint_config(config, rules_to_enable)

    # Should only enable rules that are not disabled in config
    # C0103 is disabled, so should not be enabled
    # C0111 and R0124 should be enabled
    expected_enable = {"C0111", "R0124"}
    assert (
        set(result["tool"]["pylint"]["messages_control"]["enable"]) == expected_enable
    )
    # Should preserve existing disabled rules
    assert set(result["tool"]["pylint"]["messages_control"]["disable"]) == {
        "R0903",
        "C0103",
    }
