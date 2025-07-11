# Pylint-Ruff Sync Precommit Hook

A precommit hook that automatically updates your `pyproject.toml` file to enable only those pylint rules that haven't been implemented by ruff, based on the current status from the [ruff pylint implementation tracking issue](https://github.com/astral-sh/ruff/issues/970).

## Overview

As the ruff project continues to implement more pylint rules, projects using both tools need to avoid duplication by disabling pylint rules that are already covered by ruff. This precommit hook automates this process by:

1. Extracting all available pylint rules using `pylint --list-msgs`
2. Fetching the current implementation status from the GitHub issue
3. Calculating which rules should be enabled (not implemented in ruff) - this creates a shorter, more maintainable list
4. Updating the `pyproject.toml` file with the appropriate configuration

## Features

- 🔄 **Always Up-to-Date**: References the live GitHub issue to ensure accuracy
- 🚀 **Automated**: Runs as part of your pre-commit workflow
- 📊 **Comprehensive**: Handles all pylint rules automatically
- 🔧 **Configurable**: Supports dry-run mode and custom configuration paths
- 📝 **Well-Documented**: Includes detailed logging and type hints
- ✅ **CI-Ready**: Works with pre-commit.ci

## Installation

### For Any Project

Simply add the hook to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0  # Use the latest version
    hooks:
      - id: pylint-ruff-sync
```

#### Custom Rules (Optional)

You can also pass custom enable/disable rules by code or name:

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0
    hooks:
      - id: pylint-ruff-sync
        args: [
          "--custom-enable", "C0103", "invalid-name",  # Enable specific rules
          "--custom-disable", "R0903", "too-few-public-methods"  # Disable specific rules
        ]
```

That's it! The hook will automatically:
- Install its own dependencies
- Run when `pyproject.toml` is modified
- Update your pylint configuration
- Apply your custom enable/disable rules

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

# With custom enable/disable rules (by code or name)
pylint-ruff-sync --custom-enable C0103 invalid-name --custom-disable R0903 too-few-public-methods
```

## Configuration

The hook will automatically create and manage the following section in your `pyproject.toml`:

```toml
[tool.pylint.messages_control]
# This section will be automatically updated by the precommit hook
# based on ruff implementation status from https://github.com/astral-sh/ruff/issues/970
# Custom rules added via --custom-enable and --custom-disable are preserved
enable = [
    # Rules NOT implemented in ruff - automatically generated
    "C0112",  # empty-docstring
    "C0113",  # unneeded-not
    # Custom enabled rules (if any)
    "C0103",  # invalid-name (custom)
    # ... more rules
]
disable = [
    # Custom disabled rules (if any)
    "R0903",  # too-few-public-methods (custom)
    # ... more custom disabled rules
]
```

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
- Calculates which rules should be disabled (implemented in ruff)
- Updates the `pyproject.toml` file with the new configuration
- Preserves existing configuration while updating the disable list

## Benefits

- **Avoid Duplication**: Prevents running the same checks twice
- **Stay Current**: Automatically adapts as ruff implements more rules
- **Shorter Lists**: Enable-only approach creates more maintainable configuration
- **Reduce Noise**: Eliminates redundant warnings and errors
- **Improve Performance**: Faster linting by avoiding duplicate work
- **Maintain Quality**: Ensures you still get comprehensive code analysis
- **Future-Proof**: List gets shorter over time as ruff implements more rules

## Example Output

```
INFO: Extracting pylint rules from 'pylint --list-msgs'
INFO: Found 409 total pylint rules
INFO: Fetching ruff pylint implementation status from https://github.com/astral-sh/ruff/issues/970
INFO: Found 127 implemented pylint rules in ruff
INFO: Total pylint rules: 409
INFO: Rules implemented in ruff: 127
INFO: Rules to enable (not implemented in ruff): 282
INFO: Custom enable rules: 2
INFO: Custom disable rules: 1
INFO: Updated enable list with 282 auto-generated rules
INFO: Added 2 custom enable rules
INFO: Updated disable list with 1 custom disable rules
INFO: Updated configuration written to pyproject.toml
INFO: Pylint configuration updated successfully
INFO: Enabled 284 total rules
INFO: Disabled 1 custom rules
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
- tomli-w 1.0.0+

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
