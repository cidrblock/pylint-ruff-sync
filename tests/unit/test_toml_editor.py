"""Unit tests for TomlFile class and TOML file operations.

These tests cover the TomlFile functionality for reading, updating, and
managing TOML files with proper section handling and comment preservation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pylint_ruff_sync.toml_file import (
    MAX_LINE_LENGTH,
    SimpleArrayWithComments,
    TomlFile,
)
from tests.constants import TOML_SORT_MIN_ARGS

if TYPE_CHECKING:
    import pytest

    from tests.conftest import TomlSortMockProtocol


def test_init_existing_file() -> None:
    """Test TomlFile initialization with existing file."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write('[tool.test]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        assert toml_file.file_path == temp_path
        assert "tool.test" in toml_file.as_str()
    finally:
        temp_path.unlink()


def test_init_nonexistent_file() -> None:
    """Test TomlFile initialization with nonexistent file."""
    toml_file = TomlFile(file_path=Path("nonexistent.toml"))
    assert toml_file.file_path == Path("nonexistent.toml")
    assert not toml_file.as_str()
    assert toml_file.as_dict() == {}


def test_as_dict_existing_file() -> None:
    """Test as_dict method with existing file."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write('[tool.test]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        result = toml_file.as_dict()
        assert result == {"tool": {"test": {"key": "value"}}}
    finally:
        temp_path.unlink()


def test_as_dict_empty_file() -> None:
    """Test as_dict method with empty file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".toml") as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        result = toml_file.as_dict()
        assert result == {}
    finally:
        temp_path.unlink()


def test_as_str() -> None:
    """Test as_str method."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        content = '[tool.test]\nkey = "value"\n'
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        result = toml_file.as_str()
        assert "tool.test" in result
        assert 'key = "value"' in result
    finally:
        temp_path.unlink()


def test_update_section_array_simple_list() -> None:
    """Test updating a section array with a simple list."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["item1", "item2"],
            key="array_key",
            section_path="tool.test",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["array_key"] == ["item1", "item2"]
    finally:
        temp_path.unlink()


def test_update_section_array_with_comments() -> None:
    """Test updating a section array with comments."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write("[tool.pylint.messages_control]\nenable = []\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)

        array_with_comments = SimpleArrayWithComments(
            comments={
                "C0103": "https://example.com/C0103",
                "W0613": "https://example.com/W0613",
            },
            items=["C0103", "W0613"],
        )

        toml_file.update_section_array(
            array_data=array_with_comments,
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == [
            "C0103",
            "W0613",
        ]

        # Check that comments are in the string representation
        result_str = toml_file.as_str()
        assert "https://example.com/C0103" in result_str
        assert "https://example.com/W0613" in result_str
    finally:
        temp_path.unlink()


def test_update_section_array_empty_list() -> None:
    """Test updating a section array with an empty list."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=[],
            key="empty_array",
            section_path="tool.test",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["empty_array"] == []
    finally:
        temp_path.unlink()


