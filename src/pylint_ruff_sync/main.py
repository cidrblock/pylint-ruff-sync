"""Main module for the pylint-ruff-sync tool."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pylint_ruff_sync.data_collector import DataCollector
from pylint_ruff_sync.message_generator import MessageGenerator
from pylint_ruff_sync.pyproject_updater import PyprojectUpdater
from pylint_ruff_sync.rules_cache_manager import RulesCacheManager

if TYPE_CHECKING:
    from pylint_ruff_sync.rule import Rules

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

    # Create cache manager for updating
    cache_manager = RulesCacheManager(cache_path)

    # Use DataCollector to get fresh rules (bypassing cache)
    data_collector = DataCollector(cache_manager=cache_manager)

    # Force fresh collection by directly calling the fresh collection method
    try:
        all_rules = data_collector.collect_fresh_rules()

        # Save to the specified cache path using cache manager
        cache_manager.save_rules(all_rules)
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

    # Determine cache path
    if cache_path is None:
        cache_path = Path(__file__).parent / "data" / "ruff_implemented_rules.json"

    # Create cache manager
    cache_manager = RulesCacheManager(cache_path)

    # Create data collector with cache manager
    data_collector = DataCollector(cache_manager=cache_manager)
    return data_collector.collect_rules()


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

        # Extract all rule information using DataCollector with cache manager
        all_rules = _extract_all_rules(cache_path=args.cache_path)

        # Create MessageGenerator with rules for potential dry-run messages
        message_generator = MessageGenerator(rules=all_rules) if args.dry_run else None

        # Update the configuration
        updater = PyprojectUpdater(
            rules=all_rules,
            config_file=args.config_file,
            dry_run=args.dry_run,
            message_generator=message_generator,
        )
        updater.update(disable_mypy_overlap=args.disable_mypy_overlap)

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
