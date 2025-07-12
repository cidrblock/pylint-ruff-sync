"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

    from .pylint_rule import PylintRule

from .toml_editor import TomlEditor

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
        else:
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
        # Create a dictionary mapping rule codes to their descriptions
        rule_descriptions = {rule.code: rule.description for rule in all_rules}

        # Create a dictionary mapping rule codes to their names for URL generation
        rule_names = {rule.code: rule.name for rule in all_rules}

        # Store the enable list and descriptions for later use by regex replacement
        enable_list = sorted(final_enable_rules)
        config["tool"]["pylint"]["messages_control"]["enable"] = enable_list
        config["tool"]["pylint"]["messages_control"]["_enable_descriptions"] = (
            rule_descriptions
        )
        config["tool"]["pylint"]["messages_control"]["_rule_names"] = rule_names

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

        # Always ensure "all" is first in the disable list
        # This is required so that only the enabled rules run
        existing_disable = config["tool"]["pylint"]["messages_control"].get(
            "disable", []
        )

        # Ensure "all" is first in the disable list
        if "all" not in existing_disable:
            # Add "all" as the first item
            disable_list = ["all", *existing_disable]
        else:
            # Move "all" to the front if it's not already there
            disable_list = existing_disable.copy()
            disable_list.remove("all")
            disable_list.insert(0, "all")

        config["tool"]["pylint"]["messages_control"]["disable"] = disable_list

        return config

    def write_config(self, config: dict[str, Any]) -> None:
        """Write updated configuration to pyproject.toml using regex replacement.

        Args:
            config: The configuration dictionary to write to the file.

        Raises:
            Exception: If writing the configuration file fails.

        """
        try:
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

        # Generate content for enable and disable sections
        new_enable_content = self._generate_new_enable_content(pylint_config)
        new_disable_content = self._generate_new_disable_content(pylint_config)

        # Update disable section if needed
        if new_disable_content:
            self.toml_editor.update_section_content_with_regex(
                section_pattern=r"\[tool\.pylint\.messages_control\]",
                key="disable",
                new_content=new_disable_content,
            )

        # Update enable section
        self.toml_editor.update_section_content_with_regex(
            section_pattern=r"\[tool\.pylint\.messages_control\]",
            key="enable",
            new_content=new_enable_content,
        )

    def _generate_new_enable_content(self, pylint_config: dict[str, Any]) -> str:
        """Generate the new enable section content.

        Args:
            pylint_config: The pylint configuration dictionary.

        Returns:
            The formatted enable section string.

        """
        enable_list = pylint_config.get("enable", [])
        rule_names = pylint_config.get("_rule_names", {})

        new_enable_lines = ["enable = ["]

        # Add rules even if list is empty (to clear existing rules)
        for i, rule_code in enumerate(enable_list):
            rule_name = rule_names.get(rule_code, "")
            is_last = i == len(enable_list) - 1

            if rule_name:
                # Generate URL comment
                category_code = rule_code[0]
                category = self.CATEGORY_MAP.get(category_code, "error")
                base_url = "https://pylint.readthedocs.io/en/stable/user_guide/messages"
                url = f"{base_url}/{category}/{rule_name}.html"
                # Add comma only if not the last item
                comma = "" if is_last else ","
                new_enable_lines.append(f'  "{rule_code}"{comma} # {url}')
            else:
                # Add comma only if not the last item
                comma = "" if is_last else ","
                new_enable_lines.append(f'  "{rule_code}"{comma}')

        new_enable_lines.append("]")
        return "\n".join(new_enable_lines)

    def _generate_new_disable_content(self, pylint_config: dict[str, Any]) -> str:
        """Generate the new disable section content.

        Args:
            pylint_config: The pylint configuration dictionary.

        Returns:
            The formatted disable section string.

        """
        disable_list = pylint_config.get("disable", [])

        if not disable_list:
            return ""

        # Handle inline format for single "all" item
        if len(disable_list) == 1 and disable_list[0] == "all":
            return 'disable = ["all"]'

        # Handle multiline format for multiple items
        new_disable_lines = ["disable = ["]
        for i, rule_code in enumerate(disable_list):
            is_last = i == len(disable_list) - 1
            comma = "" if is_last else ","
            new_disable_lines.append(f'  "{rule_code}"{comma}')
        new_disable_lines.append("]")
        return "\n".join(new_disable_lines)
