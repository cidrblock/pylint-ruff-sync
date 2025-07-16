"""Test module for main functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest  # noqa: TC002

from pylint_ruff_sync.main import (
    _resolve_rule_identifiers,
    _setup_argument_parser,
)
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pylint_rule import PylintRule
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import RuffPylintExtractor
from pylint_ruff_sync.toml_file import TomlFile
from tests.constants import (
    EXPECTED_IMPLEMENTED_RULES_COUNT,
    EXPECTED_RULES_COUNT,
    setup_mocks,
)

# Constants for test expectations
EXPECTED_DISABLE_LIST_LENGTH = 3


def test_pylint_rule_init() -> None:
    """Test PylintRule initialization."""
    rule = PylintRule(rule_id="C0103", name="invalid-name", description="Invalid name")
    assert rule.code == "C0103"
    assert rule.name == "invalid-name"
    assert rule.description == "Invalid name"


def test_pylint_rule_repr() -> None:
    """Test PylintRule representation."""
    rule = PylintRule(rule_id="C0103", name="invalid-name", description="Invalid name")
    assert repr(rule) == "PylintRule(rule_id='C0103', name='invalid-name')"


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
    assert rules[0].code == "C0103"
    assert rules[0].name == "invalid-name"
    assert rules[1].code == "C0111"
    assert rules[1].name == "missing-docstring"
    assert rules[2].code == "E501"
    assert rules[2].name == "line-too-long"
    assert rules[3].code == "F401"
    assert rules[3].name == "unused-import"
    assert rules[4].code == "F841"
    assert rules[4].name == "unused-variable"
    assert rules[5].code == "R0903"
    assert rules[5].name == "too-few-public-methods"


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
            PylintRule(
                rule_id="F401", name="unused-import", description="Unused import"
            ),
            PylintRule(
                rule_id="F841", name="unused-variable", description="Unused variable"
            ),
        ]
        enable_rules = [
            PylintRule(
                rule_id="C0103", name="invalid-name", description="Invalid name"
            ),
        ]

        updater.update_pylint_config(disable_rules, enable_rules)

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
    all_rules = [
        PylintRule(rule_id="F401", name="unused-import", description="Unused import"),
        PylintRule(
            rule_id="F841", name="unused-variable", description="Unused variable"
        ),
        PylintRule(rule_id="E501", name="line-too-long", description="Line too long"),
        PylintRule(rule_id="C0103", name="invalid-name", description="Invalid name"),
    ]

    extractor = PylintExtractor()

    # Test with rule codes
    rule_identifiers = ["F401", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=all_rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with rule names
    rule_identifiers = ["unused-import", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=all_rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with mixed codes and names
    rule_identifiers = ["F401", "invalid-name"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=all_rules
    )
    assert resolved == {"F401", "C0103"}

    # Test with unknown identifiers (should be ignored)
    rule_identifiers = ["F401", "unknown-rule", "C0103"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=all_rules
    )
    assert resolved == {"F401", "C0103"}


def test_disabled_rule_by_name_not_enabled() -> None:
    """Test that disabled rules by name are not enabled."""
    all_rules = [
        PylintRule(rule_id="F401", name="unused-import", description="Unused import"),
        PylintRule(rule_id="C0103", name="invalid-name", description="Invalid name"),
    ]

    extractor = PylintExtractor()

    # Test resolving rule names to codes
    rule_identifiers = ["unused-import"]
    resolved = extractor.resolve_rule_identifiers(
        rule_identifiers=rule_identifiers, all_rules=all_rules
    )
    assert resolved == {"F401"}


def test_update_pylint_config_with_existing_disabled_rules() -> None:
    """Test updating pylint configuration with existing disabled rules."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""[tool.pylint.messages_control]
