"""Test module for main functionality."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Never

import pytest

from pylint_ruff_sync.main import (
    _resolve_rule_identifiers,
    _setup_argument_parser,
    main,
)
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import (
    RUFF_PYLINT_ISSUE_URL,
    RuffPylintExtractor,
)
from pylint_ruff_sync.rule import Rule, Rules
from pylint_ruff_sync.toml_file import TomlFile
from tests.constants import (
    EXPECTED_IMPLEMENTED_RULES_COUNT,
    EXPECTED_RULES_COUNT,
    setup_mocks,
)

# Constants for test expectations
EXPECTED_DISABLE_LIST_LENGTH = 3


def test_rule_init() -> None:
    """Test Rule initialization."""
    rule = Rule(
        pylint_id="C0103", pylint_name="invalid-name", description="Invalid name"
    )
    assert rule.code == "C0103"
    assert rule.name == "invalid-name"
    assert rule.description == "Invalid name"


def test_extract_implemented_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting implemented rules from GitHub issue.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    setup_mocks(monkeypatch)

    extractor = RuffPylintExtractor()
    result = extractor.get_implemented_rules()

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
    setup_mocks(monkeypatch)

    extractor = PylintExtractor()
    rules = extractor.extract_all_rules()

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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        updater = PyprojectUpdater(toml_file)

        disable_rules = [
            Rule(
                pylint_id="F401",
                pylint_name="unused-import",
                description="Unused import",
            ),
            Rule(
                pylint_id="F841",
                pylint_name="unused-variable",
                description="Unused variable",
            ),
        ]
        enable_rules = [
            Rule(
                pylint_id="C0103",
                pylint_name="invalid-name",
                description="Invalid name",
            ),
        ]

        updater.update_pylint_config(disable_rules, [], enable_rules)

        result_dict = toml_file.as_dict()
        assert "tool" in result_dict
        assert "pylint" in result_dict["tool"]
        assert "messages_control" in result_dict["tool"]["pylint"]

        # Check that enable rules are present
        assert "C0103" in result_dict["tool"]["pylint"]["messages_control"]["enable"]

        # Check that disable rules include "all" and the disabled rules
        disable_list = result_dict["tool"]["pylint"]["messages_control"]["disable"]
        assert "all" in disable_list
        assert "F401" in disable_list
        assert "F841" in disable_list
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
    """Test resolving rule identifiers to codes."""
    # Create a Rules object with test rules
    rules = Rules()
    rules.add_rule(
        Rule(pylint_id="F401", pylint_name="unused-import", description="Unused import")
    )
    rules.add_rule(
        Rule(
            pylint_id="F841",
            pylint_name="unused-variable",
            description="Unused variable",
        )
    )
    rules.add_rule(
        Rule(pylint_id="E501", pylint_name="line-too-long", description="Line too long")
    )
    rules.add_rule(
        Rule(pylint_id="C0103", pylint_name="invalid-name", description="Invalid name")
    )

    extractor = PylintExtractor()

    # Test with rule codes
    rule_identifiers = ["F401", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with rule names
    rule_identifiers = ["unused-import", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with mixed codes and names
    rule_identifiers = ["F401", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with unknown identifiers (should be ignored)
    rule_identifiers = ["F401", "unknown-rule", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=rules
    )
    assert resolved == {"F401", "C0103"}


def test_main_function_flow() -> Never:
    """Test that main function doesn't crash.

    This test is intentionally minimal to avoid subprocess mocking complexity.
    """
    # Test that main function runs without crashing on invalid file
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        invalid_config_path = Path(f.name)
        invalid_config_path.unlink()  # Remove the file to make it invalid

    # Test that main handles invalid config gracefully

    original_argv = sys.argv[:]
    try:
        sys.argv = ["test", "--config-file", str(invalid_config_path)]
        result = main()
        assert result == 1  # Should return error code for missing file
    finally:
        sys.argv = original_argv

    pytest.skip("Main function flow test completed")


def test_ruff_extractor_initialization() -> None:
    """Test RuffPylintExtractor initialization."""
    extractor = RuffPylintExtractor()
    assert extractor.issue_url == RUFF_PYLINT_ISSUE_URL


def test_mypy_overlap_filtering() -> None:
    """Test that mypy overlap rules are filtered correctly."""
    # Create test rules including known mypy overlap rules
    rules = Rules()
    rules.add_rule(
        Rule(pylint_id="E1101", pylint_name="no-member", description="No member")
    )  # mypy overlap
    rules.add_rule(
        Rule(pylint_id="E1102", pylint_name="not-callable", description="Not callable")
    )  # mypy overlap
    rules.add_rule(
        Rule(
            pylint_id="R0903",
            pylint_name="too-few-public-methods",
            description="Too few methods",
        )
    )  # not mypy overlap
    rules.add_rule(
        Rule(pylint_id="C0103", pylint_name="invalid-name", description="Invalid name")
    )  # not mypy overlap

    # Create temporary config file with no disabled rules
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as tmp_file:
        tmp_file.write("""[tool.pylint.messages_control]
