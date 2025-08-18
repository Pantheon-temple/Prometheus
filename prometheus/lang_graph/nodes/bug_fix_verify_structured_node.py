import logging
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.subgraphs.bug_fix_verification_state import BugFixVerificationState
from prometheus.utils.lang_graph_util import get_last_message_content


class BugFixVerifyStructureOutput(BaseModel):
    reproducing_test_fail_log: str = Field(
        description="If the test failed, contains the complete test failure log. Otherwise empty string"
    )


class BugFixVerifyStructuredNode:
    SYS_PROMPT = """\
You are a test result parser. Your only task is to check if the bug reproducing test now passes after code changes.

Your task is to:
1. Check if the test passes by looking for test pass indicators:
   - Test summary showing "passed" or "PASSED"
   - Warning is ok
   - No "FAILURES" section
2. If the test fails, capture the complete failure output

Return:
- reproducing_test_fail_log: empty string if test passes, complete test output if it fails

Example of Fixed Bug (Test Passes):
```
Test Execute Messages:
run_command: pytest tests/test_json_parser.py

Output:
============================= test session starts ==============================
platform linux -- Python 3.9.20, pytest-7.4.4, pluggy-1.0.0
collected 1 item

tests/test_json_parser.py .                                              [100%]

============================== 1 passed in 0.16s =============================
```

Example Output for Fixed Bug:
{
    "reproducing_test_fail_log": ""
}

Example of Unfixed Bug (Test Still Fails):
```
Test Execute Messages:
run_command: pytest tests/test_json_parser.py

Output:
============================= test session starts ==============================
platform linux -- Python 3.9.20, pytest-7.4.4, pluggy-1.0.0
collected 1 item

tests/test_json_parser.py F                                              [100%]

================================= FAILURES ==================================
_________________________ test_empty_array_parsing _________________________
    def test_empty_array_parsing():
>       assert parser.parse_array(['[', ']']) == []
E       ValueError: Empty array not supported

tests/test_json_parser.py:7: ValueError
=========================== short test summary info ==========================
FAILED tests/test_json_parser.py::test_empty_array_parsing - ValueError
============================== 1 failed in 0.16s =============================
```

Example Output for Unfixed Bug:
{
    "reproducing_test_fail_log": "<complete test output above>"
}

Important:
- Only look at test pass/fail status
- A single failing test means the bug isn't fixed
- Include complete test output in failure log
- Any error or failure means the bug isn't fixed yet
""".replace("{", "{{").replace("}", "}}")

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{bug_reproducing_logs}")]
        )
        structured_llm = model.with_structured_output(BugFixVerifyStructureOutput)
        self.model = prompt | structured_llm
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.bug_fix_verify_structured_node"
        )

    def __call__(self, state: BugFixVerificationState):
        bug_fix_verify_message = get_last_message_content(state["bug_fix_verify_messages"])
        response = self.model.invoke({"bug_reproducing_logs": bug_fix_verify_message})

        self._logger.debug(response)

        return {
            "reproducing_test_fail_log": response.reproducing_test_fail_log,
        }
