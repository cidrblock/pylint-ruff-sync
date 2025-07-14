"""Generic TOML file editor with support for surgical updates and formatting."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from toml_sort.tomlsort import FormattingConfiguration, SortConfiguration, TomlSort

from .toml_regex import TOML_REGEX

if TYPE_CHECKING:
    from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SimpleArrayWithComments:
    """Represents a simple TOML array with optional comments for each item.

    Attributes:
        items: List of string values for the array.
        comments: Optional dict mapping item values to their comments.

    """

    items: list[str]
    comments: dict[str, str] | None = None

    def format_as_toml(self) -> str:
        """Format the array as TOML with proper formatting.

        Returns:
            Formatted TOML array string.

        """
        if not self.items:
            return "[]"

        # Use single-line format if no comments, multi-line if comments exist
        has_comments = self.comments and any(
            self.comments.get(item, "") for item in self.items
        )

        if not has_comments:
            # Single-line format for arrays without comments
            items_str = ", ".join(f'"{item}"' for item in self.items)
            return f"[{items_str}]"

        # Multi-line format for arrays with comments
        lines = ["["]
        for i, item in enumerate(self.items):
            comment = self.comments.get(item, "") if self.comments else ""
            is_last = i == len(self.items) - 1

            if comment:
                if is_last:
                    lines.append(f'  "{item}" # {comment}')
                else:
                    lines.append(f'  "{item}", # {comment}')
            elif is_last:
                lines.append(f'  "{item}"')
            else:
                lines.append(f'  "{item}",')
        lines.append("]")
        return "\n".join(lines)


class TomlFile:
    """Represents a TOML file with in-memory editing capabilities.

    This class loads a TOML file once into memory and provides methods to modify
    the in-memory representation. All changes are applied with toml-sort formatting.
    The file is only written when explicitly requested.

    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the TomlFile with content loaded from disk.

        Args:
            file_path: Path to the TOML file to load.

        """
        self.file_path = file_path
        self._raw_content = ""
        self._content = self._load_file()

    @property
    def _content(self) -> str:
        """Get the current file content.

        Returns:
            The current file content as a string.

        """
        return self._raw_content

    @_content.setter
    def _content(self, value: str) -> None:
        """Set the file content with automatic toml-sort application.

        Args:
            value: The new content to set.

        """
        # Apply toml-sort automatically whenever content changes
        self._raw_content = self._apply_toml_sort(value)

    def _load_file(self) -> str:
        """Load the TOML file content from disk.

        Returns:
            The file content as a string.

        """
        if not self.file_path.exists():
            return ""
        return self.file_path.read_text(encoding="utf-8")

    def _apply_toml_sort(self, content: str) -> str:
        """Apply toml-sort formatting to the content.

        Args:
            content: TOML content to sort.

        Returns:
            Sorted TOML content.

        """
        if not content.strip():
            return content

        sort_config = SortConfiguration(
            inline_tables=True,
            table_keys=True,
        )
        format_config = FormattingConfiguration(
            spaces_before_inline_comment=1,
            trailing_comma_inline_array=False,
        )

        sorter = TomlSort(
            input_toml=content, sort_config=sort_config, format_config=format_config
        )
        return sorter.sorted()

    def as_dict(self) -> dict[str, Any]:
        """Return the current file content as a dictionary.

        Returns:
            Dictionary representation of the TOML file.

        Raises:
            tomllib.TOMLDecodeError: If the TOML content is invalid.

        """
        if not self._content.strip():
            return {}
        try:
            return tomllib.loads(self._content)
        except tomllib.TOMLDecodeError:
            logger.exception("Failed to parse TOML content")
            raise

    def as_str(self) -> str:
        """Return the current file content as a string.

        Returns:
            String representation of the TOML file (already sorted).

        """
        return self._content

    def update_section_array(
        self,
        section_path: str,
        key: str,
        array_data: list[str] | SimpleArrayWithComments,
    ) -> None:
        """Update an array in a specific section.

        Args:
            section_path: Dot-separated path to the section.
            key: Key within the section to update.
            array_data: Either a simple list of strings or SimpleArrayWithComments.

        """
        if isinstance(array_data, SimpleArrayWithComments):
            formatted_array = array_data.format_as_toml()
        # Simple list - format as basic TOML array and let toml-sort handle formatting
        elif not array_data:
            formatted_array = "[]"
        else:
            formatted_items = [f'"{item}"' for item in array_data]
            formatted_array = f"[{', '.join(formatted_items)}]"

        self._update_section_key_with_regex(
            section_path=section_path,
            key=key,
            new_value=formatted_array,
        )

    def ensure_item_in_array(
        self,
        section_path: str,
        key: str,
        item: str,
    ) -> None:
        """Ensure an item exists in an array, adding it if not present.

        Args:
            section_path: Dot-separated path to the section.
            key: Key within the section.
            item: Item to ensure exists in the array.

        """
        current_dict = self.as_dict()

        # Navigate to the section
        section_parts = section_path.split(".")
        current_section = current_dict
        for part in section_parts:
            if part not in current_section:
                current_section[part] = {}
            current_section = current_section[part]

        # Get current array or create empty one
        current_array = current_section.get(key, [])
        if not isinstance(current_array, list):
            current_array = []

        # Add item if not present
        if item not in current_array:
            current_array.append(item)
            self.update_section_array(section_path, key, current_array)

    def _update_section_key_with_regex(
        self,
        section_path: str,
        key: str,
        new_value: str,
    ) -> None:
        """Update a specific key in a section using regex replacement.

        This method uses the centralized TomlRegex class for all regex operations.

        Args:
            section_path: Dot-separated path to the section.
            key: Key within the section to update.
            new_value: New value for the key.

        """
        try:
            # Try to replace the key using the centralized regex
            new_content = TOML_REGEX.replace_key_in_section(
                self._content, section_path, key, new_value
            )
            self._content = new_content
        except ValueError:
            # Key not found, add it using the centralized regex
            new_content = TOML_REGEX.add_key_to_section(
                self._content, section_path, key, new_value
            )
            self._content = new_content

    def write(self) -> None:
        """Write the current in-memory content to the file with toml-sort formatting."""
        # Apply toml-sort before writing
        formatted_content = self._apply_toml_sort(self._content)
        self.file_path.write_text(formatted_content, encoding="utf-8")
