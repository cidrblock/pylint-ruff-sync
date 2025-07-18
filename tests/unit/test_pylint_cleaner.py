"""Unit tests for PylintCleaner class."""  # pylint: disable=redefined-outer-name

from __future__ import annotations

from pathlib import Path

import pytest

from pylint_ruff_sync.pylint_cleaner import DisableComment, PylintCleaner
from pylint_ruff_sync.rule import Rule, Rules, RuleSource


@pytest.fixture
def mock_rules() -> Rules:
    """Create a mock Rules object for testing.

    Returns:
        Rules object with test data.

    """
    rules = Rules()

    # Add some test rules
    test_rules = [
        Rule(
            pylint_id="C0103",
            pylint_name="invalid-name",
            description="Invalid name",
            source=RuleSource.PYLINT_LIST,
        ),
        Rule(
            pylint_id="W0613",
            pylint_name="unused-argument",
            description="Unused argument",
            source=RuleSource.PYLINT_LIST,
        ),
        Rule(
            pylint_id="C0116",
            pylint_name="missing-function-docstring",
            description="Missing function docstring",
            source=RuleSource.PYLINT_LIST,
        ),
    ]

    for rule in test_rules:
        rules.add_rule(rule=rule)

    return rules


@pytest.fixture
def pylint_cleaner(tmp_path: Path, mock_rules: Rules) -> PylintCleaner:
    """Create a PylintCleaner instance for testing.

    Args:
        tmp_path: Temporary project directory from pytest.
        mock_rules: Mock rules object.

    Returns:
        PylintCleaner instance.

    """
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("""
[tool.pylint.messages_control]
disable = ["all"]
enable = ["C0103", "W0613"]
""")

    return PylintCleaner(
        config_file=config_file,
        dry_run=False,
        project_root=tmp_path,
        rules=mock_rules,
    )


@pytest.fixture
def pylint_cleaner_dry_run(tmp_path: Path, mock_rules: Rules) -> PylintCleaner:
    """Create a PylintCleaner instance for dry-run testing.

    Args:
        tmp_path: Temporary project directory from pytest.
        mock_rules: Mock rules object.

    Returns:
        PylintCleaner instance configured for dry-run mode.

    """
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("""
[tool.pylint.messages_control]
disable = ["all"]
enable = ["C0103", "W0613"]
""")

    return PylintCleaner(
        config_file=config_file,
        dry_run=True,
        project_root=tmp_path,
        rules=mock_rules,
    )


def test_disable_comment_dataclass() -> None:
    """Test DisableComment dataclass creation."""
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=EXAMPLE_LINE_NUMBER,
        original_line="x = eval('1')  # pylint: disable=eval-used",
        pylint_rules=["eval-used"],
        other_tools_content="",
        comment_format="inline",
    )

    assert comment.file_path == Path("test.py")
    assert comment.line_number == EXAMPLE_LINE_NUMBER
    assert comment.pylint_rules == ["eval-used"]
    assert comment.comment_format == "inline"


