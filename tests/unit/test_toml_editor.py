"""Tests for the TomlEditor class."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from pylint_ruff_sync.toml_editor import SimpleArrayWithComments, TomlEditor

# Test constants
EXPECTED_FALLBACK_CALLS = 2
EXPECTED_ALL_FAIL_CALLS = 3


def test_init() -> None:
    """Test TomlEditor initialization."""
    file_path = Path("test.toml")
    editor = TomlEditor(file_path)
    assert editor.file_path == file_path


def test_read_config_existing_file() -> None:
    """Test reading an existing TOML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.test]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        config = editor.read_config()
        assert config == {"tool": {"test": {"key": "value"}}}
    finally:
        temp_path.unlink()


def test_read_config_nonexistent_file() -> None:
    """Test reading a nonexistent TOML file returns empty dict."""
    editor = TomlEditor(Path("nonexistent.toml"))
    config = editor.read_config()
    assert config == {}


def test_read_config_invalid_toml() -> None:
    """Test reading invalid TOML raises exception."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid toml [")
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        with pytest.raises((ValueError, TypeError, OSError)):
            editor.read_config()
    finally:
        temp_path.unlink()


def test_write_config_simple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test writing a simple configuration."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        config = {"tool": {"test": {"key": "value"}}}

        mock_sort_called = []

        def mock_sort_file(_: TomlEditor) -> None:
            mock_sort_called.append(True)

        monkeypatch.setattr(TomlEditor, "sort_file", mock_sort_file)

        editor.write_config(config)
        assert len(mock_sort_called) == 1

        # Read back and verify
        result = editor.read_config()
        assert result == config
    finally:
        temp_path.unlink()


def test_write_config_no_sort(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test writing configuration without sorting."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        config = {"key": "value"}

        mock_sort_called = []

        def mock_sort_file(_: TomlEditor) -> None:
            mock_sort_called.append(True)

        monkeypatch.setattr(TomlEditor, "sort_file", mock_sort_file)

        editor.write_config(config, run_sort=False)
        assert len(mock_sort_called) == 0
    finally:
        temp_path.unlink()


def test_sort_file_success_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful toml-sort with uv command."""

    class MockResult:
        def __init__(self, returncode: int, stderr: str) -> None:
            self.returncode = returncode
            self.stderr = stderr

    mock_calls = []

    def mock_run(cmd: list[str], **_kwargs: object) -> MockResult:
        mock_calls.append(cmd)
        return MockResult(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    editor = TomlEditor(Path("test.toml"))
    editor.sort_file()

    assert len(mock_calls) == 1
    args = mock_calls[0]
    assert args[0] == "uv"
    assert "toml-sort" in args
    assert "--sort-inline-tables" in args
    assert "--sort-table-keys" in args


def test_sort_file_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test toml-sort with fallback commands."""

    class MockResult:
        def __init__(self, returncode: int, stderr: str) -> None:
            self.returncode = returncode
            self.stderr = stderr

    mock_calls = []

    def mock_run(cmd: list[str], **_kwargs: object) -> MockResult:
        mock_calls.append(cmd)
        if len(mock_calls) == 1:
            uv_not_found_msg = "uv not found"
            raise FileNotFoundError(uv_not_found_msg)
        return MockResult(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    editor = TomlEditor(Path("test.toml"))
    editor.sort_file()

    assert len(mock_calls) == EXPECTED_FALLBACK_CALLS


def test_sort_file_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test toml-sort when all commands fail."""
    mock_calls = []

    def mock_run(cmd: list[str], **_kwargs: object) -> None:
        mock_calls.append(cmd)
        command_failed_msg = "Command failed"
        raise FileNotFoundError(command_failed_msg)

    monkeypatch.setattr(subprocess, "run", mock_run)

    editor = TomlEditor(Path("test.toml"))
    # Should not raise an exception
    editor.sort_file()

    assert len(mock_calls) == EXPECTED_ALL_FAIL_CALLS


def test_ensure_section_exists_new_section() -> None:
    """Test creating a new section path."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        config = editor.ensure_section_exists(["tool", "pylint", "messages_control"])

        assert "tool" in config
        assert "pylint" in config["tool"]
        assert "messages_control" in config["tool"]["pylint"]
    finally:
        temp_path.unlink()


def test_ensure_section_exists_partial_existing() -> None:
    """Test creating section path when part already exists."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[tool.existing]\nkey = "value"\n')
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)
        config = editor.ensure_section_exists(["tool", "new", "subsection"])

        assert "tool" in config
        assert "existing" in config["tool"]
        assert "new" in config["tool"]
        assert "subsection" in config["tool"]["new"]
    finally:
        temp_path.unlink()


