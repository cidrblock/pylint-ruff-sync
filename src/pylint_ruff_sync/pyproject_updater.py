"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .toml_editor import SimpleArrayWithComments, TomlEditor

if TYPE_CHECKING:
    from pathlib import Path

    from .pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration.

    Attributes:
        CATEGORY_MAP: Map rule category codes to URL categories.

    """

    # Map rule category codes to URL categories
    CATEGORY_MAP: ClassVar[dict[str, str]] = {
        "C": "convention",
        "E": "error",
        "W": "warning",
        "R": "refactor",
        "F": "fatal",
        "I": "info",
    }

    def __init__(self, config_file: Path) -> None:
        """Initialize a PyprojectUpdater instance.

        Args:
            config_file: Path to the pyproject.toml file

        """
        self.config_file = config_file
        self.toml_editor = TomlEditor(config_file)

    @staticmethod
    def extract_disabled_rules_from_config(config: dict[str, Any]) -> list[str]:
        """Extract the disabled rules from the configuration.

        Args:
            config: The configuration dictionary.

        Returns:
            List of disabled rule identifiers from the configuration.

        """
        disabled_rules = (
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("disable", [])
        )
        return disabled_rules if isinstance(disabled_rules, list) else []

    def read_config(self) -> dict[str, Any]:
        """Read current configuration from pyproject.toml.

        Returns:
            The current configuration dictionary from pyproject.toml, or empty dict
            if file not found.

        Raises:
            Exception: If parsing the configuration file fails.

        """
        try:
            config = self.toml_editor.read_config()
        except Exception:
            logger.exception("Failed to read configuration file")
            raise

        if not config:
            logger.warning("No pyproject.toml found, creating new configuration")
        return config

    def update_pylint_config(
        self,
        config: dict[str, Any],
        rules_to_enable: set[str],
        existing_disabled: set[str],
        all_rules: list[PylintRule],
    ) -> dict[str, Any]:
        """Update pylint configuration to enable only non-implemented rules.

        Args:
            config: Current configuration dictionary.
            rules_to_enable: Set of rule codes to enable (not implemented in ruff).
            existing_disabled: Set of resolved rule codes that are disabled by user.
            all_rules: List of all pylint rules with their descriptions.

        Returns:
            Updated configuration dictionary.

        """
        # Ensure pylint section exists
        if "tool" not in config:
            config["tool"] = {}
        if "pylint" not in config["tool"]:
            config["tool"]["pylint"] = {}
        if "messages_control" not in config["tool"]["pylint"]:
            config["tool"]["pylint"]["messages_control"] = {}

        # Don't enable rules that are explicitly disabled by the user
        final_enable_rules = rules_to_enable - existing_disabled

        # Always update enable list, even if empty (to clear existing rules)
        enable_list = sorted(final_enable_rules)
        config["tool"]["pylint"]["messages_control"]["enable"] = enable_list

        # Ensure "all" is in the disable list to prevent duplicate rule execution
        existing_disable = (
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("disable", [])
        )
        if "all" not in existing_disable:
            existing_disable.append("all")
            config["tool"]["pylint"]["messages_control"]["disable"] = existing_disable

        if final_enable_rules:
            logger.info(
                "Updated enable list with %d rules (not implemented in ruff)",
                len(final_enable_rules),
            )

            if existing_disabled & rules_to_enable:
                skipped_count = len(existing_disabled & rules_to_enable)
                logger.info(
                    "Skipped enabling %d rules that are explicitly disabled in config",
                    skipped_count,
                )
        else:
            logger.info(
                "Cleared enable list (all rules are implemented in ruff or disabled)"
            )

        # Log the "all" disable functionality
        logger.info("Added 'all' to disable list to prevent duplicate rule execution")

        # Create rule lookup dictionaries for enable array with comments
        rule_descriptions = {rule.code: rule.description for rule in all_rules}
        rule_names = {rule.code: rule.name for rule in all_rules}

        # Store these for write_config to use
        config["tool"]["pylint"]["messages_control"]["_enable_descriptions"] = (
            rule_descriptions
        )
        config["tool"]["pylint"]["messages_control"]["_rule_names"] = rule_names

        return config

    def write_config(self, config: dict[str, Any]) -> None:
        """Write updated configuration to pyproject.toml using surgical updates.

        Args:
            config: The configuration dictionary to write to the file.

        Raises:
            Exception: If writing the configuration file fails.

        """
        try:
            # Ensure "all" is in the disable list before writing
            self.toml_editor.ensure_item_in_array(
                section_path=["tool", "pylint", "messages_control"],
                key="disable",
                item="all",
                preserve_format=True,
            )

            # Use surgical regex updates for pylint section
            self._update_pylint_section_with_toml_editor(config)
            logger.info("Updated configuration written to %s", self.config_file)
        except Exception:
            logger.exception("Failed to write configuration file")
            raise

    def _update_pylint_section_with_toml_editor(self, config: dict[str, Any]) -> None:
        """Update pylint section using TomlEditor for surgical updates.

        Args:
            config: The configuration dictionary containing pylint settings.

        """
        # Extract pylint config
        pylint_config = (
            config.get("tool", {}).get("pylint", {}).get("messages_control", {})
        )

        if not pylint_config:
            return

        # Create enable array with comments
        enable_list = pylint_config.get("enable", [])
        rule_names = pylint_config.get("_rule_names", {})

        # Generate URL comments for enabled rules
        enable_comments: dict[str, str] = {}
        for rule_code in enable_list:
            rule_name = rule_names.get(rule_code, "")
            if rule_name:
                category_code = rule_code[0]
                category = self.CATEGORY_MAP.get(category_code, "error")
                base_url = "https://pylint.readthedocs.io/en/stable/user_guide/messages"
                url = f"{base_url}/{category}/{rule_name}.html"
                enable_comments[rule_code] = url

        # Create SimpleArrayWithComments for enable list
        enable_array = SimpleArrayWithComments(
            items=enable_list, comments=enable_comments if enable_comments else None
        )

        # Update enable section with preserve_format=True for surgical replacement
        self.toml_editor.update_section_array(
            section_path=["tool", "pylint", "messages_control"],
            key="enable",
            array_data=enable_array,
            preserve_format=True,
        )
