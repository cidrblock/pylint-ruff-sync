"""Unit tests for main functionality."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

from pylint_ruff_sync.constants import RUFF_PYLINT_ISSUE_URL
from pylint_ruff_sync.main import _setup_argument_parser, main
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import RuffPylintExtractor
from pylint_ruff_sync.rule import Rule, Rules
from tests.constants import (
    EXPECTED_IMPLEMENTED_RULES_COUNT,
    EXPECTED_RULES_COUNT,
)

# Constants for test expectations
EXPECTED_DISABLE_LIST_LENGTH = 3

# We expect 6 mock rules total in our test setup
EXPECTED_MOCK_RULES_COUNT = 6


def test_rule_init() -> None:
    """Test Rule initialization and properties."""
    rule = Rule(description="Test", pylint_id="C0103", pylint_name="invalid-name")
    assert rule.pylint_id == "C0103"
    assert rule.pylint_name == "invalid-name"
    assert rule.description == "Test"


@pytest.mark.usefixtures("mocked_subprocess")
def test_extract_implemented_rules() -> None:
    """Test extracting implemented rules from GitHub issue."""
    rules = Rules()
    extractor = RuffPylintExtractor(rules=rules)
    result = extractor.get_implemented_rules()

    # Should find F401, F841, and E501 as implemented (checked checkboxes)
    assert "F401" in result
    assert "F841" in result
    assert "E501" in result
    assert len(result) == EXPECTED_IMPLEMENTED_RULES_COUNT


@pytest.mark.usefixtures("mocked_subprocess")
def test_extract_all_rules() -> None:
    """Test extracting all pylint rules."""
    rules = Rules()
    extractor = PylintExtractor(rules=rules)
    extractor.extract()

    assert len(rules) == EXPECTED_RULES_COUNT
    # Rules should be sorted by code
    rule_list = list(rules.rules)
    assert rule_list[0].code == "C0103"
    assert rule_list[0].name == "invalid-name"
    assert rule_list[1].code == "C0111"
    assert rule_list[1].name == "missing-docstring"
    assert rule_list[2].code == "E501"
    assert rule_list[2].name == "line-too-long"
    assert rule_list[3].code == "F401"
    assert rule_list[3].name == "unused-import"
    assert rule_list[4].code == "F841"
    assert rule_list[4].name == "unused-variable"
    assert rule_list[5].code == "R0903"
    assert rule_list[5].name == "too-few-public-methods"


def test_update_pylint_config() -> None:
    """Test updating pylint configuration."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        # Create Rules instance with test rules
        rules = Rules()

        test_rules = [
            Rule(
                description="Unused import",
                is_implemented_in_ruff=True,
                pylint_id="F401",
                pylint_name="unused-import",
            ),
            Rule(
                description="Unused variable",
                is_implemented_in_ruff=True,
                pylint_id="F841",
                pylint_name="unused-variable",
            ),
            Rule(
                description="Invalid name",
                is_implemented_in_ruff=False,
                pylint_id="C0103",
                pylint_name="invalid-name",
            ),
        ]

        # Add all rules to the Rules instance
        for rule in test_rules:
            rules.add_rule(rule=rule)

        # Use new PyprojectUpdater pattern with simplified interface
        updater = PyprojectUpdater(config_file=temp_path, dry_run=False, rules=rules)
        updater.update()

        # Check the results by reading the file directly
        result_dict = updater.toml_file.as_dict()
        assert "tool" in result_dict
        assert "pylint" in result_dict["tool"]
        assert "messages_control" in result_dict["tool"]["pylint"]

        # Check that enable rules contain non-ruff-implemented rules
        enable_list = result_dict["tool"]["pylint"]["messages_control"]["enable"]
        assert "C0103" in enable_list

        # Check that disable rules include "all" (but ruff-implemented rules
        # are optimized out)
        disable_list = result_dict["tool"]["pylint"]["messages_control"]["disable"]
        assert "all" in disable_list
        # Ruff-implemented rules should NOT be in disable list (optimization)
        assert "F401" not in disable_list
        assert "F841" not in disable_list
    finally:
        temp_path.unlink()