def test_update_section_array_simple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test updating array in section without preserve_format."""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        editor = TomlEditor(temp_path)

        mock_write_called = []

        def mock_write_config(
            _: TomlEditor, config: dict[str, Any], **_kwargs: object
        ) -> None:
            mock_write_called.append(config)

        monkeypatch.setattr(TomlEditor, "write_config", mock_write_config)

        editor.update_section_array(
            section_path=["tool", "test"],
            key="rules",
            array_data=["rule1", "rule2"],
        )

        assert len(mock_write_called) == 1
        config = mock_write_called[0]
        assert config["tool"]["test"]["rules"] == ["rule1", "rule2"]
    finally:
        temp_path.unlink()


def test_update_section_array_preserve_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test updating section array with preserve_format=True."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_update_array_with_surgical_replacement(
        _: TomlEditor,
        section_path: list[str],
        key: str,
        array_data: list[str] | SimpleArrayWithComments,
    ) -> None:
        mock_calls.append((section_path, key, array_data))

    monkeypatch.setattr(
        TomlEditor,
        "_update_array_with_surgical_replacement",
        mock_update_array_with_surgical_replacement,
    )

    # Mock file exists to trigger surgical replacement
    monkeypatch.setattr(Path, "exists", lambda _: True)

    editor.update_section_array(
        section_path=["tool", "pylint"],
        key="enable",
        array_data=["C0103", "C0111"],
        preserve_format=True,
    )

    assert len(mock_calls) == 1
    call_args = mock_calls[0]
    assert call_args[0] == ["tool", "pylint"]
    assert call_args[1] == "enable"
    assert call_args[2] == ["C0103", "C0111"]


def test_update_section_array_simple_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test updating section array with simple replacement through config."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_write_config(
        _: TomlEditor, config: dict[str, Any], **_kwargs: object
    ) -> None:
        mock_calls.append(config)

    monkeypatch.setattr(TomlEditor, "write_config", mock_write_config)

    # Mock file doesn't exist to trigger simple replacement
    monkeypatch.setattr(Path, "exists", lambda _: False)

    editor.update_section_array(
        section_path=["tool", "pylint"],
        key="enable",
        array_data=["C0103", "C0111"],
        preserve_format=True,
    )

    assert len(mock_calls) == 1
    config = mock_calls[0]
    assert config["tool"]["pylint"]["enable"] == ["C0103", "C0111"]


def test_simple_array_with_comments_format_empty() -> None:
    """Test SimpleArrayWithComments formatting with empty array."""
    array_data = SimpleArrayWithComments(items=[])
    result = array_data.format_as_toml("enable")
    assert result == "enable = []"


def test_simple_array_with_comments_format_single_no_comment() -> None:
    """Test SimpleArrayWithComments formatting with single item and no comment."""
    array_data = SimpleArrayWithComments(items=["C0103"])
    result = array_data.format_as_toml("enable")
    assert result == 'enable = ["C0103"]'


def test_simple_array_with_comments_format_single_with_comment() -> None:
    """Test SimpleArrayWithComments formatting with single item and comment."""
    array_data = SimpleArrayWithComments(
        items=["C0103"], comments={"C0103": "https://example.com/C0103"}
    )
    result = array_data.format_as_toml("enable")
    expected = """enable = [
  "C0103" # https://example.com/C0103
]"""
    assert result == expected


def test_simple_array_with_comments_format_multiple_with_comments() -> None:
    """Test SimpleArrayWithComments formatting with multiple items and comments."""
    array_data = SimpleArrayWithComments(
        items=["C0103", "C0111", "R0903"],
        comments={
            "C0103": "https://example.com/C0103",
            "R0903": "https://example.com/R0903",
        },
    )
    result = array_data.format_as_toml("enable")
    expected = """enable = [
  "C0103", # https://example.com/C0103
  "C0111",
  "R0903" # https://example.com/R0903
]"""
    assert result == expected


def test_write_dict_to_lines_simple() -> None:
    """Test writing simple dictionary to lines."""
    editor = TomlEditor(Path("test.toml"))
    lines: list[str] = []

    data: dict[str, Any] = {"key": "value", "number": 42, "array": ["a", "b"]}
    editor._write_dict_to_lines(data, lines)

    assert 'key = "value"' in lines
    assert "number = 42" in lines
    assert "array = [" in lines
    assert '  "a",' in lines
    assert '  "b"' in lines


def test_write_dict_to_lines_nested() -> None:
    """Test writing nested dictionary to lines."""
    editor = TomlEditor(Path("test.toml"))
    lines: list[str] = []

    data: dict[str, Any] = {"simple": "value", "tool": {"test": {"nested": "deep"}}}
    editor._write_dict_to_lines(data, lines)

    assert 'simple = "value"' in lines
    assert any("[tool]" in line for line in lines)
    assert any("[tool.test]" in line for line in lines)
    assert 'nested = "deep"' in lines


def test_write_dict_to_lines_empty_array() -> None:
    """Test writing empty array."""
    editor = TomlEditor(Path("test.toml"))
    lines: list[str] = []

    data: dict[str, Any] = {"empty": []}
    editor._write_dict_to_lines(data, lines)

    assert "empty = []" in lines


def test_write_dict_to_lines_single_item_array() -> None:
    """Test writing single-item array."""
    editor = TomlEditor(Path("test.toml"))
    lines: list[str] = []

    data: dict[str, Any] = {"single": ["item"]}
    editor._write_dict_to_lines(data, lines)

    assert 'single = ["item"]' in lines


def test_get_nested_section_existing() -> None:
    """Test getting existing nested section."""
    editor = TomlEditor(Path("test.toml"))
    config = {"tool": {"test": {"existing": "value"}}}

    section = editor._get_nested_section(config, ["tool", "test"])
    assert section == {"existing": "value"}


def test_get_nested_section_create_missing() -> None:
    """Test creating missing nested sections."""
    editor = TomlEditor(Path("test.toml"))
    config: dict[str, Any] = {}

    section = editor._get_nested_section(config, ["tool", "new", "section"])
    assert config == {"tool": {"new": {"section": {}}}}
    assert section == {}


def test_update_key_in_section_replace_existing() -> None:
    """Test replacing existing key in section."""
    editor = TomlEditor(Path("test.toml"))
    section_content = """[tool.test]
