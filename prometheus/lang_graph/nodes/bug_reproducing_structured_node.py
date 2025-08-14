from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.utils.issue_util import format_issue_comments
from prometheus.utils.lang_graph_util import (
    format_agent_tool_message_history,
    get_last_message_content,
)
from prometheus.utils.logger_manager import get_logger


class BugReproducingStructuredOutput(BaseModel):
    reproduced_bug: bool = Field(
        description="True ONLY if test fails as described in the issue and uses provided examples if any exist"
    )
    reproduced_bug_failure_log: str = Field(
        description="Complete test execution log. If test passes, include explanation that test should fail to demonstrate the bug"
    )
    reproduced_bug_commands: Sequence[str] = Field(
        description="A list of commands run to the single file to reproduce the bug"
    )


class BugReproducingStructuredNode:
    SYS_PROMPT = """\
You are an agent that verifies if a test properly reproduces a reported bug. You analyze:
1. Issue description and any provided examples
2. The test code written to reproduce the bug
3. The test execution results

For reproduced_bug to be True, the test MUST:
1. Fail (since bug isn't fixed yet)
2. Fail in exactly the same way described in the issue
3. Use the exact examples from the issue if any were provided
4. Demonstrate the same underlying problem

Set reproduced_bug_failure_log to contain:
- The complete test execution output/log
- For passing tests: Explanation that test passed but should fail to demonstrate the unfixed bug
- For wrong failures: Full error log and explanation of how the error differs from what's described
- For wrong examples: Full error log and explanation of which example from the issue should be used
- For wrong behavior: Full error log and explanation of what behavior should be tested instead
- For any other issues: Full error log and detailed explanation of the problem

Example 1 - Correct Reproduction:
```
Issue:
Title: Array.pop() crashes on empty array
Description: Calling pop() on empty array throws "Cannot read property 'length' of undefined" but should throw "Array is empty"
Example: let arr = []; arr.pop(); // Shows wrong error

Test:
def test_empty_array_pop():
    arr = []
    with pytest.raises(ValueError, match="Cannot read property 'length' of undefined"):
        arr.pop()

Result: Test failed with "Cannot read property 'length' of undefined"

Output:
{
    "reproduced_bug": true,
    "reproduced_bug_failure_log": "FAILED tests/test_array.py::test_empty_array_pop - Cannot read property 'length' of undefined",
    "reproduced_bug_commands": ["pytest tests/test_array.py"]
}
```

Example 2 - Wrong Error:
```
Issue:
Title: Array.pop() crashes on empty array
Description: Calling pop() on empty array throws "Cannot read property 'length' of undefined" but should throw "Array is empty"
Example: let arr = []; arr.pop(); // Shows wrong error

Test:
def test_empty_array_pop():
    arr = []
    with pytest.raises(IndexError):
        arr.pop()

Result: Test failed with "IndexError: pop from empty list"

Output:
{
    "reproduced_bug": false,
    "reproduced_bug_failure_log": "FAILED tests/test_array.py::test_empty_array_pop - IndexError: pop from empty list\\n\\nTest fails with IndexError but issue describes 'Cannot read property length' error. Test needs to verify the specific error message reported in the bug.",
    "reproduced_bug_commands": ["pytest tests/test_array.py"]
}
```

Example 3 - Wrong Example:
```
Issue:
Title: Array.pop() crashes on empty array
Description: Calling pop() on empty array throws "Cannot read property 'length' of undefined" but should throw "Array is empty"
Example: let arr = []; arr.pop(); // Shows wrong error

Test:
def test_array_pop():
    arr = [1, 2, 3]
    arr.pop()
    assert len(arr) == 2

Result: Test passed

Output:
{
    "reproduced_bug": false,
    "reproduced_bug_failure_log": "PASSED tests/test_array.py::test_array_pop\\n\\nTest passes but should fail since the bug is not fixed. Test should verify pop() behavior on an empty array as shown in the issue example. Current test uses [1,2,3] array which doesn't demonstrate the reported bug.",
    "reproduced_bug_commands": ["pytest tests/test_array.py"]
}
""".replace("{", "{{").replace("}", "}}")

    HUMAN_PROMPT = """\
ISSUE INFORMATION:
Title: {title}
Description: {body}
Comments: {comments}

Bug reproduction code:
{bug_reproducing_code}

Log from executing bug reproducing file:
{bug_reproducing_log}
"""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{bug_reproducing_info}")]
        )
        structured_llm = model.with_structured_output(BugReproducingStructuredOutput)
        self.model = prompt | structured_llm
        self._logger = get_logger(__name__)

    def __call__(self, state: BugReproductionState):
        bug_reproducing_log = format_agent_tool_message_history(
            state["bug_reproducing_execute_messages"]
        )
        bug_reproducing_info = self.HUMAN_PROMPT.format(
            title=state["issue_title"],
            body=state["issue_body"],
            comments=format_issue_comments(state["issue_comments"]),
            bug_reproducing_code=get_last_message_content(state["bug_reproducing_write_messages"]),
            bug_reproducing_log=bug_reproducing_log,
        )

        response = self.model.invoke({"bug_reproducing_info": bug_reproducing_info})
        self._logger.debug(response)

        return {
            "reproduced_bug": response.reproduced_bug,
            "reproduced_bug_failure_log": response.reproduced_bug_failure_log,
            "reproduced_bug_commands": response.reproduced_bug_commands,
        }
