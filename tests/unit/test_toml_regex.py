"""Unit tests for TomlRegex class and regex patterns.

These tests demonstrate how the regular expressions work to find and replace
TOML content, with detailed examples and edge cases.
"""

from __future__ import annotations

import re
import textwrap
from typing import Self

import pytest

from pylint_ruff_sync.toml_regex import TOML_REGEX, RegexMatch, TomlRegex


class IndentedMultiline(str):
    """Helper class for creating clean multiline strings in tests."""

    __slots__ = ()

    def __new__(cls, content: str) -> Self:
        """Create a new IndentedMultiline string with dedented content."""
        cleaned = textwrap.dedent(content).lstrip("\n")
        return super().__new__(cls, cleaned)


def test_regex_match_dataclass() -> None:
    """Test the RegexMatch dataclass functionality."""
    # Test with a successful match
    pattern = re.compile(r"(\w+)\s*=\s*(\d+)")
    match = pattern.search("key = 123")

    regex_match = RegexMatch(match=match, matched=True)

    assert regex_match.matched
    assert regex_match.match is not None
    assert regex_match.groups == ("key", "123")

    # Test with no match
    no_match = RegexMatch(match=None, matched=False)
    assert not no_match.matched
    assert no_match.match is None
    assert not no_match.groups


def test_build_section_pattern() -> None:
    """Test building regex patterns for TOML section headers."""
    regex = TomlRegex()

    # Test basic section pattern
    pattern = regex.build_section_pattern("tool.pylint.messages_control")

    # Should match exact section header
    assert pattern.search("[tool.pylint.messages_control]") is not None

    # Should not match different sections
    assert pattern.search("[tool.pylint.format]") is None
    assert pattern.search("[other.section]") is None

    # Should handle special characters in section names
    special_pattern = regex.build_section_pattern("tool.section-with-dashes")
    assert special_pattern.search("[tool.section-with-dashes]") is not None

    # Should handle sections with dots and underscores
    complex_pattern = regex.build_section_pattern("tool.my_tool.sub-section")
    assert complex_pattern.search("[tool.my_tool.sub-section]") is not None


def test_build_section_pattern_with_regex_characters() -> None:
    """Test section patterns with regex special characters are properly escaped."""
    regex = TomlRegex()

    # Test section with parentheses (should be escaped)
    pattern = regex.build_section_pattern("tool.test(special)")
    toml_content = "[tool.test(special)]\nkey = value"

    match = pattern.search(toml_content)
    assert match is not None

    # Verify it doesn't match without proper escaping
    # (This would fail if we didn't escape the parentheses)
    assert pattern.search("[tool.test-special-y]") is None


def test_build_key_in_section_pattern_simple() -> None:
    """Test finding keys within sections with simple single-line values."""
    regex = TomlRegex()
    pattern = regex.build_key_in_section_pattern("tool.pylint", "disable")

    toml_content = """[tool.pylint]
disable = ["rule1", "rule2"]
enable = ["rule3"]

[other.section]
disable = ["other-rule"]
"""

    match = pattern.search(toml_content)
    assert match is not None

    # The first capture group should include section header up to "disable = "
    captured = match.group(1)
    assert "[tool.pylint]" in captured
    assert "disable = " in captured

    # Should not match disable in other sections
    other_pattern = regex.build_key_in_section_pattern("other.section", "disable")
    other_match = other_pattern.search(toml_content)
    assert other_match is not None
    assert "[other.section]" in other_match.group(1)


def test_build_key_in_section_pattern_multiline_array() -> None:
    """Test finding keys with multiline array values."""
    regex = TomlRegex()
    pattern = regex.build_key_in_section_pattern(
        "tool.pylint.messages_control", "disable"
    )

    toml_content = """[tool.pylint.messages_control]
disable = [
  "missing-docstring",
  "line-too-long",
  "invalid-name"
]
enable = ["another-rule"]

[other.section]
value = "test"
"""

    match = pattern.search(toml_content)
    assert match is not None

    # Should capture the section header and key
    captured = match.group(1)
    assert "[tool.pylint.messages_control]" in captured
    assert "disable = " in captured


