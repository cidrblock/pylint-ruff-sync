#!/usr/bin/env python3
"""Script to regenerate test fixtures using pytest infrastructure."""

import shutil
from pathlib import Path

from constants import setup_mocks

from pylint_ruff_sync.main import main


def regenerate_fixture(fixture_name: str) -> None:
    """Regenerate a single fixture file.

    Args:
        fixture_name: The base name of the fixture (e.g., 'empty_pyproject')

    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    before_fixture = fixtures_dir / f"{fixture_name}_before.toml"
    after_fixture = fixtures_dir / f"{fixture_name}_after.toml"
    temp_file = fixtures_dir / "temp_working.toml"

    print(f"Regenerating {fixture_name}...")

    # Copy before fixture to temp location
    shutil.copy2(before_fixture, temp_file)

    try:
        # Mock the environment using pytest's monkeypatch infrastructure
        from _pytest.monkeypatch import MonkeyPatch

        with MonkeyPatch().context() as m:
            setup_mocks(m)

            # Mock sys.argv
            m.setattr("sys.argv", ["pylint-ruff-sync", "--config-file", str(temp_file)])

            # Run the tool
            result = main()

            # Copy result to after fixture
            shutil.copy2(temp_file, after_fixture)

            print(f"  ✓ Generated {fixture_name} (exit code: {result})")

    except Exception as e:
        print(f"  ✗ Failed to generate {fixture_name}: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        if temp_file.exists():
            temp_file.unlink()


def main_regenerate() -> None:
    """Regenerate all test fixtures."""
    fixture_names = [
        "empty_pyproject",
        "existing_pylint_config",
        "other_tools_only",
        "comments_and_formatting",
        "pylint_without_messages_control",
        "disabled_rules_by_name",
        "complex_existing_config",
    ]

    for fixture_name in fixture_names:
        regenerate_fixture(fixture_name)


if __name__ == "__main__":
    main_regenerate()
