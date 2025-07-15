"""Shared test constants and mock data for pylint-ruff-sync tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import pytest

# Mock GitHub API response for tests
MOCK_GITHUB_RESPONSE = """
<html>
<body>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>F401</code> <code>F401</code>
</li>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>F841</code> <code>F841</code>
</li>
<li class="task-list-item">
    <input type="checkbox" checked="checked" />
    <code>E501</code> <code>E501</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>C0103</code> <code>C0103</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>C0111</code> <code>C0111</code>
</li>
<li class="task-list-item">
    <input type="checkbox" />
    <code>R0903</code> <code>R0903</code>
</li>
</body>
</html>
"""

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


def _apply_toml_sort_mock(file_path: str) -> None:
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


def setup_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up all mocks needed for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """

    # Mock the GitHub API call
    class MockResponse:
        """Mock response object for GitHub API calls."""

        def __init__(self, content: str) -> None:
            """Initialize with content string.

            Args:
                content: The response content as string.

            """
            self.content = content.encode("utf-8")

        def raise_for_status(self) -> None:
            """Mock method that does nothing."""

    def mock_requests_get(*_args: object, **_kwargs: object) -> MockResponse:
        return MockResponse(MOCK_GITHUB_RESPONSE)

    monkeypatch.setattr("requests.get", mock_requests_get)

    # Mock the pylint command output
    class MockSubprocessResult:
        """Mock subprocess result object."""

        def __init__(self, stdout: str) -> None:
            """Initialize with stdout string.

            Args:
                stdout: The subprocess stdout as string.

            """
            self.stdout = stdout
            self.returncode = 0
            self.stderr = ""

    mock_result = MockSubprocessResult(stdout=MOCK_PYLINT_OUTPUT)

    def mock_subprocess_run(*args: object, **_kwargs: object) -> MockSubprocessResult:
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
                _apply_toml_sort_mock(file_path)
                return MockSubprocessResult(stdout="")

        # For other subprocess calls (like pylint), return the default mock
        return mock_result

    def mock_shutil_which(_cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)
