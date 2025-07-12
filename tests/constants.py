"""Shared test constants and mock data for pylint-ruff-sync tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

# We're mocking with exactly 6 rules, 3 implemented in ruff, 3 not implemented
EXPECTED_RULES_COUNT = 6
EXPECTED_IMPLEMENTED_RULES_COUNT = 3
EXPECTED_NOT_IMPLEMENTED_RULES_COUNT = 3

# Sample HTML response with some implemented rules (mocked GitHub issue)
# Contains 6 rules total:
# - F401 (unused-import): ✓ implemented in ruff
# - F841 (unused-variable): ✓ implemented in ruff
# - E501 (line-too-long): ✓ implemented in ruff
# - C0103 (invalid-name): ✗ not implemented in ruff
# - C0111 (missing-docstring): ✗ not implemented in ruff
# - R0903 (too-few-public-methods): ✗ not implemented in ruff
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

# Sample pylint output (mocked pylint --list-msgs)
MOCK_PYLINT_OUTPUT = """
:unused-import (F401): *Unused import*
:unused-variable (F841): *Unused variable*
:line-too-long (E501): *Line too long*
:invalid-name (C0103): *Invalid name*
:missing-docstring (C0111): *Missing docstring*
:too-few-public-methods (R0903): *Too few public methods*
"""


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

    mock_result = MockSubprocessResult(stdout=MOCK_PYLINT_OUTPUT)

    def mock_subprocess_run(*_args: object, **_kwargs: object) -> MockSubprocessResult:
        return mock_result

    def mock_shutil_which(_cmd: str) -> str:
        return "/usr/bin/pylint"

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("shutil.which", mock_shutil_which)
