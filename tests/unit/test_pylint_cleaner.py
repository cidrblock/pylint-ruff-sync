"""Unit tests for PylintCleaner class."""

from __future__ import annotations

import tempfile
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
def temp_project_dir() -> Path:
    """Create a temporary directory for testing.

    Returns:
        Path to temporary directory.

    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def pylint_cleaner(temp_project_dir: Path, mock_rules: Rules) -> PylintCleaner:
    """Create a PylintCleaner instance for testing.

    Args:
        temp_project_dir: Temporary project directory.
        mock_rules: Mock rules object.

    Returns:
        PylintCleaner instance.

    """
    return PylintCleaner(project_root=temp_project_dir, rules=mock_rules)


def test_disable_comment_dataclass() -> None:
    """Test DisableComment dataclass creation."""
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=10,
        original_line="x = eval('1')  # pylint: disable=eval-used",
        pylint_rules=["eval-used"],
        other_tools_content="",
        comment_format="inline",
    )

    assert comment.file_path == Path("test.py")
    assert comment.line_number == 10
    assert comment.pylint_rules == ["eval-used"]
    assert comment.comment_format == "inline"


def test_compile_disable_patterns(pylint_cleaner: PylintCleaner) -> None:
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


def test_parse_disable_comment_simple(pylint_cleaner: PylintCleaner) -> None:
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


def test_parse_disable_comment_multiple_rules(pylint_cleaner: PylintCleaner) -> None:
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
    assert len(comment.pylint_rules) == 2


def test_parse_disable_comment_with_noqa(pylint_cleaner: PylintCleaner) -> None:
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


def test_parse_disable_comment_skip_file(pylint_cleaner: PylintCleaner) -> None:
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


def test_remove_useless_rules_partial(pylint_cleaner: PylintCleaner) -> None:
    """Test removing some but not all rules from a disable comment.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    comment = DisableComment(
        file_path=Path("test.py"),
        line_number=1,
        original_line="def foo():  # pylint: disable=missing-function-docstring,unused-argument",
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


def test_remove_useless_rules_all(pylint_cleaner: PylintCleaner) -> None:
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


def test_remove_useless_rules_preserve_noqa(pylint_cleaner: PylintCleaner) -> None:
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


def test_remove_useless_rules_skip_file(pylint_cleaner: PylintCleaner) -> None:
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


def test_parse_pylint_output(pylint_cleaner: PylintCleaner) -> None:
    """Test parsing pylint useless-suppression output.

    Args:
        pylint_cleaner: PylintCleaner instance.

    """
    output = """test.py:10:1: R0903: Useless suppression of 'eval-used'
test.py:15:1: R0903: Useless suppression of 'unused-argument'
other.py:5:1: R0903: Useless suppression of 'missing-function-docstring'
"""

    result = pylint_cleaner._parse_pylint_output(output=output)

    assert len(result) == 2  # Two files
    assert Path("test.py") in result
    assert Path("other.py") in result

    test_py_suppressions = result[Path("test.py")]
    assert len(test_py_suppressions) == 2
    assert (10, "eval-used") in test_py_suppressions
    assert (15, "unused-argument") in test_py_suppressions

    other_py_suppressions = result[Path("other.py")]
    assert len(other_py_suppressions) == 1
    assert (5, "missing-function-docstring") in other_py_suppressions


def test_clean_files_dry_run(
    pylint_cleaner: PylintCleaner,
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean_files in dry-run mode.

    Args:
        pylint_cleaner: PylintCleaner instance.
        temp_project_dir: Temporary project directory.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Create a test file
    test_file = temp_project_dir / "test.py"
    test_file.write_text("x = eval('1')  # pylint: disable=eval-used\n")

    # Mock the useless suppressions detection
    mock_suppressions = {test_file: [(1, "eval-used")]}
    monkeypatch.setattr(
        pylint_cleaner,
        "_detect_useless_suppressions",
        lambda: mock_suppressions,
    )

    # Run in dry-run mode
    result = pylint_cleaner.clean_files(dry_run=True)

    # Should report modifications but not change file
    assert test_file in result
    assert result[test_file] == 1

    # File should be unchanged
    content = test_file.read_text()
    assert "pylint: disable=eval-used" in content


def test_clean_files_actual_modification(
    pylint_cleaner: PylintCleaner,
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean_files with actual file modification.

    Args:
        pylint_cleaner: PylintCleaner instance.
        temp_project_dir: Temporary project directory.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Create a test file
    test_file = temp_project_dir / "test.py"
    test_file.write_text("x = eval('1')  # pylint: disable=eval-used\n")

    # Mock the useless suppressions detection
    mock_suppressions = {test_file: [(1, "eval-used")]}
    monkeypatch.setattr(
        pylint_cleaner,
        "_detect_useless_suppressions",
        lambda: mock_suppressions,
    )

    # Run actual cleaning
    result = pylint_cleaner.clean_files(dry_run=False)

    # Should report modifications and change file
    assert test_file in result
    assert result[test_file] == 1

    # File should be modified
    content = test_file.read_text()
    assert "pylint: disable=eval-used" not in content
    assert "x = eval('1')" in content
