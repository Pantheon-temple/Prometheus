
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.context_retrieval_state import ContextRetrievalState
from prometheus.utils.logger_manager import get_logger


class ContextRefineStructuredOutput(BaseModel):
    reasoning: str = Field(description="Your step by step reasoning.")
    refined_query: str = Field(
        "Additional query to ask the ContextRetriever if the context is not enough. Empty otherwise."
    )


class ContextRefineNode:
    SYS_PROMPT = """\
You are an intelligent assistant specialized in analyzing code context to determine if
additional source code or documentation from the codebase is necessary to fulfill the user's query.

Your goal is to request additional context ONLY when necessary:
1. When critical implementation details are missing to understand the current code
2. When key dependencies or related code are not visible in the current context
3. When documentation is needed to understand complex business logic, architecture, or requirements
4. When referenced files, classes, or functions are not included in the current context
5. When understanding the broader system context is essential for the task

DO NOT request additional context if:
1. The current context already contains sufficient information to complete the task
2. The additional context would only provide nice-to-have but non-essential details
3. The information is redundant with what's already available

Output format:
```python
class ContextRefineStructuredOutput(BaseModel):
    reasoning: str     # Why current context is/isn't enough
    refined_query: str # Additional query to ask the ContextRetriever if the context is not enough. Empty otherwise
```

The codebase structure:
{file_tree}
"""

    REFINE_PROMPT = """\
This is the original user query:
{original_query}

All aggregated context for the queries:
{context}

Analyze if the current context is sufficient to complete the user query by considering:
1. Do you understand the full scope and requirements of the user query?
2. Do you have access to all relevant code that needs to be examined or modified?
3. Are all critical dependencies and their interfaces visible?
4. Is there enough context about the system architecture and design patterns?
5. Do you have access to relevant documentation or tests if needed?

Only request additional context if essential information is missing. Ensure you're not requesting:
- Information already provided in previous queries
- Nice-to-have but non-essential details
- Implementation details that aren't relevant to the current task

If additional context is needed:
- Be specific about what you're looking for
- Consider both code and documentation that might be relevant
"""

    def __init__(self, model: BaseChatModel, kg: KnowledgeGraph):
        file_tree = kg.get_file_tree().replace("{", "{{").replace("}", "}}")
        system_prompt = self.SYS_PROMPT.format(file_tree=file_tree)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{human_prompt}"),
            ]
        )
        structured_llm = model.with_structured_output(ContextRefineStructuredOutput)
        self.model = prompt | structured_llm
        self._logger = get_logger(__name__)

    def format_refine_message(self, state: ContextRetrievalState):
        original_query = state["query"]
        context = "\n\n".join([str(context) for context in state["context"]])
        return self.REFINE_PROMPT.format(
            original_query=original_query,
            context=context,
        )

    def __call__(self, state: ContextRetrievalState):
        if "max_refined_query_loop" in state and state["max_refined_query_loop"] == 0:
            self._logger.info("Reached max_refined_query_loop, not asking for more context")
            return {"refined_query": ""}

        human_prompt = self.format_refine_message(state)
        self._logger.debug(human_prompt)
        response = self.model.invoke({"human_prompt": human_prompt})
        self._logger.debug(response)

        state_update = {"refined_query": response.refined_query}

        if "max_refined_query_loop" in state:
            state_update["max_refined_query_loop"] = state["max_refined_query_loop"] - 1

        if response.refined_query:
            state_update["context_provider_messages"] = [
                HumanMessage(content=response.refined_query)
            ]

        return state_update