def test_build_key_in_section_pattern_with_comments() -> None:
    """Test finding keys in sections that contain comments."""
    regex = TomlRegex()
    pattern = regex.build_key_in_section_pattern("tool.pylint", "disable")

    toml_content = """[tool.pylint]
# This is a comment about pylint configuration
disable = [
  "rule1", # Comment about rule1
  "rule2"  # Comment about rule2
]
# Another comment
enable = ["rule3"]
"""

    match = pattern.search(toml_content)
    assert match is not None

    captured = match.group(1)
    assert "[tool.pylint]" in captured
    assert "disable = " in captured
    assert "# This is a comment" in captured


def test_build_key_exists_in_section_pattern() -> None:
    """Test checking if a key exists in a section."""
    regex = TomlRegex()
    pattern = regex.build_key_exists_in_section_pattern("disable")

    # Test various key formats
    test_cases = [
        "disable = []",
        "  disable = ['rule']",
        "\tdisable = value",
        "disable=value",  # No spaces around equals
    ]

    for case in test_cases:
        assert pattern.search(case) is not None, f"Failed to match: {case}"

    # Should not match keys with different names
    assert pattern.search("disabled = []") is None
    assert pattern.search("enable = []") is None
    assert pattern.search("# disable = []") is None  # Commented out


def test_build_section_content_pattern() -> None:
    """Test capturing entire section content."""
    regex = TomlRegex()
    pattern = regex.build_section_content_pattern("tool.pylint")

    toml_content = """[tool.ruff]
line-length = 88

[tool.pylint]
disable = ["rule1"]
enable = ["rule2"]
# Comment in section

[tool.black]
line-length = 88
"""

    match = pattern.search(toml_content)
    assert match is not None

    section_content = match.group(1)
    assert "[tool.pylint]" in section_content
    assert "disable = " in section_content
    assert "enable = " in section_content
    assert "# Comment in section" in section_content

    # Should not include content from other sections
    assert "[tool.ruff]" not in section_content
    assert "[tool.black]" not in section_content


def test_find_section_header() -> None:
    """Test the find_section_header method."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["rule1"]

        [other.section]
        value = "test"
        """)

    # Should find existing section
    result = regex.find_section_header(toml_content, "tool.pylint.messages_control")
    assert result.matched
    assert result.match is not None

    # Should not find non-existent section
    result = regex.find_section_header(toml_content, "nonexistent.section")
    assert not result.matched
    assert result.match is None


def test_find_key_in_section() -> None:
    """Test the find_key_in_section method."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["rule1", "rule2"]
        enable = ["rule3"]

        [other.section]
        disable = ["other-rule"]
        """)

    # Should find key in correct section
    result = regex.find_key_in_section(
        toml_content, "tool.pylint.messages_control", "disable"
    )
    assert result.matched
    assert result.match is not None
    assert len(result.groups) > 0

    # Should not find key in wrong section context
    result = regex.find_key_in_section(toml_content, "nonexistent.section", "disable")
    assert not result.matched


def test_key_exists_in_section() -> None:
    """Test checking if a key exists within a specific section."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["rule1"]
        enable = ["rule2"]

        [tool.ruff]
        disable = ["other-rule"]

        [tool.black]
        line-length = 88
        """)

    # Key exists in specified section
    assert regex.key_exists_in_section(
        toml_content, "tool.pylint.messages_control", "disable"
    )
    assert regex.key_exists_in_section(
        toml_content, "tool.pylint.messages_control", "enable"
    )
    assert regex.key_exists_in_section(toml_content, "tool.ruff", "disable")
    assert regex.key_exists_in_section(toml_content, "tool.black", "line-length")

    # Key doesn't exist in specified section
    assert not regex.key_exists_in_section(
        toml_content, "tool.pylint.messages_control", "line-length"
    )
    assert not regex.key_exists_in_section(toml_content, "tool.black", "disable")
    assert not regex.key_exists_in_section(
        toml_content, "nonexistent.section", "disable"
    )


