"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .toml_file import SimpleArrayWithComments, TomlFile

if TYPE_CHECKING:
    from .pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration.

    This class works with a TomlFile to update pylint configuration in-memory,
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

    def __init__(self, toml_file: TomlFile) -> None:
        """Initialize the PyprojectUpdater.

        Args:
            toml_file: TomlFile instance to work with.

        """
        self.toml_file = toml_file

    def update_pylint_config(
        self,
        disable_rules: list[PylintRule],
        unknown_disabled_rules: list[str],
        enable_rules: list[PylintRule],
    ) -> None:
        """Update the pylint configuration with disable and enable rules.

        This method first updates the disable array (ensuring "all" is included),
        then updates the enable array with URL comments.

        Args:
            disable_rules: List of rules to disable.
            unknown_disabled_rules: List of unknown rule identifiers to keep disabled.
            enable_rules: List of rules to enable.

        """
        # Step 1: Update disable array with "all" and collected disable rules
        self._update_disable_array(disable_rules, unknown_disabled_rules)

        # Step 2: Update enable array with URL comments
        self._update_enable_array(enable_rules)

    def _update_disable_array(
        self, disable_rules: list[PylintRule], unknown_disabled_rules: list[str]
    ) -> None:
        """Update the disable array with "all", disable rules, and unknown rules.

        Args:
            disable_rules: List of rules to disable.
            unknown_disabled_rules: List of unknown rule identifiers to keep disabled.

        """
        # Create set to avoid duplicates and ensure "all" is included
        disable_set = {"all"}
        disable_set.update(rule.rule_id for rule in disable_rules)
        disable_set.update(unknown_disabled_rules)

        # Update the disable array with sorted list
        disable_list = sorted(disable_set)
        self.toml_file.update_section_array(
            section_path="tool.pylint.messages_control",
            key="disable",
            array_data=disable_list,
        )

    def _update_enable_array(self, enable_rules: list[PylintRule]) -> None:
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
        enable_items = [rule.rule_id for rule in enable_rules]
        enable_comments = {
            rule.rule_id: self._generate_url_comment(rule) for rule in enable_rules
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

    def _generate_url_comment(self, rule: PylintRule) -> str:
        """Generate a URL comment for a pylint rule.

        Args:
            rule: The pylint rule to generate a comment for.

        Returns:
            URL comment string.

        """
        category = self.CATEGORY_MAP.get(rule.rule_id[0], "unknown")
        return f"https://pylint.readthedocs.io/en/stable/user_guide/messages/{category}/{rule.name}.html"

    def write_config(self) -> None:
        """Write the updated configuration to the file."""
        self.toml_file.write()
