"""Tests for the TomlFile class."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pylint_ruff_sync.toml_editor import SimpleArrayWithComments, TomlFile


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
    assert toml_file.as_str() == ""
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
    """Test that toml-sort is applied to content."""
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

        # The content should be sorted
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
line-length = 88
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
        assert result_dict["tool"]["pylint"]["main"]["jobs"] == 0
        assert result_dict["tool"]["ruff"]["line-length"] == 88
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
        assert result_dict["tool"]["pylint"]["main"]["jobs"] == 0
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
    """Test adding a key to a section when there's duplicate content that could confuse string replacement."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # TOML with duplicate content that could cause issues with string replacement
        content = """[tool.pylint.messages_control]
disable = ["all"]

[tool.ruff]
# This comment contains the same text as above: disable = ["all"]
line-length = 88

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
        assert result_dict["tool"]["ruff"]["line-length"] == 88

        # Check that the content appears only once in the right place
        result_str = toml_file.as_str()
        # Count occurrences of the section header
        section_count = result_str.count("[tool.pylint.messages_control]")
        assert section_count == 1, (
            f"Expected 1 occurrence of section header, got {section_count}"
        )

        # Check that enable was added to the correct section
        pylint_section_start = result_str.find("[tool.pylint.messages_control]")
        next_section_start = result_str.find("[tool.ruff]", pylint_section_start)

        pylint_section_content = result_str[pylint_section_start:next_section_start]
        assert "enable" in pylint_section_content
        assert "C0103" in pylint_section_content

    finally:
        temp_path.unlink()


def test_add_key_to_section_string_replacement_issue() -> None:
    """Test that demonstrates the potential string replacement issue in _add_key_to_section."""
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
        toml_file._add_key_to_section(
            section_path="tool.pylint.messages_control",
            key="enable",
            value='["C0103"]',
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


def test_update_multiline_array_with_comments_existing_key() -> None:
    """Test updating a multiline array with comments when the key already exists - this reproduces the KeyAlreadyPresent error."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # This is the exact structure from the actual pyproject.toml that causes the issue
        content = """[tool.pylint.messages_control]
disable = ["all", "locally-disabled", "suppressed-message"]
enable = [
  "C0104", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0104.html
  "C0117", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0117.html
  "C0200", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0200.html
]
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)

        # This should update the existing disable key, not try to add a new one
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=["all", "new-rule"],
        )

        result_dict = toml_file.as_dict()

        # Check that the disable key was updated correctly
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "all",
            "new-rule",
        ]

        # Check that the enable key was not affected
        assert result_dict["tool"]["pylint"]["messages_control"]["enable"] == [
            "C0104",
            "C0117",
            "C0200",
        ]

    finally:
        temp_path.unlink()


def test_regex_pattern_matching_issue() -> None:
    """Test that demonstrates the regex pattern matching issue in _update_section_key_with_regex."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Content that might cause the regex to fail
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

        # Test the internal regex matching directly
        import re

        section_pattern = toml_file._build_section_pattern(
            "tool.pylint.messages_control"
        )

        # This should match the disable key pattern
        key_pattern = (
            rf"({section_pattern}.*?^\s*disable\s*=\s*)"
            rf".*?(?=\n\s*\w+\s*=|\n\s*\[|\Z)"
        )

        match = re.search(
            key_pattern,
            toml_file._content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # The regex should find the disable key
        assert match is not None, "Regex should match the disable key but didn't"

        # Test the replacement
        new_content = re.sub(
            key_pattern,
            r"\g<1>['all', 'new-rule']",
            toml_file._content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # The replacement should work
        assert new_content != toml_file._content, (
            "Regex replacement should have changed the content"
        )
        assert "'new-rule'" in new_content

    finally:
        temp_path.unlink()


def test_key_already_present_error_reproduction() -> None:
    """Test that reproduces the exact KeyAlreadyPresent error from the pyproject.toml file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # This is the exact structure from pyproject.toml that causes the issue
        content = """[tool.pylint.messages_control]
disable = ["all", "locally-disabled", "suppressed-message"]
enable = [
  "C0104", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0104.html
  "C0117", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0117.html
  "C0200", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0200.html
  "C0203", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0203.html
  "C0204", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0204.html
  "C0209", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0209.html
  "C0302", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0302.html
  "C0325", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0325.html
  "C0327", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0327.html
  "C0328", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0328.html
  "C0401", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0401.html
  "C0402", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0402.html
  "C0403", # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/0403.html
]

[tool.other]
value = "test"
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)

        # This should reproduce the KeyAlreadyPresent error
        # The issue is that the disable key is on a single line, but the enable key is multiline
        # The regex might not handle this correctly
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=["all", "new-rule"],
        )

        result_dict = toml_file.as_dict()

        # Check that the disable key was updated correctly
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "all",
            "new-rule",
        ]

    finally:
        temp_path.unlink()


