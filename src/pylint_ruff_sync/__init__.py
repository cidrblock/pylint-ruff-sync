"""Pylint-Ruff Sync: A precommit hook to sync pylint configuration with ruff.

This package provides a precommit hook that automatically updates your pyproject.toml
file to disable pylint rules that have been implemented in ruff, based on the current
status from the ruff GitHub issue.
"""

__version__ = "0.1.0"
__author__ = "ansible-creator contributors"
__email__ = "ansible-creator@redhat.com"

from .main import main

__all__ = ["main"]
