from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class RunRegressionTestsState(TypedDict):
    passed_regression_tests: Sequence[str]

    selected_regression_tests: Sequence[str]

    run_regression_tests_messages: Annotated[Sequence[BaseMessage], add_messages]

    regression_test_fail_log: str

    total_tests_run: int
