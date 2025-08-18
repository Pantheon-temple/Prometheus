import logging
import threading

from langchain_core.messages import HumanMessage

from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.utils.issue_util import format_issue_info


class BugReproducingWriteMessageNode:
    FIRST_HUMAN_PROMPT = """\
{issue_info}

Bug reproducing context:
{bug_reproducing_context}

Now generate the complete self-contained test case that reproduces the bug with the same error/exception.
"""

    FOLLOWUP_HUMAN_PROMPT = """\
Your previous test case failed to reproduce the bug. Here is the failure log:
{reproduced_bug_failure_log}

Now think about what went wrong and generate the complete self-contained test case that reproduces the bug with the same error/exception again.
"""

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.bug_reproducing_write_message_node"
        )

    def format_human_message(self, state: BugReproductionState):
        if "reproduced_bug_failure_log" in state and state["reproduced_bug_failure_log"]:
            return HumanMessage(
                self.FOLLOWUP_HUMAN_PROMPT.format(
                    reproduced_bug_failure_log=state["reproduced_bug_failure_log"],
                )
            )

        return HumanMessage(
            self.FIRST_HUMAN_PROMPT.format(
                issue_info=format_issue_info(
                    state["issue_title"], state["issue_body"], state["issue_comments"]
                ),
                bug_reproducing_context="\n\n".join(
                    [str(context) for context in state["bug_reproducing_context"]]
                ),
            )
        )

    def __call__(self, state: BugReproductionState):
        human_message = self.format_human_message(state)
        self._logger.debug(f"Sending message to BugReproducingWriteNode:\n{human_message}")
        return {"bug_reproducing_write_messages": [human_message]}
