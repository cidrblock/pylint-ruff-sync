# Pylint-Ruff Sync Precommit Hook

> [!CAUTION] > **This project needs a maintainer!**
>
> This repository was created as a proof-of-concept and demonstration project. **Do not use this repository directly** as it may be removed or archived without notice.
>
> If you're interested in using this tool:
>
> - **Fork this repository** to create your own maintained version
> - **Consider becoming the maintainer** by reaching out to [@cidrblock](https://github.com/cidrblock)
> - **Check for community forks** that may have active maintenance
>
> This codebase is production-ready with comprehensive tests and documentation, but requires ongoing maintenance for GitHub API changes, ruff updates, and dependency management.

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

# Disable mypy overlap filtering (include all rules)
pylint-ruff-sync --disable-mypy-overlap
```

## Mypy Integration

By default, `pylint-ruff-sync` automatically excludes pylint rules that overlap with mypy functionality. This prevents redundant checking when you're already using mypy for type checking.

### Mypy Overlap Rules

The tool automatically filters out 78 pylint rules that have equivalent functionality in mypy, including:

- **Type checking errors** (E1101: no-member, E1102: not-callable, etc.)
- **Attribute access issues** (E0237: assigning-non-slot, E0202: method-hidden)
- **Function signature problems** (W0221: arguments-differ, W0222: signature-differs)
- **Import and module issues** (E0401: import-error, E0402: relative-beyond-top-level)
- **Assignment and value errors** (E1128: assignment-from-none, E0601: used-before-assignment)

The complete list is based on research from the [antonagestam/pylint-mypy-overlap](https://github.com/antonagestam/pylint-mypy-overlap) repository and [ruff issue #970](https://github.com/astral-sh/ruff/issues/970#issuecomment-1565594417).

### Disabling Mypy Overlap Filtering

If you want to include mypy overlap rules (for example, if you're not using mypy), use the `--disable-mypy-overlap` flag:

```bash
# Include all rules, even those that overlap with mypy
pylint-ruff-sync --disable-mypy-overlap
```

### Logging

When mypy overlap filtering is active, the tool will log how many rules were excluded:

```
INFO: Excluded 12 rules that overlap with mypy functionality
INFO: Use --disable-mypy-overlap to include these rules
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

- Using GitHub CLI: `gh issue view 970 --repo astral-sh/ruff --json body`
- Parsing the JSON response to extract the issue body
- Using regex patterns to find checked items in the markdown task list
- Identifying which pylint rules are implemented in ruff

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

### 6. Disable List Optimization

The tool automatically optimizes your disable list to reduce unnecessary entries over time:

- **Removes redundant disabled rules**: If a rule is in your disable list but is implemented in ruff, it will be removed since ruff handles it anyway
- **Respects explicit enables**: If you explicitly enable a rule (via the enable list), it takes precedence over any disable entry for the same rule
- **Preserves unknown rules**: Custom or unrecognized rules in your disable list are preserved
- **Handles mypy overlap**: Rules that overlap with mypy functionality are removed from the disable list (unless `--disable-mypy-overlap` is used)

**Important**: The burden of ensuring that overlapping rules that should be enabled in ruff are properly configured is on you, the user. This tool removes disabled rules that are handled by ruff, but it's your responsibility to ensure ruff is configured to check those rules if you want them enforced.

#### Example Optimization

Before:

```toml
[tool.pylint.messages_control]
disable = ["locally-disabled", "invalid-name", "unused-import"]  # invalid-name and unused-import implemented in ruff
enable = ["C0103"]  # Explicitly enable invalid-name
```

After:

```toml
[tool.pylint.messages_control]
disable = ["locally-disabled", "all"]  # Removed invalid-name (explicitly enabled) and unused-import (ruff handles it)
enable = ["C0103"]  # Still enabled since user explicitly requested it
```

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
- **GitHub CLI (`gh`)** - for fetching live ruff implementation status

### GitHub CLI Dependency

This tool uses the [GitHub CLI (`gh`)](https://cli.github.com/) to fetch the current ruff pylint implementation status from [GitHub issue #970](https://github.com/astral-sh/ruff/issues/970).

#### Installation

**macOS:**

```bash
brew install gh
```

**Ubuntu/Debian:**

```bash
sudo apt install gh
```

**Other platforms:** See the [official installation guide](https://github.com/cli/cli#installation)

#### Authentication

The tool only reads public issue data, so **no authentication is required**. However, if you want to authenticate to avoid rate limits:

```bash
gh auth login
```

#### Caching and Offline Support

The tool includes sophisticated caching to ensure reliable operation in offline environments:

**Automatic Caching:**

- Fetched data is automatically cached for future offline use
- Cache includes 220+ implemented rules as of the latest update
- Cache file: `src/pylint_ruff_sync/data/ruff_implemented_rules.json`

**Manual Cache Updates:**

```bash
# Update cache manually
pylint-ruff-sync --update-cache

# Update cache to custom location
pylint-ruff-sync --update-cache --cache-path /path/to/cache.json

# Use custom cache for operations
pylint-ruff-sync --cache-path /path/to/cache.json --config-file pyproject.toml
```

**Fallback Behavior:**

The tool gracefully handles scenarios where GitHub CLI is unavailable:

```
INFO: Fetching ruff pylint implementation status...
WARNING: Failed to fetch from GitHub: command failed
INFO: Attempting to use cached data...
INFO: Using cached data with 220 rules
```

This ensures the tool works reliably in:

- **precommit.ci** environments (which may restrict external commands)
- CI environments without GitHub CLI installed
- Docker containers without `gh` available
- Corporate networks with restricted tool access
- Offline development environments

#### Error Handling

**When GitHub CLI is unavailable and no cache exists:**

The tool will fail with a clear error message indicating that GitHub CLI is required or cached data is needed.

```
ERROR: Failed to fetch GitHub issue using GitHub CLI
ERROR: No cache available and GitHub fetch failed
ERROR: Make sure 'gh' is installed and available in PATH
```

**Requirements for reliable operation:**

- **Primary:** GitHub CLI (`gh`) must be installed and available in PATH
- **Fallback:** Cached data available when GitHub CLI fails
- **Authentication:** None required (tool only reads public issue data)
- **Network:** Internet connection preferred for live data, cached data for offline use

## Project Structure

```
pylint-ruff-sync/
├── src/pylint_ruff_sync/           # Main package source
│   ├── __init__.py                 # Package initialization
│   ├── main.py                     # CLI entry point and orchestration
│   ├── pylint_extractor.py         # Pylint rule extraction logic
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

## TOML Formatting with toml-sort

The tool automatically applies consistent formatting to the `pyproject.toml` file using [toml-sort](https://github.com/pappasam/toml-sort) via subprocess. This ensures:

- **Consistent key ordering** across all TOML sections
- **Standardized formatting** for arrays and nested structures
- **Preserved comments** while maintaining clean organization
- **Respects your project's toml-sort configuration**

### Configuration

The tool uses the toml-sort CLI via subprocess, which **automatically respects your project's toml-sort configuration** if you have one.

#### Using Default Configuration

If no explicit `[tool.toml-sort]` section exists in your `pyproject.toml`, toml-sort uses its built-in defaults:

```toml
# toml-sort default configuration (automatically applied)
# - Sorts keys alphabetically within sections
# - Maintains section order as defined
# - Preserves comments and formatting where possible
# - Uses consistent indentation and spacing
```

#### Custom Configuration

To customize toml-sort behavior, add a `[tool.toml-sort]` section to your `pyproject.toml`:

```toml
[tool.toml-sort]
# Custom toml-sort configuration
all = true                    # Sort all keys
in_place = true               # Sort in place
trailing_comma_inline_array = false
trailing_comma_multiline_array = true
overrides."tool.poetry.dependencies".first = ["python"]
spaces_indent_inline_array = 2
```

**Common configuration options:**

- **`all = true`**: Sort all keys (default behavior)
- **`trailing_comma_inline_array`**: Control trailing commas in single-line arrays
- **`trailing_comma_multiline_array`**: Control trailing commas in multi-line arrays
- **`spaces_indent_inline_array`**: Set indentation for arrays
- **`overrides`**: Section-specific sorting rules

See the [toml-sort documentation](https://github.com/pappasam/toml-sort#configuration) for all available options.

### Automatic Application

toml-sort is applied automatically during the pylint configuration update process:

1. **Update pylint rules**: Modify enable/disable arrays
2. **Apply toml-sort**: Format the entire file using subprocess
3. **Respect user config**: Use your project's `[tool.toml-sort]` settings
4. **Preserve structure**: Maintain comments and section organization

This ensures that all changes integrate seamlessly with your existing `pyproject.toml` structure while following your preferred formatting standards.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run pre-commit hooks: `pre-commit run --all-files`
6. Submit a pull request

## Development Collaboration

This project was developed through an innovative collaborative process between [Bradley Thornton (cidrblock)](https://github.com/cidrblock) and [Cursor](https://cursor.com) using Claude 4 Sonnet AI. The development process showcased the potential of human-AI collaboration in software engineering.

### The Development Journey

**Initial Problem**: Bradley needed a solution to automatically sync pylint configuration with ruff's implementation status for the ansible-creator project, avoiding duplicate rule checking between the two tools.

**Collaborative Process**:

1. **Problem Definition & Architecture**: Bradley presented the initial requirements and we collaboratively designed the overall architecture, deciding on a precommit hook approach that would surgically update TOML files while preserving formatting.

2. **Iterative Development**: The development proceeded through multiple phases:
   - **Core Implementation**: Built the basic pylint rule extraction and ruff status parsing
   - **TOML Manipulation**: Developed sophisticated regex-based TOML editing that preserves comments and formatting
   - **Error Handling**: Discovered and fixed edge cases through testing on real-world configurations
   - **Architecture Refactoring**: Centralized regex patterns into a dedicated `TomlRegex` class for maintainability
   - **GitHub CLI Integration**: Replaced HTTP requests with direct GitHub CLI calls for better reliability

3. **Problem-Solving Approach**: Each challenge was addressed through:
   - **Analysis**: Understanding the root cause of issues (e.g., `KeyAlreadyPresent` errors, URL format problems)
   - **Solution Design**: Collaborative brainstorming of approaches
   - **Implementation**: AI-assisted coding with human oversight and feedback
   - **Testing**: Comprehensive test coverage with both unit and integration tests
   - **Refinement**: Iterative improvements based on real-world usage

4. **Quality Assurance**: Maintained high code quality through:
   - Type hints for all functions and return types
   - Comprehensive error handling and logging
   - 66 test cases covering edge cases and integration scenarios
   - Adherence to coding standards (ruff, mypy, pylint)
   - Pre-commit hooks ensuring code quality

## Troubleshooting

### Cache File

The tool maintains a cache of ruff implementation status to ensure it works correctly in offline environments like precommit.ci. The cache file is located at:

```
src/pylint_ruff_sync/data/ruff_implemented_rules.json
```

**Cache Behavior:**

- **Online**: When GitHub CLI is available, fetches the latest data from the [ruff tracking issue](https://github.com/astral-sh/ruff/issues/970)
- **Offline**: Falls back to the cached data automatically
- **Format**: JSON file containing detailed rule metadata including implementation status, mypy overlap, and documentation URLs
- **Updates**: Cache is updated when using `--update-cache` flag or when GitHub data is successfully fetched

**Cache Contents:**
The cache contains comprehensive information about each pylint rule:

- Rule ID and name (e.g., `C0103`, `invalid-name`)
- Implementation status in ruff
- Whether the rule overlaps with mypy functionality
- Documentation URLs for each rule
- Rule source (pylint list, ruff issue tracking)

**Troubleshooting Cache Issues:**

- If you encounter unexpected rule behavior, check the cache file contents
- Use `--update-cache` to refresh with latest GitHub data
- The cache only includes rules from official pylint and ruff sources, not user-specific disabled rules
- Cache entries are automatically ordered by pylint rule ID for consistency

### Technical Highlights

The collaboration resulted in several innovative solutions:

- **Surgical TOML Editing**: Regex-based approach that preserves formatting, comments, and structure
- **Direct GitHub Integration**: Real-time fetching of ruff implementation status using GitHub CLI
- **URL Generation**: Automatic generation of documentation links for pylint rules
- **Comprehensive Testing**: Test fixtures demonstrating various TOML configurations and edge cases

### Lessons Learned

This project demonstrated the effectiveness of human-AI collaboration where:

- **Human expertise** provided domain knowledge, requirements clarity, and strategic direction
- **AI capabilities** accelerated implementation, testing, and documentation
- **Iterative feedback** between human and AI led to robust, production-ready code
- **Diverse perspectives** (human creativity + AI systematic analysis) resulted in comprehensive solutions

The final result is a production-ready tool with 220 ruff rule implementations detected, 68 passing tests, and deployment to precommit.ci environments.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the [pylint-to-ruff](https://github.com/akx/pylint-to-ruff) project
- Built for the [ansible-creator](https://github.com/ansible/ansible-creator) project
- References the [ruff pylint tracking issue](https://github.com/astral-sh/ruff/issues/970)
- Uses the approach from [this gist](https://gist.github.com/cidrblock/ec3412bacfeb34dbc2d334c1d53bef83)
