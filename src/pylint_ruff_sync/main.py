"""Main module for pylint-ruff-sync precommit hook.

This module contains the core logic for updating pylint configuration
to enable only those rules that haven't been implemented in ruff.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .pylint_extractor import PylintExtractor
from .pyproject_updater import PyprojectUpdater
from .ruff_pylint_extractor import RuffPylintExtractor
from .toml_editor import TomlFile

if TYPE_CHECKING:
    from .pylint_rule import PylintRule

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser.

    Returns:
        Configured argument parser.

    """
    parser = argparse.ArgumentParser(
        description=(
            "Update pylint configuration to enable only rules not implemented in ruff"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml file (default: pyproject.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def _configure_logging(*, verbose: bool) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: Whether to enable verbose logging.

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger().setLevel(level)
    logger.setLevel(level)


def _extract_pylint_rules() -> list[PylintRule]:
    """Extract all pylint rules.

    Returns:
        List of all pylint rules.

    Raises:
        RuntimeError: If pylint rule extraction fails.

    """
    try:
        extractor = PylintExtractor()
        return extractor.extract_all_rules()
    except Exception as e:
        msg = f"Failed to extract pylint rules: {e}"
        raise RuntimeError(msg) from e


def _extract_ruff_implemented_rules() -> set[str]:
    """Extract rules implemented in ruff.

    Returns:
        Set of rule codes implemented in ruff.

    Raises:
        RuntimeError: If ruff rule extraction fails.

    """
    try:
        extractor = RuffPylintExtractor()
        return extractor.extract_implemented_rules()
    except Exception as e:
        msg = f"Failed to extract ruff-implemented rules: {e}"
        raise RuntimeError(msg) from e


def _categorize_rules(
    all_rules: list[PylintRule],
    ruff_implemented: set[str],
    toml_file: TomlFile,
) -> tuple[list[PylintRule], list[PylintRule]]:
    """Categorize rules into those to disable and enable.

    Args:
        all_rules: List of all pylint rules.
        ruff_implemented: Set of rule codes implemented in ruff.
        toml_file: TomlFile instance for checking current config.

    Returns:
        Tuple of (disable_rules, enable_rules).

    """
    # Get currently disabled rules from the file
    current_dict = toml_file.as_dict()
    current_disable = (
        current_dict.get("tool", {})
        .get("pylint", {})
        .get("messages_control", {})
        .get("disable", [])
    )

    # Convert to set for easier manipulation
    current_disable_set = set(current_disable) if current_disable else set()

    # No rules to disable - we only add "all" and keep existing disabled rules
    disable_rules: list[PylintRule] = []

    # Rules to enable: those NOT implemented in ruff and not explicitly disabled by user
    # Check both rule ID and rule name when determining if already disabled
    enable_rules = [
        rule
        for rule in all_rules
        if rule.rule_id not in ruff_implemented
        and rule.rule_id not in current_disable_set
        and rule.name not in current_disable_set
    ]

    return disable_rules, enable_rules


def _update_config(
    toml_file: TomlFile,
    disable_rules: list[PylintRule],
    enable_rules: list[PylintRule],
    *,
    dry_run: bool,
) -> None:
    """Update the pylint configuration.

    Args:
        toml_file: TomlFile instance to update.
        disable_rules: Rules to disable.
        enable_rules: Rules to enable.
        dry_run: Whether this is a dry run.

    """
    if dry_run:
        logger.info("DRY RUN: Would update configuration with:")
        logger.info("  Rules to disable: %d", len(disable_rules))
        logger.info("  Rules to enable: %d", len(enable_rules))

        if disable_rules:
            logger.info(
                "  Sample disable rules: %s",
                [rule.rule_id for rule in disable_rules[:5]],
            )
        if enable_rules:
            logger.info(
                "  Sample enable rules: %s", [rule.rule_id for rule in enable_rules[:5]]
            )
        return

    # Update the configuration
    updater = PyprojectUpdater(toml_file)
    updater.update_pylint_config(disable_rules, enable_rules)
    updater.write_config()

    logger.info("Configuration updated successfully")
    logger.info("  Rules disabled: %d", len(disable_rules))
    logger.info("  Rules enabled: %d", len(enable_rules))


def main() -> int:
    """Run the pylint-ruff-sync tool.

    Returns:
        Exit code (0 for success, 1 for failure).

    """
    parser = _setup_argument_parser()
    args = parser.parse_args()

    _configure_logging(verbose=args.verbose)

    try:
        # Validate config file path
        if not args.config.exists():
            logger.error("Configuration file not found: %s", args.config)
            return 1

        # Load the TOML file
        toml_file = TomlFile(args.config)

        # Extract rules
        logger.info("Extracting pylint rules...")
        all_rules = _extract_pylint_rules()
        logger.info("Found %d total pylint rules", len(all_rules))

        logger.info("Extracting ruff-implemented rules...")
        ruff_implemented = _extract_ruff_implemented_rules()
        logger.info("Found %d rules implemented in ruff", len(ruff_implemented))

        # Categorize rules
        disable_rules, enable_rules = _categorize_rules(
            all_rules, ruff_implemented, toml_file
        )

        # Update configuration
        _update_config(toml_file, disable_rules, enable_rules, dry_run=args.dry_run)

    except Exception as e:
        logger.exception("Failed to update pylint configuration: %s", e)
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
