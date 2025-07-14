"""Integration tests for pylint-ruff-sync using fixture files."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pylint_ruff_sync.main import main
from tests.constants import setup_mocks


def copy_fixture_to_temp(fixture_name: str, temp_dir: Path) -> Path:
    """Copy a fixture file to temporary directory.

    Args:
        fixture_name: Name of the fixture file
        temp_dir: Temporary directory path

    Returns:
        Path to the copied file

    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    temp_file = temp_dir / "pyproject.toml"
    shutil.copy2(fixture_path, temp_file)
    return temp_file


def read_expected_result(fixture_name: str) -> str:
    """Read the expected result from an 'after' fixture.

    Args:
        fixture_name: Name of the 'after' fixture file

    Returns:
        Content of the expected result file

    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    return fixture_path.read_text()


def normalize_content(content: str) -> str:
    """Normalize content for comparison by removing extra whitespace.

    Args:
        content: Content to normalize

    Returns:
        Normalized content

    """
    # Remove extra whitespace and normalize line endings
    lines = [line.rstrip() for line in content.splitlines()]
    return "\n".join(lines).strip()


@pytest.mark.parametrize(
    "test_case",
    [
        "empty_pyproject",
        "existing_pylint_config",
        "other_tools_only",
        "comments_and_formatting",
        "pylint_without_messages_control",
        "disabled_rules_by_name",
        "complex_existing_config",
    ],
)
def test_pyproject_integration(
    tmp_path: Path,
    test_case: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test integration with various pyproject.toml configurations.

    Args:
        tmp_path: Temporary directory fixture from pytest
        test_case: The test case name (corresponds to fixture file names)
        monkeypatch: Pytest monkeypatch for mocking

    """
    setup_mocks(monkeypatch)

    # Copy before fixture to temp directory
    before_fixture = f"{test_case}_before.toml"
    after_fixture = f"{test_case}_after.toml"

    config_file = copy_fixture_to_temp(before_fixture, tmp_path)

    # Mock sys.argv for main function
    monkeypatch.setattr("sys.argv", ["pylint-ruff-sync", "--config", str(config_file)])

    # Run the tool
    result = main()

    # Check that the tool ran successfully
    # NOTE: Tool returns 1 when changes are made (for precommit hooks),
    # 0 when no changes
    assert result in (0, 1), (
        f"Tool failed unexpectedly for {test_case} (exit code: {result})"
    )

    # Read the actual result
    actual_content = config_file.read_text()

    # Read the expected result
    expected_content = read_expected_result(after_fixture)

    # Normalize both contents for comparison
    actual_normalized = normalize_content(actual_content)
    expected_normalized = normalize_content(expected_content)

    # Compare the results
    assert actual_normalized == expected_normalized, (
        f"Result doesn't match expected for {test_case}.\n"
        f"Expected:\n{expected_normalized}\n"
        f"Actual:\n{actual_normalized}\n"
    )


def test_dry_run_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test dry run mode doesn't modify files.

    Args:
        tmp_path: Temporary directory fixture from pytest
        monkeypatch: Pytest monkeypatch for mocking

    """
    setup_mocks(monkeypatch)

    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp("empty_pyproject_before.toml", tmp_path)

    # Read original content
    original_content = config_file.read_text()

    # Mock sys.argv for main function with dry-run flag
    monkeypatch.setattr(
        "sys.argv", ["pylint-ruff-sync", "--config", str(config_file), "--dry-run"]
    )

    # Run the tool
    result = main()

    # Check that the tool ran successfully
    assert not result, f"Tool failed unexpectedly (exit code: {result})"

    # Read the content after running
    after_content = config_file.read_text()

    # Content should be unchanged
    assert after_content == original_content, (
        "File was modified during dry run when it shouldn't have been"
    )


def test_file_not_found_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error handling when config file doesn't exist.

    Args:
        tmp_path: Temporary directory fixture from pytest
        monkeypatch: Pytest monkeypatch for mocking

    """
    setup_mocks(monkeypatch)

    # Use a non-existent file path
    nonexistent_file = tmp_path / "nonexistent.toml"

    # Mock sys.argv for main function
    monkeypatch.setattr(
        "sys.argv", ["pylint-ruff-sync", "--config", str(nonexistent_file)]
    )

    # Run the tool and expect it to fail
    result = main()

    # Should return non-zero exit code for file not found
    assert result, "Tool should have failed with non-existent config file"


def test_invalid_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error handling with invalid TOML file.

    Args:
        tmp_path: Temporary directory fixture from pytest
        monkeypatch: Pytest monkeypatch for mocking

    """
    setup_mocks(monkeypatch)

    # Create an invalid TOML file
    invalid_file = tmp_path / "invalid.toml"
    invalid_file.write_text("invalid toml content [[[")

    # Mock sys.argv for main function
    monkeypatch.setattr("sys.argv", ["pylint-ruff-sync", "--config", str(invalid_file)])

    # Run the tool and expect it to fail
    result = main()

    # Should return non-zero exit code for invalid TOML
    assert result, "Tool should have failed with invalid TOML file"