disable = []
""")
        config_file = Path(tmp_file.name)

    try:
        # Test with mypy overlap filtering enabled (default)
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            _resolve_rule_identifiers(
                all_rules=rules,
                config_file=config_file,
                disable_mypy_overlap=False,
            )
        )

        enabled_rule_ids = {rule.pylint_id for rule in rules_to_enable}
        # Should exclude mypy overlap rules
        assert "E1101" not in enabled_rule_ids
        assert "E1102" not in enabled_rule_ids
        # Should include non-mypy overlap rules
        assert "R0903" in enabled_rule_ids
        assert "C0103" in enabled_rule_ids

        # Test with mypy overlap filtering disabled
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            _resolve_rule_identifiers(
                all_rules=rules,
                config_file=config_file,
                disable_mypy_overlap=True,
            )
        )

        enabled_rule_ids = {rule.pylint_id for rule in rules_to_enable}
        # Should include all rules when filtering is disabled
        assert "E1101" in enabled_rule_ids
        assert "E1102" in enabled_rule_ids
        assert "R0903" in enabled_rule_ids
        assert "C0103" in enabled_rule_ids

    finally:
        Path(tmp_file.name).unlink()


def test_main_with_update_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test main function with --update-cache argument.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    # Setup mocks for GitHub CLI
    setup_mocks(monkeypatch)

    # Create temporary cache file path
    cache_file = tmp_path / "test_cache.json"

    # Mock sys.argv to simulate --update-cache
    monkeypatch.setattr(
        "sys.argv",
        ["pylint-ruff-sync", "--update-cache", "--cache-path", str(cache_file)],
    )

    # Run main function
    result = main()

    # Should exit successfully (return 0)
    assert not result

    # Cache file should be created
    assert cache_file.exists()

    # Check cache content
    with cache_file.open() as f:
        cache_data = json.load(f)

    assert "rules" in cache_data
    assert isinstance(cache_data["rules"], list)
    assert len(cache_data["rules"]) > 0


def test_disable_list_optimization_removes_ruff_implemented_rules() -> None:
    """Test that rules implemented in ruff are removed from disable list."""
    rules = Rules()
    rules.add_rule(
        Rule(pylint_id="C0103", pylint_name="invalid-name", description="Invalid name")
    )
    rules.add_rule(
        Rule(
            pylint_id="W0613",
            pylint_name="unused-argument",
            description="Unused argument",
            is_implemented_in_ruff=True,
        )
    )
    rules.add_rule(
        Rule(
            pylint_id="R0903",
            pylint_name="too-few-public-methods",
            description="Too few public methods",
        )
    )

    # Create config with all rules disabled
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as tmp_file:
        tmp_file.write("""[tool.pylint.messages_control]
disable = ["invalid-name", "unused-argument", "too-few-public-methods"]
""")
        config_file = Path(tmp_file.name)

    try:
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            _resolve_rule_identifiers(
                all_rules=rules,
                config_file=config_file,
                disable_mypy_overlap=True,  # Disable mypy filtering for this test
            )
        )

        # Only R0903 should remain in disable list (not implemented in ruff)
        disabled_rule_ids = {rule.pylint_id for rule in rules_to_disable}
        assert "R0903" in disabled_rule_ids
        assert "C0103" in disabled_rule_ids  # Not implemented in ruff
        assert "W0613" not in disabled_rule_ids  # Removed (implemented in ruff)

        # No rules should be enabled (all are disabled by user)
        assert not rules_to_enable

    finally:
        config_file.unlink()


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
