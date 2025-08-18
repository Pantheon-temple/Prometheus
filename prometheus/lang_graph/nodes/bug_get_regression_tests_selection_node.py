import logging
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.subgraphs.bug_get_regression_tests_state import (
    BugGetRegressionTestsState,
)
from prometheus.utils.issue_util import format_issue_info


class RegressionTestStructuredOutPut(BaseModel):
    reasoning: str = Field(description="Your step-by-step reasoning why this test is selected")
    test_identifier: str = Field(
        description="The test identifier that you select (e.g., class name and method name)"
    )


class RegressionTestsStructuredOutPut(BaseModel):
    selected_tests: list[RegressionTestStructuredOutPut] = Field(
        description="List of selected regression tests with reasoning and identifiers"
    )


class BugGetRegressionTestsSelectionNode:
    SYS_PROMPT = """\
You are an expert programming assistant specialized in evaluating and selecting regression tests for a given issue among multiple candidate test cases.

Your goal is to analyze each test and select appropriate regression tests based on the following prioritized criteria:

1. The test is relevant to the issue at hand, fixing the bug could affect this test
2. The test cases that most likely to break existing functionality if this issue is fixed or new changes apply.

Analysis Process:
1. First, understand the issue from the provided issue info
2. Examine each tests carefully, considering:
   - Is it relevant to the issue at hand?
   - Does fixing the bug could affect this test?
   - Does this test case is most likely to break existing functionality if this issue is fixed or new changes apply?
3. Compare tests systematically against each criterion
4. Provide detailed reasoning for your selection

Output Requirements:
- You MUST provide structured output in the following format:
{{
  "selected_tests": [
    {{
      "reasoning": "", # Your step-by-step reasoning why this test is selected
      "test_identifier": "" # The test identifier that you select (e.g., class name and method name)
    }}
  ]
}}

ALL fields are REQUIRED!

EXAMPLE OUTPUT:
```json
{{
  "selected_tests": [
    {{
      "reasoning": "1. Relevance to issue: The test directly exercises the functionality described in the issue, specifically handling edge cases that are likely to be affected by the bug fix.\n2. Impact likelihood: Given the test's focus on critical paths mentioned in the issue, it is highly probable that fixing the bug will influence this test's behavior.",
      "test_identifier": "pvlib/tests/test_iam.py::test_ashrae"
    }}
  ]
}}
```

Remember:
- Always analyze all available tests thoroughly
- Provide clear, step-by-step reasoning for your selection
- Select the tests that best balances the prioritized criteria
"""

    HUMAN_PROMPT = """\
PLEASE SELECT {number_of_selected_regression_tests} RELEVANT REGRESSION TESTS FOR THE FOLLOWING ISSUE:
--- BEGIN ISSUE ---
{issue_info}
--- END ISSUE ---

Select Regression Tests Context:
{select_regression_context}

You MUST select {number_of_selected_regression_tests} regression tests that are most likely to break existing functionality if this issue is fixed or new changes apply.
"""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{human_prompt}")]
        )
        structured_llm = model.with_structured_output(RegressionTestsStructuredOutPut)
        self.model = prompt | structured_llm
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.bug_get_regression_tests_selection_node"
        )

    def format_human_message(self, state: BugGetRegressionTestsState):
        return self.HUMAN_PROMPT.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
            select_regression_context="\n\n".join(
                [str(context) for context in state["select_regression_context"]]
            ),
            number_of_selected_regression_tests=state["number_of_selected_regression_tests"],
        )

    def __call__(self, state: BugGetRegressionTestsState):
        human_prompt = self.format_human_message(state)
        response = self.model.invoke({"human_prompt": human_prompt})
        self._logger.debug(f"Model response: {response}")
        self._logger.debug(f"{len(response.selected_tests)} tests selected as regression tests")
        # Return only the identifiers of the selected regression tests
        return {
            "selected_regression_tests": [test.test_identifier for test in response.selected_tests]
        }
