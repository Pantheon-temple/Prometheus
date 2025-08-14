
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.graphs.issue_state import IssueType
from prometheus.lang_graph.subgraphs.issue_classification_state import IssueClassificationState
from prometheus.utils.issue_util import format_issue_info
from prometheus.utils.logger_manager import get_logger


class IssueClassifierOutput(BaseModel):
    issue_type: IssueType = Field(
        description='Classified issue type, can only be one of "bug", "feature", "documentation", or "question"',
    )


class IssueClassifierNode:
    SYS_PROMPT = """\
You are an expert GitHub issue classifier. Your task is to analyze GitHub issues and classify them into exactly one of these categories:
- "bug": Issues reporting software defects, unexpected behavior, or crashes
- "feature": Feature requests, enhancements, or new functionality proposals
- "documentation": Requests for documentation improvements, corrections, or additions
- "question": Questions about usage, implementation, or general inquiries

You will receive issue information including the title, body, comments, and relevant codebase context. Analyze all provided information carefully to determine the most appropriate category.

Guidelines for classification:
1. Each issue must be classified as exactly one type
2. Focus on the core intent of the issue, not peripheral discussions
3. If an issue contains multiple aspects, classify based on the primary purpose
4. Consider both the original post and any follow-up comments

Here are examples of inputs and their corresponding classifications:

INPUT 1:
```
ISSUE INFORMATION:
Title: App crashes when processing large files
Body: When I try to process files larger than 1GB, the application crashes with an OutOfMemoryError. Steps to reproduce:
1. Load file larger than 1GB
2. Click process
3. Application crashes
Comments:
User1: I can confirm this issue on version 2.1.0
User2: Same problem here, happens with 1.2GB files

CODEBASE CONTEXT:
Current file processing implementation uses in-memory buffering without streaming support.
```

OUTPUT 1:
{
  "issue_type": "bug"
}

INPUT 2:
```
ISSUE INFORMATION:
Title: Add dark mode support
Body: It would be great if we could add dark mode support to the UI. Many users work at night and the current light theme can be straining on the eyes.
Comments:
User1: +1 for dark mode
User2: Could we also add custom theme support while we're at it?

CODEBASE CONTEXT:
UI currently only supports light theme, using hard-coded color values.
```

OUTPUT 2:
{
  "issue_type": "feature"
}

INPUT 3:
```
ISSUE INFORMATION:
Title: Installation instructions unclear for Windows
Body: The README doesn't explain how to install on Windows. The Linux instructions don't work and there's no mention of Windows-specific steps.
Comments:
User1: Adding steps for Windows would be helpful
User2: The prerequisites section should also mention required Windows components

CODEBASE CONTEXT:
README.md focuses on Linux/Mac installation processes.
```

OUTPUT 3:
{
  "issue_type": "documentation"
}

INPUT 4:
```
ISSUE INFORMATION:
Title: How to implement custom authentication?
Body: I want to add my own authentication provider. What's the best way to implement this? Should I extend the BaseAuth class?
Comments:
User1: Have you checked the authentication docs?
User2: You'll need to implement the AuthProvider interface

CODEBASE CONTEXT:
Authentication system supports custom providers through AuthProvider interface.
```

OUTPUT 4:
{
  "issue_type": "question"
}

Analyze the provided issue and respond with a JSON object containing only the issue_type field with one of the four allowed values: "bug", "feature", "documentation", or "question".
""".replace("{", "{{").replace("}", "}}")

    ISSUE_CLASSIFICATION_CONTEXT = """\
{issue_info}

Issue classification context:
{issue_classification_context}
"""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{context_info}")]
        )
        structured_llm = model.with_structured_output(IssueClassifierOutput)
        self.model = prompt | structured_llm
        self._logger = get_logger(__name__)

    def format_context_info(self, state: IssueClassificationState) -> str:
        context_info = self.ISSUE_CLASSIFICATION_CONTEXT.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
            issue_classification_context="\n\n".join(
                [str(context) for context in state["issue_classification_context"]]
            ),
        )
        return context_info

    def __call__(self, state: IssueClassificationState):
        context_info = self.format_context_info(state)
        response = self.model.invoke({"context_info": context_info})
        self._logger.info(f"IssueClassifierNode classified the issue as: {response.issue_type}")
        return {"issue_type": response.issue_type}
