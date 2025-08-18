import logging
import threading
from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.subgraphs.run_regression_tests_state import RunRegressionTestsState
from prometheus.utils.lang_graph_util import get_last_message_content


class RunRegressionTestsStructureOutput(BaseModel):
    passed_regression_tests: Sequence[str] = Field(
        description="List of test identifier of regression tests that passed (e.g., class name and method name)"
    )
    regression_test_fail_log: str = Field(
        description="If the test failed, contains the complete test FAILURE log. Otherwise empty string"
    )
    total_tests_run: int = Field(
        description="Total number of tests run, including both passed and failed tests"
    )


class RunRegressionTestsStructuredNode:
    SYS_PROMPT = """\
You are a test result parser. Your only task is to check if the executed tests passed.

Your task is to:
1. Check which sets of tests passes by looking for test pass indicators:
   - Test summary showing "passed" or "PASSED"
   - Warning is ok
   - No "FAILURES" section
2. If a test fails, capture the complete failure output
3. Return the exact test identifiers that passed

Return:
- passed_regression_tests: List of test identifier of regression tests that passed (e.g., class name and method name)
- regression_test_fail_log: empty string if all tests pass, exact complete test output if a test fails
- total_tests_run: Total number of tests run, including both passed and failed tests

Example 1:
```
Run Regression Tests Logs:
============================= test session starts ==============================
collecting ... collected 7 items

test_file_operation.py::test_create_and_read_file PASSED                 [ 14%]
test_file_operation.py::test_read_file_nonexistent PASSED                [ 28%]
test_file_operation.py::test_read_file_with_line_numbers PASSED          [ 42%]
test_file_operation.py::test_delete PASSED                               [ 57%]
test_file_operation.py::test_delete_nonexistent PASSED                   [ 71%]
test_file_operation.py::test_edit_file PASSED                            [ 85%]
test_file_operation.py::test_create_file_already_exists PASSED           [100%]

============================== 7 passed in 1.53s ===============================
```

Example 1 Output:
{{  
    "passed_regression_tests": [
        "test_file_operation.py::test_create_and_read_file",
        "test_file_operation.py::test_read_file_nonexistent",
        "test_file_operation.py::test_read_file_with_line_numbers",
        "test_file_operation.py::test_delete",
        "test_file_operation.py::test_delete_nonexistent",
        "test_file_operation.py::test_edit_file",
        "test_file_operation.py::test_create_file_already_exists"
    ],
    "reproducing_test_fail_log": "" # ONLY output the log exact and complete test FAILURE log when test failure. Otherwise empty string,
    "total_tests_run": 7
}}

Important:
- Only look at test pass/fail status
- A single failing test means the test is not passing
- Include complete test output in failure log
- Do Not output any log when where is no test executed. ONLY output the log exact and complete test FAILURE log when test failure!
"""
    HUMAN_PROMPT = """
We have run the selected regression tests on the codebase.
The following regression tests were selected to run:
--- BEGIN SELECTED REGRESSION TESTS ---
{selected_regression_tests}
--- END SELECTED REGRESSION TESTS ---
Run Regression Tests Logs:
--- BEGIN LOG ---
{run_regression_tests_messages}
--- END LOG ---
Please analyze the logs and determine which regression tests passed!. You should return the exact test identifier 
that we give to you.
"""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{human_message}")]
        )
        structured_llm = model.with_structured_output(RunRegressionTestsStructureOutput)
        self.model = prompt | structured_llm
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.run_regression_tests_structure_node"
        )

    def get_human_message(self, state: RunRegressionTestsState) -> str:
        # Format the human message using the state
        return self.HUMAN_PROMPT.format(
            selected_regression_tests="\n".join(state["selected_regression_tests"]),
            run_regression_tests_messages=get_last_message_content(
                state["run_regression_tests_messages"]
            ),
        )

    def __call__(self, state: RunRegressionTestsState):
        # Get human message from the state
        human_message = self.get_human_message(state)
        self._logger.debug(f"Human Message: {human_message}")
        response = self.model.invoke({"human_message": human_message})
        # Log the full response for debugging
        self._logger.debug(response)
        return {
            "regression_test_fail_log": response.regression_test_fail_log,
            "passed_regression_tests": response.passed_regression_tests,
            "total_tests_run": response.total_tests_run,
        }