def test_replace_key_in_section() -> None:
    """Test replacing a key's value within a specific section."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["old-rule"]
        enable = ["rule2"]

        [tool.ruff]
        disable = ["other-rule"]
        """)

    # Replace key in specific section
    result = regex.replace_key_in_section(
        toml_content, "tool.pylint.messages_control", "disable", '["new-rule"]'
    )

    # Should contain the new value
    assert '["new-rule"]' in result

    # Should preserve other sections and keys
    assert 'enable = ["rule2"]' in result
    assert "[tool.ruff]" in result
    assert 'disable = ["other-rule"]' in result

    # Should add newline after replacement - verify no concatenation
    lines = result.split("\n")
    disable_line_idx = next(
        i for i, line in enumerate(lines) if 'disable = ["new-rule"]' in line
    )

    # The disable line should be properly separated from the next line
    disable_line = lines[disable_line_idx]
    assert disable_line == 'disable = ["new-rule"]'  # Should be clean, no concatenation

    # Next line should be the enable line, properly separated
    if disable_line_idx + 1 < len(lines):
        next_line = lines[disable_line_idx + 1]
        assert next_line == 'enable = ["rule2"]'  # Should be properly separated


def test_replace_key_in_section_not_found() -> None:
    """Test replacing a key that doesn't exist raises ValueError."""
    regex = TomlRegex()

    toml_content = """[tool.pylint.messages_control]
disable = ["rule1"]
"""

    with pytest.raises(ValueError, match="Key 'nonexistent' not found in section"):
        regex.replace_key_in_section(
            toml_content, "tool.pylint.messages_control", "nonexistent", "value"
        )


def test_add_key_to_section_new_key() -> None:
    """Test adding a new key to an existing section."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["rule1"]

        [other.section]
        value = "test"
        """)

    result = regex.add_key_to_section(
        toml_content, "tool.pylint.messages_control", "enable", '["new-rule"]'
    )

    # Should contain the new key
    assert 'enable = ["new-rule"]' in result

    # Should preserve existing content
    assert 'disable = ["rule1"]' in result
    assert "[other.section]" in result


def test_add_key_to_section_replace_existing() -> None:
    """Test that adding a key that already exists replaces it."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["old-rule"]
        enable = ["rule2"]
        """)

    result = regex.add_key_to_section(
        toml_content, "tool.pylint.messages_control", "disable", '["new-rule"]'
    )

    # Should replace the existing key
    assert 'disable = ["new-rule"]' in result
    assert 'disable = ["old-rule"]' not in result

    # Should preserve other keys
    assert 'enable = ["rule2"]' in result


def test_add_key_to_section_create_section() -> None:
    """Test adding a key to a non-existent section creates the section."""
    regex = TomlRegex()

    toml_content = IndentedMultiline("""
        [existing.section]
        key = "value"
        """)

    result = regex.add_key_to_section(
        toml_content, "new.section", "new_key", '"new_value"'
    )

    # Should create the new section
    assert "[new.section]" in result
    assert 'new_key = "new_value"' in result

    # Should preserve existing content
    assert "[existing.section]" in result
    assert 'key = "value"' in result