def test_regex_issue_with_single_line_vs_multiline() -> None:
    """Test the regex issue where single-line key is followed by multiline key."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Test case where the key being updated is single line but followed by multiline
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

        # Test the regex pattern directly
        import re

        section_pattern = toml_file._build_section_pattern(
            "tool.pylint.messages_control"
        )

        # This is the exact pattern from _update_section_key_with_regex
        key_pattern = (
            rf"({section_pattern}.*?^\s*disable\s*=\s*)"
            rf".*?(?=\n\s*\w+\s*=|\n\s*\[|\Z)"
        )

        print(f"Content:\n{toml_file._content}")
        print(f"Section pattern: {section_pattern}")
        print(f"Key pattern: {key_pattern}")

        match = re.search(
            key_pattern,
            toml_file._content,
            flags=re.MULTILINE | re.DOTALL,
        )

        if match:
            print(f"Match found: {match.group(0)}")
            print(f"Group 1: {match.group(1)}")
        else:
            print("No match found")

        # The issue might be that the pattern doesn't match correctly
        # Let's check what happens when we try to replace
        new_content = re.sub(
            key_pattern,
            r"\g<1>['all', 'new-rule']",
            toml_file._content,
            flags=re.MULTILINE | re.DOTALL,
        )

        print(f"New content:\n{new_content}")
        print(f"Content changed: {new_content != toml_file._content}")

    finally:
        temp_path.unlink()


def test_string_replacement_creates_duplicate_keys() -> None:
    """Test that demonstrates how string replacement in _add_key_to_section can create duplicate keys."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Create content where the section content appears multiple times
        content = """[tool.pylint.messages_control]
disable = ["all"]

[tool.other]
# This comment contains: disable = ["all"]
value = "test"

[tool.another]
disable = ["all"]
value = "test"
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)

        # Force the _add_key_to_section path by calling it directly
        # This should trigger the string replacement issue
        toml_file._add_key_to_section(
            section_path="tool.pylint.messages_control",
            key="disable",
            value='["all", "new-rule"]',
        )

        # This should fail with KeyAlreadyPresent when toml-sort is applied
        # because the string replacement might create duplicate keys
        result_dict = toml_file.as_dict()

        # Check that only one disable key exists in the target section
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "all",
            "new-rule",
        ]
        assert result_dict["tool"]["another"]["disable"] == ["all"]

    finally:
        temp_path.unlink()


def test_exact_string_replacement_issue() -> None:
    """Test the exact issue: when section content appears multiple times, string replacement fails."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Create content where section boundary detection could fail
        content = """[tool.pylint.messages_control]
disable = ["all"]

# Some comment with disable = ["all"] in it
[tool.other]
disable = ["all"]
"""
        f.write(content)
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)

        # Test the regex pattern from _add_key_to_section
        import re

        section_pattern = toml_file._build_section_pattern(
            "tool.pylint.messages_control"
        )

        # The current pattern in _add_key_to_section
        pattern = rf"({section_pattern}.*?)(?=^\[|\Z)"

        match = re.search(
            pattern,
            toml_file._content,
            flags=re.MULTILINE | re.DOTALL,
        )

        if match:
            section_content = match.group(1)
            print(f"Section content: {section_content!r}")

            # Check if this content appears multiple times
            count = toml_file._content.count(section_content)
            print(f"Section content appears {count} times")

            # This could cause issues if count > 1
            new_section_content = (
                f"{section_content.rstrip()}\ndisable = ['all', 'new-rule']\n"
            )

            # This replace could replace wrong occurrences
            new_content = toml_file._content.replace(
                section_content, new_section_content
            )
            print(f"New content after replacement:\n{new_content}")

            # Check if this created duplicate keys
            # By manually counting disable keys
            disable_count = new_content.count("disable = ")
            print(f"Number of 'disable = ' occurrences: {disable_count}")

            if disable_count > 2:  # We expect exactly 2 (one in each section)
                print("ERROR: String replacement created duplicate keys!")

    finally:
        temp_path.unlink()
