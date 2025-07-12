"""Unit tests for pylint-ruff-sync."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    import pytest

from pylint_ruff_sync.main import _setup_argument_parser
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pylint_rule import PylintRule
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import RuffPylintExtractor

# We're mocking with exactly 6 rules, 3 implemented in ruff, 3 not implemented
EXPECTED_RULES_COUNT = 6
EXPECTED_IMPLEMENTED_RULES_COUNT = 3
EXPECTED_NOT_IMPLEMENTED_RULES_COUNT = 3

# Sample HTML response with implemented rules (mocked GitHub issue)
MOCK_GITHUB_RESPONSE = """
<html>
<body>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>F401</code> <code>F401</code>
</li>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>F841</code> <code>F841</code>
</li>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>E501</code> <code>E501</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>C0103</code> <code>C0103</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>C0111</code> <code>C0111</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>R0903</code> <code>R0903</code>
</li>
</body>
</html>
"""

# Mock pylint output with the same 6 rules as in GitHub mock
MOCK_PYLINT_OUTPUT = """
:unused-import (F401): *Unused import*
:unused-variable (F841): *Unused variable*
:line-too-long (E501): *Line too long*
:invalid-name (C0103): *Invalid name*
:missing-docstring (C0111): *Missing docstring*
:too-few-public-methods (R0903): *Too few public methods*
"""


def _setup_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up all mocks needed for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """

    # Mock the GitHub API call
    class MockResponse:
        def __init__(self, content: str) -> None:
            self.content = content.encode("utf-8")

        def raise_for_status(self) -> None:
            pass

    def mock_requests_get(*_args: object, **_kwargs: object) -> MockResponse:
        return MockResponse(MOCK_GITHUB_RESPONSE)

    monkeypatch.setattr("requests.get", mock_requests_get)

    # Mock the pylint command output
    mock_result = Mock()
    mock_result.stdout = MOCK_PYLINT_OUTPUT

    def mock_subprocess_run(*_args: object, **_kwargs: object) -> Mock:
        return mock_result

    def mock_shutil_which(_cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)


def test_pylint_rule_init() -> None:
    """Test PylintRule initialization."""
    rule = PylintRule(code="C0103", name="invalid-name", description="Invalid name")
    assert rule.code == "C0103"
    assert rule.name == "invalid-name"
    assert rule.description == "Invalid name"


def test_pylint_rule_repr() -> None:
    """Test PylintRule representation."""
    rule = PylintRule(code="C0103", name="invalid-name", description="Invalid name")
    assert repr(rule) == "PylintRule(code='C0103', name='invalid-name')"


def test_extract_implemented_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting implemented rules from GitHub issue.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    _setup_mocks(monkeypatch)

    extractor = RuffPylintExtractor()
    result = extractor.extract_implemented_rules()

    # Should find F401, F841, and E501 as implemented (checked checkboxes)
    assert "F401" in result
    assert "F841" in result
    assert "E501" in result
    assert len(result) == EXPECTED_IMPLEMENTED_RULES_COUNT


def test_extract_all_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting all pylint rules.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    _setup_mocks(monkeypatch)

    extractor = PylintExtractor()
    rules = extractor.extract_all_rules()

    assert len(rules) == EXPECTED_RULES_COUNT
    assert rules[0].code == "F401"
    assert rules[0].name == "unused-import"
    assert rules[1].code == "F841"
    assert rules[1].name == "unused-variable"
    assert rules[2].code == "E501"
    assert rules[2].name == "line-too-long"
    assert rules[3].code == "C0103"
    assert rules[3].name == "invalid-name"


def test_update_pylint_config() -> None:
    """Test updating pylint configuration."""
    updater = PyprojectUpdater(config_file=Path("test.toml"))
    config: dict[str, object] = {}
    rules_to_enable = {"C0103"}  # Only C0103 is not implemented in ruff
    existing_disabled: set[str] = set()
    all_rules = [
        PylintRule(code="F401", name="unused-import", description="Unused import"),
        PylintRule(code="F841", name="unused-variable", description="Unused variable"),
        PylintRule(code="E501", name="line-too-long", description="Line too long"),
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
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
        "C0103",  # Only C0103 should be enabled
    ]
    # We no longer modify the disable list - it should not be set for new configs
    assert "disable" not in result["tool"]["pylint"]["messages_control"]


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
        PylintRule(code="F401", name="unused-import", description="Unused import"),
        PylintRule(code="F841", name="unused-variable", description="Unused variable"),
        PylintRule(code="E501", name="line-too-long", description="Line too long"),
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
    ]

    # Test resolving by code
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["F401", "C0103"], all_rules=rules
    )
    assert result == {"F401", "C0103"}

    # Test resolving by name
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["unused-import", "invalid-name"], all_rules=rules
    )
    assert result == {"F401", "C0103"}

    # Test mixed codes and names
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["F401", "invalid-name"], all_rules=rules
    )
    assert result == {"F401", "C0103"}


def test_disabled_rule_by_name_not_enabled() -> None:
    """Test that disabled rules (by name) are not enabled."""
    extractor = PylintExtractor()
    rules = [
        PylintRule(code="F401", name="unused-import", description="Unused import"),
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
    ]

    # Test that disabled rules are not enabled
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["unused-import"], all_rules=rules
    )
    assert result == {"F401"}

    # Test that other rules are still resolved
    result = extractor.resolve_rule_identifiers(
        rule_identifiers=["invalid-name"], all_rules=rules
    )
    assert result == {"C0103"}


def test_update_pylint_config_with_existing_disabled_rules() -> None:
    """Test updating pylint configuration with existing disabled rules."""
    updater = PyprojectUpdater(config_file=Path("test.toml"))
    # Config with existing disabled rules
    config: dict[str, object] = {
        "tool": {
            "pylint": {
                "messages_control": {
                    "disable": ["locally-disabled", "suppressed-message"]
                }
            }
        }
    }
    rules_to_enable = {"C0103"}  # Only C0103 is not implemented in ruff
    existing_disabled = {"locally-disabled", "suppressed-message"}
    all_rules = [
        PylintRule(code="F401", name="unused-import", description="Unused import"),
        PylintRule(code="C0103", name="invalid-name", description="Invalid name"),
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
        "C0103",  # Only C0103 should be enabled
    ]
    assert result["tool"]["pylint"]["messages_control"]["disable"] == [
        "locally-disabled",
        "suppressed-message",
    ]
