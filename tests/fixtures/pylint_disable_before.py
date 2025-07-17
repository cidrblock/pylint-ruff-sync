# Example 1: Disable by rule name (single line)
x = eval("1 + 2")  # pylint: disable=eval-used

# Example 2: Disable by rule code (single line)
y = eval("3 + 4")  # pylint: disable=W0123


# Example 3: Disable multiple rules by name
def foo(bar):  # pylint: disable=unused-argument,missing-function-docstring
    pass


# Example 4: Disable multiple rules by code
def bar(baz):  # pylint: disable=W0613,C0116
    pass


# Example 5a: Disable with
z = eval("5 + 6")  # pylint: disable=eval-used

# Example 5b: Combine for both tools in one comment (rare, but possible)
w = eval("7 + 8")

# Example 6: Disable for an entire file (at the top of the file)
# pylint: skip-file


# Example 7: Mixed necessary and unnecessary rules
def mixed_example():  # pylint: disable=missing-function-docstring,some-necessary-rule
    print("This has both necessary and unnecessary disables")


# Example 8: Standalone comment line with disable
# pylint: disable=unused-import


# Example 9: Multiple lines with different patterns
def complex_function(arg1, arg2):  # pylint: disable=too-many-arguments
    # This line has an unnecessary disable
    result = eval("arg1 + arg2")  # pylint: disable=eval-used
    return result


# Example 10: Whitespace variations
def whitespace_test():  # pylint:disable=bad-whitespace,missing-function-docstring
    pass


# Example 11: Comment with other content
def documented_disable():  # This disables a check  # pylint: disable=missing-function-docstring
    """This function actually has a docstring."""
