"""Main module for the pylint-ruff-sync tool."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pylint_ruff_sync.cache_manager import CacheManager
from pylint_ruff_sync.mypy_overlap import get_mypy_overlap_rules
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.ruff_pylint_extractor import (
    RuffPylintExtractor,
)
from pylint_ruff_sync.toml_file import TomlFile

if TYPE_CHECKING:
    from collections.abc import Callable

    from pylint_ruff_sync.pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RuleContext:
    """Context for processing disabled rules.

    Attributes:
        name_to_id_map: Mapping from rule names to rule IDs.
        id_to_rule_map: Mapping from rule IDs to PylintRule objects.
        ruff_implemented: List of rule codes implemented in ruff.
        mypy_overlaps: Set of rules that overlap with mypy.
        enabled_checker: Function to check if a rule is explicitly enabled.

    """

    name_to_id_map: dict[str, str]
    id_to_rule_map: dict[str, PylintRule]
    ruff_implemented: list[str]
    mypy_overlaps: set[str]
    enabled_checker: Callable[[str, str], bool]


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


def _extract_ruff_implemented_rules() -> list[str]:
    """Extract pylint rule codes that have been implemented in ruff.

    Returns:
        List of pylint rule codes that are implemented in ruff.

    """
    logger.info("Extracting implemented rules from ruff")
    extractor = RuffPylintExtractor()
    return extractor.get_implemented_rules()


def _process_disabled_rules(
    disabled_set: set[str],
    context: RuleContext,
) -> tuple[list[PylintRule], list[str], int]:
    """Process disabled rules to determine which ones should be kept.

    Args:
        disabled_set: Set of currently disabled rule identifiers.
        context: Context containing rule mappings and filters.

    Returns:
        Tuple of (rules_to_disable, unknown_disabled_rules,
        disabled_rules_removed_count).

    """
    rules_to_disable = []
    unknown_disabled_rules = []
    disabled_rules_removed = 0

    for disabled_item in disabled_set:
        if disabled_item == "all":
            continue  # "all" is handled separately by PyprojectUpdater

        # Find the rule ID for this disabled item (could be ID or name)
        rule_id = (
            disabled_item
            if disabled_item in context.id_to_rule_map
            else context.name_to_id_map.get(disabled_item)
        )

        if rule_id is None:
            # Unknown rule - keep it in disable list (could be custom or future rule)
            unknown_disabled_rules.append(disabled_item)
            continue

        rule = context.id_to_rule_map[rule_id]

        # Check if this rule is explicitly enabled (takes precedence)
        explicitly_enabled = context.enabled_checker(rule.rule_id, rule.name)

        if explicitly_enabled:
            # Rule is explicitly enabled - remove from disable list
            disabled_rules_removed += 1
            continue

        # Only keep disabled rule if it would otherwise be enabled
        # (not implemented in ruff AND not overlapping with mypy)
        if (
            rule_id not in context.ruff_implemented  # Not implemented in ruff
            and rule_id not in context.mypy_overlaps  # Not overlapping with mypy
        ):
            rules_to_disable.append(rule)
        else:
            # Rule is implemented in ruff or overlaps with mypy - no point keeping
            # it disabled
            disabled_rules_removed += 1

    return rules_to_disable, unknown_disabled_rules, disabled_rules_removed


def _resolve_rule_identifiers(
    *,
    all_rules: list[PylintRule],
    implemented_codes: list[str],
    config_file: Path,
    disable_mypy_overlap: bool = False,
) -> tuple[list[PylintRule], list[str], list[PylintRule]]:
    """Resolve rule identifiers to determine which rules to enable and disable.

    Args:
        all_rules: List of all available pylint rules.
        implemented_codes: List of rule codes implemented in ruff.
        config_file: Path to the pyproject.toml file to check existing disabled rules.
        disable_mypy_overlap: If False (default), exclude rules that overlap with mypy.

    Returns:
        Tuple of (rules_to_disable, unknown_disabled_rules, rules_to_enable).

    """
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

    # Get mypy overlap rules if filtering is enabled
    mypy_overlap_rules = set() if disable_mypy_overlap else get_mypy_overlap_rules()

    # Create lookup maps for rule names to rule IDs and vice versa
    rule_name_to_id = {rule.name: rule.rule_id for rule in all_rules}
    rule_id_to_rule = {rule.rule_id: rule for rule in all_rules}

    # Helper function to check if a rule is explicitly enabled (by ID or name)
    def is_explicitly_enabled(rule_id: str, rule_name: str) -> bool:
        return rule_id in current_enable_set or rule_name in current_enable_set

    # Get rules to enable: not implemented in ruff AND (not disabled OR explicitly
    # enabled) AND not mypy overlap
    rules_to_enable = []
    for rule in all_rules:
        if rule.rule_id in implemented_codes:
            # Skip rules implemented in ruff - they shouldn't be enabled
            continue

        if rule.rule_id in mypy_overlap_rules:
            # Skip rules that overlap with mypy (unless mypy filtering is disabled)
            continue

        # Check if rule is explicitly enabled (takes precedence over disable)
        explicitly_enabled = is_explicitly_enabled(rule.rule_id, rule.name)

        # Check if rule is disabled (by ID or name)
        disabled_by_id = rule.rule_id in current_disable_set
        disabled_by_name = rule.name in current_disable_set

        if explicitly_enabled or (not disabled_by_id and not disabled_by_name):
            # Enable if: explicitly enabled OR not disabled at all
            rules_to_enable.append(rule)

    # Process disabled rules to determine which ones to keep
    context = RuleContext(
        name_to_id_map=rule_name_to_id,
        id_to_rule_map=rule_id_to_rule,
        ruff_implemented=implemented_codes,
        mypy_overlaps=mypy_overlap_rules,
        enabled_checker=is_explicitly_enabled,
    )
    rules_to_disable, unknown_disabled_rules, disabled_rules_removed = (
        _process_disabled_rules(
            disabled_set=current_disable_set,
            context=context,
        )
    )

    # Log mypy overlap filtering if enabled
    if not disable_mypy_overlap:
        mypy_filtered_count = sum(
            1
            for rule in all_rules
            if rule.rule_id in mypy_overlap_rules
            and rule.rule_id not in implemented_codes
            and not is_explicitly_enabled(rule.rule_id, rule.name)
            and rule.rule_id not in current_disable_set
            and rule.name not in current_disable_set
        )
        if mypy_filtered_count > 0:
            logger.info(
                "Excluded %d rules that overlap with mypy functionality",
                mypy_filtered_count,
            )
            logger.info("Use --disable-mypy-overlap to include these rules")

    # Log disable list optimization
    if disabled_rules_removed > 0:
        logger.info(
            "Removed %d unnecessary disabled rules (implemented in ruff, overlap "
            "with mypy, or explicitly enabled)",
            disabled_rules_removed,
        )
        logger.info("This helps reduce your disable list over time")

    return rules_to_disable, unknown_disabled_rules, rules_to_enable


def _update_pylint_config(
    *,
    config_file: Path,
    rules_to_disable: list[PylintRule],
    unknown_disabled_rules: list[str],
    rules_to_enable: list[PylintRule],
    dry_run: bool = False,
) -> bool:
    """Update the pylint configuration in pyproject.toml.

    Args:
        config_file: Path to the pyproject.toml file.
        rules_to_disable: List of rules to disable.
        unknown_disabled_rules: List of unknown rule identifiers to keep disabled.
        rules_to_enable: List of rules to enable.
        dry_run: If True, only show what would be changed without writing.

    Returns:
        True if configuration was updated (or would be updated in dry-run mode).

    """
    logger.info("Updating pylint configuration...")

    if dry_run:
        logger.info("DRY RUN: Would update configuration with:")
        logger.info("  Rules to disable: %d", len(rules_to_disable))
        logger.info("  Unknown rules to keep disabled: %d", len(unknown_disabled_rules))
        logger.info("  Rules to enable: %d", len(rules_to_enable))
        return True

    # Load the TOML file and create updater
    toml_file = TomlFile(config_file)
    updater = PyprojectUpdater(toml_file=toml_file)

    # Update the configuration
    updater.update_pylint_config(
        disable_rules=rules_to_disable,
        unknown_disabled_rules=unknown_disabled_rules,
        enable_rules=rules_to_enable,
    )

    # Write the updated configuration
    toml_file.write()

    logger.info("Updated configuration written to %s", config_file)
    logger.info("Pylint configuration updated successfully")
    logger.info("Enabled %d total rules", len(rules_to_enable))

    return True


def update_cache_from_github(cache_path: Path) -> None:
    """Update the cached ruff implementation data from GitHub.

    Args:
        cache_path: Path to the cache file.

    """
    logger.info("Updating cache from GitHub...")
    extractor = RuffPylintExtractor()
    cache_manager = CacheManager(cache_path=cache_path, extractor=extractor)
    result = cache_manager.update_cache()

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
        "version": result.version,
    }

    print(json.dumps(summary, indent=2, sort_keys=True))  # noqa: T201

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
            update_cache_from_github(
                args.cache_path if args.cache_path else Path("ruff_implemented.json")
            )
            return 0

        # Extract all pylint rules
        all_rules = _extract_all_pylint_rules()
        logger.info("Found %d total pylint rules", len(all_rules))

        # Extract implemented rules from ruff
        ruff_implemented = _extract_ruff_implemented_rules()
        logger.info("Found %d rules implemented in ruff", len(ruff_implemented))

        # Resolve which rules to enable/disable
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            _resolve_rule_identifiers(
                all_rules=all_rules,
                implemented_codes=ruff_implemented,
                config_file=args.config_file,
                disable_mypy_overlap=args.disable_mypy_overlap,
            )
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
            unknown_disabled_rules=unknown_disabled_rules,
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
