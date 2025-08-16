import functools

from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.tools.file_operation import FileOperationTool
from prometheus.utils.logger_manager import get_logger


class BugReproducingWriteNode:
    SYS_PROMPT = '''\
You are a QA automation expert who writes focused a single test case to reproduce software bugs.
Given an issue description, create a single minimal test with MINIMAL number of assertions
that demonstrates the problem.

Requirements:
- Include all necessary imports and setup code shown in similar tests
- Must use the example from the issue if provided
- Focus on the core problem of the bug issue
- Write MINIMAL number of assertions that fail now but will pass when fixed
- Keep tests minimal and focused, do not write duplicate tests that test the same bug
- Follow the style and patterns used in the similar test cases

<example>
<bug_report>
Title: JSON parser fails with empty arrays
Description: The JsonParser class crashes when trying to parse an empty array - it should return an empty list but instead raises a ValueError.
Example:
```python
parser = JsonParser()
result = parser.parse_array(['[', ']'])  # Raises ValueError!
```
</bug_report>

<similar_test_cases>
### Existing Array Parser Tests
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def parser():
    """Fixture to create a fresh parser instance for each test."""
    return JsonParser()

def test_parse_single_element_array(parser):
    """Test parsing array with single element.
    Validates basic array parsing functionality.
    """
    tokens = ['[', '42', ']']
    result = parser.parse_array(tokens)
    assert result == [42]

def test_parse_nested_arrays(parser):
    """Test parsing nested array structures.
    Ensures proper handling of array nesting.
    """
    tokens = ['[', '[', '1', ']', ',', '[', '2', ',', '3', ']', ']']
    result = parser.parse_array(tokens)
    assert result == [[1], [2, 3]]

@patch('json.parser.TokenStream')
def test_parse_with_mocked_stream(mock_stream, parser):
    """Test parsing with mocked token stream."""
    mock_stream.peek.return_value = ']'
    mock_stream.consume.return_value = ']'
    result = parser.parse_with_stream(mock_stream)
    assert mock_stream.peek.called
```
</similar_test_cases>

<thought_process>
1. Look at Similar Tests:
   - Check the imports and setup they use
   - Note the fixture and mock patterns
   - See how assertions are written
   - Match their style and format

2. Core Issue:
   - What is the bug
   - What should happen instead
   - What examples were given

3. Write Test:
   - Use same patterns as similar tests
   - Include same import style
   - Match fixture usage
   - Follow same assertion style
</thought_process>

<test_code>
import pytest
from json.parser import JsonParser

@pytest.fixture
def parser():
    """Fixture to create a fresh parser instance for each test."""
    return JsonParser()

def test_empty_array_parsing(parser):
    """Test parsing of empty array.
    Validates that empty arrays are handled correctly without raising errors.
    """
    tokens = ['[', ']']
    result = parser.parse_array(tokens)
    assert result == []
</test_code>
</example>
'''

    def __init__(self, model: BaseChatModel, kg: KnowledgeGraph):
        self.file_operation_tool = FileOperationTool(str(kg.get_local_path()))
        self.tools = self._init_tools()
        self.system_prompt = SystemMessage(self.SYS_PROMPT)
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

        return tools

    def __call__(self, state: BugReproductionState):
        message_history = [self.system_prompt] + state["bug_reproducing_write_messages"]
        response = self.model_with_tools.invoke(message_history)

        self._logger.debug(response)
        return {"bug_reproducing_write_messages": [response]}