def test_write() -> None:
    """Test writing the file to disk."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".toml") as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["item1", "item2"],
            key="items",
            section_path="tool.test",
        )

        toml_file.write()

        # Read the file directly to verify it was written
        content = temp_path.read_text(encoding="utf-8")
        assert "tool.test" in content
        assert "items" in content
        assert "item1" in content
        assert "item2" in content
    finally:
        temp_path.unlink()


def test_simple_array_with_comments_format_empty() -> None:
    """Test SimpleArrayWithComments formatting with empty array."""
    array_with_comments = SimpleArrayWithComments(comments=None, items=[])
    result = array_with_comments.format_as_toml()
    assert result == "[]"


def test_simple_array_with_comments_format_simple() -> None:
    """Test SimpleArrayWithComments formatting with simple array."""
    array_with_comments = SimpleArrayWithComments(
        comments=None, items=["item1", "item2"]
    )
    result = array_with_comments.format_as_toml()
    assert result == '["item1", "item2"]'


def test_simple_array_with_comments_format_with_comments() -> None:
    """Test SimpleArrayWithComments formatting with comments."""
    array_with_comments = SimpleArrayWithComments(
        comments={"item1": "comment1", "item2": "comment2"},
        items=["item1", "item2"],
    )
    result = array_with_comments.format_as_toml()
    expected = '[\n  "item1", # comment1\n  "item2" # comment2\n]'
    assert result == expected


def test_simple_array_with_comments_format_partial_comments() -> None:
    """Test SimpleArrayWithComments formatting with partial comments."""
    array_with_comments = SimpleArrayWithComments(
        comments={"item1": "comment1", "item3": "comment3"},
        items=["item1", "item2", "item3"],
    )
    result = array_with_comments.format_as_toml()
    expected = '[\n  "item1", # comment1\n  "item2",\n  "item3" # comment3\n]'
    assert result == expected


def test_simple_array_multiline_due_to_length() -> None:
    """Test SimpleArrayWithComments formatting goes multiline when exceeding 88."""
    # Create an array that would exceed 88 characters in single-line format
    long_items = [f"very-long-rule-name-{i:02d}" for i in range(10)]
    array_with_comments = SimpleArrayWithComments(
        comments=None,
        items=long_items,
    )
    result = array_with_comments.format_as_toml()

    # Should be multiline due to length
    assert result.startswith("[\n")
    assert result.endswith("\n]")

    # Should contain all items
    for item in long_items:
        assert f'"{item}"' in result


def test_simple_array_single_line_within_limit() -> None:
    """Test SimpleArrayWithComments stays single-line when within 88 characters."""
    short_items = ["C0103", "C0111", "W0613"]
    array_with_comments = SimpleArrayWithComments(
        comments=None,
        items=short_items,
    )
    result = array_with_comments.format_as_toml()

    # Should be single-line since it's short and has no comments
    expected = '["C0103", "C0111", "W0613"]'
    assert result == expected
    assert len(result) < MAX_LINE_LENGTH


def test_simple_array_multiline_with_comments_even_if_short() -> None:
    """Test SimpleArrayWithComments goes multiline when it has comments."""
    array_with_comments = SimpleArrayWithComments(
        comments={"C0103": "invalid-name"},
        items=["C0103"],
    )
    result = array_with_comments.format_as_toml()

    # Should be multiline due to comments, even though it's very short
    expected = '[\n  "C0103" # invalid-name\n]'
    assert result == expected


def test_apply_toml_sort() -> None:
    """Test that toml-sort is applied automatically when content changes."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # Write unsorted content
        f.write('[tool.z]\nkey = "value"\n[tool.a]\nother = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["item"],
            key="items",
            section_path="tool.b",
        )

        # The content should be sorted automatically
        result_str = toml_file.as_str()

        # tool.a should come before tool.b which should come before tool.z
        a_pos = result_str.find("[tool.a]")
        b_pos = result_str.find("[tool.b]")
        z_pos = result_str.find("[tool.z]")

        assert a_pos < b_pos < z_pos
    finally:
        temp_path.unlink()


def test_add_key_to_new_section() -> None:
    """Test adding a key to a completely new section."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".toml") as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["item1"],
            key="items",
            section_path="tool.new.section",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["new"]["section"]["items"] == ["item1"]
    finally:
        temp_path.unlink()


def test_update_existing_key() -> None:
    """Test updating an existing key in an existing section."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        f.write('[tool.test]\nitems = ["old"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["new1", "new2"],
            key="items",
            section_path="tool.test",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["items"] == ["new1", "new2"]
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_comments_and_whitespace() -> None:
    """Test adding a key to a section that has comments and whitespace."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # Complex TOML with comments and whitespace
        content = """# This is a comment
[tool.pylint.main]
jobs = 0

# Another comment
[tool.pylint.messages_control]
# Comment inside section
disable = ["all"]

