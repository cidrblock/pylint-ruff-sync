"""Main module for pylint-ruff-sync precommit hook.

This module contains the core logic for updating pylint configuration
to enable only those rules that haven't been implemented in ruff.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .pylint_extractor import PylintExtractor
from .pyproject_updater import PyprojectUpdater
from .ruff_pylint_extractor import RuffPylintExtractor

if TYPE_CHECKING:
    from .pylint_rule import PylintRule

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


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
) -> tuple[set[str], set[str], set[str], list[PylintRule]]:
    """Extract rules and calculate what changes are needed.

    Args:
        config: The current configuration dictionary to check for existing disabled
            rules.

    Returns:
        A tuple of (rules_to_enable, implemented_in_ruff, existing_disabled,
            all_pylint_rules).

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
    existing_disabled_raw = (
        config.get("tool", {})
        .get("pylint", {})
        .get("messages_control", {})
        .get("disable", [])
    )

    # Resolve disabled rule identifiers (names and codes) to codes
    existing_disabled = pylint_extractor.resolve_rule_identifiers(
        rule_identifiers=existing_disabled_raw, all_rules=all_pylint_rules
    )

    return rules_to_enable, implemented_in_ruff, existing_disabled, all_pylint_rules


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
        updater = PyprojectUpdater(config_file=args.config_file)
        config = updater.read_config()

        rules_to_enable, implemented_in_ruff, existing_disabled, all_pylint_rules = (
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

        # Check if changes are needed before updating
        original_enable = set(
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("enable", []),
        )

        # Calculate what the final enable list would be
        final_enable = rules_to_enable - existing_disabled

        # Only update and write if there are changes
        if original_enable != final_enable:
            updated_config = updater.update_pylint_config(
                config=config,
                rules_to_enable=rules_to_enable,
                existing_disabled=existing_disabled,
                all_rules=all_pylint_rules,
            )
            updater.write_config(updated_config)

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
