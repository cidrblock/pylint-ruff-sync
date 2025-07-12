# Integration Example for ansible-creator

This document shows how to integrate the pylint-ruff sync precommit hook into the ansible-creator project.

## Steps for Integration

### 1. Update .pre-commit-config.yaml

Add the following hook to the ansible-creator's `.pre-commit-config.yaml`:

```yaml
repos:
  # ... existing repos ...

  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0 # Use the latest version
    hooks:
      - id: pylint-ruff-sync
        # Optional: Add custom rules specific to ansible-creator
        args: [
            "--custom-enable",
            "C0103", # Allow specific naming patterns
            "--custom-disable",
            "R0903", # Disable too-few-public-methods for DTOs
          ]
```

That's it! No need to copy scripts or manage dependencies manually. The custom rules will be preserved and noted in the generated configuration.

### 2. Test the Integration

Run pre-commit to test the hook:

```bash
pre-commit run pylint-ruff-sync --all-files
```

Or test manually if you have the package installed:

```bash
# Test dry run
pylint-ruff-sync --dry-run --verbose

# Apply changes
pylint-ruff-sync --verbose
```

### 3. First Run Output

After the first run, your `pyproject.toml` should have an updated pylint configuration like:

```toml
[tool.pylint.messages_control]
# This section will be automatically updated by the precommit hook
# based on ruff implementation status from https://github.com/astral-sh/ruff/issues/970
# Custom rules added via --custom-enable and --custom-disable are preserved
enable = [
    # Rules NOT implemented in ruff - automatically generated with documentation URLs
    "C0103",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/invalid-name.html
    "C0112",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/empty-docstring.html
    "C0113",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/unneeded-not.html
    "R0124",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/refactor/comparison-with-callable.html
    "W0108",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/warning/unnecessary-lambda.html
    # ... more rules (only those not implemented in ruff)
]
disable = [
    # Custom disabled rules
    "R0903",  # too-few-public-methods (custom disabled)
]
```

## Benefits for ansible-creator

1. **Reduced Duplication**: Avoid running the same checks in both ruff and pylint
2. **Better Performance**: Faster CI/CD due to reduced duplicate work
3. **Always Current**: Automatically adapts as ruff implements more rules
4. **Consistent**: Ensures the team is always using the most up-to-date configuration
5. **Shorter Lists**: Enable-only approach creates more maintainable configuration
6. **Future-Proof**: Rule lists get shorter over time as ruff implements more rules

## Maintenance

The hook will automatically:

- Run whenever `pyproject.toml` is modified
- Check the GitHub issue for the latest ruff implementation status
- Update the pylint configuration to enable only non-implemented rules
- Work with pre-commit.ci for automated updates
- Create shorter, more maintainable rule lists that shrink over time

No manual maintenance is required - the hook keeps everything in sync automatically.

## Troubleshooting

If the hook fails:

1. **Check Network**: Ensure the CI/CD environment can access GitHub
2. **Check Pylint**: Ensure pylint is installed and accessible in the environment
3. **Manual Run**: Test the hook manually with `pylint-ruff-sync --dry-run --verbose`
4. **Version Issues**: Make sure you're using the correct `rev` in your `.pre-commit-config.yaml`

## Example CI/CD Workflow

The hook integrates seamlessly with GitHub Actions:

```yaml
name: Pre-commit

on:
  pull_request:
  push:
    branches: [main]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - uses: pre-commit/action@v3.0.0
```

The `update-pylint-config` hook will run automatically and update the configuration if needed.
