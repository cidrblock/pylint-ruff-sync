"""Regular expression patterns and utilities for TOML file manipulation.

This module provides a centralized location for all regex patterns used in TOML
file editing operations, with comprehensive documentation and examples.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match, Pattern


@dataclass
class RegexMatch:
    """Result of a regex match operation.

    Attributes:
        match: The regex match object, or None if no match.
        matched: Whether a match was found.
        groups: Captured groups from the match.

    """

    match: Match[str] | None
    matched: bool
    groups: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Initialize groups from match object."""
        if self.match:
            self.groups = self.match.groups()


class TomlRegex:
    """Regular expression patterns for TOML file manipulation.

    This class provides pre-compiled regex patterns for common TOML editing
    operations like finding sections, keys, and values. All patterns are
    thoroughly documented with examples.
    """

    def __init__(self) -> None:
        """Initialize the TomlRegex with compiled patterns."""
        # Compile all patterns for better performance
        self._section_header_pattern = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)

        self._key_value_pattern = re.compile(
            r"^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*(.+?)$", re.MULTILINE
        )

        self._multiline_array_pattern = re.compile(
            r"^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*\[\s*\n(.*?)\n\s*\]",
            re.MULTILINE | re.DOTALL,
        )

    def build_section_pattern(self, section_path: str) -> Pattern[str]:
        """Build a regex pattern to match a specific TOML section header.

        This pattern matches section headers like [tool.pylint.messages_control].
        The section path is escaped to handle special regex characters in section names.

        Args:
            section_path: Dot-separated path to the section
                (e.g., "tool.pylint.messages_control").

        Returns:
            Compiled regex pattern that matches the section header.

        Examples:
            >>> regex = TomlRegex()
            >>> pattern = regex.build_section_pattern("tool.pylint.messages_control")
            >>> bool(pattern.search("[tool.pylint.messages_control]"))
            True
            >>> bool(pattern.search("[other.section]"))
            False

        """
        escaped_path = re.escape(section_path)
        pattern = rf"^\[{escaped_path}\]"
        return re.compile(pattern, re.MULTILINE)

    def build_key_in_section_pattern(self, section_path: str, key: str) -> Pattern[str]:
        """Build a regex pattern to find a key within a specific section.

        This pattern matches a key-value pair within a specific TOML section.
        It captures:
        1. The section header and everything up to the key
        2. The key name and equals sign
        3. Handles both single-line and multiline values

        Args:
            section_path: Dot-separated path to the section.
            key: The key name to find.

        Returns:
            Compiled regex pattern with capture groups.

        Pattern Explanation:
            - Group 1: Section header + content up to "key = "
            - Matches everything after "= " until next key, section, or end of file
            - Uses non-greedy matching to avoid over-capturing

        Examples:
            >>> regex = TomlRegex()
            >>> pattern = regex.build_key_in_section_pattern("tool.pylint", "disable")
            >>> text = '''[tool.pylint]
            ... disable = ["rule1", "rule2"]
            ... enable = ["rule3"]'''
            >>> match = pattern.search(text)
            >>> bool(match)
            True

        """
        section_pattern = self.build_section_pattern(section_path)
        escaped_key = re.escape(key)

        # Pattern explanation:
        # - ({section_pattern.pattern}.*?^\s*{escaped_key}\s*=\s*) captures:
        #   * The section header: [tool.pylint.messages_control]
        #   * Any content between section and key (other keys, comments, whitespace)
        #   * The key name and equals sign: "disable = "
        # - .*? matches the value (non-greedy to stop at next boundary)
        # - (?=^\s*\w+\s*=|^\s*\[|\Z) positive lookahead for boundaries:
        #   * ^\s*\w+\s*= : next key-value pair
        #   * ^\s*\[ : next section header
        #   * \Z : end of string
        pattern = (
            rf"({section_pattern.pattern}.*?^\s*{escaped_key}\s*=\s*)"
            rf".*?(?=^\s*\w+\s*=|^\s*\[|\Z)"
        )
        return re.compile(pattern, re.MULTILINE | re.DOTALL)

    def build_key_exists_in_section_pattern(self, key: str) -> Pattern[str]:
        """Build a regex pattern to check if a key exists.

        This is a simpler pattern than build_key_in_section_pattern that only
        checks for the existence of a key, not for replacement. It should be used
        within a specific section's content.

        Args:
            key: The key name to check for.

        Returns:
            Compiled regex pattern for existence checking.

        Examples:
            >>> regex = TomlRegex()
            >>> pattern = regex.build_key_exists_in_section_pattern("disable")
            >>> text = '''disable = ["rule1"]'''
            >>> bool(pattern.search(text))
            True

        """
        escaped_key = re.escape(key)
        pattern = rf"^\s*{escaped_key}\s*="
        return re.compile(pattern, re.MULTILINE)

    def build_section_content_pattern(self, section_path: str) -> Pattern[str]:
        """Build a regex pattern to capture entire section content.

        This pattern captures everything from the section header until the next
        section or end of file. Useful for operations that need to work within
        a specific section's boundaries.

        Args:
            section_path: Dot-separated path to the section.

        Returns:
            Compiled regex pattern that captures section content.

        Pattern Explanation:
            - Matches section header
            - Captures everything until next section header or end of file
            - Uses non-greedy matching to stop at section boundaries

        Examples:
            >>> regex = TomlRegex()
            >>> pattern = regex.build_section_content_pattern("tool.pylint")
            >>> text = '''[tool.pylint]
            ... disable = ["rule1"]
            ... enable = ["rule2"]
            ...
            ... [other.section]
            ... value = "test"'''
            >>> match = pattern.search(text)
            >>> bool(match)
            True

        """
        section_pattern = self.build_section_pattern(section_path)

        # Pattern explanation:
        # - ({section_pattern.pattern}.*?) captures:
        #   * The section header: [tool.pylint]
        #   * All content in the section
        # - (?=^\[|\Z) positive lookahead for boundaries:
        #   * ^\[ : next section header
        #   * \Z : end of string
        pattern = rf"({section_pattern.pattern}.*?)(?=^\[|\Z)"
        return re.compile(pattern, re.MULTILINE | re.DOTALL)

    def find_section_header(self, content: str, section_path: str) -> RegexMatch:
        """Find a section header in TOML content.

        Args:
            content: TOML content to search.
            section_path: Section path to find.

        Returns:
            RegexMatch with the result.

        """
        pattern = self.build_section_pattern(section_path)
        match = pattern.search(content)
        return RegexMatch(match=match, matched=bool(match))

    def find_key_in_section(
        self, content: str, section_path: str, key: str
    ) -> RegexMatch:
        """Find a key within a specific section.

        Args:
            content: TOML content to search.
            section_path: Section path containing the key.
            key: Key name to find.

        Returns:
            RegexMatch with the result and capture groups.

        """
        pattern = self.build_key_in_section_pattern(section_path, key)
        match = pattern.search(content)
        return RegexMatch(match=match, matched=bool(match))

    def key_exists_in_section(self, content: str, section_path: str, key: str) -> bool:
        """Check if a key exists within a section's content.

        This method first finds the section, then checks if the key exists
        within that section's boundaries.

        Args:
            content: TOML content to search.
            section_path: Section path to search within.
            key: Key name to check for.

        Returns:
            True if the key exists in the section, False otherwise.

        """
        # First find the section content
        section_pattern = self.build_section_content_pattern(section_path)
        section_match = section_pattern.search(content)

        if not section_match:
            return False

        # Then check if key exists within that section
        section_content = section_match.group(1)
        key_pattern = self.build_key_exists_in_section_pattern(key)
        return bool(key_pattern.search(section_content))

    def replace_key_in_section(
        self, content: str, section_path: str, key: str, new_value: str
    ) -> str:
        """Replace a key's value within a specific section.

        Args:
            content: TOML content to modify.
            section_path: Section path containing the key.
            key: Key name to replace.
            new_value: New value for the key.

        Returns:
            Modified TOML content with the key's value replaced.

        Raises:
            ValueError: If the key is not found in the section.

        """
        pattern = self.build_key_in_section_pattern(section_path, key)

        # The replacement preserves everything up to and including "key = "
        # and replaces everything after with the new value plus a newline
        replacement = rf"\g<1>{new_value}\n"

        new_content = pattern.sub(replacement, content)

        if new_content == content:
            msg = f"Key '{key}' not found in section '{section_path}'"
            raise ValueError(msg)

        return new_content

    def add_key_to_section(
        self, content: str, section_path: str, key: str, value: str
    ) -> str:
        """Add a new key-value pair to a section.

        If the section doesn't exist, it will be created.
        If the key already exists, it will be replaced.

        Args:
            content: TOML content to modify.
            section_path: Section path to add the key to.
            key: Key name to add.
            value: Value for the key.

        Returns:
            Modified TOML content with the key added.

        """
        # Check if key already exists and replace if so
        if self.key_exists_in_section(content, section_path, key):
            return self.replace_key_in_section(content, section_path, key, value)

        # Find the section
        section_pattern = self.build_section_content_pattern(section_path)
        section_match = section_pattern.search(content)

        if section_match:
            # Section exists, add key to it
            section_content = section_match.group(1)
            new_section_content = f"{section_content.rstrip()}\n{key} = {value}\n"
            return content.replace(section_content, new_section_content, 1)
        # Section doesn't exist, create it
        new_section = f"\n[{section_path}]\n{key} = {value}\n"
        return content + new_section


# Pre-compiled patterns for common operations
TOML_REGEX = TomlRegex()
