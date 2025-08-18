from typing import Annotated, Mapping, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from prometheus.models.context import Context
from prometheus.models.test_patch_result import TestedPatchResult


class IssueVerifiedBugState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    max_refined_query_loop: int
    refined_query: str

    run_build: bool
    run_existing_test: bool
    run_regression_test: bool

    selected_regression_tests: Sequence[str]
    tested_patch_result: Sequence[TestedPatchResult]

    reproduced_bug_file: str
    reproduced_bug_commands: Sequence[str]
    reproduced_bug_patch: str

    bug_fix_query: str
    bug_fix_context: Sequence[Context]

    issue_bug_analyzer_messages: Annotated[Sequence[BaseMessage], add_messages]
    edit_messages: Annotated[Sequence[BaseMessage], add_messages]

    edit_patch: str

    reproducing_test_fail_log: str

    exist_build: bool
    build_command_summary: str
    build_fail_log: str

    exist_test: bool
    test_command_summary: str
    existing_test_fail_log: str
