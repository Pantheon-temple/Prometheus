from typing import Dict

from langchain_core.messages import HumanMessage

from prometheus.utils.issue_util import format_issue_info
from prometheus.utils.logger_manager import get_logger


class IssueBugAnalyzerMessageNode:
    FIRST_HUMAN_PROMPT = """\
I am going to share details about an issue reported to a codebase and its related bug context.
Please analyze this bug and provide a high-level description of what needs to be changed:

1. Issue Understanding:
- Analyze the issue title, description, and comments provided
- Identify the reported symptoms and unexpected behaviors

2. Code Analysis:
- Identify which files, functions, or code blocks are involved
- Explain what the problematic code is currently doing

3. Root Cause:
- Explain why the current behavior is incorrect
- Identify which specific parts of the code are causing the issue

4. Fix Suggestion:
For each needed change, describe in plain English:
- Which file needs to be modified
- Which function or code block needs changes
- What needs to be changed (e.g., "rename variable x to y", "add null check for parameter z")
- Why this change would fix the issue

Do NOT provide actual code snippets or diffs. Focus on describing what needs to be changed.

Here are the details for analysis:

{issue_info}

Bug Context:
{bug_fix_context}
"""

    FOLLOWUP_HUMAN_PROMPT = """\
Given your suggestion, the edit agent generated the following patch:
{edit_patch}

The patch generated following error:
{edit_error}

Please analyze the failure and provide a revised suggestion:

1. Error Analysis:
- Explain why the previous changes failed
- Identify what specific aspects were problematic

2. Revised Fix Suggestion:
Describe in plain English:
- Which file needs to be modified
- Which function or code block needs changes
- What needs to be changed (e.g., "rename variable x to y", "add null check for parameter z")
- Why this change would fix both the original issue and the new error

Do NOT provide actual code snippets or diffs. Focus on describing what needs to be changed.
"""

    def __init__(self):
        self._logger = get_logger(__name__)

    def format_human_message(self, state: Dict):
        edit_error = ""
        if "reproducing_test_fail_log" in state and state["reproducing_test_fail_log"]:
            edit_error = f"The patch failed to pass the bug exposing test cases:\n{state['reproducing_test_fail_log']}"
        elif "build_fail_log" in state and state["build_fail_log"]:
            edit_error = f"The patch failed to pass the build:\n{state['build_fail_log']}"
        elif "existing_test_fail_log" in state and state["existing_test_fail_log"]:
            edit_error = (
                f"The patch failed to existing test cases:\n{state['existing_test_fail_log']}"
            )

        if not edit_error:
            return HumanMessage(
                self.FIRST_HUMAN_PROMPT.format(
                    issue_info=format_issue_info(
                        state["issue_title"], state["issue_body"], state["issue_comments"]
                    ),
                    bug_fix_context="\n\n".join(
                        [str(context) for context in state["bug_fix_context"]]
                    ),
                )
            )

        return HumanMessage(
            self.FOLLOWUP_HUMAN_PROMPT.format(
                edit_patch=state["edit_patch"],
                edit_error=edit_error,
            )
        )

    def __call__(self, state: Dict):
        human_message = self.format_human_message(state)
        self._logger.debug(f"Sending message to IssueBugAnalyzerNode:\n{human_message}")
        return {"issue_bug_analyzer_messages": [human_message]}
