"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
import re
import tomllib
from typing import TYPE_CHECKING, Any, ClassVar

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
            with self.config_file.open("rb") as f:
                config: dict[str, Any] = tomllib.load(f)
                return config
        except FileNotFoundError:
            logger.warning("No pyproject.toml found, creating new configuration")
            return {}
        except Exception:
            logger.exception("Failed to read configuration file")
            raise

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
        enable_list = list(final_enable_rules)
        enable_list.sort()
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

        # Do NOT modify the disable list - leave it completely untouched

        return config

    def write_config(self, config: dict[str, Any]) -> None:
        """Write updated configuration to pyproject.toml using regex replacement.

        Args:
            config: The configuration dictionary to write to the file.

        Raises:
            Exception: If writing the configuration file fails.

        """
        try:
            # Read the original file content
            if self.config_file.exists():
                with self.config_file.open("r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = ""

            # Update the content using regex replacement
            updated_content = self._update_pylint_section(content, config)

            # Write the updated content back to file
            with self.config_file.open("w", encoding="utf-8") as f:
                f.write(updated_content)
            logger.info("Updated configuration written to %s", self.config_file)
        except Exception:
            logger.exception("Failed to write configuration file")
            raise

    def _update_pylint_section(self, content: str, config: dict[str, Any]) -> str:
        """Update only the enable key in the pylint section using regex.

        Args:
            content: The original TOML file content.
            config: The configuration dictionary.

        Returns:
            The updated TOML content.

        """
        # Extract pylint config
        pylint_config = (
            config.get("tool", {}).get("pylint", {}).get("messages_control", {})
        )

        if not pylint_config:
            return content

        # Always process if we have pylint config, even if enable list is empty
        # (we might need to clear an existing enable list)
        new_enable_content = self._generate_new_enable_content(pylint_config)

        # Check if there's an existing [tool.pylint.messages_control] section
        messages_control_pattern = re.compile(
            r"(\[tool\.pylint\.messages_control\].*?)(?=\n\[|\Z)",
            re.DOTALL | re.MULTILINE,
        )

        existing_match = messages_control_pattern.search(content)

        if existing_match:
            # Section exists - replace only the enable part
            section_content = existing_match.group(1)
            updated_section = self._update_existing_section(
                section_content, new_enable_content
            )

            # Replace the entire section in the content
            updated_content = messages_control_pattern.sub(
                updated_section.rstrip(), content
            )
        else:
            # Add new section only if we have rules to enable
            enable_list = pylint_config.get("enable", [])
            if enable_list:
                new_section = self._generate_new_messages_control_section(pylint_config)
                updated_content = self._add_pylint_section(content, new_section)
            else:
                updated_content = content

        return updated_content

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
        for rule_code in enable_list:
            rule_name = rule_names.get(rule_code, "")
            if rule_name:
                # Generate URL comment
                category_code = rule_code[0]
                category = self.CATEGORY_MAP.get(category_code, "error")
                base_url = "https://pylint.readthedocs.io/en/stable/user_guide/messages"
                url = f"{base_url}/{category}/{rule_name}.html"
                new_enable_lines.append(f'  "{rule_code}",  # {url}')
            else:
                new_enable_lines.append(f'  "{rule_code}",')

        new_enable_lines.append("]")
        return "\n".join(new_enable_lines)

    def _update_existing_section(
        self, section_content: str, new_enable_content: str
    ) -> str:
        """Update an existing messages_control section with new enable content.

        Args:
            section_content: The existing section content.
            new_enable_content: The new enable content to insert.

        Returns:
            The updated section content.

        """
        # Look for existing enable = [...] pattern and replace it
        enable_pattern = re.compile(
            r"enable\s*=\s*\[(?:[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]",
            re.DOTALL | re.MULTILINE,
        )

        if enable_pattern.search(section_content):
            # Replace existing enable section
            return enable_pattern.sub(new_enable_content, section_content)
        # Add enable section - delegate to helper method
        return self._add_enable_to_section(section_content, new_enable_content)

    def _add_enable_to_section(
        self, section_content: str, new_enable_content: str
    ) -> str:
        """Add enable section to an existing messages_control section.

        Args:
            section_content: The existing section content.
            new_enable_content: The new enable content to add.

        Returns:
            The updated section content.

        """
        lines = section_content.split("\n")
        header_line = lines[0]  # [tool.pylint.messages_control]
        rest_lines = lines[1:]

        # Add automatic generation comment if not present
        comment_lines = [
            "# This section will be automatically updated by the precommit hook",
            "# based on ruff implementation status from "
            "https://github.com/astral-sh/ruff/issues/970",
        ]

        # Check if comment is already there
        has_comment = any("automatically updated" in line for line in rest_lines)

        if has_comment:
            # Insert enable right after comments
            insert_index = 0
            for i, line in enumerate(rest_lines):
                if line.strip() and not line.strip().startswith("#"):
                    insert_index = i
                    break
            else:
                insert_index = len(rest_lines)
        else:
            # Add comments first, then enable
            rest_lines = comment_lines + rest_lines
            insert_index = len(comment_lines)

        # Insert the enable section
        enable_lines = new_enable_content.split("\n")
        for i, enable_line in enumerate(enable_lines):
            rest_lines.insert(insert_index + i, enable_line)

        return header_line + "\n" + "\n".join(rest_lines)

    def _generate_new_messages_control_section(
        self, pylint_config: dict[str, Any]
    ) -> str:
        """Generate a new [tool.pylint.messages_control] section for new files.

        Args:
            pylint_config: The pylint configuration dictionary.

        Returns:
            The formatted pylint section string.

        """
        lines = ["[tool.pylint.messages_control]"]

        # Add comment about automatic generation
        lines.append(
            "# This section will be automatically updated by the precommit hook"
        )
        lines.append(
            "# based on ruff implementation status from "
            "https://github.com/astral-sh/ruff/issues/970"
        )

        # Handle enable list
        enable_list = pylint_config.get("enable", [])
        if enable_list:
            rule_names = pylint_config.get("_rule_names", {})
            lines.append("enable = [")
            for rule_code in enable_list:
                rule_name = rule_names.get(rule_code, "")
                if rule_name:
                    # Generate URL comment
                    category_code = rule_code[0]
                    category = self.CATEGORY_MAP.get(category_code, "error")
                    base_url = (
                        "https://pylint.readthedocs.io/en/stable/user_guide/messages"
                    )
                    url = f"{base_url}/{category}/{rule_name}.html"
                    lines.append(f'  "{rule_code}",  # {url}')
                else:
                    lines.append(f'  "{rule_code}",')
            lines.append("]")

        return "\n".join(lines) + "\n"

    def _add_pylint_section(self, content: str, new_section: str) -> str:
        """Add the pylint section to the TOML content.

        Args:
            content: The original TOML content.
            new_section: The new pylint section to add.

        Returns:
            The updated TOML content.

        """
        # Try to find [tool.pylint] section and add messages_control under it
        tool_pylint_pattern = re.compile(
            r"(\[tool\.pylint\].*?)(?=\n\[|\Z)", re.DOTALL | re.MULTILINE
        )

        if tool_pylint_pattern.search(content):
            # Find the end of [tool.pylint] section and insert our messages_control
            def replace_tool_pylint(match: re.Match[str]) -> str:
                existing_section = match.group(1)
                if "[tool.pylint.messages_control]" in existing_section:
                    # messages_control already exists, just return original
                    return existing_section
                # Add our messages_control section
                return existing_section.rstrip() + "\n\n" + new_section.rstrip()

            return tool_pylint_pattern.sub(replace_tool_pylint, content)

        # If no [tool.pylint] section exists, add everything at the end
        if content and not content.endswith("\n"):
            content += "\n"

        content += "\n[tool.pylint]\n\n" + new_section

        return content
