"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .rule import Rule, RuleSource
from .toml_file import SimpleArrayWithComments, TomlFile

if TYPE_CHECKING:
    from pathlib import Path

    from .rule import Rules

# Configure logging
logger = logging.getLogger(__name__)


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration.

    This class manages a TomlFile internally to update pylint configuration,
    automatically determining which rules to enable/disable based on ruff
    implementation status and current configuration.

    """

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

    def update(self, *, disable_mypy_overlap: bool = False) -> None:
        """Update the pylint configuration with optimized rule settings.

        Automatically determines which rules to enable/disable based on ruff
        implementation status and current configuration.

        Args:
            disable_mypy_overlap: If False (default), exclude rules that overlap
                with mypy.

        """
        logger.info("Updating pylint configuration in %s", self.config_file)

        # Resolve which rules to enable/disable
        rules_to_disable, unknown_disabled_rules, rules_to_enable = (
            self._resolve_rule_identifiers(disable_mypy_overlap=disable_mypy_overlap)
        )

        if self.dry_run:
            logger.info("DRY RUN: Would update configuration with:")
            logger.info("  - Rules to disable: %d", len(rules_to_disable))
            logger.info(
                "  - Unknown disabled rules preserved: %d", len(unknown_disabled_rules)
            )
            logger.info("  - Rules to enable: %d", len(rules_to_enable))
            return

        # Step 1: Update disable array with "all" and collected disable rules
        self._update_disable_array(rules_to_disable, unknown_disabled_rules)

        # Step 2: Update enable array with URL comments
        self._update_enable_array(rules_to_enable)

        # Step 3: Save the file
        self.save()
        logger.info("Configuration updated successfully")

    def _resolve_rule_identifiers(
        self, *, disable_mypy_overlap: bool = False
    ) -> tuple[list[Rule], list[str], list[Rule]]:
        """Resolve rule identifiers to determine which rules to enable and disable.

        Args:
            disable_mypy_overlap: If False (default), exclude rules that overlap
                with mypy.

        Returns:
            Tuple of (rules_to_disable, unknown_disabled_rules, rules_to_enable).

        """
        # Add any user-disabled rules that we don't know about
        self._add_user_disabled_rules()

        # Load existing configuration to check currently disabled and enabled rules
        current_dict = self.toml_file.as_dict()
        messages_control = (
            current_dict.get("tool", {}).get("pylint", {}).get("messages_control", {})
        )

        current_disable = messages_control.get("disable", [])
        current_enable = messages_control.get("enable", [])

        # Convert to sets for easier checking (includes both rule IDs and names)
        current_disable_set = set(current_disable) if current_disable else set()
        current_enable_set = set(current_enable) if current_enable else set()

        # Get optimized disable list
        rules_to_disable, unknown_disabled_rules = (
            self.rules.get_optimized_disable_list(
                current_disabled=current_disable_set,
                current_enabled=current_enable_set,
                disable_mypy_overlap=disable_mypy_overlap,
            )
        )

        # Get rules to enable
        rules_to_enable = self.rules.get_rules_to_enable(
            current_disabled=current_disable_set,
            current_enabled=current_enable_set,
            disable_mypy_overlap=disable_mypy_overlap,
        )

        disabled_rules_removed = (
            len(current_disable_set)
            - len(rules_to_disable)
            - len(unknown_disabled_rules)
        )

        logger.info("Total pylint rules: %d", len(self.rules))
        logger.info(
            "Rules implemented in ruff: %d",
            len(self.rules.filter_implemented_in_ruff()),
        )
        logger.info(
            "Rules to enable (not implemented in ruff): %d", len(rules_to_enable)
        )
        logger.info("Rules to keep disabled: %d", len(rules_to_disable))
        logger.info("Unknown disabled rules preserved: %d", len(unknown_disabled_rules))
        logger.info("Disabled rules removed (optimization): %d", disabled_rules_removed)

        return rules_to_disable, unknown_disabled_rules, rules_to_enable

    def _add_user_disabled_rules(self) -> None:
        """Add user-disabled rules that aren't in the main rule set."""
        # Load existing configuration to check currently disabled rules
        current_dict = self.toml_file.as_dict()
        messages_control = (
            current_dict.get("tool", {}).get("pylint", {}).get("messages_control", {})
        )

        current_disable = messages_control.get("disable", [])
        if not current_disable:
            return

        # Check for any disabled rules that aren't in our rule set
        for disabled_item in current_disable:
            if disabled_item == "all":
                continue

            existing_rule = self.rules.get_by_identifier(disabled_item)
            if not existing_rule:
                # This is a user-disabled rule we don't know about
                # Add it as an unknown rule
                rule = Rule(
                    pylint_id=disabled_item,
                    pylint_name=disabled_item if not disabled_item.isupper() else "",
                    source=RuleSource.USER_DISABLE,
                )
                self.rules.add_rule(rule)
                logger.debug("Added user-disabled rule: %s", disabled_item)

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
        # Collect all disable items: "all" + rule IDs + unknown rules
        disable_set = {"all"}
        disable_set.update(rule.pylint_id for rule in disable_rules)
        disable_set.update(unknown_disabled_rules)

        # Sort for consistent output
        disable_list = sorted(disable_set)

        self.toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=disable_list,
        )

    def _update_enable_array(self, enable_rules: list[Rule]) -> None:
        """Update the enable array with rules and URL comments.

        Args:
            enable_rules: List of rules to enable.

        """
        if not enable_rules:
            # Ensure enable array exists but is empty
            self.toml_file.update_section_array(
                section_path="tool.pylint.messages_control",
                key="enable",
                array_data=[],
            )
            return

        # Create SimpleArrayWithComments with URL comments from rule data
        enable_items = [rule.pylint_id for rule in enable_rules]
        enable_comments = {
            rule.pylint_id: rule.pylint_docs_url or "" for rule in enable_rules
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