def test_compile_disable_patterns(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test that disable patterns are compiled correctly.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    patterns = pylint_cleaner._disable_patterns
    assert len(patterns) > 0

    # Test that patterns can match basic disable comments
    test_line = "x = eval('1')  # pylint: disable=eval-used"
    matched = any(pattern.match(test_line) for pattern in patterns)
    assert matched


def test_parse_disable_comment_simple(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test parsing a simple disable comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    line = "x = eval('1')  # pylint: disable=eval-used"
    comment = pylint_cleaner._parse_disable_comment(
        file_path=Path("test.py"),
        line_content=line,
        line_number=1,
    )

    assert comment is not None
    assert comment.pylint_rules == ["eval-used"]
    assert comment.comment_format == "inline"
    assert comment.original_line == line


def test_parse_disable_comment_multiple_rules(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test parsing disable comment with multiple rules.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    line = "def foo():  # pylint: disable=missing-function-docstring,unused-argument"
    comment = pylint_cleaner._parse_disable_comment(
        file_path=Path("test.py"),
        line_content=line,
        line_number=1,
    )

    assert comment is not None
    assert "missing-function-docstring" in comment.pylint_rules
    assert "unused-argument" in comment.pylint_rules
    assert len(comment.pylint_rules) == EXPECTED_RULE_COUNT


def test_parse_disable_comment_with_noqa(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test parsing disable comment mixed with noqa.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    line = "x = eval('1')  # noqa: E501  # pylint: disable=eval-used"
    comment = pylint_cleaner._parse_disable_comment(
        file_path=Path("test.py"),
        line_content=line,
        line_number=1,
    )

    assert comment is not None
    assert comment.pylint_rules == ["eval-used"]
    assert "noqa" in comment.other_tools_content


def test_parse_disable_comment_skip_file(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test parsing skip-file comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    line = "# pylint: skip-file"
    comment = pylint_cleaner._parse_disable_comment(
        file_path=Path("test.py"),
        line_content=line,
        line_number=1,
    )

    assert comment is not None
    assert comment.pylint_rules == ["skip-file"]
    assert comment.comment_format == "skip-file"


def test_remove_useless_rules_partial(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test removing some but not all rules from a disable comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=1,
        original_line=(
            "def foo():  # pylint: disable=missing-function-docstring,unused-argument"
        ),
        pylint_rules=["missing-function-docstring", "unused-argument"],
        other_tools_content="",
        comment_format="inline",
    )

    # Remove only one rule
    useless_rules = ["missing-function-docstring"]
    result = pylint_cleaner._remove_useless_rules_from_comment(
        disable_comment=comment,
        useless_rules=useless_rules,
    )

    assert result is not None
    assert "unused-argument" in result
    assert "missing-function-docstring" not in result
    assert "pylint: disable=" in result


def test_remove_useless_rules_all(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test removing all rules from a disable comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=1,
        original_line="x = eval('1')  # pylint: disable=eval-used",
        pylint_rules=["eval-used"],
        other_tools_content="",
        comment_format="inline",
    )

    # Remove all rules
    useless_rules = ["eval-used"]
    result = pylint_cleaner._remove_useless_rules_from_comment(
        disable_comment=comment,
        useless_rules=useless_rules,
    )

    # Should return code part only
    assert result is not None
    assert "x = eval('1')" in result
    assert "pylint" not in result


def test_remove_useless_rules_preserve_noqa(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test preserving noqa when removing pylint rules.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=1,
        original_line="x = eval('1')  # noqa: E501  # pylint: disable=eval-used",
        pylint_rules=["eval-used"],
        other_tools_content="noqa: E501",
        comment_format="inline",
    )

    # Remove all pylint rules
    useless_rules = ["eval-used"]
    result = pylint_cleaner._remove_useless_rules_from_comment(
        disable_comment=comment,
        useless_rules=useless_rules,
    )

    assert result is not None
    assert "noqa: E501" in result
    assert "pylint" not in result


def test_remove_useless_rules_skip_file(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test removing skip-file comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=1,
        original_line="# pylint: skip-file",
        pylint_rules=["skip-file"],
        other_tools_content="",
        comment_format="skip-file",
    )

    # Remove skip-file
    useless_rules = ["skip-file"]
    result = pylint_cleaner._remove_useless_rules_from_comment(
        disable_comment=comment,
        useless_rules=useless_rules,
    )

    # Should return None to indicate line removal
    assert result is None


def test_parse_pylint_output(
    pylint_cleaner: PylintCleaner,
) -> None:
    """Test parsing pylint useless-suppression output.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    output = """test.py:10:0: I0021: Useless suppression of 'eval-used'
test.py:15:0: I0021: Useless suppression of 'unused-argument'
other.py:5:0: I0021: Useless suppression of 'missing-docstring'
"""

    result = pylint_cleaner._parse_pylint_output(output=output)

    assert len(result) == EXPECTED_FILE_COUNT  # Two files
    assert Path("test.py") in result
    assert Path("other.py") in result

    test_py_suppressions = result[Path("test.py")]
    assert len(test_py_suppressions) == EXPECTED_SUPPRESSION_COUNT
    assert (EXAMPLE_LINE_10, "eval-used") in test_py_suppressions
    assert (EXAMPLE_LINE_15, "unused-argument") in test_py_suppressions

    other_py_suppressions = result[Path("other.py")]
    assert len(other_py_suppressions) == 1
    assert (EXAMPLE_LINE_5, "missing-docstring") in other_py_suppressions


def test_clean_files_dry_run(
    pylint_cleaner_dry_run: PylintCleaner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean_files method in dry run mode.

    Args:
        pylint_cleaner_dry_run: PylintCleaner instance in dry run mode.
        tmp_path: Temporary directory fixture from pytest.
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("x = eval('1')  # pylint: disable=eval-used\n")

    # Mock the useless suppressions detection
    mock_suppressions = {test_file: [(1, "eval-used")]}
    monkeypatch.setattr(
        pylint_cleaner_dry_run,
        "_detect_useless_suppressions",
        lambda: mock_suppressions,
    )

    # Run in dry-run mode
    result = pylint_cleaner_dry_run.run()

    # Should report modifications but not change file
    assert test_file in result
    assert result[test_file] == 1

    # File should be unchanged
    content = test_file.read_text()
    assert "pylint: disable=eval-used" in content


def test_clean_files_actual_modification(
    pylint_cleaner: PylintCleaner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean_files with actual file modification.

    Args:
        pylint_cleaner: PylintCleaner instance.
        tmp_path: Temporary project directory.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("x = eval('1')  # pylint: disable=eval-used\n")

    # Mock the useless suppressions detection
    mock_suppressions = {test_file: [(1, "eval-used")]}
    monkeypatch.setattr(
        pylint_cleaner,
        "_detect_useless_suppressions",
        lambda: mock_suppressions,
    )

    # Run actual cleaning
    result = pylint_cleaner.run()

    # Should report modifications and change file
    assert test_file in result
    assert result[test_file] == 1

    # File should be modified
    content = test_file.read_text()
    assert "pylint: disable=eval-used" not in content
    assert "x = eval('1')" in content


def test_integration_real_pylint_execution(
    tmp_path: Path,
    mock_rules: Rules,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test integration with real pylint execution to detect useless suppressions.

    This test mocks the pylint output to ensure the regex parsing works correctly
    and the cleaner properly removes suppressions.

    Args:
        tmp_path: Temporary project directory.
        mock_rules: Mock rules object.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Create pyproject.toml with minimal pylint config
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("""
[tool.pylint.messages_control]
disable = ["all"]
enable = ["invalid-name", "unused-argument", "useless-suppression"]
""")

    # Create a test Python file with suppressions
    test_file = tmp_path / "test_module.py"
    test_content = '''"""Test module with pylint suppressions."""

def valid_function_name():  # pylint: disable=invalid-name
    """Function with suppression to be removed."""
    pass

def another_function(used_arg):  # pylint: disable=unused-argument
    """Function with suppression to be removed."""
    return used_arg

# This should remain - different from useless ones
def x():  # pylint: disable=missing-function-docstring
    """Function that keeps its suppression."""
    pass
'''
    test_file.write_text(test_content)

    # Mock the pylint execution to return specific useless suppressions
    def mock_detect_useless_suppressions() -> dict[Path, list[tuple[int, str]]]:
        return {
            test_file: [
                (3, "invalid-name"),  # Line with valid_function_name
                (7, "unused-argument"),  # Line with another_function
            ]
        }

    # Create PylintCleaner instance
    cleaner = PylintCleaner(
        config_file=config_file,
        dry_run=False,
        project_root=tmp_path,
        rules=mock_rules,
    )

    # Mock the useless suppressions detection
    monkeypatch.setattr(
        cleaner, "_detect_useless_suppressions", mock_detect_useless_suppressions
    )

    # Run the cleaner
    result = cleaner.run()

    # Read the modified content
    modified_content = test_file.read_text()

    # Check that useless suppressions were removed
    lines = modified_content.split("\n")

    # Find the lines that should have been modified
    function_line = next(line for line in lines if "def valid_function_name" in line)
    assert "pylint: disable=invalid-name" not in function_line

    used_arg_line = next(line for line in lines if "def another_function" in line)
    assert "pylint: disable=unused-argument" not in used_arg_line

    # The last suppression should remain (not in the useless list)
    doc_line = next(line for line in lines if "def x():" in line)
    assert "pylint: disable=missing-function-docstring" in doc_line

    # Should report modifications
    assert test_file in result
    assert result[test_file] >= 1  # At least one line modified


def test_real_pylint_output_parsing(
    tmp_path: Path,
    mock_rules: Rules,
) -> None:
    """Test that _parse_pylint_output correctly handles real pylint output.

    Args:
        tmp_path: Temporary project directory.
        mock_rules: Mock rules object.

    """
    config_file = tmp_path / "pyproject.toml"
    cleaner = PylintCleaner(
        config_file=config_file,
        dry_run=True,
        project_root=tmp_path,
        rules=mock_rules,
    )

    # Real pylint output format (can vary based on configuration)
    # Testing both common formats
    real_output = (
        "************* Module test_module\n"
        "src/test_module.py:10: [I0021(useless-suppression), ] "
        "Useless suppression of 'invalid-name'\n"
        "src/test_module.py:15:0: I0021: Useless suppression of 'unused-argument'\n"
        "src/other_module.py:5:0: I0021: Useless suppression of 'missing-docstring'\n"
        "\n"
        "--------------------------------------------------------------------\n"
        "Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)\n"
    )

    result = cleaner._parse_pylint_output(output=real_output)

    # Should correctly parse the real format
    assert len(result) == EXPECTED_FILE_COUNT
    assert Path("src/test_module.py") in result
    assert Path("src/other_module.py") in result

    test_module_suppressions = result[Path("src/test_module.py")]
    assert len(test_module_suppressions) == EXPECTED_TEST_MODULE_SUPPRESSIONS
    assert (EXAMPLE_LINE_10, "invalid-name") in test_module_suppressions
    assert (EXAMPLE_LINE_15, "unused-argument") in test_module_suppressions

    other_module_suppressions = result[Path("src/other_module.py")]
    assert len(other_module_suppressions) == 1
    assert (5, "missing-docstring") in other_module_suppressions


# Constants for test values
EXAMPLE_LINE_NUMBER = 10
EXPECTED_RULE_COUNT = 2
EXPECTED_FILE_COUNT = 2
EXPECTED_SUPPRESSION_COUNT = 2
EXAMPLE_LINE_5 = 5
EXAMPLE_LINE_10 = 10
EXAMPLE_LINE_15 = 15
EXPECTED_TEST_MODULE_SUPPRESSIONS = 2