disable = ["existing-rule"]
""")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        updater = PyprojectUpdater(toml_file)

        disable_rules = [
            PylintRule(
                rule_id="F401", name="unused-import", description="Unused import"
            ),
        ]
        enable_rules = [
            PylintRule(
                rule_id="C0103", name="invalid-name", description="Invalid name"
            ),
        ]

        updater.update_pylint_config(disable_rules, enable_rules)

        result_dict = toml_file.as_dict()

        # Check that existing disabled rules are preserved
        disable_list = result_dict["tool"]["pylint"]["messages_control"]["disable"]
        assert "existing-rule" in disable_list
        assert "all" in disable_list
        assert "F401" in disable_list

        # Check that enable rules are present
        assert "C0103" in result_dict["tool"]["pylint"]["messages_control"]["enable"]
    finally:
        temp_path.unlink()


def test_r0917_specific_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that R0917 is specifically detected from GitHub issue content.

    Args:
        monkeypatch: pytest fixture for mocking.

    """
    # Create a mock response with R0917 using exact GitHub formatting
    mock_r0917_response = (
        '{"body": "## Status\\\\n\\\\n### Implemented Rules\\\\n\\\\n'
        '- [x] `too-many-positional-arguments` /  `R0917` (`PLR0917`)\\\\n"}'
    )

    class MockSubprocessResult:
        """Mock subprocess.run result."""

        def __init__(self, returncode: int, stdout: str) -> None:
            """Initialize mock result.

            Args:
                returncode: The return code of the process.
                stdout: The stdout output of the process.

            """
            self.stdout = stdout
            self.returncode = returncode
            self.stderr = ""

    def mock_subprocess_run_r0917(
        *args: object, **_kwargs: object
    ) -> MockSubprocessResult:
        """Mock subprocess.run for R0917 test case.

        Args:
            *args: Command arguments (unused).
            **_kwargs: Keyword arguments (unused).

        Returns:
            MockSubprocessResult with R0917 issue data.

        """
        if (
            args
            and len(args) > 0
            and isinstance(args[0], list)
            and len(args[0]) > 0
            and args[0][0] == "gh"
        ):
            return MockSubprocessResult(returncode=0, stdout=mock_r0917_response)
        # Return empty result for other commands
        return MockSubprocessResult(returncode=0, stdout="")

    monkeypatch.setattr("subprocess.run", mock_subprocess_run_r0917)

    extractor = RuffPylintExtractor()
    implemented_rules = extractor._fetch_from_github()

    # This should find R0917 but currently fails due to regex pattern
    assert "R0917" in implemented_rules, (
        f"R0917 should be detected as implemented. Found rules: {implemented_rules}"
    )


def test_disable_mypy_overlap_argument() -> None:
    """Test that the --disable-mypy-overlap argument is parsed correctly."""
    parser = _setup_argument_parser()

    # Test disable mypy overlap argument
    args = parser.parse_args(["--disable-mypy-overlap"])
    assert args.disable_mypy_overlap is True

    # Test default mypy overlap behavior
    args = parser.parse_args([])
    assert args.disable_mypy_overlap is False


def test_mypy_overlap_filtering() -> None:
    """Test that mypy overlap rules are filtered correctly."""
    # Create test rules including known mypy overlap rules
    all_rules = [
        PylintRule(
            rule_id="E1101", name="no-member", description="No member"
        ),  # mypy overlap
        PylintRule(
            rule_id="E1102", name="not-callable", description="Not callable"
        ),  # mypy overlap
        PylintRule(
            rule_id="R0903",
            name="too-few-public-methods",
            description="Too few methods",
        ),  # not mypy overlap
        PylintRule(
            rule_id="C0103", name="invalid-name", description="Invalid name"
        ),  # not mypy overlap
    ]

    implemented_codes: list[str] = []  # None implemented in ruff

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
        rules_to_disable, rules_to_enable = _resolve_rule_identifiers(
            all_rules=all_rules,
            implemented_codes=implemented_codes,
            config_file=config_file,
            disable_mypy_overlap=False,
        )

        enabled_rule_ids = {rule.rule_id for rule in rules_to_enable}
        # Should exclude mypy overlap rules
        assert "E1101" not in enabled_rule_ids
        assert "E1102" not in enabled_rule_ids
        # Should include non-mypy overlap rules
        assert "R0903" in enabled_rule_ids
        assert "C0103" in enabled_rule_ids

        # Test with mypy overlap filtering disabled
        rules_to_disable, rules_to_enable = _resolve_rule_identifiers(
            all_rules=all_rules,
            implemented_codes=implemented_codes,
            config_file=config_file,
            disable_mypy_overlap=True,
        )

        enabled_rule_ids = {rule.rule_id for rule in rules_to_enable}
        # Should include all rules when filtering is disabled
        assert "E1101" in enabled_rule_ids
        assert "E1102" in enabled_rule_ids
        assert "R0903" in enabled_rule_ids
        assert "C0103" in enabled_rule_ids

    finally:
        Path(tmp_file.name).unlink()
