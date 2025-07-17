"""Pytest configuration and shared fixtures for pylint-ruff-sync tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

import pytest


class TomlSortMockProtocol(Protocol):
    """Protocol for toml sort mock function."""

    def __call__(self, *, file_path: str) -> None:
        """Apply toml sort mock to file path.

        Args:
            file_path: Path to the file to sort.

        """
        ...


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


@pytest.fixture(name="mock_github_response")
def _mock_github_response() -> str:
    """Mock GitHub CLI response for tests.

    Returns:
        Mock response body content from the GitHub issue.

    """
    return (
        '{"body": "## Status\\n\\nThis issue tracks implementation of pylint rules '
        "in ruff.\\n\\n### Implemented Rules\\n\\n"
        "- [x] `unused-import` / `F401` (`PYF401`)\\n"
        "- [x] `unused-variable` / `F841` (`PYF841`)\\n"
        "- [x] `line-too-long` / `E501` (`PYE501`)\\n\\n"
        "### Not Yet Implemented\\n\\n- [ ] `invalid-name` / `C0103` (`PYC0103`)\\n"
        "- [ ] `missing-docstring` / `C0111` (`PYC0111`)\\n"
        '- [ ] `too-few-public-methods` / `R0903` (`PYR0903`)"}'
    )


@pytest.fixture(name="mock_pylint_output")
def _mock_pylint_output() -> str:
    """Mock pylint command output for tests.

    Returns:
        Mock pylint output with rule definitions.

    """
    return """
:invalid-name (C0103): *Invalid name*
:missing-docstring (C0111): *Missing docstring*
:line-too-long (E501): *Line too long*
:unused-import (F401): *Unused import*
:unused-variable (F841): *Unused variable*
:too-few-public-methods (R0903): *Too few public methods*
"""


@pytest.fixture(name="toml_sort_mock")
def _toml_sort_mock() -> TomlSortMockProtocol:
    """Apply toml-sort with desired configuration to a file.

    Returns:
        Function that applies toml-sort mock to a file path.

    """

    def _apply_toml_sort_mock(*, file_path: str) -> None:
        """Apply toml-sort with desired configuration to a file.

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

    return _apply_toml_sort_mock


@pytest.fixture(name="mocked_subprocess")
def _mocked_subprocess(
    *,
    monkeypatch: pytest.MonkeyPatch,
    mock_github_response: str,
    mock_pylint_output: str,
    toml_sort_mock: TomlSortMockProtocol,
) -> None:
    """Set up all subprocess mocks needed for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        mock_github_response: Mock GitHub CLI response.
        mock_pylint_output: Mock pylint output.
        toml_sort_mock: Function to apply toml-sort mock.

    """
    # Constants for toml-sort mocking
    toml_sort_min_args = 3

    mock_pylint_result = MockSubprocessResult(stdout=mock_pylint_output)
    mock_gh_result = MockSubprocessResult(stdout=mock_github_response)

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
            if "--in-place" in command_args and len(command_args) >= toml_sort_min_args:
                file_path = command_args[2]
                toml_sort_mock(file_path=file_path)
                return MockSubprocessResult(stdout="")

        # For other subprocess calls (like pylint), return the default mock
        return mock_pylint_result

    def mock_shutil_which(*, _cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)
