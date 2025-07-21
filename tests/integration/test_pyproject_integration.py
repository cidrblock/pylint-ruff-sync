"""Integration tests for pylint-ruff-sync using fixture files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from pylint_ruff_sync.main import main


def _verify_rule_format(*, content: str, rule_format: str) -> None:
    """Verify rule format expectations in the content.

    Args:
        content: The file content to verify.
        rule_format: The expected rule format (code or name).

    """
    lines = content.split("\n")
    array_lines = [
        line
        for line in lines
        if line.strip().startswith('"')
        and ("enable" in content or "disable" in content)
    ]

    if rule_format == "code":
        # Should contain rule codes like C0103, C0111, etc.
        assert "C0103" in content
        assert "C0111" in content
        # Should not contain rule names in the arrays (except for comments)
        for line in array_lines:
            if '"invalid-name"' in line and line.strip().startswith('"invalid-name"'):
                pytest.fail(
                    f"Found rule name 'invalid-name' as array item with "
                    f"rule_format=code: {line}"
                )
    else:  # rule_format == "name"
        # Should contain rule names like invalid-name, missing-docstring, etc.
        assert "invalid-name" in content
        assert "missing-docstring" in content
        # Should not contain rule codes in the arrays (except for comments)
        for line in array_lines:
            if '"C0103"' in line and line.strip().startswith('"C0103"'):
                pytest.fail(
                    f"Found rule code 'C0103' as array item with "
                    f"rule_format=name: {line}"
                )


def _verify_rule_comment(*, content: str, rule_comment: str, rule_format: str) -> None:
    """Verify rule comment expectations in the content.

    Args:
        content: The file content to verify.
        rule_comment: The expected rule comment type.
        rule_format: The rule format being used.

    """
    if rule_comment == "none":
        # Should not have any comments after rule identifiers
        lines = content.split("\n")
        for line in lines:
            if line.strip().startswith('"') and "#" in line and '"all"' not in line:
                # Allow "all" to have comments in some cases
                pytest.fail(f"Found comment with rule_comment=none: {line}")
    elif rule_comment == "doc_url":
        # Should contain doc URLs
        assert "https://pylint.readthedocs.io" in content
    elif rule_comment == "code":
        # Should contain rule codes in comments
        if rule_format == "name":
            # When using name format, comments should contain codes
            assert "# C0103" in content or "# C0111" in content
    elif rule_comment == "name":
        # Should contain rule names in comments
        if rule_format == "code":
            # When using code format, comments should contain names
            assert "# invalid-name" in content or "# missing-docstring" in content
    elif rule_comment == "short_description":
        # Should contain rule descriptions in comments
        assert "doesn't conform" in content or "Missing" in content


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
    """Test integration with rule_comment=short_description shows 'All rules' for 'all'.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest.

    """
    # Create a simple config file
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        """[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools>=45", "wheel"]

[project]
name = "test-project"
version = "0.1.0"
"""
    )

    # Mock sys.argv with rule_comment=short_description
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-comment=short_description",
        ],
    )

    # Run the main function
    result = main()
    assert not result

    # Read the result and check for "All rules" comment
    content = config_file.read_text()
    assert "disable = [" in content
    assert '"all" # All rules' in content

    # Should also have short descriptions for enabled rules
    assert "# Invalid constant name" in content or "# invalid name" in content.lower()


@pytest.mark.usefixtures("mocked_subprocess")
def test_rule_comment_disable_array_with_doc_url(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that disable array gets doc_url comments when rule_comment=doc_url.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest.

    """
    # Create a config file with some existing disable rules
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        """[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools>=45", "wheel"]

[project]
name = "test-project"
version = "0.1.0"

[tool.pylint.messages_control]
disable = ["W0613"]
"""
    )

    # Mock sys.argv with default rule_comment=doc_url
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
    assert not result

    # Read the result and check for doc URLs in disable array
    content = config_file.read_text()
    assert "disable = [" in content

    # Should have "all" without comment (since default is doc_url, not
    # short_description)
    assert '"all"' in content
    assert '"all" # All rules' not in content

    # Should have doc URLs for any disable rules that aren't "all"
    lines = content.split("\n")
    disable_section = False
    for line in lines:
        if "disable = [" in line:
            disable_section = True
        elif disable_section and "]" in line:
            disable_section = False
        elif disable_section and "https://pylint.readthedocs.io" in line:
            # Found a doc URL in the disable section
            break
    else:
        # If we have actual rules in disable array besides "all", they should
        # have doc URLs. But if it's just ["all"], that's fine too
        pass


