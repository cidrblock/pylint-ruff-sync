"""Constants for the pylint-ruff-sync tool."""

from __future__ import annotations

from typing import Final

# GitHub repo and issue details for ruff pylint implementation tracking
RUFF_REPO = "astral-sh/ruff"
RUFF_PYLINT_ISSUE_NUMBER = "970"
RUFF_PYLINT_ISSUE_URL = (
    f"https://github.com/{RUFF_REPO}/issues/{RUFF_PYLINT_ISSUE_NUMBER}"
)

# Pylint rules that overlap with mypy functionality
# Based on antonagestam/pylint-mypy-overlap analysis
# The rule list is based on research from:
# - GitHub Issue: https://github.com/astral-sh/ruff/issues/970#issuecomment-1565594417
# - Repository: https://github.com/antonagestam/pylint-mypy-overlap
MYPY_OVERLAP_RULES: Final[set[str]] = {
    # Abstract class and method issues
    "E0110",  # abstract-class-instantiated
    "E0100",  # init-is-generator
    "E0301",  # non-iterator-returned
    # Assignment and value issues
    "E1128",  # assignment-from-none
    "E1111",  # assignment-from-no-return
    "E0601",  # used-before-assignment
    "W0601",  # global-variable-undefined
    # Attribute and member access
    "E1101",  # no-member
    "E0202",  # method-hidden
    "E0237",  # assigning-non-slot
    # Callable and function issues
    "E1102",  # not-callable
    "E1120",  # no-value-for-parameter
    "E1121",  # too-many-function-args
    "E1123",  # unexpected-keyword-arg
    "E1124",  # redundant-keyword-arg
    "E1125",  # missing-kwoa
    "W0143",  # comparison-with-callable
    # Class and inheritance issues
    "E0239",  # inherit-non-class
    "E0240",  # inconsistent-mro
    "E0243",  # invalid-class-object
    "E0244",  # invalid-enum-extension
    "W0221",  # arguments-differ
    "W0222",  # signature-differs
    "W0236",  # invalid-overridden-method
    "W0239",  # overridden-final-method
    "W0240",  # subclassed-final-class
    "W0245",  # super-without-brackets
    # Context manager issues
    "E1129",  # not-context-manager
    "E1701",  # not-async-context-manager
    # Exception handling
    "E0702",  # raising-bad-type
    "E0705",  # bad-exception-cause
    "E0710",  # raising-non-exception
    "E0712",  # catching-non-exception
    "W0716",  # wrong-exception-operation
    # Format and string issues
    "E1300",  # bad-format-character
    "E0306",  # invalid-repr-returned
    "E0307",  # invalid-str-returned
    "E0309",  # invalid-hash-returned
    "E0311",  # invalid-format-returned
    "W1303",  # missing-format-argument-key
    "W1305",  # format-combined-specification
    "W1306",  # missing-format-attribute
    "E0119",  # misplaced-format-function
    # Import issues
    "E0401",  # import-error
    "E0402",  # relative-beyond-top-level
    # Iterable and sequence issues
    "E1133",  # not-an-iterable
    "E1134",  # not-a-mapping
    "E1135",  # unsupported-membership-test
    "E1136",  # unsubscriptable-object
    "E1126",  # invalid-sequence-index
    "E1127",  # invalid-slice-index
    "E0111",  # bad-reversed-sequence
    "E0633",  # unpacking-non-sequence
    "E1143",  # unhashable-member
    "E1141",  # dict-iter-missing-items
    # Metaclass and slot issues
    "E1139",  # invalid-metaclass
    "E0236",  # invalid-slots-object
    "E0238",  # invalid-slots
    # Operation issues
    "E1130",  # invalid-unary-operand-type
    "E1131",  # unsupported-binary-operation
    "E1137",  # unsupported-assignment-operation
    "E1138",  # unsupported-delete-operation
    # Star assignment and unpacking
    "E0113",  # invalid-star-assignment-target
    "E0114",  # star-needs-assignment-target
    "W0632",  # unbalanced-tuple-unpacking
    "W0644",  # unbalanced-dict-unpacking
    # Super call issues
    "E1003",  # bad-super-call
    # Threading issues
    "W1506",  # bad-thread-instantiation
    # Type annotation issues
    "C0131",  # typevar-double-variance
    "C0132",  # typevar-name-mismatch
    "W1115",  # non-str-assignment-to-dunder-name
    "W1116",  # isinstance-second-argument-not-valid-type
    # Unicode and encoding
    "E2501",  # invalid-unicode-codec
    # Variable scope issues
    "E0115",  # nonlocal-and-global
    "W0642",  # self-cls-assignment
    # Version compatibility
    "W2602",  # using-final-decorator-in-unsupported-version
    # Environment and system issues
    "E1507",  # invalid-envvar-value
    # Deprecated functionality
    "W4904",  # deprecated-class
}
