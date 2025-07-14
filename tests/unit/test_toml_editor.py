"""Tests for the TomlFile class."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pylint_ruff_sync.toml_file import SimpleArrayWithComments, TomlFile


def test_init_existing_file() -> None:
    """Test TomlFile initialization with existing file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.test]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        assert toml_file.file_path == temp_path
        assert "tool.test" in toml_file.as_str()
    finally:
        temp_path.unlink()


def test_init_nonexistent_file() -> None:
    """Test TomlFile initialization with nonexistent file."""
    toml_file = TomlFile(Path("nonexistent.toml"))
    assert toml_file.file_path == Path("nonexistent.toml")
    assert not toml_file.as_str()
    assert toml_file.as_dict() == {}


def test_as_dict_existing_file() -> None:
    """Test as_dict method with existing file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.test]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        result = toml_file.as_dict()
        assert result == {"tool": {"test": {"key": "value"}}}
    finally:
        temp_path.unlink()


def test_as_dict_empty_file() -> None:
    """Test as_dict method with empty file."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        result = toml_file.as_dict()
        assert result == {}
    finally:
        temp_path.unlink()


def test_as_str() -> None:
    """Test as_str method."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        content = '[tool.test]\nkey = "value"\n'
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        result = toml_file.as_str()
        assert "tool.test" in result
        assert 'key = "value"' in result
    finally:
        temp_path.unlink()


def test_update_section_array_simple_list() -> None:
    """Test updating a section array with a simple list."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.test",
            key="array_key",
            array_data=["item1", "item2"],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["array_key"] == ["item1", "item2"]
    finally:
        temp_path.unlink()


def test_update_section_array_with_comments() -> None:
    """Test updating a section array with comments."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[tool.pylint.messages_control]\nenable = []\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)

        array_with_comments = SimpleArrayWithComments(
            items=["C0103", "W0613"],
            comments={
                "C0103": "https://example.com/C0103",
                "W0613": "https://example.com/W0613",
            },
        )

        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=array_with_comments,
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[tool.test]\nkey = 'value'\n")
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.test",
            key="empty_array",
            array_data=[],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["empty_array"] == []
    finally:
        temp_path.unlink()


def test_ensure_item_in_array_existing_section() -> None:
    """Test ensuring an item exists in an array within an existing section."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.pylint.messages_control]\ndisable = ["existing-rule"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.ensure_item_in_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            item="new-rule",
        )

        result_dict = toml_file.as_dict()
        disable_list = result_dict["tool"]["pylint"]["messages_control"]["disable"]
        assert "existing-rule" in disable_list
        assert "new-rule" in disable_list
    finally:
        temp_path.unlink()


def test_ensure_item_in_array_new_section() -> None:
    """Test ensuring an item exists in an array when section doesn't exist."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.ensure_item_in_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            item="new-rule",
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "new-rule"
        ]
    finally:
        temp_path.unlink()


def test_ensure_item_in_array_already_exists() -> None:
    """Test ensuring an item exists when it's already in the array."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.pylint.messages_control]\ndisable = ["existing-rule"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.ensure_item_in_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            item="existing-rule",
        )

        result_dict = toml_file.as_dict()
        disable_list = result_dict["tool"]["pylint"]["messages_control"]["disable"]
        assert disable_list == ["existing-rule"]  # Should not duplicate
    finally:
        temp_path.unlink()


def test_write() -> None:
    """Test writing the file to disk."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.test",
            key="items",
            array_data=["item1", "item2"],
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
    array_with_comments = SimpleArrayWithComments(items=[], comments=None)
    result = array_with_comments.format_as_toml()
    assert result == "[]"


def test_simple_array_with_comments_format_simple() -> None:
    """Test SimpleArrayWithComments formatting with simple array."""
    array_with_comments = SimpleArrayWithComments(
        items=["item1", "item2"], comments=None
    )
    result = array_with_comments.format_as_toml()
    assert result == '["item1", "item2"]'


def test_simple_array_with_comments_format_with_comments() -> None:
    """Test SimpleArrayWithComments formatting with comments."""
    array_with_comments = SimpleArrayWithComments(
        items=["item1", "item2"],
        comments={"item1": "comment1", "item2": "comment2"},
    )
    result = array_with_comments.format_as_toml()
    expected = '[\n  "item1", # comment1\n  "item2" # comment2\n]'
    assert result == expected


def test_simple_array_with_comments_format_partial_comments() -> None:
    """Test SimpleArrayWithComments formatting with partial comments."""
    array_with_comments = SimpleArrayWithComments(
        items=["item1", "item2", "item3"],
        comments={"item1": "comment1", "item3": "comment3"},
    )
    result = array_with_comments.format_as_toml()
    expected = '[\n  "item1", # comment1\n  "item2",\n  "item3" # comment3\n]'
    assert result == expected


def test_apply_toml_sort() -> None:
    """Test that toml-sort is applied automatically when content changes."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Write unsorted content
        f.write('[tool.z]\nkey = "value"\n[tool.a]\nother = "value"\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.b",
            key="items",
            array_data=["item"],
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
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.new.section",
            key="items",
            array_data=["item1"],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["new"]["section"]["items"] == ["item1"]
    finally:
        temp_path.unlink()


def test_update_existing_key() -> None:
    """Test updating an existing key in an existing section."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.test]\nitems = ["old"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.test",
            key="items",
            array_data=["new1", "new2"],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["test"]["items"] == ["new1", "new2"]
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_comments_and_whitespace() -> None:
    """Test adding a key to a section that has comments and whitespace."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103", "W0613"],
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103"],
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # TOML with section at end, no trailing newline
        content = """[tool.first]
value = 1

[tool.last]
existing = true"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.last",
            key="items",
            array_data=["item1"],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["last"]["items"] == ["item1"]
        assert result_dict["tool"]["last"]["existing"] is True
    finally:
        temp_path.unlink()


def test_add_key_to_section_with_multiline_values() -> None:
    """Test adding a key to a section that has multiline values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103"],
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103"],
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)

        # This call should only affect the first section
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103"],
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
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
        toml_file = TomlFile(temp_path)

        # This should work with the new implementation
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=["C0103", "C0117", "C0200"],
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


def test_automatic_toml_sort_application(tmp_path: Path) -> None:
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

    toml_file = TomlFile(temp_file)

    # Update an array - this should trigger automatic sorting
    toml_file.update_section_array(
        "tool.pylint.messages_control", "disable", ["rule-c", "rule-a"]
    )

    result = toml_file.as_str()

    # The content should be properly formatted by toml-sort
    assert "rule-c" in result
    assert "rule-a" in result

    # Verify it's valid TOML
    parsed = toml_file.as_dict()
    assert "rule-c" in parsed["tool"]["pylint"]["messages_control"]["disable"]
    assert "rule-a" in parsed["tool"]["pylint"]["messages_control"]["disable"]
