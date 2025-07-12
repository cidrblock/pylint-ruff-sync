# Pylint-Ruff Sync Precommit Hook

A precommit hook that automatically updates your `pyproject.toml` file to enable only those pylint rules that haven't been implemented by ruff, based on the current status from the [ruff pylint implementation tracking issue](https://github.com/astral-sh/ruff/issues/970).

## Overview

As the ruff project continues to implement more pylint rules, projects using both tools need to avoid duplication by disabling pylint rules that are already covered by ruff. This precommit hook automates this process by:

1. Extracting all available pylint rules using `pylint --list-msgs`
2. Fetching the current implementation status from the GitHub issue
3. Calculating which rules should be enabled (not implemented in ruff) - this creates a shorter, more maintainable list
4. **Automatically adding `disable = ["all"]` as the first item** to ensure only enabled rules run
5. **Surgically updating only the enable/disable arrays** while preserving all other formatting and comments
6. **Placing new sections at the end of the file** for consistent organization

## Features

- 🔄 **Always Up-to-Date**: References the live GitHub issue to ensure accuracy
- 🚀 **Automated**: Runs as part of your pre-commit workflow
- 📊 **Comprehensive**: Handles all pylint rules automatically
- 🔧 **Configurable**: Supports dry-run mode and custom configuration paths
- 📝 **Well-Documented**: Includes detailed logging and type hints
- 🔗 **Documentation URLs**: Adds clickable links to pylint rule documentation
- ✅ **CI-Ready**: Works with pre-commit.ci
- 🎯 **Surgical Updates**: Only modifies enable/disable arrays, preserves all other content
- 🚫 **Smart Disabling**: Automatically adds `disable = ["all"]` to prevent duplicate rule execution

## Installation

### For Any Project

Simply add the hook to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0 # Use the latest version
    hooks:
      - id: pylint-ruff-sync
```

That's it! The hook will automatically:

- Install its own dependencies
- Run when `pyproject.toml` is modified
- Update your pylint configuration
- Preserve existing disabled rules

## Usage

### As a Pre-commit Hook

The hook will automatically run when you commit changes to `pyproject.toml`. It will:

- Extract all pylint rules from your environment
- Check the current ruff implementation status
- Update the pylint configuration if needed
- Commit the changes along with your other modifications

### Manual Execution

You can also run the tool manually if you have it installed:

```bash
# Install the package
pip install pylint-ruff-sync

# Update configuration
pylint-ruff-sync

# Dry run (show what would change)
pylint-ruff-sync --dry-run

# Verbose output
pylint-ruff-sync --verbose

# Custom config file
pylint-ruff-sync --config-file path/to/pyproject.toml
```

## Configuration

The hook will automatically create and manage the following section in your `pyproject.toml`:

```toml
[tool.pylint.messages_control]
# This section will be automatically updated by the precommit hook
# based on ruff implementation status from https://github.com/astral-sh/ruff/issues/970
disable = ["all"]  # Disables all rules by default
enable = [
    # Rules NOT implemented in ruff - automatically generated with documentation URLs
    "C0112",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/empty-docstring.html
    "C0113",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/unneeded-not.html
    "C0114",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/missing-module-docstring.html
    "C0115",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/missing-class-docstring.html
    "C0116",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/missing-function-docstring.html
    # ... more rules with documentation URLs
]
```

### Smart Disable List Management

The tool automatically manages the `disable` list to ensure optimal behavior:

1. **Always includes "all"** as the first disabled rule to prevent duplicate execution
2. **Preserves existing user-disabled rules** after "all"
3. **Uses inline format** when only `disable = ["all"]` is present
4. **Uses multiline format** when additional rules are disabled:

```toml
# Inline format (single item)
disable = ["all"]

