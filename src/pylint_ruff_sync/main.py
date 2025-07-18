"""Main module for pylint-ruff-sync application."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .data_collector import DataCollector
from .message_generator import MessageGenerator
from .pylint_cleaner import PylintCleaner
from .pyproject_updater import PyprojectUpdater
from .rules_cache_manager import RulesCacheManager

if TYPE_CHECKING:
    from .rule import Rules

# Configure logging
logger = logging.getLogger(__name__)


class Application:
    """Main application class for pylint-ruff-sync tool.

    Encapsulates the core functionality and manages component initialization
    to eliminate duplication of class instantiation.
    """

    def __init__(self, *, args: argparse.Namespace) -> None:
        """Initialize the application with parsed command line arguments.

        Args:
            args: Parsed command line arguments from argparse.

        """
        self.args = args

        # Determine cache path
        cache_path = args.cache_path
        if cache_path is None:
            cache_path = Path(__file__).parent / "data" / "ruff_implemented_rules.json"

        self.cache_path = cache_path
        self._cache_manager = RulesCacheManager(cache_path=self.cache_path)
        self._data_collector = DataCollector(cache_manager=self._cache_manager)
        self._rules: Rules | None = None
        self._message_generator: MessageGenerator | None = None

    @property
    def cache_manager(self) -> RulesCacheManager:
        """Get the cache manager instance.

        Returns:
            RulesCacheManager instance.

        """
        return self._cache_manager

    @property
    def data_collector(self) -> DataCollector:
        """Get the data collector instance.

        Returns:
            DataCollector instance.

        """
        return self._data_collector

    @property
    def rules(self) -> Rules:
        """Get all rule information using DataCollector.

        Returns:
            Rules object containing all available pylint rules with ruff data.

        """
        if self._rules is None:
            logger.info("Extracting all rule information")
            self._rules = self._data_collector.collect_rules()

        return self._rules

    def update_cache_from_github(self) -> None:
        """Update the cache from GitHub issue.

        This uses DataCollector to ensure fresh data is collected following
        the proper initialization flow.

        Raises:
            Exception: If cache update fails for any reason.

        """
        logger.info("Updating cache from GitHub...")

        try:
            # Force fresh collection by directly calling the fresh collection method
            all_rules = self._data_collector.collect_fresh_rules()

            # Save to the specified cache path using cache manager
            self._cache_manager.save_rules(rules=all_rules)
            logger.info("Cache updated successfully with %d rules", len(all_rules))

            # Update cached rules
            self._rules = all_rules
        except Exception:
            logger.exception("Failed to update cache")
            raise

    def get_message_generator(self) -> MessageGenerator:
        """Get or create a message generator instance.

        Returns:
            MessageGenerator instance.

        """
        if self._message_generator is None:
            rules = self.rules
            self._message_generator = MessageGenerator(rules=rules)

        return self._message_generator

    def create_pyproject_updater(
        self,
        config_file: Path,
        *,
        dry_run: bool = False,
    ) -> PyprojectUpdater:
        """Create a PyprojectUpdater with the application's rules.

        Args:
            config_file: Path to pyproject.toml file.
            dry_run: Whether to run in dry-run mode.

        Returns:
            PyprojectUpdater instance.

        """
        rules = self.rules
        message_generator = self.get_message_generator() if dry_run else None

        return PyprojectUpdater(
            config_file=config_file,
            dry_run=dry_run,
            message_generator=message_generator,
            rules=rules,
        )

    def run(self) -> int:
        """Run the application with the provided arguments.

        Returns:
            Exit code (0 for success, non-zero for failure).

        """
        try:
            # Check if config file exists early
            if not self.args.config_file.exists():
                logger.error("Configuration file not found: %s", self.args.config_file)
                return 1

            # Handle --update-cache argument
            if self.args.update_cache:
                self.update_cache_from_github()
                return 0

            # Create and configure PyprojectUpdater through the application
            updater = self.create_pyproject_updater(
                config_file=self.args.config_file,
                dry_run=self.args.dry_run,
            )
            updater.update(disable_mypy_overlap=self.args.disable_mypy_overlap)

            # Run PylintCleaner after configuration update if enabled
            if not getattr(self.args, "disable_pylint_cleaner", False):
                project_root = self.args.config_file.parent
                rules = self.rules
                cleaner = PylintCleaner(
                    config_file=self.args.config_file,
                    dry_run=self.args.dry_run,
                    project_root=project_root,
                    rules=rules,
                )
                cleaner.run()
            else:
                logger.info("PylintCleaner disabled via --disable-pylint-cleaner")

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception:
            logger.exception("Unexpected error occurred")
            return 1

        return 0


def _setup_logging(*, verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, enable debug logging.

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser.

    Returns:
        Configured ArgumentParser instance.

    """
    parser = argparse.ArgumentParser(
        description="Synchronize pylint configuration with ruff implementation status",
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config-file",
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml file (default: %(default)s)",
        type=Path,
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
        help="Path to cache file (default: package data location)",
        type=Path,
    )

    parser.add_argument(
        "--disable-pylint-cleaner",
        action="store_true",
        help="Disable the pylint cleaner functionality",
    )

    return parser


def main() -> int:
    """Run the pylint-ruff-sync tool.

    Returns:
        Exit code (0 for success, non-zero for failure).

    """
    parser = _setup_argument_parser()
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)

    # Create application instance and run
    app = Application(args=args)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
