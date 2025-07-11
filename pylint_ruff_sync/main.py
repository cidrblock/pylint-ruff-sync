"""Main module for pylint-ruff-sync precommit hook.

This module contains the core logic for updating pylint configuration
to enable only those rules that haven't been implemented in ruff.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import requests  # type: ignore[import-untyped]
    import tomli_w  # type: ignore[import-not-found]
    import tomllib  # type: ignore[import-not-found]
    from bs4 import BeautifulSoup, Tag
except ImportError:
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# GitHub issue URL for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_URL = "https://github.com/astral-sh/ruff/issues/970"
# Minimum number of code elements expected in an implemented rule list item
MIN_CODE_ELEMENTS = 2


class PylintRule:  # pylint: disable=too-few-public-methods
    """Represents a pylint rule with its metadata."""

    def __init__(self, code: str, name: str, description: str) -> None:
        """Initialize a PylintRule instance.

        Args:
            code: The rule code (e.g., 'C0103')
            name: The rule name (e.g., 'invalid-name')
            description: The rule description

        """
        self.code = code
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        """Return a string representation of the PylintRule.

        Returns:
            A string representation of the PylintRule instance.

        """
        return f"PylintRule(code='{self.code}', name='{self.name}')"


class RuffPylintExtractor:  # pylint: disable=too-few-public-methods
    """Extracts pylint rules implemented in ruff from GitHub issue."""

    def __init__(self, issue_url: str = RUFF_PYLINT_ISSUE_URL) -> None:
        """Initialize a RuffPylintExtractor instance.

        Args:
            issue_url: The GitHub issue URL to fetch from

        """
        self.issue_url = issue_url

    def extract_implemented_rules(self) -> set[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        Returns:
            Set of pylint rule codes that are implemented in ruff.

        Raises:
            requests.RequestException: If unable to fetch the GitHub issue.
            Exception: If parsing fails.

        """
        try:  # pylint: disable=too-many-nested-blocks
            logger.info(
                "Fetching ruff pylint implementation status from %s", self.issue_url
            )
            response = requests.get(self.issue_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            li_tags = soup.find_all("li")

            implemented_rules = set()

            for li in li_tags:
                # Only process Tag objects that have attrs and children
                if (
                    isinstance(li, Tag)
                    and hasattr(li, "attrs")
                    and "class" in li.attrs
                    and "task-list-item" in li.attrs["class"]
                ):
                    names = [
                        child.name
                        for child in li.children
                        if hasattr(child, "name") and child.name
                    ]
                    if "input" in names and "code" in names:
                        # Check if the checkbox is checked
                        checked = [
                            child.attrs.get("checked")
                            for child in li.children
                            if hasattr(child, "name")
                            and child.name == "input"
                            and hasattr(child, "attrs")
                            and "checked" in child.attrs
                        ]
                        if checked:
                            codes = [
                                child.text
                                for child in li.children
                                if hasattr(child, "name") and child.name == "code"
                            ]
                            if len(codes) >= MIN_CODE_ELEMENTS:
                                pylint_code = codes[
                                    1
                                ]  # Second code element is the pylint code
                                implemented_rules.add(pylint_code)
                                logger.debug("Found implemented rule: %s", pylint_code)

            logger.info(
                "Found %d implemented pylint rules in ruff", len(implemented_rules)
            )

        except requests.RequestException:
            logger.exception("Failed to fetch GitHub issue")
            raise
        except Exception:
            logger.exception("Failed to parse GitHub issue")
            raise
        return implemented_rules


class PylintExtractor:
    """Extracts pylint rules from pylint --list-msgs command."""

    def extract_all_rules(self) -> list[PylintRule]:
        """Extract all pylint rules from pylint --list-msgs.

        Returns:
            List of PylintRule objects.

        Raises:
            FileNotFoundError: If pylint executable is not found in PATH.
            subprocess.CalledProcessError: If pylint command fails.
            Exception: If parsing fails.

        """
        try:
            logger.info("Extracting pylint rules from 'pylint --list-msgs'")
            pylint_path = shutil.which("pylint")
            if not pylint_path:
                msg = "pylint executable not found in PATH"
                raise FileNotFoundError(msg)  # noqa: TRY301

            result = subprocess.run(  # noqa: S603
                [pylint_path, "--list-msgs"],
                capture_output=True,
                text=True,
                check=True,
            )

            rules = []

            for line in result.stdout.split("\n"):
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                # Match rule header like ":missing-docstring (C0111): *Missing*"
                rule_match = re.match(
                    r"^:([a-z-]+)\s+\(([A-Z]\d+)\):\s*\*(.+)\*$", stripped_line
                )
                if rule_match:
                    name, code, description = rule_match.groups()
                    rule = PylintRule(code, name, description)
                    rules.append(rule)
                    logger.debug("Found pylint rule: %s (%s)", code, name)

            logger.info("Found %d total pylint rules", len(rules))

        except subprocess.CalledProcessError:
            logger.exception("Failed to run pylint --list-msgs")
            logger.exception("Make sure pylint is installed and available in PATH")
            raise
        except Exception:
            logger.exception("Failed to parse pylint output")
            raise
        return rules

    def resolve_rule_identifiers(
        self,
        rule_identifiers: list[str],
        all_rules: list[PylintRule],
    ) -> set[str]:
        """Resolve rule identifiers to rule codes.

        Args:
            rule_identifiers: List of rule codes or names to resolve.
            all_rules: List of all available pylint rules.

        Returns:
            Set of resolved rule codes.

        """
        resolved_codes = set()
        name_to_code = {rule.name: rule.code for rule in all_rules}
        valid_codes = {rule.code for rule in all_rules}

        for identifier in rule_identifiers:
            if identifier in valid_codes:
                # Direct code match
                resolved_codes.add(identifier)
            elif identifier in name_to_code:
                # Name match - resolve to code
                resolved_codes.add(name_to_code[identifier])
            else:
                logger.warning("Unknown rule identifier: %s", identifier)

        return resolved_codes


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration."""

    def __init__(self, config_file: Path) -> None:
        """Initialize a PyprojectUpdater instance.

        Args:
            config_file: Path to the pyproject.toml file

        """
        self.config_file = config_file

    def read_config(self) -> dict[str, Any]:
        """Read current configuration from pyproject.toml.

        Returns:
            The current configuration dictionary from pyproject.toml, or empty dict
            if file not found.

        Raises:
            Exception: If parsing the configuration file fails.

        """
        try:
            with self.config_file.open("rb") as f:
                config: dict[str, Any] = tomllib.load(f)
                return config
        except FileNotFoundError:
            logger.warning("No pyproject.toml found, creating new configuration")
            return {}
        except Exception:
            logger.exception("Failed to read configuration file")
            raise

    def update_pylint_config(
        self,
        config: dict[str, Any],
        rules_to_enable: set[str],
    ) -> dict[str, Any]:
        """Update pylint configuration to enable only non-implemented rules.

        Args:
            config: Current configuration dictionary.
            rules_to_enable: Set of rule codes to enable (not implemented in ruff).

        Returns:
            Updated configuration dictionary.

        """
        # Ensure pylint section exists
        if "tool" not in config:
            config["tool"] = {}
        if "pylint" not in config["tool"]:
            config["tool"]["pylint"] = {}
        if "messages_control" not in config["tool"]["pylint"]:
            config["tool"]["pylint"]["messages_control"] = {}

        # Get existing disabled rules to respect user preferences
        existing_disabled = set(
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("disable", [])
        )

        # Don't enable rules that are explicitly disabled by the user
        final_enable_rules = rules_to_enable - existing_disabled

        # Update enable list
        if final_enable_rules:
            enable_list = list(final_enable_rules)
            enable_list.sort()
            config["tool"]["pylint"]["messages_control"]["enable"] = enable_list

            logger.info(
                "Updated enable list with %d rules (not implemented in ruff)",
                len(final_enable_rules),
            )

            if existing_disabled & rules_to_enable:
                skipped_count = len(existing_disabled & rules_to_enable)
                logger.info(
                    "Skipped enabling %d rules that are explicitly disabled in config",
                    skipped_count,
                )

        # Preserve existing disable list - don't modify user's manual disable choices
        if existing_disabled:
            disable_list = list(existing_disabled)
            disable_list.sort()
            config["tool"]["pylint"]["messages_control"]["disable"] = disable_list
        else:
            config["tool"]["pylint"]["messages_control"]["disable"] = []

        return config

    def write_config(self, config: dict[str, Any]) -> None:
        """Write updated configuration to pyproject.toml.

        Args:
            config: The configuration dictionary to write to the file.

        Raises:
            Exception: If writing the configuration file fails.

        """
        try:
            with self.config_file.open("wb") as f:
                tomli_w.dump(config, f)
            logger.info("Updated configuration written to %s", self.config_file)
        except Exception:
            logger.exception("Failed to write configuration file")
            raise


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser.

    Returns:
        The configured ArgumentParser instance.

    """
    parser = argparse.ArgumentParser(
        description="Update pylint configuration to enable only rules not in ruff",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml file (default: pyproject.toml)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser


def _extract_rules_and_calculate_changes(
    config: dict[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    """Extract rules and calculate what changes are needed.

    Args:
        config: The current configuration dictionary to check for existing disabled
            rules.

    Returns:
        A tuple of (rules_to_enable, implemented_in_ruff, existing_disabled).

    """
    # Extract all pylint rules
    pylint_extractor = PylintExtractor()
    all_pylint_rules = pylint_extractor.extract_all_rules()
    all_pylint_codes = {rule.code for rule in all_pylint_rules}

    # Extract implemented rules from ruff
    ruff_extractor = RuffPylintExtractor()
    implemented_in_ruff = ruff_extractor.extract_implemented_rules()

    # Calculate rules to enable (NOT implemented in ruff)
    rules_to_enable = all_pylint_codes - implemented_in_ruff

    # Get existing disabled rules from config
    existing_disabled = set(
        config.get("tool", {})
        .get("pylint", {})
        .get("messages_control", {})
        .get("disable", [])
    )

    return rules_to_enable, implemented_in_ruff, existing_disabled


def _log_rule_summary(
    all_pylint_codes: set[str],
    implemented_in_ruff: set[str],
    rules_to_enable: set[str],
    existing_disabled: set[str],
    *,
    verbose: bool,
) -> None:
    """Log summary of rules being processed.

    Args:
        all_pylint_codes: Set of all available pylint rule codes.
        implemented_in_ruff: Set of pylint rules that are implemented in ruff.
        rules_to_enable: Set of rules to enable (not implemented in ruff).
        existing_disabled: Set of rules that are already disabled in config.
        verbose: Whether to include detailed rule listings in the log output.

    """
    logger.info("Total pylint rules: %d", len(all_pylint_codes))
    logger.info("Rules implemented in ruff: %d", len(implemented_in_ruff))
    logger.info("Rules to enable (not implemented in ruff): %d", len(rules_to_enable))
    if existing_disabled:
        logger.info("Existing disabled rules in config: %d", len(existing_disabled))
        overlap = existing_disabled & rules_to_enable
        if overlap:
            logger.info(
                "Rules that would be skipped (disabled in config): %d", len(overlap)
            )

    if verbose:
        logger.debug("Rules to enable (not implemented in ruff):")
        for rule in sorted(rules_to_enable):
            logger.debug("  %s", rule)
        logger.debug("Rules implemented in ruff (will be auto-disabled):")
        for rule in sorted(implemented_in_ruff):
            logger.debug("  %s", rule)
        if existing_disabled:
            logger.debug("Existing disabled rules in config:")
            for rule in sorted(existing_disabled):
                logger.debug("  %s", rule)


def _handle_dry_run(rules_to_enable: set[str], existing_disabled: set[str]) -> None:
    """Handle dry run mode logging.

    Args:
        rules_to_enable: Set of rules that would be enabled (not implemented in ruff).
        existing_disabled: Set of rules that are already disabled in the configuration.

    """
    logger.info("Dry run mode - no changes will be made")
    final_rules = rules_to_enable - existing_disabled
    logger.info("Would enable %d rules (not implemented in ruff)", len(final_rules))
    if existing_disabled & rules_to_enable:
        skipped_count = len(existing_disabled & rules_to_enable)
        logger.info("Would skip %d rules that are disabled in config", skipped_count)


def main() -> int:
    """Run the precommit hook to update pylint configuration.

    Returns:
        Exit code: 0 for success, 1 for failure.

    """
    parser = _setup_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Read config first to check for existing disabled rules
        updater = PyprojectUpdater(args.config_file)
        config = updater.read_config()

        rules_to_enable, implemented_in_ruff, existing_disabled = (
            _extract_rules_and_calculate_changes(config)
        )

        # Get all pylint codes for logging
        all_pylint_codes = rules_to_enable | implemented_in_ruff

        _log_rule_summary(
            all_pylint_codes,
            implemented_in_ruff,
            rules_to_enable,
            existing_disabled,
            verbose=args.verbose,
        )

        if args.dry_run:
            _handle_dry_run(rules_to_enable, existing_disabled)
            return 0

        # Store original enable list for comparison
        original_enable = set(
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("enable", []),
        )

        updated_config = updater.update_pylint_config(config, rules_to_enable)
        updater.write_config(updated_config)

        # Check if there were changes
        final_enable = rules_to_enable - existing_disabled
        if original_enable != final_enable:
            logger.info("Pylint configuration updated successfully")
            logger.info("Enabled %d total rules", len(final_enable))
            if existing_disabled:
                logger.info(
                    "Preserved %d existing disabled rules", len(existing_disabled)
                )
            return 1  # Return 1 to indicate changes were made (for precommit)
        logger.info("No changes needed - configuration is already up to date")
        return 0  # noqa: TRY300

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to update pylint configuration")
        return 1


if __name__ == "__main__":
    sys.exit(main())
