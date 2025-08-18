import logging
import threading

from prometheus.lang_graph.subgraphs.bug_get_regression_tests_state import (
    BugGetRegressionTestsState,
)
from prometheus.utils.issue_util import format_issue_info


class BugGetRegressionContextMessageNode:
    SELECT_REGRESSION_QUERY = """\
We are currently solving the following issue within our repository. Here is the issue text:

--- BEGIN ISSUE ---
{issue_info}
--- END ISSUE ---

And we need to find relevant existing tests that can be used as regression tests for this issue.

OBJECTIVE: Find {number_of_selected_regression_tests} relevant existing test cases that most likely to break existing functionality if this issue is fixed or new changes apply.
including ALL necessary imports, test setup, mocking, assertions, and any test method used in the test case.

<reasoning>
1. Analyze bug characteristics:
   - Core functionality being tested
   - Input parameters and configurations
   - Expected error conditions
   - Environmental dependencies

2. Search requirements:
   - Required imports and dependencies
   - Test files exercising similar functionality
   - Mock/fixture setup patterns
   - Assertion styles
   - Error handling tests

3. Focus areas:
   - All necessary imports (standard library, testing frameworks, mocking utilities)
   - Dependencies and third-party packages
   - Test setup and teardown
   - Mock object configuration
   - Network/external service simulation
   - Error condition verification
</reasoning>

REQUIREMENTS:
- Return {number_of_selected_regression_tests} complete, self-contained test cases that most likely to break existing functionality if this issue is fixed or new changes apply.
- Must include the identification of the test case (e.g., class name and method name)
- Must preserve exact file paths and line numbers

<examples>
--- BEGIN ISSUE ---
Title: parse_iso8601 drops timezone information for 'Z' suffix
Body: The helper `parse_iso8601` in `utils/datetime.py` incorrectly returns a naive datetime when the input ends with 'Z' (UTC). For example, "2024-10-12T09:15:00Z" becomes a naive dt instead of timezone-aware UTC. This breaks downstream scheduling.
Expected: Return timezone-aware datetime in UTC for 'Z' inputs and preserve offsets like "+09:00".
--- END ISSUE ---
--- BEGIN TEST CASES ---
File: tests/test_datetime.py
Line Number: 118-156
Content:
import datetime
import pytest

from utils.datetime import parse_iso8601  # target under test

def test_z_suffix_returns_utc_aware(self):
    # Input ending with 'Z' should be interpreted as UTC and be timezone-aware
    s = "2024-10-12T09:15:00Z"
    dt = parse_iso8601(s)

    assert isinstance(dt, datetime.datetime)
    assert dt.tzinfo is not None
    # Use UTC comparison that works across pytz/zoneinfo
    assert dt.utcoffset() == datetime.timedelta(0)

def test_offset_preserved(self):
    # Offset like +09:00 should be preserved (e.g., Asia/Tokyo offset)
    s = "2024-10-12T18:00:00+09:00"
    dt = parse_iso8601(s)

    assert isinstance(dt, datetime.datetime)
    assert dt.tzinfo is not None
    assert dt.utcoffset() == datetime.timedelta(hours=9)
--- END TEST CASES ---
</example>
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.bug_get_regression_context_message_node"
        )

    def __call__(self, state: BugGetRegressionTestsState):
        select_regression_query = self.SELECT_REGRESSION_QUERY.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
            number_of_selected_regression_tests=state["number_of_selected_regression_tests"] + 3,
        )
        self._logger.debug(
            f"Sending query to context provider subgraph:\n{select_regression_query}"
        )
        return {"select_regression_query": select_regression_query}
