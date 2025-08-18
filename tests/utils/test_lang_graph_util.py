from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from prometheus.utils.lang_graph_util import (
    check_remaining_steps,
    extract_ai_responses,
    extract_human_queries,
    extract_last_tool_messages,
    format_agent_tool_message_history,
    get_last_message_content,
)
from prometheus.utils.llm_util import str_token_counter, tiktoken_counter


# Test check_remaining_steps
def test_check_remaining_steps():
    def mock_router(state):
        return "next_step"

    state_enough_steps = {"remaining_steps": 5}
    state_low_steps = {"remaining_steps": 2}

    assert check_remaining_steps(state_enough_steps, mock_router, 3) == "next_step"
    assert check_remaining_steps(state_low_steps, mock_router, 3) == "low_remaining_steps"


# Test str_token_counter
def test_str_token_counter():
    text = "Hello, world!"
    token_count = str_token_counter(text)
    assert isinstance(token_count, int)
    assert token_count > 0


# Test tiktoken_counter
def test_tiktoken_counter():
    messages = [
        SystemMessage(content="System message"),
        HumanMessage(content="Human message"),
        AIMessage(content="AI response"),
        ToolMessage(content="Tool message", tool_call_id="call_1"),
    ]

    token_count = tiktoken_counter(messages)
    assert isinstance(token_count, int)
    assert token_count > 0


# Test extract_ai_responses
def test_extract_ai_responses():
    messages = [
        HumanMessage(content="Human 1"),
        AIMessage(content="AI 1"),
        HumanMessage(content="Human 2"),
        AIMessage(content="AI 2"),
    ]

    responses = extract_ai_responses(messages)
    assert len(responses) == 2
    assert "AI 1" in responses
    assert "AI 2" in responses


# Test extract_human_queries
def test_extract_human_queries():
    messages = [
        SystemMessage(content="System"),
        HumanMessage(content="Human 1"),
        AIMessage(content="AI 1"),
        HumanMessage(content="Human 2"),
    ]

    queries = extract_human_queries(messages)
    assert len(queries) == 2
    assert "Human 1" in queries
    assert "Human 2" in queries


# Test extract_last_tool_messages
def test_extract_last_tool_messages():
    messages = [
        HumanMessage(content="Human 1"),
        ToolMessage(content="Tool 1", tool_call_id="call_1"),
        AIMessage(content="AI 1"),
        HumanMessage(content="Human 2"),
        ToolMessage(content="Tool 2", tool_call_id="call_2"),
        ToolMessage(content="Tool 3", tool_call_id="call_3"),
    ]

    tool_messages = extract_last_tool_messages(messages)
    assert len(tool_messages) == 2
    assert all(isinstance(msg, ToolMessage) for msg in tool_messages)
    assert tool_messages[-1].content == "Tool 3"


# Test get_last_message_content
def test_get_last_message_content():
    messages = [
        HumanMessage(content="Human"),
        AIMessage(content="AI"),
        ToolMessage(content="Last message", tool_call_id="call_1"),
    ]

    content = get_last_message_content(messages)
    assert content == "Last message"


def test_format_agent_tool_message_history():
    messages = [
        AIMessage(content="Let me analyze this"),
        AIMessage(
            content="I'll use a tool for this",
            additional_kwargs={"tool_calls": [{"function": "analyze_data"}]},
        ),
        ToolMessage(content="Analysis results: Success", tool_call_id="call_1"),
    ]

    result = format_agent_tool_message_history(messages)

    expected = (
        "Assistant internal thought: Let me analyze this\n\n"
        "Assistant internal thought: I'll use a tool for this\n\n"
        "Assistant executed tool: analyze_data\n\n"
        "Tool output: Analysis results: Success"
    )

    assert result == expected
