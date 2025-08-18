import pytest
from langchain_core.messages import AIMessage, ToolMessage

from prometheus.lang_graph.nodes.context_provider_node import ContextProviderNode
from tests.test_utils.fixtures import neo4j_container_with_kg_fixture  # noqa: F401
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.mark.slow
async def test_context_provider_node_basic_query(neo4j_container_with_kg_fixture):  # noqa: F811
    """Test basic query handling with the ContextProviderNode."""
    neo4j_container, kg = neo4j_container_with_kg_fixture
    fake_response = "Fake response"
    fake_llm = FakeListChatWithToolsModel(responses=[fake_response])
    node = ContextProviderNode(
        model=fake_llm,
        kg=kg,
        neo4j_driver=neo4j_container.get_driver(),
        max_token_per_result=1000,
    )

    test_messages = [
        AIMessage(content="This code handles file processing"),
        ToolMessage(content="Found implementation in utils.py", tool_call_id="test_tool_call_1"),
    ]
    test_state = {
        "original_query": "How does the error handling work?",
        "context_provider_messages": test_messages,
    }

    result = node(test_state)

    assert "context_provider_messages" in result
    assert len(result["context_provider_messages"]) == 1
    assert result["context_provider_messages"][0].content == fake_response
