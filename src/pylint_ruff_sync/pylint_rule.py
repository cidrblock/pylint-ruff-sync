"""PylintRule class definition."""

from __future__ import annotations


class PylintRule:  # pylint: disable=too-few-public-methods
    """Represents a pylint rule with its metadata."""

    def __init__(self, code: str, name: str, description: str) -> None:
        """Initialize a PylintRule instance.

        Args:
            code: The rule code (e.g., 'C0103')
            name: The rule name (e.g., 'invalid-name')
            description: The rule description

        """
        self.code = code
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        """Return a string representation of the PylintRule.

        Returns:
            A string representation of the PylintRule instance.

        """
        return f"PylintRule(code='{self.code}', name='{self.name}')"