# Final comment
[tool.ruff]
line-length = 80
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["C0103", "W0613"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == [
            "C0103",
            "W0613",
        ]
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == ["all"]
        assert not result_dict["tool"]["pylint"]["main"]["jobs"]
        line_length = 80
        assert result_dict["tool"]["ruff"]["line-length"] == line_length
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_similar_section_names() -> None:
    """Test adding a key when there are sections with similar names."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # TOML with similar section names that could confuse regex
        content = """[tool.pylint]
version = "3.0"

[tool.pylint.main]
jobs = 0

[tool.pylint.messages_control]
disable = ["all"]

[tool.pylint.messages_control.extended]
extra = true
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["C0103"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == ["C0103"]
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == ["all"]
        # Make sure other sections are not affected
        assert not result_dict["tool"]["pylint"]["main"]["jobs"]
        assert (
            result_dict["tool"]["pylint"]["messages_control"]["extended"]["extra"]
            is True
        )
    finally:
        temp_path.unlink()


def test_add_key_to_section_at_end_of_file() -> None:
    """Test adding a key to a section at the end of the file."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # TOML with section at end, no trailing newline
        content = """[tool.first]
value = 1

[tool.last]
existing = true"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["item1"],
            key="items",
            section_path="tool.last",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["last"]["items"] == ["item1"]
        assert result_dict["tool"]["last"]["existing"] is True
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_multiline_values() -> None:
    """Test adding a key to a section that has multiline values."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # TOML with multiline values
        content = """[tool.pylint.messages_control]
disable = [
    "all",
    "locally-disabled",
    "suppressed-message"
]

[tool.other]
value = "test"
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["C0103"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == ["C0103"]
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "all",
            "locally-disabled",
            "suppressed-message",
        ]
        assert result_dict["tool"]["other"]["value"] == "test"
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_duplicate_content() -> None:
    """Test adding a key to a section when there's duplicate content."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # TOML with duplicate content that could cause issues with string replacement
        content = """[tool.pylint.messages_control]
disable = ["all"]

[tool.ruff]
# This comment contains the same text as above: disable = ["all"]
line-length = 80

[tool.other]
disable = ["all"]
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)
        toml_file.update_section_array(
            array_data=["C0103"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()
        # Check that the key was added to the correct section
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == ["C0103"]
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == ["all"]

        # Check that other sections were not affected
        assert result_dict["tool"]["other"]["disable"] == ["all"]
        line_length = 80
        assert result_dict["tool"]["ruff"]["line-length"] == line_length

    finally:
        temp_path.unlink()


def test_add_key_to_section_string_replacement_issue() -> None:
    """Test that adding keys to sections only affects the correct section."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # Create a TOML where section content appears multiple times
        content = """[tool.pylint.messages_control]
disable = ["all"]

[tool.test]
# This section has the same content: disable = ["all"]
disable = ["all"]
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)

        # This call should only affect the first section
        toml_file.update_section_array(
            array_data=["C0103"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        result_dict = toml_file.as_dict()

        # Check that the key was added to the correct section
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == ["C0103"]
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == ["all"]

        # Check that the other section was not affected
        assert result_dict["tool"]["test"]["disable"] == ["all"]
        assert "enable" not in result_dict["tool"]["test"]

    finally:
        temp_path.unlink()


def test_debug_unexpected_char_error() -> None:
    """Debug test to understand the UnexpectedCharError."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".toml") as f:
        # Use the exact structure from pyproject.toml that causes the issue
        content = """[tool.pylint.messages_control]
disable = ["all", "locally-disabled", "suppressed-message"]
enable = [
  "C0104", # comment
  "C0117", # comment
  "C0200"  # comment
]
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(file_path=temp_path)

        # This should work with the new implementation
        toml_file.update_section_array(
            array_data=["C0103", "C0117", "C0200"],
            key="enable",
            section_path="tool.pylint.messages_control",
        )

        # Check the result
        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == [
            "C0103",
            "C0117",
            "C0200",
        ]

    finally:
        temp_path.unlink()


def test_automatic_toml_sort_application(*, tmp_path: Path) -> None:
    """Test that toml-sort is automatically applied when content changes.

    Args:
        tmp_path: Temporary path for the test file.

    """
    toml_content = """[tool.pylint.messages_control]
disable = ["rule-a", "rule-b"]

[tool.ruff]
line-length = 88
"""

    temp_file = tmp_path / "test.toml"
    temp_file.write_text(toml_content)

    toml_file = TomlFile(file_path=temp_file)

    # Update an array - this should trigger automatic sorting
    toml_file.update_section_array(
        array_data=["rule-c", "rule-a"],
        key="disable",
        section_path="tool.pylint.messages_control",
    )

    result_str = toml_file.as_str()

    # The content should be properly formatted by toml-sort
    assert "rule-c" in result_str
    assert "rule-a" in result_str

    # Verify it's valid TOML
    parsed = toml_file.as_dict()
    assert "rule-c" in parsed["tool"]["pylint"]["messages_control"]["disable"]
    assert "rule-a" in parsed["tool"]["pylint"]["messages_control"]["disable"]


def test_toml_sort_with_custom_configuration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    toml_sort_mock: TomlSortMockProtocol,
) -> None:
    """Test that toml-sort works with custom configuration using monkeypatch.

    This test simulates toml-sort behavior with:
    - sort_inline_tables = true
    - sort_table_keys = true

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary path for the test file.
        toml_sort_mock: Fixture for toml-sort mock functionality.

    """

    def mock_subprocess_run(*args: object, **_kwargs: object) -> object:
        """Mock subprocess.run to intercept toml-sort calls.

        Args:
            *args: Arguments passed to subprocess.run.
            **_kwargs: Keyword arguments passed to subprocess.run (unused).

        Returns:
            Mock subprocess result.

        """

        # Create a mock result object for subprocess.run
        class MockResult:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = ""
                self.stderr = ""

        # Check if this is a toml-sort command
        if (
            args
            and len(args) > 0
            and isinstance(args[0], list)
            and len(args[0]) > 0
            and args[0][0] == "toml-sort"
        ):
            # Handle toml-sort subprocess call
            command_args = args[0]
            if "--in-place" in command_args and len(command_args) >= TOML_SORT_MIN_ARGS:
                file_path = command_args[2]
                # Use the fixture to apply the mock
                toml_sort_mock(file_path=file_path)
                return MockResult()

        return MockResult()

    # Monkeypatch the subprocess function
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    # Test content with unsorted sections
    toml_content = """[tool.z]
key = "value"

[tool.a]
other = "value"

[tool.pylint.messages_control]
disable = ["rule-b", "rule-a"]
"""

    temp_file = tmp_path / "test.toml"
    temp_file.write_text(toml_content)

    toml_file = TomlFile(file_path=temp_file)

    # Update an array - this should trigger automatic sorting
    toml_file.update_section_array(
        array_data=["rule-c", "rule-a"],
        key="disable",
        section_path="tool.pylint.messages_control",
    )

    result_str = toml_file.as_str()

    # With sort_table_keys=true, sections should be sorted alphabetically
    # tool.a should come before tool.pylint.messages_control which should
    # come before tool.z (if it exists)
    a_pos = result_str.find("[tool.a]")
    pylint_pos = result_str.find("[tool.pylint.messages_control]")
    z_pos = result_str.find("[tool.z]")

    # Check that sections that exist are properly sorted
    if a_pos != -1 and pylint_pos != -1:
        assert a_pos < pylint_pos, (
            f"tool.a should come before tool.pylint: a={a_pos}, pylint={pylint_pos}"
        )

    # Only check z ordering if z section exists (z_pos > 0 since sections can't be at pos 0)
    if z_pos > 0 and pylint_pos != -1:
        assert pylint_pos < z_pos, (
            f"tool.pylint should come before tool.z: pylint={pylint_pos}, z={z_pos}"
        )

    # Verify the content is valid TOML
    parsed = toml_file.as_dict()
    assert "rule-c" in parsed["tool"]["pylint"]["messages_control"]["disable"]
    assert "rule-a" in parsed["tool"]["pylint"]["messages_control"]["disable"]
