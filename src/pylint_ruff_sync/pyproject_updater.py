"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
import re
import subprocess
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

            # Run toml-sort to format the file
            self._run_toml_sort()
        except Exception:
            logger.exception("Failed to write configuration file")
            raise

    def _run_toml_sort(self) -> None:
        """Run toml-sort on the configuration file."""
        commands_to_try = [
            [
                "uv",
                "run",
                "toml-sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.config_file),
            ],
            [
                "toml-sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.config_file),
            ],
            [
                "python",
                "-m",
                "toml_sort",
                "--sort-inline-tables",
                "--sort-table-keys",
                "--in-place",
                str(self.config_file),
            ],
        ]

        for cmd in commands_to_try:
            try:
                result = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if not result.returncode:
                    logger.debug(
                        "toml-sort completed successfully with command: %s", cmd[0]
                    )
                    return
                logger.warning(
                    "toml-sort returned non-zero exit code: %d", result.returncode
                )
                if result.stderr:
                    logger.warning("toml-sort stderr: %s", result.stderr)
                # Try next command
                continue

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.debug("Command %s failed: %s", cmd[0], e)
                # Try next command
                continue

        # If we get here, all commands failed
        logger.warning(
            "Failed to run toml-sort with any available command, "
            "continuing without formatting"
        )

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
        new_disable_content = self._generate_new_disable_content(pylint_config)

        # Check if there's an existing [tool.pylint.messages_control] section
        messages_control_pattern = re.compile(
            r"(\[tool\.pylint\.messages_control\].*?)(\n*?)(?=\n\[|\Z)",
            re.DOTALL | re.MULTILINE,
        )

        existing_match = messages_control_pattern.search(content)

        if existing_match:
            # Section exists - replace only the enable part
            section_content = existing_match.group(1)
            trailing_newlines = existing_match.group(2)
            updated_section = self._update_existing_section(
                section_content, new_enable_content, new_disable_content
            )

            # Replace the entire section in the content, preserving trailing newlines
            replacement = updated_section.rstrip() + trailing_newlines
            updated_content = messages_control_pattern.sub(replacement, content)
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
                # Always add comma for consistency with TOML formatting
                new_enable_lines.append(f'  "{rule_code}", # {url}')
            else:
                # Always add comma for consistency with TOML formatting
                new_enable_lines.append(f'  "{rule_code}",')

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

    def _update_existing_section(
        self,
        section_content: str,
        new_enable_content: str,
        new_disable_content: str = "",
    ) -> str:
        """Update an existing messages_control section with new content.

        Args:
            section_content: The existing section content.
            new_enable_content: The new enable content to insert.
            new_disable_content: The new disable content to insert.

        Returns:
            The updated section content.

        """
        updated_content = section_content

        # Handle disable first, then enable to maintain proper order
        disable_pattern = re.compile(
            r"disable\s*=\s*\[(?:[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]",
            re.DOTALL | re.MULTILINE,
        )

        enable_pattern = re.compile(
            r"enable\s*=\s*\[(?:[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]",
            re.DOTALL | re.MULTILINE,
        )

        # First, handle disable section
        if new_disable_content:
            if disable_pattern.search(updated_content):
                # Replace existing disable section
                updated_content = disable_pattern.sub(
                    new_disable_content, updated_content
                )
            else:
                # Add disable section - delegate to helper method
                updated_content = self._add_disable_to_section(
                    updated_content, new_disable_content
                )

        # Then, handle enable section
        if enable_pattern.search(updated_content):
            # Replace existing enable section
            updated_content = enable_pattern.sub(new_enable_content, updated_content)
        else:
            # Add enable section - delegate to helper method
            updated_content = self._add_enable_to_section(
                updated_content, new_enable_content
            )

        return updated_content

    def _add_disable_to_section(
        self, section_content: str, new_disable_content: str
    ) -> str:
        """Add disable section to an existing messages_control section.

        Args:
            section_content: The existing section content.
            new_disable_content: The new disable content to add.

        Returns:
            The updated section content.

        """
        lines = section_content.split("\n")
        header_line = lines[0]  # [tool.pylint.messages_control]
        rest_lines = lines[1:]

        # Find the insertion point (after comments, before existing content)
        insert_index = 0
        for i, line in enumerate(rest_lines):
            if line.strip() and not line.strip().startswith("#"):
                insert_index = i
                break
        else:
            insert_index = len(rest_lines)

        # Insert the disable section
        disable_lines = new_disable_content.split("\n")
        for i, disable_line in enumerate(disable_lines):
            rest_lines.insert(insert_index + i, disable_line)

        return header_line + "\n" + "\n".join(rest_lines)

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

        # Handle disable list first
        disable_list = pylint_config.get("disable", [])
        if disable_list:
            if len(disable_list) == 1 and disable_list[0] == "all":
                # Inline format for single "all" item
                lines.append('disable = ["all"]')
            else:
                # Multiline format for multiple items
                lines.append("disable = [")
                for i, rule_code in enumerate(disable_list):
                    is_last = i == len(disable_list) - 1
                    comma = "" if is_last else ","
                    lines.append(f'  "{rule_code}"{comma}')
                lines.append("]")

        # Handle enable list
        enable_list = pylint_config.get("enable", [])
        if enable_list:
            rule_names = pylint_config.get("_rule_names", {})
            lines.append("enable = [")
            for i, rule_code in enumerate(enable_list):
                rule_name = rule_names.get(rule_code, "")
                is_last = i == len(enable_list) - 1

                if rule_name:
                    # Generate URL comment
                    category_code = rule_code[0]
                    category = self.CATEGORY_MAP.get(category_code, "error")
                    base_url = (
                        "https://pylint.readthedocs.io/en/stable/user_guide/messages"
                    )
                    url = f"{base_url}/{category}/{rule_name}.html"
                    # Always add comma for consistency with TOML formatting
                    lines.append(f'  "{rule_code}", # {url}')
                else:
                    # Always add comma for consistency with TOML formatting
                    lines.append(f'  "{rule_code}",')
            lines.append("]")

        return "\n".join(lines) + "\n\n"

    def _add_pylint_section(self, content: str, new_section: str) -> str:
        """Add the pylint section to the TOML content.

        Args:
            content: The original TOML content.
            new_section: The new pylint section to add.

        Returns:
            The updated TOML content.

        """
        # If no [tool.pylint] section exists, add at the end
        if content and not content.endswith("\n"):
            content += "\n"

        content += "\n[tool.pylint]\n\n" + new_section

        return content
