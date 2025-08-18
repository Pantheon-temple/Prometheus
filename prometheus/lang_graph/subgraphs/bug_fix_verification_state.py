from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BugFixVerificationState(TypedDict):
    reproduced_bug_file: str
    reproduced_bug_commands: Sequence[str]
    reproduced_bug_patch: str

    bug_fix_verify_messages: Annotated[Sequence[BaseMessage], add_messages]

    reproducing_test_fail_log: str

    edit_patch: str
