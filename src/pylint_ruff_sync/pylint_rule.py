"""PylintRule class definition."""

from __future__ import annotations


class PylintRule:
    """Represents a pylint rule with its metadata."""

    def __init__(self, rule_id: str, name: str, description: str) -> None:
        """Initialize a PylintRule instance.

        Args:
            rule_id: The rule code (e.g., 'C0103')
            name: The rule name (e.g., 'invalid-name')
            description: The rule description

        """
        self.rule_id = rule_id
        self.name = name
        self.description = description

    @property
    def code(self) -> str:
        """Backward compatibility property for rule_id.

        Returns:
            The rule ID (same as rule_id).

        """
        return self.rule_id

    def __repr__(self) -> str:
        """Return a string representation of the PylintRule.

        Returns:
            A string representation of the PylintRule instance.

        """
        return f"PylintRule(rule_id='{self.rule_id}', name='{self.name}')"
