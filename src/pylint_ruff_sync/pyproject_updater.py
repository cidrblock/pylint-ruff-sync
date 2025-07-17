"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .toml_file import SimpleArrayWithComments, TomlFile

if TYPE_CHECKING:
    from pathlib import Path

    from .rule import Rule, Rules

# Configure logging
logger = logging.getLogger(__name__)


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration.

    This class manages a TomlFile internally to update pylint configuration,
    first updating the disable array with "all", then updating the enable array
    based on the collected disable rules.

    Attributes:
        CATEGORY_MAP: Map rule category codes to URL categories.

    """

    # Map rule category codes to URL categories
    CATEGORY_MAP: ClassVar[dict[str, str]] = {
        "C": "convention",
        "E": "error",
        "W": "warning",
        "R": "refactor",
        "I": "info",
        "F": "fatal",
    }

    def __init__(
        self, rules: Rules, config_file: Path, *, dry_run: bool = False
    ) -> None:
        """Initialize the PyprojectUpdater.

        Args:
            rules: Rules instance containing all rule information.
            config_file: Path to the pyproject.toml file to update.
            dry_run: If True, don't actually modify the file, just log what would
                be done.

        """
        self.rules = rules
        self.config_file = config_file
        self.dry_run = dry_run
        self.toml_file = TomlFile(config_file)

    def update_pylint_config(
        self,
        disable_rules: list[Rule],
        unknown_disabled_rules: list[str],
        enable_rules: list[Rule],
    ) -> None:
        """Update the pylint configuration with disable and enable rules.

        This method first updates the disable array (ensuring "all" is included),
        then updates the enable array with URL comments.

        Args:
            disable_rules: List of rules to disable.
            unknown_disabled_rules: List of unknown rule identifiers to keep disabled.
            enable_rules: List of rules to enable.

        """
        logger.info("Updating pylint configuration in %s", self.config_file)

        if self.dry_run:
            logger.info("DRY RUN: Would update configuration with:")
            logger.info("  - Rules to disable: %d", len(disable_rules))
            logger.info(
                "  - Unknown disabled rules preserved: %d", len(unknown_disabled_rules)
            )
            logger.info("  - Rules to enable: %d", len(enable_rules))
            return

        # Step 1: Update disable array with "all" and collected disable rules
        self._update_disable_array(disable_rules, unknown_disabled_rules)

        # Step 2: Update enable array with URL comments
        self._update_enable_array(enable_rules)

        # Step 3: Save the file
        self.save()
        logger.info("Configuration updated successfully")

    def save(self) -> None:
        """Save the updated configuration to the file."""
        if self.dry_run:
            logger.debug("DRY RUN: Would save configuration to %s", self.config_file)
            return

        self.toml_file.write()
        logger.debug("Saved configuration to %s", self.config_file)

    def _update_disable_array(
        self, disable_rules: list[Rule], unknown_disabled_rules: list[str]
    ) -> None:
        """Update the disable array with "all", disable rules, and unknown rules.

        Args:
            disable_rules: List of rules to disable.
            unknown_disabled_rules: List of unknown rule identifiers to keep disabled.

        """
        # Create set to avoid duplicates and ensure "all" is included
        disable_set = {"all"}
        disable_set.update(rule.pylint_id for rule in disable_rules)
        disable_set.update(unknown_disabled_rules)

        # Update the disable array with sorted list
        disable_list = sorted(disable_set)
        self.toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=disable_list,
        )

    def _update_enable_array(self, enable_rules: list[Rule]) -> None:
        """Update the enable array with URL comments.

        Args:
            enable_rules: List of rules to enable.

        """
        if not enable_rules:
            # If no rules to enable, set empty array
            self.toml_file.update_section_array(
                section_path="tool.pylint.messages_control",
                key="enable",
                array_data=[],
            )
            return

        # Create SimpleArrayWithComments with URL comments
        enable_items = [rule.pylint_id for rule in enable_rules]
        enable_comments = {
            rule.pylint_id: self._generate_url_comment(rule) for rule in enable_rules
        }

        enable_array = SimpleArrayWithComments(
            items=enable_items,
            comments=enable_comments,
        )

        self.toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="enable",
            array_data=enable_array,
        )

    def _get_current_disable_array(self, current_dict: dict[str, Any]) -> list[str]:
        """Get the current disable array from the file dictionary.

        Args:
            current_dict: Current file content as dictionary.

        Returns:
            List of currently disabled rules.

        """
        try:
            disable_value = (
                current_dict.get("tool", {})
                .get("pylint", {})
                .get("messages_control", {})
                .get("disable", [])
            )
            # Ensure we return a list of strings
            if isinstance(disable_value, list):
                return [str(item) for item in disable_value]
            return []  # noqa: TRY300
        except (KeyError, TypeError):
            return []

    def _generate_url_comment(self, rule: Rule) -> str:
        """Generate a URL comment for a pylint rule.

        Args:
            rule: Rule object containing rule information.

        Returns:
            URL comment string for the rule.

        """
        # Use the pylint_docs_url if available, otherwise generate one
        if rule.pylint_docs_url:
            return rule.pylint_docs_url

        # Fallback: generate URL from rule category and name
        if rule.pylint_category and rule.pylint_name:
            category_name = self.CATEGORY_MAP.get(rule.pylint_category, "")
            if category_name:
                return (
                    f"https://pylint.readthedocs.io/en/stable/user_guide/messages/"
                    f"{category_name}/{rule.pylint_name}.html"
                )

        # Final fallback: generic pylint docs
        return "https://pylint.readthedocs.io/en/stable/user_guide/messages/"