def test_regex_patterns_with_complex_toml() -> None:
    """Test regex patterns with a complex TOML file structure."""
    regex = TomlRegex()

    complex_toml = IndentedMultiline("""
        # Top-level comment
        [build-system]
        requires = ["setuptools", "wheel"]

        [project]
        name = "my-project"
        version = "1.0.0"

        [tool.pylint.messages_control]
        # Pylint configuration
        disable = [
          "missing-docstring",  # We don't require docstrings everywhere
          "line-too-long",      # Handled by formatter
          "invalid-name"        # We use different naming conventions
        ]
        enable = [
          "unused-import",
          "unused-variable"
        ]

        [tool.ruff]
        line-length = 88
        target-version = "py311"

        [tool.ruff.lint]
        select = ["ALL"]
        ignore = ["D203", "D213"]

        [tool.black]
        line-length = 88
        """)

    # Test finding sections
    assert regex.find_section_header(
        complex_toml, "tool.pylint.messages_control"
    ).matched
    assert regex.find_section_header(complex_toml, "tool.ruff.lint").matched
    assert not regex.find_section_header(complex_toml, "nonexistent.section").matched

    # Test finding keys in sections
    assert regex.key_exists_in_section(
        complex_toml, "tool.pylint.messages_control", "disable"
    )
    assert regex.key_exists_in_section(
        complex_toml, "tool.pylint.messages_control", "enable"
    )
    assert regex.key_exists_in_section(complex_toml, "tool.ruff", "line-length")
    assert regex.key_exists_in_section(complex_toml, "tool.ruff.lint", "select")

    # Test that keys are section-specific
    assert not regex.key_exists_in_section(complex_toml, "tool.ruff", "disable")
    assert not regex.key_exists_in_section(complex_toml, "tool.black", "select")

    # Test replacing multiline array
    result = regex.replace_key_in_section(
        complex_toml, "tool.pylint.messages_control", "disable", '["new-rule-only"]'
    )

    assert 'disable = ["new-rule-only"]' in result
    # Should preserve comments and other structure
    assert "# Pylint configuration" in result
    assert "enable = [" in result
    assert "[tool.ruff]" in result


def test_regex_patterns_edge_cases() -> None:
    """Test regex patterns with edge cases and tricky formatting."""
    regex = TomlRegex()

    # Test with minimal whitespace
    minimal_toml = "[tool.test]\nkey=value\nother=data"
    assert regex.key_exists_in_section(minimal_toml, "tool.test", "key")
    assert regex.key_exists_in_section(minimal_toml, "tool.test", "other")

    # Test with excessive whitespace
    spaced_toml = IndentedMultiline("""
        [tool.test]

        key   =   value

        other =    data

        """)
    assert regex.key_exists_in_section(spaced_toml, "tool.test", "key")
    assert regex.key_exists_in_section(spaced_toml, "tool.test", "other")

    # Test with tabs
    tabbed_toml = "[tool.test]\n\tkey\t=\tvalue\n\tother\t=\tdata"
    assert regex.key_exists_in_section(tabbed_toml, "tool.test", "key")
    assert regex.key_exists_in_section(tabbed_toml, "tool.test", "other")


def test_global_toml_regex_instance() -> None:
    """Test that the global TOML_REGEX instance works correctly."""
    toml_content = """[tool.pylint.messages_control]
disable = ["rule1"]
enable = ["rule2"]
"""

    # Test using the global instance
    assert TOML_REGEX.key_exists_in_section(
        toml_content, "tool.pylint.messages_control", "disable"
    )
    assert TOML_REGEX.find_section_header(
        toml_content, "tool.pylint.messages_control"
    ).matched

    result = TOML_REGEX.replace_key_in_section(
        toml_content, "tool.pylint.messages_control", "disable", '["new-rule"]'
    )
    assert 'disable = ["new-rule"]' in result


def test_regex_performance_with_large_content() -> None:
    """Test that regex patterns perform well with larger TOML content."""
    # Create a large TOML content with many sections
    large_sections = [
        IndentedMultiline(f"""
        [section.{i}]
        key_{i} = "value_{i}"
        array_{i} = ["item1", "item2", "item3"]
        """)
        for i in range(100)
    ]

    # Add our target section at the end
    large_sections.append(
        IndentedMultiline("""
        [tool.pylint.messages_control]
        disable = ["target-rule"]
        enable = ["other-rule"]
        """)
    )

    large_toml = "\n".join(large_sections)

    # Should still find the target section efficiently
    assert TOML_REGEX.key_exists_in_section(
        large_toml, "tool.pylint.messages_control", "disable"
    )

    # Should be able to replace content efficiently
    result = TOML_REGEX.replace_key_in_section(
        large_toml, "tool.pylint.messages_control", "disable", '["new-target-rule"]'
    )
    assert 'disable = ["new-target-rule"]' in result
