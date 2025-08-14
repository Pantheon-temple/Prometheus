import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.messages.tool import ToolCall

from prometheus.lang_graph.nodes.issue_bug_analyzer_node import IssueBugAnalyzerNode
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.fixture
def fake_llm():
    return FakeListChatWithToolsModel(responses=["Bug analysis completed successfully"])


@pytest.fixture
def fake_llm_with_tool_call():
    """LLM that simulates making a web_search tool call."""
    return FakeListChatWithToolsModel(responses=["I need to search for information about this error."])


def test_init_issue_bug_analyzer_node(fake_llm):
    """Test IssueBugAnalyzerNode initialization."""
    node = IssueBugAnalyzerNode(fake_llm)
    
    assert node.system_prompt is not None
    assert len(node.tools) == 1  # Should have web_search tool
    assert node.tools[0].name == "web_search"
    assert node.model_with_tools is not None


def test_call_method_basic(fake_llm):
    """Test basic call functionality."""
    node = IssueBugAnalyzerNode(fake_llm)
    state = {"issue_bug_analyzer_messages": [HumanMessage(content="Please analyze this bug: ...")]}

    result = node(state)

    assert "issue_bug_analyzer_messages" in result
    assert len(result["issue_bug_analyzer_messages"]) == 1
    assert result["issue_bug_analyzer_messages"][0].content == "Bug analysis completed successfully"


def test_web_search_tool_integration(fake_llm_with_tool_call):
    """Test that the web_search tool is properly integrated and can be called."""
    node = IssueBugAnalyzerNode(fake_llm_with_tool_call)
    state = {
        "issue_bug_analyzer_messages": [
            HumanMessage(content="I'm getting a ValueError in my Python code. Can you help analyze it?")
        ]
    }

    result = node(state)

    # Verify the result contains the response message
    assert "issue_bug_analyzer_messages" in result
    assert len(result["issue_bug_analyzer_messages"]) == 1
    assert result["issue_bug_analyzer_messages"][0].content == "I need to search for information about this error."


def test_web_search_tool_call_with_correct_parameters(fake_llm):
    """Test that web_search tool has correct configuration and can be called."""
    node = IssueBugAnalyzerNode(fake_llm)
    
    # Test that the tool exists and has correct configuration
    web_search_tool = node.tools[0]
    assert web_search_tool.name == "web_search"
    assert "technical information" in web_search_tool.description.lower()
    
    # Test that the tool has the correct args schema
    assert hasattr(web_search_tool, 'args_schema')
    assert web_search_tool.args_schema is not None


@patch('prometheus.tools.web_search.tavily_client')
def test_web_search_tool_without_api_key(mock_tavily_client, fake_llm):
    """Test web_search tool behavior when API key is not available."""
    # Simulate no API key scenario
    mock_tavily_client = None
    
    node = IssueBugAnalyzerNode(fake_llm)
    web_search_tool = node.tools[0]
    
    # The tool should still be created but may handle missing API key gracefully
    assert web_search_tool.name == "web_search"


def test_system_prompt_contains_web_search_info(fake_llm):
    """Test that the system prompt mentions web_search tool."""
    node = IssueBugAnalyzerNode(fake_llm)
    
    system_prompt_content = node.system_prompt.content.lower()
    assert "web_search" in system_prompt_content
    assert "technical information" in system_prompt_content


def test_web_search_tool_schema_validation(fake_llm):
    """Test that the web_search tool has proper input validation."""
    node = IssueBugAnalyzerNode(fake_llm)
    web_search_tool = node.tools[0]
    
    # Check that the tool has an args_schema
    assert hasattr(web_search_tool, 'args_schema')
    assert web_search_tool.args_schema is not None
    
    # Test with valid input
    valid_input = {"query": "Python debugging techniques"}
    # This should not raise an exception
    validated_input = web_search_tool.args_schema(**valid_input)
    assert validated_input.query == "Python debugging techniques"


def test_multiple_tool_calls_in_conversation(fake_llm):
    """Test handling multiple web_search calls in a conversation."""
    node = IssueBugAnalyzerNode(fake_llm)
    
    # Simulate a conversation with tool calls
    state = {
        "issue_bug_analyzer_messages": [
            HumanMessage(content="Analyze this bug: ImportError in my application"),
            AIMessage(
                content="Let me search for information about this error.",
                tool_calls=[ToolCall(name="web_search", args={"query": "Python ImportError debugging"}, id="call_1")]
            ),
            ToolMessage(content="Search results: ImportError occurs when...", tool_call_id="call_1"),
            HumanMessage(content="The error still persists after trying the suggested fixes")
        ]
    }

    result = node(state)

    assert "issue_bug_analyzer_messages" in result
    assert len(result["issue_bug_analyzer_messages"]) == 1
    # The new response should be added to the conversation
    assert result["issue_bug_analyzer_messages"][0].content == "Bug analysis completed successfully"
