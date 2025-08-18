import logging
import threading
from typing import Dict

from prometheus.utils.issue_util import format_issue_info


class IssueBugContextMessageNode:
    BUG_FIX_QUERY = """\
{issue_info}

Find all relevant source code context and documentation needed to understand and fix this issue.
Focus on production code (ignore test files) and follow these steps:
1. Identify key components mentioned in the issue, especially from the error message(functions, classes, types, etc.)
2. Find their complete implementations and class definitions
3. Include related code from the same module that affects the behavior
4. Follow imports to find dependent code that directly impacts the issue

Skip any test files
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_bug_context_message_node"
        )

    def __call__(self, state: Dict):
        bug_fix_query = self.BUG_FIX_QUERY.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
        )
        self._logger.debug(f"Sending query to context provider:\n{bug_fix_query}")
        return {"bug_fix_query": bug_fix_query}