# Multiline format (multiple items)
disable = [
  "all",
  "locally-disabled",
  "suppressed-message"
]
```

## Section Placement Strategy

The tool follows a specific strategy for placing and organizing pylint configuration:

### New Projects

- **Creates new `[tool.pylint]` section** at the end of the file
- **Adds `[tool.pylint.messages_control]` subsection** immediately after
- **Maintains clean separation** from other tools

### Existing Projects

- **Preserves existing pylint section locations**
- **Only updates the `enable` and `disable` arrays** within `[tool.pylint.messages_control]`
- **Surgically replaces content** without affecting surrounding configuration
- **Maintains all existing comments, formatting, and other subsections**

### Section Ordering Within messages_control

1. **Comments**: Automatic generation notice preserved
2. **disable**: Always first, with "all" as the first item
3. **enable**: Lists rules not implemented in ruff
4. **Other settings**: Preserved exactly as they were

## How It Works

### 1. Pylint Rule Extraction

The script runs `pylint --list-msgs` to extract all available pylint rules with their codes, names, and descriptions.

### 2. Ruff Implementation Status

It fetches the current status from the [ruff pylint tracking issue](https://github.com/astral-sh/ruff/issues/970) by:

- Making an HTTP request to the GitHub issue
- Parsing the HTML with BeautifulSoup
- Extracting checked items from the task list
- Identifying which pylint rules are implemented

### 3. Configuration Update

The script then:

- Calculates which rules should be enabled (not implemented in ruff)
- **Ensures "all" is first in the disable list** to prevent rule conflicts
- Updates the `pyproject.toml` file with the new configuration
- **Preserves existing disabled rules** while updating the enable list
- **Uses surgical regex replacement** to modify only the enable/disable arrays
- Adds inline comments with URLs to the official pylint documentation for each rule

### 4. Documentation URLs

For each enabled rule, the tool automatically generates a URL comment pointing to the official pylint documentation. The URLs follow the format:

```
https://pylint.readthedocs.io/en/stable/user_guide/messages/{category}/{rule-name}.html
```

Where:

- `category` is determined by the rule code prefix (C=convention, E=error, W=warning, R=refactor, F=fatal, I=info)
- `rule-name` is the actual pylint rule name (e.g., "missing-function-docstring")

This makes it easy to quickly understand what each rule does and access detailed documentation.

### 5. Surgical Updates

The tool uses advanced regex patterns to surgically update only the necessary parts:

- **Preserves all comments** including user-added ones
- **Maintains original formatting** for untouched sections
- **Only replaces enable/disable arrays** within existing sections
- **Adds new sections at the end** when none exist
- **Respects existing section organization** and doesn't reorder other pylint settings

## Benefits

- **Avoid Duplication**: Prevents running the same checks twice by disabling all rules then enabling only needed ones
- **Stay Current**: Automatically adapts as ruff implements more rules
- **Shorter Lists**: Enable-only approach creates more maintainable configuration
- **Reduce Noise**: Eliminates redundant warnings and errors
- **Improve Performance**: Faster linting by avoiding duplicate work through smart disable strategy
- **Maintain Quality**: Ensures you still get comprehensive code analysis
- **Future-Proof**: List gets shorter over time as ruff implements more rules
- **Easy Reference**: Direct links to pylint documentation for each rule
- **Preserve Customization**: Maintains all existing configuration and comments

## Example Output

```
INFO: Extracting pylint rules from 'pylint --list-msgs'
INFO: Found 409 total pylint rules
INFO: Fetching ruff pylint implementation status from https://github.com/astral-sh/ruff/issues/970
INFO: Found 127 implemented pylint rules in ruff
INFO: Total pylint rules: 409
INFO: Rules implemented in ruff: 127
INFO: Rules to enable (not implemented in ruff): 282
INFO: Added 'all' to disable list to prevent duplicate rule execution
INFO: Updated enable list with 282 rules
INFO: Updated configuration written to pyproject.toml
INFO: Pylint configuration updated successfully
INFO: Enabled 282 total rules
```

## Integration with CI/CD

This hook works seamlessly with:

- **pre-commit.ci**: Automatically updates configuration in pull requests
- **GitHub Actions**: Runs as part of your pre-commit workflow
- **GitLab CI**: Compatible with GitLab's pre-commit integration

## Requirements

- Python 3.8+
- pylint 2.15.0+
- requests 2.28.0+
- beautifulsoup4 4.11.0+

## Project Structure

```
pylint-ruff-sync/
├── src/pylint_ruff_sync/           # Main package source
│   ├── __init__.py                 # Package initialization
│   ├── main.py                     # CLI entry point and orchestration
│   ├── pylint_extractor.py         # Pylint rule extraction logic
│   ├── pylint_rule.py              # Rule data structures
│   ├── pyproject_updater.py        # TOML file surgical updates
│   └── ruff_pylint_extractor.py    # GitHub issue parsing
├── tests/                          # Comprehensive test suite
│   ├── integration/                # End-to-end integration tests
│   ├── unit/                       # Unit tests for individual components
│   ├── fixtures/                   # Test fixture files (before/after pairs)
│   └── constants.py                # Shared test data and mock helpers
├── pyproject.toml                  # Project configuration
└── README.md                       # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run pre-commit hooks: `pre-commit run --all-files`
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the [pylint-to-ruff](https://github.com/akx/pylint-to-ruff) project
- Built for the [ansible-creator](https://github.com/ansible/ansible-creator) project
- References the [ruff pylint tracking issue](https://github.com/astral-sh/ruff/issues/970)
- Uses the approach from [this gist](https://gist.github.com/cidrblock/ec3412bacfeb34dbc2d334c1d53bef83)
