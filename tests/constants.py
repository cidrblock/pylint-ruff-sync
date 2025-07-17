"""Shared test constants and mock data for pylint-ruff-sync tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

# Mock GitHub CLI response for tests - should be the body content from the issue
MOCK_GITHUB_CLI_RESPONSE = (
    '{"body": "## Status\\n\\nThis issue tracks implementation of pylint rules '
    "in ruff.\\n\\n### Implemented Rules\\n\\n"
    "- [x] `unused-import` / `F401` (`PYF401`)\\n"
    "- [x] `unused-variable` / `F841` (`PYF841`)\\n"
    "- [x] `line-too-long` / `E501` (`PYE501`)\\n\\n"
    "### Not Yet Implemented\\n\\n- [ ] `invalid-name` / `C0103` (`PYC0103`)\\n"
    "- [ ] `missing-docstring` / `C0111` (`PYC0111`)\\n"
    '- [ ] `too-few-public-methods` / `R0903` (`PYR0903`)"}'
)

# Mock pylint command output for tests
MOCK_PYLINT_OUTPUT = """
:invalid-name (C0103): *Invalid name*
:missing-docstring (C0111): *Missing docstring*
:line-too-long (E501): *Line too long*
:unused-import (F401): *Unused import*
:unused-variable (F841): *Unused variable*
:too-few-public-methods (R0903): *Too few public methods*
"""

# Constants for toml-sort mocking
TOML_SORT_MIN_ARGS = 3

# We're mocking with exactly 6 rules, 3 implemented in ruff, 3 not implemented
EXPECTED_RULES_COUNT = 6
EXPECTED_IMPLEMENTED_RULES_COUNT = 3


def _apply_toml_sort_mock(*, file_path: str) -> None:
    """Apply toml-sort with desired configuration to a file.

    This is extracted to reduce complexity and eliminate code duplication.

    Args:
        file_path: Path to the TOML file to sort.

    """
    try:
        # Read the file content
        content = Path(file_path).read_text(encoding="utf-8")

        # Apply toml-sort with the desired configuration
        try:
            # Import here to avoid import errors if toml-sort not available
            from toml_sort.tomlsort import (  # noqa: PLC0415
                FormattingConfiguration,
                SortConfiguration,
                TomlSort,
            )

            # Configure toml-sort with desired settings
            sort_config = SortConfiguration(
                table_keys=True,
                inline_tables=True,
                inline_arrays=True,
            )
            formatting_config = FormattingConfiguration(
                # Don't add trailing commas
                trailing_comma_inline_array=False,
            )

            # Apply sorting
            sorter = TomlSort(
                input_toml=content,
                sort_config=sort_config,
                format_config=formatting_config,
            )

            result = sorter.sorted()

            # Post-process to normalize spacing to match expected
            # fixture format
            # Fix extra spaces after commas in arrays with comments
            # Change ",  # comment" to ", # comment"
            result = re.sub(r",\s{2,}(#.*)", r", \1", result)

            # Remove trailing spaces before comments in arrays
            # (for last items)
            # Change '"item"  # comment' to '"item" # comment'
            result = re.sub(r'"\s{2,}(#.*)', r'" \1', result)

            # Write the sorted content back to the file
            Path(file_path).write_text(result, encoding="utf-8")

        except ImportError:
            # If toml-sort is not available, leave content as-is
            pass

    except Exception:  # noqa: S110, BLE001
        # If anything fails, leave content as-is
        pass


def setup_mocks(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up all mocks needed for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """

    # Mock the pylint command output
    class MockSubprocessResult:
        """Mock subprocess result object."""

        def __init__(self, *, stdout: str, returncode: int = 0) -> None:
            """Initialize with stdout string.

            Args:
                stdout: The subprocess stdout as string.
                returncode: The return code.

            """
            self.stdout = stdout
            self.returncode = returncode
            self.stderr = ""

    mock_pylint_result = MockSubprocessResult(stdout=MOCK_PYLINT_OUTPUT)
    mock_gh_result = MockSubprocessResult(stdout=MOCK_GITHUB_CLI_RESPONSE)

    def mock_subprocess_run(*args: object, **_kwargs: object) -> MockSubprocessResult:
        # Check if this is a gh CLI command
        if (
            args
            and len(args) > 0
            and isinstance(args[0], list)
            and len(args[0]) > 0
            and args[0][0] == "gh"
        ):
            # Return mock GitHub CLI response
            return mock_gh_result

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
                _apply_toml_sort_mock(file_path=file_path)
                return MockSubprocessResult(stdout="")

        # For other subprocess calls (like pylint), return the default mock
        return mock_pylint_result

    def mock_shutil_which(*, _cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)
