import logging
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from prometheus.lang_graph.subgraphs.issue_question_state import IssueQuestionState
from prometheus.utils.issue_util import format_issue_info


class IssueQuestionAnalyzerNode:
    SYS_PROMPT = """
You are an expert software engineer specializing in analysis and answering issue. Your role is to:

1. Carefully analyze reported software issues and question by:
   - Understanding issue descriptions and symptoms
   - Identifying related code components

2. Answer the question through systematic investigation:
   - Identify which specific code elements are related to the question
   - Understand the context and interactions related to the question or issue

3. Provide high-level answer suggestions step by step

Important:
- You may provide actual code snippets or diffs if necessary
- Keep descriptions precise and actionable

Communicate in a clear, technical manner focused on accurate analysis and practical suggestions
rather than implementation details.
"""
    HUMAN_PROMPT = """
    Here is a Github issue description:
    -- BEGIN ISSUE --
    {issue_info}
    -- END ISSUE --
    
    Here is the relevant code context and documentation needed to understand and answer this issue:
    --- BEGIN CONTEXT --
    {question_context}
    --- END CONTEXT --
    
    Based on the above information, please provide a detailed answer to the question.
    """

    def __init__(self, model: BaseChatModel):
        self.system_prompt = SystemMessage(self.SYS_PROMPT)
        self.model = model
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_question_analyzer_node"
        )

    def __call__(self, state: IssueQuestionState):
        human_prompt = HumanMessage(
            self.HUMAN_PROMPT.format(
                issue_info=format_issue_info(
                    state["issue_title"], state["issue_body"], state["issue_comments"]
                ),
                question_context="\n\n".join(
                    [str(context) for context in state["question_context"]]
                ),
            )
        )
        message_history = [self.system_prompt, human_prompt]
        response = self.model.invoke(message_history)

        self._logger.debug(response)
        return {"question_response": response.content}
