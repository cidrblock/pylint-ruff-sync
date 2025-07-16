"""Main module for the pylint-ruff-sync tool."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pylint_ruff_sync.mypy_overlap import get_mypy_overlap_rules
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import (
    RuffPylintExtractor,
)
from pylint_ruff_sync.toml_file import TomlFile

if TYPE_CHECKING:
    from pylint_ruff_sync.pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser.

    Returns:
        Configured argument parser.

    """
    parser = argparse.ArgumentParser(
        description="Sync pylint configuration with ruff implementation status"
    )

    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml file (default: %(default)s)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making modifications",
    )

    parser.add_argument(
        "--disable-mypy-overlap",
        action="store_true",
        help="Disable filtering of pylint rules that overlap with mypy functionality. "
        "By default, rules that mypy already covers are excluded from being enabled.",
    )

    parser.add_argument(
        "--update-cache",
        action="store_true",
        help="Update the cached ruff implementation data from GitHub and exit",
    )

    parser.add_argument(
        "--cache-path",
        type=Path,
        help="Path to cache file for offline usage (optional)",
    )

    return parser


def _setup_logging(*, verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: Enable debug level logging if True.

    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


def _extract_all_pylint_rules() -> list[PylintRule]:
    """Extract all available pylint rules from the configuration.

    Returns:
        List of PylintRule objects representing all available pylint rules.

    """
    logger.info("Extracting pylint rules from 'pylint --list-msgs'")
    extractor = PylintExtractor()
    return extractor.extract_all_rules()


def _extract_ruff_implemented_rules(cache_path: Path | None = None) -> list[str]:
    """Extract the list of pylint rules implemented in ruff from GitHub.

    Args:
        cache_path: Path to a local cache file to use instead of fetching from GitHub.

    Returns:
        List of pylint rule codes that are implemented in ruff.

    """
    logger.info("Extracting implemented rules from ruff")
    extractor = RuffPylintExtractor(cache_path=cache_path)
    return extractor.get_implemented_rules()


def _resolve_rule_identifiers(
    *,
    all_rules: list[PylintRule],
    implemented_codes: list[str],
    config_file: Path,
    disable_mypy_overlap: bool = False,
) -> tuple[list[PylintRule], list[PylintRule]]:
    """Resolve rule identifiers to determine which rules to enable and disable.

    Args:
        all_rules: List of all available pylint rules.
        implemented_codes: List of rule codes implemented in ruff.
        config_file: Path to the pyproject.toml file to check existing disabled rules.
        disable_mypy_overlap: If False (default), exclude rules that overlap with mypy.

    Returns:
        Tuple of (rules_to_disable, rules_to_enable).

    """
    # Load existing configuration to check currently disabled rules
    toml_file = TomlFile(config_file)
    current_dict = toml_file.as_dict()
    current_disable = (
        current_dict.get("tool", {})
        .get("pylint", {})
        .get("messages_control", {})
        .get("disable", [])
    )

    # Convert to set for easier checking (includes both rule IDs and names)
    current_disable_set = set(current_disable) if current_disable else set()

    # Get mypy overlap rules if filtering is enabled
    mypy_overlap_rules = set() if disable_mypy_overlap else get_mypy_overlap_rules()

    # Always disable "all" to prevent duplicate rule execution (no PylintRule needed)
    rules_to_disable: list[PylintRule] = []

    # Get rules to enable (not implemented in ruff AND not explicitly disabled by user)
    rules_to_enable = [
        rule
        for rule in all_rules
        if (
            rule.rule_id not in implemented_codes  # Not implemented in ruff
            and rule.rule_id not in current_disable_set  # Not disabled by ID
            and rule.name not in current_disable_set  # Not disabled by name
            and rule.rule_id not in mypy_overlap_rules  # Not overlapping with mypy
        )
    ]

    # Log mypy overlap filtering if enabled
    if not disable_mypy_overlap:
        mypy_filtered_count = sum(
            1
            for rule in all_rules
            if rule.rule_id in mypy_overlap_rules
            and rule.rule_id not in implemented_codes
            and rule.rule_id not in current_disable_set
            and rule.name not in current_disable_set
        )
        if mypy_filtered_count > 0:
            logger.info(
                "Excluded %d rules that overlap with mypy functionality",
                mypy_filtered_count,
            )
            logger.info("Use --disable-mypy-overlap to include these rules")

    return rules_to_disable, rules_to_enable


def _update_pylint_config(
    *,
    config_file: Path,
    rules_to_disable: list[PylintRule],
    rules_to_enable: list[PylintRule],
    dry_run: bool = False,
) -> bool:
    """Update the pylint configuration in pyproject.toml.

    Args:
        config_file: Path to the pyproject.toml file.
        rules_to_disable: List of rules to disable.
        rules_to_enable: List of rules to enable.
        dry_run: If True, only show what would be changed without writing.

    Returns:
        True if configuration was updated (or would be updated in dry-run mode).

    """
    logger.info("Updating pylint configuration...")

    if dry_run:
        logger.info("DRY RUN: Would update configuration with:")
        logger.info("  Rules to disable: %d", len(rules_to_disable))
        logger.info("  Rules to enable: %d", len(rules_to_enable))
        return True

    # Load the TOML file and create updater
    toml_file = TomlFile(config_file)
    updater = PyprojectUpdater(toml_file=toml_file)

    # Update the configuration
    updater.update_pylint_config(
        disable_rules=rules_to_disable,
        enable_rules=rules_to_enable,
    )

    # Write the updated configuration
    toml_file.write()

    logger.info("Updated configuration written to %s", config_file)
    logger.info("Pylint configuration updated successfully")
    logger.info("Enabled %d total rules", len(rules_to_enable))

    return True


def _update_cache(cache_path: Path) -> None:
    """Update the cached ruff implementation data from GitHub.

    Args:
        cache_path: Path to the cache file.

    """
    logger.info("Updating cache from GitHub...")
    extractor = RuffPylintExtractor(cache_path=cache_path)
    result = extractor.update_cache()

    # Emit JSON summary for GitHub Actions consumption
    summary = {
        "has_changes": result.has_changes,
        "rules_added": result.rules_added,
        "rules_removed": result.rules_removed,
        "added_count": len(result.rules_added),
        "removed_count": len(result.rules_removed),
        "total_rules": result.total_rules,
        "release_notes": result.release_notes,
        "commit_message": result.commit_message,
        "pr_message": result.pr_message,
    }

    print("=== CACHE_UPDATE_RESULT ===")  # noqa: T201
    print(json.dumps(summary, indent=2, sort_keys=True))  # noqa: T201
    print("=== END_CACHE_UPDATE_RESULT ===")  # noqa: T201

    if result.has_changes:
        logger.info(
            "Cache updated successfully with %d changes (+%d -%d)",
            len(result.rules_added) + len(result.rules_removed),
            len(result.rules_added),
            len(result.rules_removed),
        )
    else:
        logger.info("Cache updated successfully - no rule changes detected")


def main() -> int:
    """Run the pylint-ruff-sync tool.

    Returns:
        Exit code (0 for success, non-zero for failure).

    """
    parser = _setup_argument_parser()
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)

    try:
        # Check if config file exists early
        if not args.config_file.exists():
            logger.error("Configuration file not found: %s", args.config_file)
            return 1

        # Handle --update-cache argument
        if args.update_cache:
            _update_cache(
                args.cache_path if args.cache_path else Path("ruff_implemented.json")
            )
            return 0

        # Extract all pylint rules
        all_rules = _extract_all_pylint_rules()
        logger.info("Found %d total pylint rules", len(all_rules))

        # Extract implemented rules from ruff
        ruff_implemented = _extract_ruff_implemented_rules(args.cache_path)
        logger.info("Found %d rules implemented in ruff", len(ruff_implemented))

        # Resolve which rules to enable/disable
        rules_to_disable, rules_to_enable = _resolve_rule_identifiers(
            all_rules=all_rules,
            implemented_codes=ruff_implemented,
            config_file=args.config_file,
            disable_mypy_overlap=args.disable_mypy_overlap,
        )

        logger.info("Total pylint rules: %d", len(all_rules))
        logger.info("Rules implemented in ruff: %d", len(ruff_implemented))
        logger.info(
            "Rules to enable (not implemented in ruff): %d", len(rules_to_enable)
        )

        # Update configuration
        _update_pylint_config(
            config_file=args.config_file,
            rules_to_disable=rules_to_disable,
            rules_to_enable=rules_to_enable,
            dry_run=args.dry_run,
        )

    except FileNotFoundError:
        logger.exception("Configuration file not found")
        return 1
    except ValueError:
        logger.exception("Invalid configuration")
        return 1
    except Exception:
        logger.exception("An unexpected error occurred")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
