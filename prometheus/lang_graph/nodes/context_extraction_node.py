from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from prometheus.exceptions.file_operation_exceptions import FileOperationException
from prometheus.lang_graph.subgraphs.context_retrieval_state import ContextRetrievalState
from prometheus.models.context import Context
from prometheus.utils.file_utils import read_file_with_line_numbers
from prometheus.utils.logger_manager import get_logger

SYS_PROMPT = """\
You are a context summary agent that summarizes code context that is relevant to a given query from history messages.
 Your goal is to extract, evaluate and summary code context that directly answers the query requirements.

Your evaluation and summarization must consider two key aspects:
1. Query Match: Which set of history messages directly address specific requirements mentioned in the query?
2. Extended relevance: Which set of history messages provide essential information needed to understand the query topic?

Follow these strict evaluation steps:
1. First, identify specific requirements in the query
2. Check which set of history messages directly addresses these requirements
3. Check which parts of code context are relevant to the query
4. Consider if they provides essential context by examining:
   - Function dependencies
   - Type definitions
   - Configuration requirements
   - Implementation details needed for completeness

Query relevance guidelines - include only if:
- It directly implements functionality mentioned in the query
- It contains specific elements the query asks about
- It's necessary to understand or implement query requirements
- It provides critical information needed to answer the query

CRITICAL RULE:
- You don't have to select whole piece of code that you have seen, ONLY select the parts that are relevant to the query.
- Each context MUST be SHORT and CONCISE, focusing ONLY on the lines that are relevant to the query.
- Several context can be extracted from the same file, but each context must be concise and relevant to the query.
- Do NOT include any irrelevant lines or comments that do not contribute to answering the query.
- Do NOT include same context multiple times, even if it appears in different history messages.

Remember: Your primary goal is to summarize context that directly helps answer the query requirements.

Provide your analysis in a structured format matching the ContextExtractionStructuredOutput model.

Example output:
```json
{
    "context": [{
        "reasoning": "1. Query requirement analysis:\n   - Query specifically asks about password validation\n   - Context provides implementation details for password validation\n2. Extended relevance:\n   - This function is essential for understanding how passwords are validated in the system",
        "relative_path": "pychemia/code/fireball/fireball.py",
        "start_line": 270, # Must be greater than or equal to 1
        "end_line": 293 # Must be greater than or equal to start_line
    } ......]
}
```

Your task is to summarize the context from the provided history messages and return it in the specified format.
"""


class ContextOutput(BaseModel):
    reasoning: str = Field(
        description="Your step-by-step reasoning why the context is relevant to the query"
    )
    relative_path: str = Field(description="Relative path to the context file in the codebase")
    start_line: int = Field(
        description="Start line number of the context in the file, minimum is 1"
    )
    end_line: int = Field(
        description="End line number of the context in the file, minimum is 1. "
        "The Content in the end line is including"
    )


class ContextExtractionStructuredOutput(BaseModel):
    context: Sequence[ContextOutput] = Field(
        description="List of contexts extracted from the history messages. "
        "Each context must have a reasoning, relative path, start line and end line."
    )


class ContextExtractionNode:
    def __init__(self, model: BaseChatModel, root_path: str):
        structured_llm = model.with_structured_output(ContextExtractionStructuredOutput)
        self.model = structured_llm
        self.system_prompt = SystemMessage(SYS_PROMPT)
        self.root_path = root_path
        self._logger = get_logger(__name__)

    def __call__(self, state: ContextRetrievalState):
        self._logger.info("Starting context extraction process")
        # Get Context List with existing context
        final_context = state.get("context", [])
        # Get chat history messages from the state
        last_messages = state["context_provider_messages"]
        # Summarize the context based on the last messages and system prompt
        response = self.model.invoke([self.system_prompt] + last_messages)
        self._logger.debug(f"Model response: {response}")
        context_list = response.context
        for context_ in context_list:
            if context_.start_line < 1 or context_.end_line < 1:
                self._logger.warning(
                    f"Skipping invalid context with start_line={context_.start_line}, end_line={context_.end_line}"
                )
                continue
            try:
                content = read_file_with_line_numbers(
                    relative_path=context_.relative_path,
                    root_path=str(self.root_path),
                    start_line=context_.start_line,
                    end_line=context_.end_line,
                )
            except FileOperationException as e:
                self._logger.error(e)
                continue
            if content:
                final_context.append(
                    Context(
                        relative_path=context_.relative_path,
                        start_line_number=context_.start_line,
                        end_line_number=context_.end_line,
                        content=content,
                    )
                )
        # Filter out duplicate Context entries
        seen = set()
        unique_context = []
        for ctx in final_context:
            key = (ctx.relative_path, ctx.start_line_number, ctx.end_line_number)
            if key not in seen:
                seen.add(key)
                unique_context.append(ctx)
        self._logger.info(f"Context extraction complete, returning context {unique_context}")
        return {"context": unique_context}
