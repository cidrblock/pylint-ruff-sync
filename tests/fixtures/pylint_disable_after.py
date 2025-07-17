# Example 1: Disable by rule name (single line) - REMOVED if eval-used is useless
x = eval("1 + 2")

# Example 2: Disable by rule code (single line) - REMOVED if W0123 is useless
y = eval("3 + 4")


# Example 3: Disable multiple rules by name - PARTIAL removal if some rules are useless
def foo(bar):  # pylint: disable=some-necessary-rule
    pass


# Example 4: Disable multiple rules by code - PARTIAL removal if some rules are useless
def bar(baz):  # pylint: disable=C0116
    pass


# Example 5a: Disable with # noqa (other tool) plus pylint - PRESERVE noqa, remove pylint if useless
z = eval("5 + 6")

# Example 5b: Combine for both tools in one comment - PRESERVE noqa, remove pylint if useless
w = eval("7 + 8")

# Example 6: Disable for an entire file - REMOVED if skip-file is useless
# (This line would be completely removed)


# Example 7: Mixed necessary and unnecessary rules - PARTIAL removal
def mixed_example():  # pylint: disable=some-necessary-rule
    print("This has both necessary and unnecessary disables")


# Example 8: Standalone comment line with disable - REMOVED if useless


# Example 9: Multiple lines with different patterns
def complex_function(arg1, arg2):  # pylint: disable=too-many-arguments
    # This line has an unnecessary disable - REMOVED
    result = eval("arg1 + arg2")
    return result


# Example 10: Whitespace variations - PARTIAL removal if some rules are useless
def whitespace_test():  # pylint:disable=bad-whitespace
    pass


# Example 11: Comment with other content - PRESERVE other content, remove pylint if useless
def documented_disable():  # This disables a check
    """This function actually has a docstring."""
