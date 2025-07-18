"""Integration tests for pylint-ruff-sync using fixture files."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pylint_ruff_sync.main import main


def copy_fixture_to_temp(*, fixture_name: str, temp_dir: Path) -> Path:
    """Copy a fixture file to temporary directory.

    Args:
        fixture_name: Name of the fixture file
        temp_dir: Temporary directory to copy to

    Returns:
        Path to the copied file

    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    temp_file = temp_dir / "pyproject.toml"
    shutil.copy2(fixture_path, temp_file)
    return temp_file


def read_expected_result(*, fixture_name: str) -> str:
    """Read the expected result from an 'after' fixture.

    Args:
        fixture_name: Name of the 'after' fixture file

    Returns:
        Content of the fixture file

    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    return fixture_path.read_text()


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
@pytest.mark.usefixtures("mocked_subprocess")
def test_pyproject_integration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    test_case: str,
    tmp_path: Path,
) -> None:
    """Test integration with different pyproject.toml configurations.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        test_case: The test case name (corresponds to fixture file names)
        tmp_path: Temporary directory fixture from pytest

    """
    # Copy before fixture to temp directory
    before_fixture = f"{test_case}_before.toml"
    after_fixture = f"{test_case}_after.toml"

    config_file = copy_fixture_to_temp(fixture_name=before_fixture, temp_dir=tmp_path)

    # Mock sys.argv to simulate running the tool
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Check the result matches expected
    actual_content = config_file.read_text()
    expected_content = read_expected_result(fixture_name=after_fixture)

    assert actual_content.strip() == expected_content.strip()


@pytest.mark.usefixtures("mocked_subprocess")
def test_dry_run_integration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test dry run functionality.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp(
        fixture_name="empty_pyproject_before.toml", temp_dir=tmp_path
    )

    original_content = config_file.read_text()

    # Mock sys.argv to simulate dry run
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--dry-run",
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # File should not be modified in dry run
    current_content = config_file.read_text()
    assert current_content == original_content


@pytest.mark.usefixtures("mocked_subprocess")
def test_rule_format_name_integration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test rule format name functionality with integration.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp(
        fixture_name="existing_pylint_config_before.toml", temp_dir=tmp_path
    )

    # Mock sys.argv to use rule names
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-format",
            "name",
            "--rule-comment",
            "none",
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Check that config file uses rule names
    content = config_file.read_text()
    assert "invalid-name" in content  # Should use rule names
    assert "enable" in content  # Should have enable section


@pytest.mark.usefixtures("mocked_subprocess")
def test_rule_comment_none_integration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test rule comment none functionality with integration.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp(
        fixture_name="existing_pylint_config_before.toml", temp_dir=tmp_path
    )

    # Mock sys.argv to disable comments
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-comment",
            "none",
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Check that config file has no URL comments in enable section
    content = config_file.read_text()
    lines = content.split("\n")
    in_enable_section = False
    for line in lines:
        if "enable" in line and "=" in line:
            in_enable_section = True
        elif line.strip().startswith("["):
            in_enable_section = False
        elif in_enable_section and line.strip().startswith('"'):
            # In enable section, should not have URL comments
            assert "https://pylint.readthedocs.io" not in line


@pytest.mark.usefixtures("mocked_subprocess")
def test_rule_comment_short_description_integration(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test rule comment short description functionality with integration.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp(
        fixture_name="existing_pylint_config_before.toml", temp_dir=tmp_path
    )

    # Mock sys.argv to use short descriptions
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-comment",
            "short_description",
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Check that config file has description comments
    content = config_file.read_text()
    # Should have some rule descriptions from the mock data
    description_found = any(
        desc in content
        for desc in ["Invalid name", "Unused import", "Missing docstring"]
    )
    assert description_found, (
        f"Expected to find rule descriptions in content: {content}"
    )


@pytest.mark.usefixtures("mocked_subprocess")
def test_file_not_found_error(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test error handling when config file doesn't exist.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    non_existent_file = tmp_path / "non_existent.toml"

    # Mock sys.argv to simulate file not found
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(non_existent_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
        ],
    )

    # Run the main function
    result = main()

    # Should return error code
    assert result == 1


@pytest.mark.usefixtures("mocked_subprocess")
def test_invalid_config_file(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test error handling with invalid config file.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest

    """
    # Create an invalid TOML file
    invalid_config = tmp_path / "invalid.toml"
    invalid_config.write_text("This is not valid TOML content [[[")

    # Mock sys.argv to simulate invalid config
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(invalid_config),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
        ],
    )

    # Run the main function
    result = main()

    # Should return error code (1 for general errors)
    assert result == 1
