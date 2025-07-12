"""Generic TOML file editor with support for surgical updates and formatting."""

from __future__ import annotations

import logging
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)


class TomlEditor:
    """A generic TOML file editor with support for surgical updates.

    This class provides methods to read, write, and surgically update TOML files
    while preserving formatting, comments, and structure where possible.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize a TomlEditor instance.

        Args:
            file_path: Path to the TOML file to edit.

        """
        self.file_path = file_path

    def read_config(self) -> dict[str, Any]:
        """Read the TOML configuration file.

        Returns:
            The configuration dictionary, or empty dict if file not found.

        Raises:
            Exception: If parsing the file fails.

        """
        try:
            with self.file_path.open("rb") as f:
                config: dict[str, Any] = tomllib.load(f)
                return config
        except FileNotFoundError:
            logger.debug(
                "TOML file %s not found, returning empty config", self.file_path
            )
            return {}
        except Exception:
            logger.exception("Failed to read TOML file: %s", self.file_path)
            raise

    def write_config(self, config: dict[str, Any], *, run_sort: bool = True) -> None:
        """Write configuration to the TOML file.

        Args:
            config: The configuration dictionary to write.
            run_sort: Whether to run toml-sort after writing.

        Raises:
            Exception: If writing the file fails.

        """
        try:
            # For now, use a simple TOML writer
            # In the future, this could be enhanced to preserve formatting
            self._write_toml_content(config)
            logger.debug("Configuration written to %s", self.file_path)

            if run_sort:
                self.sort_file()
        except Exception:
            logger.exception("Failed to write TOML file: %s", self.file_path)
            raise

    def sort_file(self) -> None:
        """Run toml-sort on the TOML file with table key and inline table sorting."""
        commands_to_try = [
            [
                "uv",
                "run",
                "toml-sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.file_path),
            ],
            [
                "toml-sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.file_path),
            ],
            [
                "python",
                "-m",
                "toml_sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.file_path),
            ],
        ]

        for cmd in commands_to_try:
            try:
                result = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if not result.returncode:
                    logger.debug(
                        "toml-sort completed successfully with command: %s", cmd[0]
                    )
                    return
                logger.warning(
                    "toml-sort returned non-zero exit code: %d", result.returncode
                )
                if result.stderr:
                    logger.warning("toml-sort stderr: %s", result.stderr)
                continue

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.debug("Command %s failed: %s", cmd[0], e)
                continue

        # If we get here, all commands failed
        logger.warning(
            "Failed to run toml-sort with any available command, "
            "continuing without formatting"
        )

    def ensure_section_exists(self, section_path: list[str]) -> dict[str, Any]:
        """Ensure a section exists in the configuration, creating nested structure.

        Args:
            section_path: List of keys representing the path to the section
                (e.g., ["tool", "pylint"]).

        Returns:
            The configuration dictionary with the section guaranteed to exist.

        """
        config = self.read_config()
        current = config

        for key in section_path:
            if key not in current:
                current[key] = {}
            current = current[key]

        return config

    def update_section_array(
        self,
        section_path: list[str],
        key: str,
        values: list[str],
        *,
        preserve_format: bool = False,
    ) -> None:
        """Update an array value in a specific section.

        Args:
            section_path: List of keys representing the path to the section.
            key: The key within the section to update.
            values: The new array values to set.
            preserve_format: If True, use surgical regex updates to preserve formatting.

        """
        if preserve_format and self.file_path.exists():
            self._update_array_with_regex(section_path, key, values)
        else:
            # Simple update through config dictionary
            config = self.ensure_section_exists(section_path)
            section = self._get_nested_section(config, section_path)
            section[key] = values
            self.write_config(config)

    def update_section_content_with_regex(
        self,
        section_pattern: str,
        key: str,
        new_content: str,
        *,
        add_if_missing: bool = True,
    ) -> None:
        r"""Update section content using regex for surgical updates.

        Args:
            section_pattern: Regex pattern to match the section
                (e.g., r"\[tool\.pylint\.messages_control\]").
            key: The key to update within the section.
            new_content: The new content to replace the key's value.
            add_if_missing: Whether to add the section if it doesn't exist.

        """
        if not self.file_path.exists():
            if add_if_missing:
                # Create a minimal file with the section
                header = section_pattern.replace("\\", "").replace(".", ".")
                content = f"{header}\n{new_content}\n"
                with self.file_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                self.sort_file()
            return

        with self.file_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Find the section
        pattern = "(" + section_pattern + r".*?)(\n*?)(?=\n\[|\Z)"
        section_regex = re.compile(
            pattern,
            re.DOTALL | re.MULTILINE,
        )

        match = section_regex.search(content)
        if match:
            section_content = match.group(1)
            trailing_newlines = match.group(2)

            # Update the key within the section
            updated_section = self._update_key_in_section(
                section_content, key, new_content
            )
            replacement = updated_section.rstrip() + trailing_newlines
            updated_content = section_regex.sub(replacement, content)
        elif add_if_missing:
            # Add new section at the end
            if content and not content.endswith("\n"):
                content += "\n"

            # For pylint.messages_control, we need to ensure parent section exists
            section_header = section_pattern.replace("\\", "").replace(".", ".")
            if (
                "pylint.messages_control" in section_header
                and "[tool.pylint]" not in content
            ):
                # Add parent [tool.pylint] section if it doesn't exist
                content += "\n[tool.pylint]\n"

            updated_content = content + f"\n{section_header}\n{new_content}\n"
        else:
            updated_content = content

        with self.file_path.open("w", encoding="utf-8") as f:
            f.write(updated_content)

        self.sort_file()

    def _write_toml_content(self, config: dict[str, Any]) -> None:
        """Write configuration as TOML content to file.

        Args:
            config: The configuration dictionary to write.

        """
        lines: list[str] = []
        self._write_dict_to_lines(config, lines)

        with self.file_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_dict_to_lines(
        self, data: dict[str, Any], lines: list[str], prefix: str = ""
    ) -> None:
        """Recursively write dictionary data as TOML lines.

        Args:
            data: Dictionary data to write.
            lines: List to append TOML lines to.
            prefix: Current section prefix for nested tables.

        """
        # Write simple key-value pairs first
        for key, value in data.items():
            if not isinstance(value, dict):
                if isinstance(value, list):
                    if len(value) == 0:
                        lines.append(f"{key} = []")
                    elif len(value) == 1:
                        lines.append(f'{key} = ["{value[0]}"]')
                    else:
                        lines.append(f"{key} = [")
                        for i, item in enumerate(value):
                            comma = "," if i < len(value) - 1 else ""
                            lines.append(f'  "{item}"{comma}')
                        lines.append("]")
                elif isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                else:
                    lines.append(f"{key} = {value}")

        # Write nested sections
        for key, value in data.items():
            if isinstance(value, dict):
                section_name = f"{prefix}.{key}" if prefix else key
                lines.append(f"\n[{section_name}]")
                self._write_dict_to_lines(value, lines, section_name)

    def _get_nested_section(
        self, config: dict[str, Any], section_path: list[str]
    ) -> dict[str, Any]:
        """Get a nested section from config, creating if necessary.

        Args:
            config: The configuration dictionary.
            section_path: Path to the section.

        Returns:
            The nested section dictionary.

        """
        current = config
        for key in section_path:
            if key not in current:
                current[key] = {}
            current = current[key]
        return current

    def _update_array_with_regex(
        self, section_path: list[str], key: str, values: list[str]
    ) -> None:
        """Update array using regex for surgical updates.

        Args:
            section_path: Path to the section containing the array.
            key: The key of the array to update.
            values: New values for the array.

        """
        if not self.file_path.exists():
            return

        # Generate the section pattern
        section_pattern = r"\[" + r"\.".join(section_path) + r"\]"

        # Generate new array content
        if len(values) == 0:
            new_content = f"{key} = []"
        elif len(values) == 1:
            new_content = f'{key} = ["{values[0]}"]'
        else:
            lines = [f"{key} = ["]
            for i, value in enumerate(values):
                comma = "," if i < len(values) - 1 else ""
                lines.append(f'  "{value}"{comma}')
            lines.append("]")
            new_content = "\n".join(lines)

        self.update_section_content_with_regex(section_pattern, key, new_content)

    def _update_key_in_section(
        self, section_content: str, key: str, new_content: str
    ) -> str:
        """Update a specific key within a section.

        Args:
            section_content: The section content to update.
            key: The key to update.
            new_content: The new content for the key.

        Returns:
            Updated section content.

        """
        # Pattern to match the key and its value (including multiline arrays)
        escaped_key = re.escape(key)
        pattern = escaped_key + r"\s*=\s*\[(?:[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]"
        key_pattern = re.compile(
            pattern,
            re.DOTALL | re.MULTILINE,
        )

        if key_pattern.search(section_content):
            # Replace existing key
            return key_pattern.sub(new_content, section_content)
        # Add new key at the end of the section
        lines = section_content.split("\n")
        if lines and not lines[-1].strip():
            lines.insert(-1, new_content)
        else:
            lines.append(new_content)
        return "\n".join(lines)
