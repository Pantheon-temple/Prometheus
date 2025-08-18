from typing import Annotated, Mapping, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from prometheus.models.context import Context


class BugReproductionState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    max_refined_query_loop: int

    bug_reproducing_query: str
    bug_reproducing_context: Sequence[Context]

    bug_reproducing_write_messages: Annotated[Sequence[BaseMessage], add_messages]
    bug_reproducing_file_messages: Annotated[Sequence[BaseMessage], add_messages]
    bug_reproducing_execute_messages: Annotated[Sequence[BaseMessage], add_messages]

    bug_reproducing_patch: str

    reproduced_bug: bool
    reproduced_bug_failure_log: str
    reproduced_bug_file: str
    reproduced_bug_commands: Sequence[str]
