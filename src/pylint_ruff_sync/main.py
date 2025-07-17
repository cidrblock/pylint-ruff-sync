"""Main module for the pylint-ruff-sync tool."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pylint_ruff_sync.data_collector import DataCollector
from pylint_ruff_sync.mypy_overlap import get_mypy_overlap_rules
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.rule import Rule, Rules, RuleSource
from pylint_ruff_sync.toml_file import TomlFile

# Configure logging
logger = logging.getLogger(__name__)


def _setup_logging(*, verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, enable debug logging.

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser.

    Returns:
        Configured ArgumentParser instance.

    """
    parser = argparse.ArgumentParser(
        description="Synchronize pylint configuration with ruff implementation status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update pyproject.toml with optimized pylint configuration
  pylint-ruff-sync

  # Dry run to see what changes would be made
  pylint-ruff-sync --dry-run

  # Update specific config file
  pylint-ruff-sync --config-file custom.toml

  # Enable verbose logging
  pylint-ruff-sync --verbose

  # Update cache from GitHub (requires internet and gh CLI)
  pylint-ruff-sync --update-cache
        """,
    )

    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml file (default: %(default)s)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what changes would be made without modifying files",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )

    parser.add_argument(
        "--disable-mypy-overlap",
        action="store_true",
        help="Disable filtering of rules that overlap with mypy functionality",
    )

    parser.add_argument(
        "--update-cache",
        action="store_true",
        help="Update the local cache from GitHub issue and exit",
    )

    parser.add_argument(
        "--cache-path",
        type=Path,
        help="Path to cache file (default: package data location)",
    )

    return parser


def update_cache_from_github(cache_path: Path) -> None:
    """Update the cache from GitHub issue.

    This uses DataCollector to ensure fresh data is collected following
    the proper initialization flow.

    Args:
        cache_path: Path to cache file.

    Raises:
        Exception: If cache update fails for any reason.

    """
    logger.info("Updating cache from GitHub...")

    # Use DataCollector to get fresh rules (bypassing cache)
    data_collector = DataCollector(cache_path=None)  # Don't use cache for update

    # Force fresh collection by directly calling the fresh collection method
    try:
        all_rules = data_collector.collect_fresh_rules()

        # Save to the specified cache path
        all_rules.save_to_cache(cache_path)
        logger.info("Cache updated successfully with %d rules", len(all_rules))
    except Exception:
        logger.exception("Failed to update cache")
        raise


def _extract_all_rules(cache_path: Path | None = None) -> Rules:
    """Extract and combine all rule information using DataCollector.

    Args:
        cache_path: Optional path to cache file.

    Returns:
        Rules object containing all available pylint rules with ruff data.

    """
    logger.info("Extracting all rule information")

    data_collector = DataCollector(cache_path=cache_path)
    return data_collector.collect_rules()


def _add_user_disabled_rules(
    all_rules: Rules,
    config_file: Path,
) -> Rules:
    """Add user-disabled rules that aren't in the main rule set.

    Args:
        all_rules: Existing Rules object.
        config_file: Path to the pyproject.toml file.

    Returns:
        Updated Rules object with user-disabled rules added.

    """
    # Load existing configuration to check currently disabled rules
    toml_file = TomlFile(config_file)
    current_dict = toml_file.as_dict()
    messages_control = (
        current_dict.get("tool", {}).get("pylint", {}).get("messages_control", {})
    )

    current_disable = messages_control.get("disable", [])
    if not current_disable:
        return all_rules

    # Check for any disabled rules that aren't in our rule set
    for disabled_item in current_disable:
        if disabled_item == "all":
            continue

        existing_rule = all_rules.get_by_identifier(disabled_item)
        if not existing_rule:
            # This is a user-disabled rule we don't know about
            # Add it as an unknown rule
            rule = Rule(
                pylint_id=disabled_item,
                pylint_name=disabled_item if not disabled_item.isupper() else "",
                source=RuleSource.USER_DISABLE,
            )
            all_rules.add_rule(rule)
            logger.debug("Added user-disabled rule: %s", disabled_item)

    return all_rules


def _resolve_rule_identifiers(
    *,
    all_rules: Rules,
    config_file: Path,
    disable_mypy_overlap: bool = False,
) -> tuple[list[Rule], list[str], list[Rule]]:
    """Resolve rule identifiers to determine which rules to enable and disable.

    Args:
        all_rules: Rules object containing all available pylint rules.
        config_file: Path to the pyproject.toml file to check existing configuration.
        disable_mypy_overlap: If False (default), exclude rules that overlap with mypy.

    Returns:
        Tuple of (rules_to_disable, unknown_disabled_rules, rules_to_enable).

    """
    # Add any user-disabled rules that we don't know about
    all_rules = _add_user_disabled_rules(all_rules, config_file)

    # Load existing configuration to check currently disabled and enabled rules
    toml_file = TomlFile(config_file)
    current_dict = toml_file.as_dict()
    messages_control = (
        current_dict.get("tool", {}).get("pylint", {}).get("messages_control", {})
    )

    current_disable = messages_control.get("disable", [])
    current_enable = messages_control.get("enable", [])

    # Convert to sets for easier checking (includes both rule IDs and names)
    current_disable_set = set(current_disable) if current_disable else set()
    current_enable_set = set(current_enable) if current_enable else set()

    # Always identify mypy overlap rules, but filtering depends on disable_mypy_overlap
    # flag
    mypy_overlap_rules = get_mypy_overlap_rules()
    all_rules.update_mypy_overlap_status(mypy_overlap_rules)

    # Get optimized disable list
    rules_to_disable, unknown_disabled_rules = all_rules.get_optimized_disable_list(
        current_disabled=current_disable_set,
        current_enabled=current_enable_set,
        disable_mypy_overlap=disable_mypy_overlap,
    )

    # Get rules to enable
    rules_to_enable = all_rules.get_rules_to_enable(
        current_disabled=current_disable_set,
        current_enabled=current_enable_set,
        disable_mypy_overlap=disable_mypy_overlap,
    )

    disabled_rules_removed = (
        len(current_disable_set) - len(rules_to_disable) - len(unknown_disabled_rules)
    )

    logger.info("Total pylint rules: %d", len(all_rules))
    logger.info(
        "Rules implemented in ruff: %d", len(all_rules.filter_implemented_in_ruff())
    )
    logger.info("Rules to enable (not implemented in ruff): %d", len(rules_to_enable))
    logger.info("Rules to keep disabled: %d", len(rules_to_disable))
    logger.info("Unknown disabled rules preserved: %d", len(unknown_disabled_rules))
    logger.info("Disabled rules removed (optimization): %d", disabled_rules_removed)

    return rules_to_disable, unknown_disabled_rules, rules_to_enable


def _update_pylint_config(
    *,
    config_file: Path,
    rules_to_disable: list[Rule],
    unknown_disabled_rules: list[str],
    rules_to_enable: list[Rule],
    dry_run: bool = False,
) -> None:
    """Update the pylint configuration in pyproject.toml.

    Args:
        config_file: Path to the pyproject.toml file.
        rules_to_disable: List of rules to disable.
        unknown_disabled_rules: List of unknown rule identifiers to keep disabled.
        rules_to_enable: List of rules to enable.
        dry_run: If True, don't actually modify the file.

    """
    logger.info("Updating pylint configuration in %s", config_file)

    # Load and update the TOML file
    toml_file = TomlFile(config_file)
    updater = PyprojectUpdater(toml_file)

    if dry_run:
        logger.info("DRY RUN: Would update configuration with:")
        logger.info("  - Rules to disable: %d", len(rules_to_disable))
        logger.info(
            "  - Unknown disabled rules preserved: %d", len(unknown_disabled_rules)
        )
        logger.info("  - Rules to enable: %d", len(rules_to_enable))
        return

    # Update the configuration
    updater.update_pylint_config(
        disable_rules=rules_to_disable,
        unknown_disabled_rules=unknown_disabled_rules,
        enable_rules=rules_to_enable,
    )

    # Save the file
    toml_file.write()
    logger.info("Configuration updated successfully")


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
            cache_path = (
                args.cache_path if args.cache_path else Path("ruff_implemented.json")
            )
            update_cache_from_github(cache_path)
            return 0

        # Extract all rule information using DataCollector
        all_rules = _extract_all_rules(cache_path=args.cache_path)

        # Resolve which rules to enable/disable
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            _resolve_rule_identifiers(
                all_rules=all_rules,
                config_file=args.config_file,
                disable_mypy_overlap=args.disable_mypy_overlap,
            )
        )

        # Update configuration
        _update_pylint_config(
            config_file=args.config_file,
            rules_to_disable=rules_to_disable,
            unknown_disabled_rules=unknown_disabled_rules,
            rules_to_enable=rules_to_enable,
            dry_run=args.dry_run,
        )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception:
        logger.exception("An unexpected error occurred")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
