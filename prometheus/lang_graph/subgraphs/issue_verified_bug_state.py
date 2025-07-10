from operator import add
from typing import Annotated, Mapping, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IssueVerifiedBugState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]
    run_build: bool
    run_existing_test: bool

    reproduced_bug_file: str
    reproduced_bug_commands: Sequence[str]
    max_refined_query_loop: int

    bug_fix_query: str
    bug_fix_context: Sequence[str]

    issue_bug_analyzer_messages: Annotated[Sequence[BaseMessage], add_messages]
    edit_messages: Annotated[Sequence[BaseMessage], add_messages]

    edit_patch: str
    edit_patches: Annotated[Sequence[str], add]

    reproducing_test_fail_log: str

    exist_build: bool
    build_command_summary: str
    build_fail_log: str

    exist_test: bool
    test_command_summary: str
    existing_test_fail_log: str

    max_refined_query_loop: int
    refined_query: str

    number_of_candidate_patch: int
