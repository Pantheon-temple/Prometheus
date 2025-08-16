"""Code editing functionality for automated issue resolution and fixing.

This module implements a specialized code editing agent that automatically handles
build failures, test failures, and other code-related issues. It uses a language
model with structured tools to analyze problems and implement precise code changes
while maintaining code integrity.
"""

import functools
from typing import Dict

from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.tools.file_operation import FileOperationTool
from prometheus.utils.logger_manager import get_logger


class EditNode:
    SYS_PROMPT = """\
You are a specialized editing agent responsible for implementing precise changes to files. Your
primary focus is on accurately implementing the code changes that have been analyzed and
proposed by the user.

CRITICAL: You must EXECUTE the provided tools directly. Do not describe tool calls in text - use the actual tool calling functionality.

ROLE AND RESPONSIBILITIES:
- Implement the exact code changes specified in the analysis using direct tool execution
- Maintain code quality and consistent style
- Ensure precise content replacement
- Verify changes after implementation

TOOL USAGE REQUIREMENTS:
1. ALWAYS start by using the read_file tool to get current content
2. EXECUTE the edit_file tool to make changes
3. VERIFY changes by using read_file tool again
4. NEVER describe tool calls in text - use actual tool execution

THINKING AND EXECUTION PROCESS:
For each edit operation:
1. READ: Execute read_file tool to get current state
2. LOCATE: Identify exact content to replace
3. EXECUTE: Call edit_file tool with precise old_content and new_content
4. VALIDATE: Execute read_file tool again to verify

CRITICAL FILE EDIT BEHAVIOR:
The edit_file operation performs an EXACT STRING REPLACEMENT in the file:
- Matches must be exact (including whitespace and indentation)
- Only one match of old_content should exist in the file
- If multiple matches exist, more context is needed
- If no matches exist, content must be verified

EXAMPLES:

<example id="simple-replacement">
<file_before>
def calculate_sum(a: int, b: int) -> int:
    # TODO: Implement addition
    return 0  # Incorrect placeholder

def other_function():
</file_before>

<execution_steps>
1. First, read the current file content:
<tool>read_file</tool>

2. Execute the edit with exact content match:
<tool>edit_file</tool> with:
{
    "old_content": "    return 0  # Incorrect placeholder",
    "new_content": "    return a + b  # Implemented correct addition"
}

3. Verify the changes:
<tool>read_file</tool>
</execution_steps>
</example>

<example id="multi-line-replacement">
<file_before>
class StringUtils:
    def reverse_string(self, s: str) -> str:
        # TODO: implement proper reversal
        result = ""
        result += s  # Bug: just copies string
        return result  # Doesn't reverse
    
    def other_method():
</file_before>

<execution_steps>
1. First, read the current file content:
<tool>read_file</tool>

2. Execute the edit with exact multi-line content match:
<tool>edit_file</tool> with:
{
    "old_content": "        # TODO: implement proper reversal\n        result = \"\"\n        result += s  # Bug: just copies string\n        return result  # Doesn't reverse",
    "new_content": "        result = s[::-1]  # Proper string reversal\n        return result"
}

3. Verify the changes:
<tool>read_file</tool>
</execution_steps>
</example>

MANDATORY REQUIREMENTS:
1. EXECUTE tools directly - do not describe tool usage in text
2. ALWAYS read file before and after changes
3. Include exact whitespace and indentation in old_content
4. When replacing multiple lines, include all lines in old_content
5. If multiple matches found, include more context
6. Verify uniqueness of matches before changes
"""

    def __init__(self, model: BaseChatModel, kg: KnowledgeGraph):
        self.system_prompt = SystemMessage(self.SYS_PROMPT)
        self.file_operation_tool = FileOperationTool(str(kg.get_local_path()))
        self.tools = self._init_tools()
        self.model_with_tools = model.bind_tools(self.tools)
        self._logger = get_logger(__name__)

    def _init_tools(self):
        """Initializes file operation tools with the given root path.

        Args:
          root_path: Base directory path for all file operations.

        Returns:
          List of StructuredTool instances configured for file operations.
        """
        tools = []

        read_file_fn = functools.partial(self.file_operation_tool.read_file)
        read_file_tool = StructuredTool.from_function(
            func=read_file_fn,
            name=self.file_operation_tool.read_file.__name__,
            description=self.file_operation_tool.read_file_spec.description,
            args_schema=self.file_operation_tool.read_file_spec.input_schema,
        )
        tools.append(read_file_tool)

        read_file_with_line_numbers_fn = functools.partial(
            self.file_operation_tool.read_file_with_line_numbers
        )
        read_file_with_line_numbers_tool = StructuredTool.from_function(
            func=read_file_with_line_numbers_fn,
            name=self.file_operation_tool.read_file_with_line_numbers.__name__,
            description=self.file_operation_tool.read_file_with_line_numbers_spec.description,
            args_schema=self.file_operation_tool.read_file_with_line_numbers_spec.input_schema,
        )
        tools.append(read_file_with_line_numbers_tool)

        create_file_fn = functools.partial(self.file_operation_tool.create_file)
        create_file_tool = StructuredTool.from_function(
            func=create_file_fn,
            name=self.file_operation_tool.create_file.__name__,
            description=self.file_operation_tool.create_file_spec.description,
            args_schema=self.file_operation_tool.create_file_spec.input_schema,
        )
        tools.append(create_file_tool)

        delete_fn = functools.partial(self.file_operation_tool.delete)
        delete_tool = StructuredTool.from_function(
            func=delete_fn,
            name=self.file_operation_tool.delete.__name__,
            description=self.file_operation_tool.delete_spec.description,
            args_schema=self.file_operation_tool.delete_spec.input_schema,
        )
        tools.append(delete_tool)

        edit_file_fn = functools.partial(self.file_operation_tool.edit_file)
        edit_file_tool = StructuredTool.from_function(
            func=edit_file_fn,
            name=self.file_operation_tool.edit_file.__name__,
            description=self.file_operation_tool.edit_file_spec.description,
            args_schema=self.file_operation_tool.edit_file_spec.input_schema,
        )
        tools.append(edit_file_tool)

        return tools

    def __call__(self, state: Dict):
        message_history = [self.system_prompt] + state["edit_messages"]
        response = self.model_with_tools.invoke(message_history)

        self._logger.debug(response)
        return {"edit_messages": [response]}
