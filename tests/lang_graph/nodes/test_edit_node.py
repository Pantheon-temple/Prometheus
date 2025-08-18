from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.edit_node import EditNode
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.fixture
def mock_kg():
    kg = Mock(spec=KnowledgeGraph)
    return kg


@pytest.fixture
def fake_llm():
    return FakeListChatWithToolsModel(responses=["File edit completed successfully"])


def test_init_edit_node(mock_kg, fake_llm):
    """Test EditNode initialization."""
    node = EditNode(fake_llm, mock_kg)

    assert isinstance(node.system_prompt, SystemMessage)
    assert len(node.tools) == 5  # Should have 5 file operation tools
    assert node.model_with_tools is not None


def test_call_method_basic(mock_kg, fake_llm):
    """Test basic call functionality without tool execution."""
    node = EditNode(fake_llm, mock_kg)
    state = {"edit_messages": [HumanMessage(content="Make the following changes: ...")]}

    result = node(state)

    assert "edit_messages" in result
    assert len(result["edit_messages"]) == 1
    assert result["edit_messages"][0].content == "File edit completed successfully"