old_key = ["old_value"]
other_key = "unchanged"
"""

    result = editor._update_key_in_section(section_content, "old_key", "old_key = []")

    assert "old_key = []" in result
    assert "other_key" in result


def test_update_key_in_section_add_new() -> None:
    """Test adding new key to section."""
    editor = TomlEditor(Path("test.toml"))
    section_content = """[tool.test]
existing_key = "value"
"""

    result = editor._update_key_in_section(section_content, "new_key", "new_key = []")

    assert "existing_key" in result
    assert "new_key = []" in result


def test_update_array_with_surgical_replacement_empty_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test surgical replacement with empty array."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_update_section_key_with_regex(
        _: TomlEditor,
        section_pattern: str,
        key: str,
        new_content: str,
        *,
        _add_if_missing: bool = True,
    ) -> None:
        mock_calls.append((section_pattern, key, new_content))

    monkeypatch.setattr(
        TomlEditor,
        "_update_section_key_with_regex",
        mock_update_section_key_with_regex,
    )

    # Mock file exists
    monkeypatch.setattr(Path, "exists", lambda _: True)

    editor._update_array_with_surgical_replacement(
        section_path=["tool", "pylint", "messages_control"],
        key="enable",
        array_data=[],
    )

    assert len(mock_calls) == 1
    call_args = mock_calls[0]
    assert call_args[0] == r"\[tool\.pylint\.messages_control\]"
    assert call_args[1] == "enable"
    assert call_args[2] == "enable = []"


def test_update_array_with_surgical_replacement_single_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test surgical replacement with single item."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_update_section_key_with_regex(
        _: TomlEditor,
        section_pattern: str,
        key: str,
        new_content: str,
        *,
        _add_if_missing: bool = True,
    ) -> None:
        mock_calls.append((section_pattern, key, new_content))

    monkeypatch.setattr(
        TomlEditor,
        "_update_section_key_with_regex",
        mock_update_section_key_with_regex,
    )

    # Mock file exists
    monkeypatch.setattr(Path, "exists", lambda _: True)

    editor._update_array_with_surgical_replacement(
        section_path=["tool", "pylint", "messages_control"],
        key="enable",
        array_data=["C0103"],
    )

    assert len(mock_calls) == 1
    call_args = mock_calls[0]
    assert call_args[0] == r"\[tool\.pylint\.messages_control\]"
    assert call_args[1] == "enable"
    assert call_args[2] == 'enable = ["C0103"]'


def test_update_array_with_surgical_replacement_multiple_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test surgical replacement with multiple items."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_update_section_key_with_regex(
        _: TomlEditor,
        section_pattern: str,
        key: str,
        new_content: str,
        *,
        _add_if_missing: bool = True,
    ) -> None:
        mock_calls.append((section_pattern, key, new_content))

    monkeypatch.setattr(
        TomlEditor,
        "_update_section_key_with_regex",
        mock_update_section_key_with_regex,
    )

    # Mock file exists
    monkeypatch.setattr(Path, "exists", lambda _: True)

    editor._update_array_with_surgical_replacement(
        section_path=["tool", "pylint", "messages_control"],
        key="enable",
        array_data=["C0103", "C0111"],
    )

    assert len(mock_calls) == 1
    call_args = mock_calls[0]
    assert call_args[0] == r"\[tool\.pylint\.messages_control\]"
    assert call_args[1] == "enable"
    expected_content = """enable = [
  "C0103",
  "C0111"
]"""
    assert call_args[2] == expected_content


def test_update_array_with_surgical_replacement_with_comments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test surgical replacement with SimpleArrayWithComments."""
    temp_path = Path("test.toml")
    editor = TomlEditor(temp_path)

    mock_calls = []

    def mock_update_section_key_with_regex(
        _: TomlEditor,
        section_pattern: str,
        key: str,
        new_content: str,
        *,
        _add_if_missing: bool = True,
    ) -> None:
        mock_calls.append((section_pattern, key, new_content))

    monkeypatch.setattr(
        TomlEditor,
        "_update_section_key_with_regex",
        mock_update_section_key_with_regex,
    )

    # Mock file exists
    monkeypatch.setattr(Path, "exists", lambda _: True)

    # Create SimpleArrayWithComments with comments
    array_with_comments = SimpleArrayWithComments(
        items=["C0103", "C0111"],
        comments={
            "C0103": "https://example.com/C0103",
            "C0111": "https://example.com/C0111",
        },
    )

    editor._update_array_with_surgical_replacement(
        section_path=["tool", "pylint", "messages_control"],
        key="enable",
        array_data=array_with_comments,
    )

    assert len(mock_calls) == 1
    call_args = mock_calls[0]
    assert call_args[0] == r"\[tool\.pylint\.messages_control\]"
    assert call_args[1] == "enable"
    expected_content = """enable = [
  "C0103", # https://example.com/C0103
  "C0111" # https://example.com/C0111
]"""
    assert call_args[2] == expected_content