def test_update_pylint_config_dry_run() -> None:
    """Test updating pylint configuration in dry run mode."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        original_content = "[tool.test]\nkey = 'value'\n"
        f.write(original_content)
        temp_path = Path(f.name)

    try:
        # Create Rules instance with test rules
        rules = Rules()

        test_rules = [
            Rule(
                description="Unused import",
                is_implemented_in_ruff=True,
                pylint_id="F401",
                pylint_name="unused-import",
            ),
            Rule(
                description="Invalid name",
                is_implemented_in_ruff=False,
                pylint_id="C0103",
                pylint_name="invalid-name",
            ),
        ]

        # Add all rules to the Rules instance
        for rule in test_rules:
            rules.add_rule(rule=rule)

        # Use PyprojectUpdater in dry run mode
        updater = PyprojectUpdater(config_file=temp_path, dry_run=True, rules=rules)
        updater.update()

        # Check that the file was not modified
        actual_content = temp_path.read_text()
        assert actual_content == original_content
    finally:
        temp_path.unlink()


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
    """Test resolving rule identifiers to rule codes."""
    # Create test rules
    rules = Rules()
    rules.add_rule(
        rule=Rule(
            description="Unused import"
        , pylint_id="F401", pylint_name="unused-import")
    )
    rules.add_rule(
        rule=Rule(
            description="Line too long"
        , pylint_id="E501", pylint_name="line-too-long")
    )
    rules.add_rule(
        rule=Rule(
            description="Invalid name"
        , pylint_id="C0103", pylint_name="invalid-name")
    )

    extractor = PylintExtractor(rules=rules)

    # Test with rule codes
    rule_identifiers = ["F401", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        all_rules=rules, rule_identifiers=rule_identifiers
    )
    assert resolved == {"F401", "C0103"}

    # Test with rule names
    rule_identifiers = ["unused-import", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        all_rules=rules, rule_identifiers=rule_identifiers
    )
    assert resolved == {"F401", "C0103"}

    # Test with mixed codes and names
    rule_identifiers = ["F401", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        all_rules=rules, rule_identifiers=rule_identifiers
    )
    assert resolved == {"F401", "C0103"}

    # Test with unknown identifiers (should be ignored)
    rule_identifiers = ["F401", "unknown-rule", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        all_rules=rules, rule_identifiers=rule_identifiers
    )
    assert resolved == {"F401", "C0103"}


@pytest.mark.usefixtures("mocked_subprocess")
def test_main_function_flow(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test main function integration flow with normal execution.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    # Create a test pyproject.toml file
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("""
[tool.pylint.messages_control]
disable = [
    "invalid-name",
    "missing-docstring",
]
""")

    # Setup mocks for all external dependencies
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--verbose",
        ],
    )

    # Run main function
    result = main()

    # Should exit successfully (return 0)
    assert not result

    # Check that config file was updated
    assert config_file.exists()
    updated_content = config_file.read_text()

    # Should contain some pylint configuration
    assert "[tool.pylint" in updated_content

    # Should preserve the original disable list but add ruff-implemented rules
    assert "disable" in updated_content


def test_ruff_extractor_initialization() -> None:
    """Test that RuffPylintExtractor can be initialized with a Rules object."""
    rules = Rules()
    extractor = RuffPylintExtractor(rules=rules)
    assert extractor.issue_url == RUFF_PYLINT_ISSUE_URL


@pytest.mark.usefixtures("mocked_subprocess")
def test_main_with_update_cache(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test main function with --update-cache argument.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    # Setup mocks for GitHub CLI
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pylint-ruff-sync",
            "--update-cache",
            "--cache-path",
            str(tmp_path / "test_cache.json"),
        ],
    )

    # Run main function
    result = main()

    # Should exit successfully (return 0)
    assert not result

    # Check that cache file was created
    assert (tmp_path / "test_cache.json").exists()

    # Check cache content
    with (tmp_path / "test_cache.json").open() as f:
        cache_data = json.load(f)

    assert "rules" in cache_data
    assert isinstance(cache_data["rules"], list)
    assert len(cache_data["rules"]) > 0


def test_argument_parser_help_text() -> None:
    """Test that argument parser includes expected help information."""
    parser = _setup_argument_parser()
    help_text = parser.format_help()

    # Should include key command line options
    assert "--config-file" in help_text
    assert "--dry-run" in help_text
    assert "--verbose" in help_text
    assert "--update-cache" in help_text
    assert "--disable-mypy-overlap" in help_text
