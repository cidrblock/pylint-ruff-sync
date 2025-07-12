"""Tests for the TomlEditor class."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from pylint_ruff_sync.toml_editor import TomlEditor


class TestTomlEditor:
    """Test cases for TomlEditor."""

    def test_init(self) -> None:
        """Test TomlEditor initialization."""
        file_path = Path("test.toml")
        editor = TomlEditor(file_path)
        assert editor.file_path == file_path

    def test_read_config_existing_file(self) -> None:
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

    def test_read_config_nonexistent_file(self) -> None:
        """Test reading a nonexistent TOML file returns empty dict."""
        editor = TomlEditor(Path("nonexistent.toml"))
        config = editor.read_config()
        assert config == {}

    def test_read_config_invalid_toml(self) -> None:
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

    def test_write_config_simple(self) -> None:
        """Test writing a simple configuration."""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)
            config = {"tool": {"test": {"key": "value"}}}

            with patch.object(editor, "sort_file") as mock_sort:
                editor.write_config(config)
                mock_sort.assert_called_once()

            # Read back and verify
            result = editor.read_config()
            assert result == config
        finally:
            temp_path.unlink()

    def test_write_config_no_sort(self) -> None:
        """Test writing configuration without sorting."""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)
            config = {"key": "value"}

            with patch.object(editor, "sort_file") as mock_sort:
                editor.write_config(config, run_sort=False)
                mock_sort.assert_not_called()
        finally:
            temp_path.unlink()

    @patch("subprocess.run")
    def test_sort_file_success_uv(self, mock_run: Mock) -> None:
        """Test successful toml-sort with uv command."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        editor = TomlEditor(Path("test.toml"))
        editor.sort_file()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "uv"
        assert "toml-sort" in args
        assert "--sort-inline-tables" in args
        assert "--sort-table-keys" in args

    @patch("subprocess.run")
    def test_sort_file_fallback(self, mock_run: Mock) -> None:
        """Test toml-sort with fallback commands."""
        # First command fails, second succeeds
        mock_run.side_effect = [
            FileNotFoundError("uv not found"),
            Mock(returncode=0, stderr=""),
        ]

        editor = TomlEditor(Path("test.toml"))
        editor.sort_file()

        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_sort_file_all_fail(self, mock_run: Mock) -> None:
        """Test toml-sort when all commands fail."""
        mock_run.side_effect = FileNotFoundError("Command failed")

        editor = TomlEditor(Path("test.toml"))
        # Should not raise an exception
        editor.sort_file()

        assert mock_run.call_count == 3

    def test_ensure_section_exists_new_section(self) -> None:
        """Test creating a new section path."""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)
            config = editor.ensure_section_exists(
                ["tool", "pylint", "messages_control"]
            )

            assert "tool" in config
            assert "pylint" in config["tool"]
            assert "messages_control" in config["tool"]["pylint"]
        finally:
            temp_path.unlink()

    def test_ensure_section_exists_partial_existing(self) -> None:
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

    def test_update_section_array_simple(self) -> None:
        """Test updating array in section without preserve_format."""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)

            with patch.object(editor, "write_config") as mock_write:
                editor.update_section_array(
                    section_path=["tool", "test"],
                    key="rules",
                    values=["rule1", "rule2"],
                )
                mock_write.assert_called_once()
        finally:
            temp_path.unlink()

    def test_update_section_array_preserve_format(self) -> None:
        """Test updating array with format preservation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.test]\nrules = ["old_rule"]\n')
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)

            with patch.object(editor, "_update_array_with_regex") as mock_regex:
                editor.update_section_array(
                    section_path=["tool", "test"],
                    key="rules",
                    values=["new_rule"],
                    preserve_format=True,
                )
                mock_regex.assert_called_once()
        finally:
            temp_path.unlink()

    def test_update_section_content_with_regex_new_file(self) -> None:
        """Test regex update on nonexistent file."""
        temp_path = Path("nonexistent.toml")
        editor = TomlEditor(temp_path)

        with patch.object(editor, "sort_file") as mock_sort:
            editor.update_section_content_with_regex(
                section_pattern=r"\[tool\.test\]",
                key="enable",
                new_content="enable = []",
            )
            mock_sort.assert_called_once()

        # Clean up if file was created
        if temp_path.exists():
            temp_path.unlink()

    def test_update_section_content_with_regex_existing_section(self) -> None:
        """Test regex update on existing section."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.test]\nold_key = ["old_value"]\n')
            temp_path = Path(f.name)

        try:
            editor = TomlEditor(temp_path)

            with patch.object(editor, "sort_file") as mock_sort:
                editor.update_section_content_with_regex(
                    section_pattern=r"\[tool\.test\]",
                    key="old_key",
                    new_content="old_key = []",
                )
                mock_sort.assert_called_once()
        finally:
            temp_path.unlink()

    def test_write_dict_to_lines_simple(self) -> None:
        """Test writing simple dictionary to lines."""
        editor = TomlEditor(Path("test.toml"))
        lines: list[str] = []

        data = {"key": "value", "number": 42, "array": ["a", "b"]}
        editor._write_dict_to_lines(data, lines)

        assert 'key = "value"' in lines
        assert "number = 42" in lines
        assert "array = [" in lines
        assert '  "a",' in lines
        assert '  "b"' in lines

    def test_write_dict_to_lines_nested(self) -> None:
        """Test writing nested dictionary to lines."""
        editor = TomlEditor(Path("test.toml"))
        lines: list[str] = []

        data: dict[str, Any] = {"simple": "value", "tool": {"test": {"nested": "deep"}}}
        editor._write_dict_to_lines(data, lines)

        assert 'simple = "value"' in lines
        assert any("[tool]" in line for line in lines)
        assert any("[tool.test]" in line for line in lines)
        assert 'nested = "deep"' in lines

    def test_write_dict_to_lines_empty_array(self) -> None:
        """Test writing empty array."""
        editor = TomlEditor(Path("test.toml"))
        lines: list[str] = []

        data = {"empty": []}
        editor._write_dict_to_lines(data, lines)

        assert "empty = []" in lines

    def test_write_dict_to_lines_single_item_array(self) -> None:
        """Test writing single-item array."""
        editor = TomlEditor(Path("test.toml"))
        lines: list[str] = []

        data = {"single": ["item"]}
        editor._write_dict_to_lines(data, lines)

        assert 'single = ["item"]' in lines

    def test_get_nested_section_existing(self) -> None:
        """Test getting existing nested section."""
        editor = TomlEditor(Path("test.toml"))
        config = {"tool": {"test": {"existing": "value"}}}

        section = editor._get_nested_section(config, ["tool", "test"])
        assert section == {"existing": "value"}

    def test_get_nested_section_create_missing(self) -> None:
        """Test creating missing nested sections."""
        editor = TomlEditor(Path("test.toml"))
        config: dict[str, Any] = {}

        section = editor._get_nested_section(config, ["tool", "new", "section"])
        assert config == {"tool": {"new": {"section": {}}}}
        assert section == {}

    def test_update_array_with_regex_empty_array(self) -> None:
        """Test updating array to empty with regex."""
        editor = TomlEditor(Path("test.toml"))

        with patch.object(editor, "update_section_content_with_regex") as mock_update:
            editor._update_array_with_regex(["tool", "test"], "rules", [])
            mock_update.assert_called_once_with(
                r"\[tool\.test\]", "rules", "rules = []"
            )

    def test_update_array_with_regex_single_item(self) -> None:
        """Test updating array to single item with regex."""
        editor = TomlEditor(Path("test.toml"))

        with patch.object(editor, "update_section_content_with_regex") as mock_update:
            editor._update_array_with_regex(["tool", "test"], "rules", ["item"])
            mock_update.assert_called_once_with(
                r"\[tool\.test\]", "rules", 'rules = ["item"]'
            )

    def test_update_array_with_regex_multiple_items(self) -> None:
        """Test updating array to multiple items with regex."""
        editor = TomlEditor(Path("test.toml"))

        with patch.object(editor, "update_section_content_with_regex") as mock_update:
            editor._update_array_with_regex(["tool", "test"], "rules", ["a", "b"])
            expected_content = 'rules = [\n  "a",\n  "b"\n]'
            mock_update.assert_called_once_with(
                r"\[tool\.test\]", "rules", expected_content
            )

    def test_update_key_in_section_replace_existing(self) -> None:
        """Test replacing existing key in section."""
        editor = TomlEditor(Path("test.toml"))
        section_content = """[tool.test]
old_key = ["old_value"]
other_key = "unchanged"
"""

        result = editor._update_key_in_section(
            section_content, "old_key", "old_key = []"
        )

        assert "old_key = []" in result
        assert "other_key" in result

    def test_update_key_in_section_add_new(self) -> None:
        """Test adding new key to section."""
        editor = TomlEditor(Path("test.toml"))
        section_content = """[tool.test]
existing_key = "value"
"""

        result = editor._update_key_in_section(
            section_content, "new_key", "new_key = []"
        )

        assert "existing_key" in result
        assert "new_key = []" in result