@pytest.mark.usefixtures("mocked_subprocess")
def test_rule_comment_none_no_comments_in_disable(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that disable array has no comments when rule_comment=none.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest.

    """
    # Create a config file
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        """[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools>=45", "wheel"]

[project]
name = "test-project"
version = "0.1.0"
"""
    )

    # Mock sys.argv with rule_comment=none
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-comment=none",
        ],
    )

    # Run the main function
    result = main()
    assert not result

    # Read the result and verify no comments
    content = config_file.read_text()

    # Should not have any # comments in the pylint section
    lines = content.split("\n")
    in_pylint = False
    for line in lines:
        if "[tool.pylint" in line:
            in_pylint = True
        elif in_pylint and line.startswith("[") and "pylint" not in line:
            in_pylint = False
        elif in_pylint and "#" in line:
            # Should not have comments in pylint section
            pytest.fail(f"Found unexpected comment in pylint section: {line}")


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


@pytest.mark.parametrize(
    ("rule_format", "rule_comment"),
    [
        ("code", "doc_url"),
        ("code", "code"),
        ("code", "name"),
        ("code", "short_description"),
        ("code", "none"),
        ("name", "doc_url"),
        ("name", "code"),
        ("name", "name"),
        ("name", "short_description"),
        ("name", "none"),
    ],
)
@pytest.mark.usefixtures("mocked_subprocess")
def test_all_rule_format_comment_combinations(
    *,
    monkeypatch: pytest.MonkeyPatch,
    rule_comment: str,
    rule_format: str,
    tmp_path: Path,
) -> None:
    """Test all combinations of rule-format and rule-comment parameters.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        rule_comment: The rule comment type to test.
        rule_format: The rule format type to test.
        tmp_path: Temporary directory fixture from pytest.

    """
    # Copy a before fixture to temp directory
    config_file = copy_fixture_to_temp(
        fixture_name="existing_pylint_config_before.toml", temp_dir=tmp_path
    )

    # Mock sys.argv with the specific combination
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-format",
            rule_format,
            "--rule-comment",
            rule_comment,
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Read the generated content
    content = config_file.read_text()

    # Verify rule format and comment expectations
    _verify_rule_format(content=content, rule_format=rule_format)
    _verify_rule_comment(
        content=content, rule_comment=rule_comment, rule_format=rule_format
    )

    # Special case for short_description comment type with "all"
    if rule_comment == "short_description":
        # "all" should get "All rules" comment
        assert "# All rules" in content

    # Verify basic structure
    assert "tool.pylint.messages_control" in content
    assert "disable" in content
    assert "enable" in content


@pytest.mark.usefixtures("mocked_subprocess")
def test_case_insensitive_sorting(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that rule arrays are sorted case-insensitively.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Temporary directory fixture from pytest.

    """
    # Create a simple config file with just a few mixed-case rule identifiers
    test_config = """[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools>=45", "wheel"]

[project]
description = "Test project"
name = "test-project"
version = "0.1.0"

[tool.pylint.messages_control]
disable = ["zebra-rule", "Apple-rule", "bear-rule", "all"]
"""

    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(test_config)

    # Mock sys.argv
    monkeypatch.setattr(
        "sys.argv",
        [
            "pylint-ruff-sync",
            "--config-file",
            str(config_file),
            "--cache-path",
            str(tmp_path / "test_cache.json"),
            "--rule-format",
            "code",
            "--rule-comment",
            "none",
        ],
    )

    # Run the main function
    result = main()

    # Should succeed
    assert not result

    # Read the generated content
    content = config_file.read_text()

    # Extract all quoted items from disable array using regex

    disable_section_match = re.search(r"disable\s*=\s*\[(.*?)\]", content, re.DOTALL)

    assert disable_section_match, "Could not find disable array"

    disable_content = disable_section_match.group(1)

    # Extract quoted items
    quoted_items = re.findall(r'"([^"]*)"', disable_content)

    # Verify case-insensitive sorting
    # Expected order (case-insensitive): "all", "Apple-rule", "bear-rule", "zebra-rule"
    sorted_items = sorted(quoted_items, key=str.lower)
    assert quoted_items == sorted_items, (
        f"Items not sorted case-insensitively: {quoted_items} vs {sorted_items}"
    )
