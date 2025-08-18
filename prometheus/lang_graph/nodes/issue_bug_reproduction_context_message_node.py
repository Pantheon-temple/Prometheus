import logging
import threading

from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.utils.issue_util import format_issue_info


class IssueBugReproductionContextMessageNode:
    BUG_REPRODUCING_QUERY = """\
{issue_info}

OBJECTIVE: Find three relevant existing test cases that demonstrates similar functionality to the reported bug,
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
- Return THREE complete, self-contained test cases most similar to bug scenario
- Must include ALL necessary imports at the start of each test file
- Must include full test method implementation
- Must include ALL mock/fixture setup
- Must include helper functions used by test
- Must preserve exact file paths and line numbers

<examples>
<example id="database-timeout">
<bug>
db.execute("SELECT * FROM users").fetchall() 
raises ConnectionTimeout when load is high
</bug>

<ideal_test_match>
# File: tests/test_database.py
import pytest
from unittest.mock import Mock, patch
from database.exceptions import ConnectionTimeout
from database.models import QueryResult
from database.client import DatabaseClient

class TestDatabaseTimeout:
    @pytest.fixture
    def mock_db_connection(self):
        conn = Mock()
        conn.execute.side_effect = [
            ConnectionTimeout("Connection timed out"),
            QueryResult(["user1", "user2"])  # Second try succeeds
        ]
        return conn
        
    def test_handle_timeout_during_query(self, mock_db_connection):
        # Complete test showing timeout scenario
        # Including retry logic verification
        # With all necessary assertions
</ideal_test_match>
</example>

<example id="file-permission">
<bug>
FileProcessor('/root/data.txt').process() 
fails with PermissionError
</bug>

<ideal_test_match>
# File: tests/test_file_processor.py
import os
import pytest
from unittest.mock import patch, mock_open
from file_processor import FileProcessor
from file_processor.exceptions import ProcessingError

class TestFilePermissions:
    @patch('os.access')
    @patch('builtins.open')
    def test_file_permission_denied(self, mock_open, mock_access):
        # Full test setup with mocked file system
        # Permission denial simulation
        # Error handling verification
</ideal_test_match>
</example>

Search priority:
1. Tests of exact same functionality (including import patterns)
2. Tests with similar error conditions
3. Tests with comparable mocking patterns
4. Tests demonstrating similar assertions

Find the THREE most relevant test cases with complete context, ensuring ALL necessary imports are included at the start of each test file.
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_bug_reproduction_context_message_node"
        )

    def __call__(self, state: BugReproductionState):
        bug_reproducing_query = self.BUG_REPRODUCING_QUERY.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
        )
        self._logger.debug(f"Sending query to context provider subgraph:\n{bug_reproducing_query}")
        return {"bug_reproducing_query": bug_reproducing_query}
