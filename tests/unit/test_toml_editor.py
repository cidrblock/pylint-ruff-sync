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
        f.write('[tool.pylint.messages_control]\ndisable = ["old-rule"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=["new-rule", "another-rule"],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == [
            "new-rule",
            "another-rule",
        ]
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
        f.write('[tool.pylint.messages_control]\ndisable = ["old-rule"]\n')
        temp_path = Path(f.name)

    try:
        toml_file = TomlFile(temp_path)
        toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=[],
        )

        result_dict = toml_file.as_dict()
        assert result_dict["tool"]["pylint"]["messages_control"]["disable"] == []
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
    """Test formatting empty SimpleArrayWithComments."""
    array = SimpleArrayWithComments(items=[])
    result = array.format_as_toml()
    assert result == "[]"


def test_simple_array_with_comments_format_simple() -> None:
    """Test formatting SimpleArrayWithComments without comments."""
    array = SimpleArrayWithComments(items=["item1", "item2"])
    result = array.format_as_toml()
    assert result == '["item1", "item2"]'


def test_simple_array_with_comments_format_with_comments() -> None:
    """Test formatting SimpleArrayWithComments with comments."""
    array = SimpleArrayWithComments(
        items=["item1", "item2"],
        comments={"item1": "comment1", "item2": "comment2"},
    )
    result = array.format_as_toml()

    # Should be multiline format with comments
    assert "# comment1" in result
    assert "# comment2" in result
    assert '"item1"' in result
    assert '"item2"' in result


def test_simple_array_with_comments_format_partial_comments() -> None:
    """Test formatting SimpleArrayWithComments with partial comments."""
    array = SimpleArrayWithComments(
        items=["item1", "item2", "item3"],
        comments={"item1": "comment1", "item3": "comment3"},
    )
    result = array.format_as_toml()

    # Should include comments for items that have them
    assert "# comment1" in result
    assert "# comment3" in result
    assert '"item1"' in result
    assert '"item2"' in result
    assert '"item3"' in result


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
