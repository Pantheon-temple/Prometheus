import logging
import threading
from typing import Dict

from prometheus.utils.issue_util import format_issue_info


class IssueQuestionContextMessageNode:
    QUESTION_QUERY = """\
{issue_info}

Find all relevant source code context and documentation needed to understand and answer this issue.
Focus on both production code (ignore test files) and documentations (e.g. README.md) and follow these steps:
1. Identify key components mentioned in the issue (functions, classes, types, etc.)
2. Find their complete implementations and class definitions
3. Include related code from the same module that affects the behavior
4. Follow imports to find dependent code that directly impacts the issue
5. Include relevant documentation that helps understand the issue

Skip any test files
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_question_context_message_node"
        )

    def __call__(self, state: Dict):
        question_query = self.QUESTION_QUERY.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
        )
        self._logger.debug(f"Sending query to context provider:\n{question_query}")
        return {"question_query": question_query}
