import logging
import threading

from prometheus.lang_graph.subgraphs.issue_classification_state import IssueClassificationState
from prometheus.utils.issue_util import format_issue_info


class IssueClassificationContextMessageNode:
    ISSUE_CLASSIFICATION_QUERY = """\
{issue_info}

OBJECTIVE: Find ALL self-contained context needed to accurately classify this issue as a bug, feature request, documentation update, or question.

<reasoning>
1. Analyze issue characteristics:
   - Error patterns suggesting bugs
   - New functionality requests
   - Documentation gaps
   - Knowledge-seeking patterns

2. Search strategy:
   - Implementation files matching descriptions
   - Similar existing features
   - Documentation coverage
   - Related Q&A patterns

3. Required context categories:
   - Core implementations
   - Feature interfaces
   - Documentation files
   - Test coverage
   - Configuration settings
   - Issue history
</reasoning>

REQUIREMENTS:
- Context MUST be fully self-contained
- MUST include complete file paths
- MUST include full function/class implementations
- MUST preserve all code structure and formatting
- MUST include line numbers

<examples>
<example id="error-classification">
<issue>
Database queries timing out randomly
Error: Connection pool exhausted
</issue>

<search_targets>
1. Connection pool implementation
2. Database configuration
3. Error handling code
4. Related timeout settings
</search_targets>

<expected_context>
- Complete connection pool class
- Full database configuration
- Error handling implementations
- Timeout management code
</expected_context>
</example>
</examples>

Search priority:
1. Implementation patterns matching issue
2. Feature definitions and interfaces
3. Documentation coverage
4. Configuration schemas
5. Test implementations
6. Integration patterns
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_classification_context_message_node"
        )

    def __call__(self, state: IssueClassificationState):
        issue_classification_query = self.ISSUE_CLASSIFICATION_QUERY.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
        )
        self._logger.debug(f"Sending query to context provider:\n{issue_classification_query}")
        return {"issue_classification_query": issue_classification_query}
