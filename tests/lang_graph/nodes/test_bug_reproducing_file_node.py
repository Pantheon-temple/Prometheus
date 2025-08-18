from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.bug_reproducing_file_node import BugReproducingFileNode
from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.fixture
def mock_kg():
    kg = Mock(spec=KnowledgeGraph)
    kg.get_file_tree.return_value = "test_dir/\n  test_file.py"
    return kg


@pytest.fixture
def fake_llm():
    return FakeListChatWithToolsModel(responses=["test_output.py"])


@pytest.fixture
def basic_state():
    return BugReproductionState(
        issue_title="mock issue title",
        issue_body="mock issue body",
        issue_comments=[],
        max_refined_query_loop=3,
        bug_reproducing_query="mock query",
        bug_reproducing_context=[],
        bug_reproducing_patch="",
        bug_reproducing_write_messages=[AIMessage(content="def test_bug():\n    assert 1 == 2")],
        bug_reproducing_file_messages=[],
        bug_reproducing_execute_messages=[],
        reproduced_bug=False,
        reproduced_bug_failure_log="",
        reproduced_bug_file="",
        reproduced_bug_commands=[],
    )


def test_initialization(mock_kg, fake_llm):
    """Test basic initialization of BugReproducingFileNode."""
    node = BugReproducingFileNode(fake_llm, mock_kg, "test/path")

    assert isinstance(node.system_prompt, SystemMessage)
    assert len(node.tools) == 2  # read_file, create_file


def test_format_human_message(mock_kg, fake_llm, basic_state):
    """Test human message formatting with bug file."""
    node = BugReproducingFileNode(fake_llm, mock_kg, "test/path")
    message = node.format_human_message(basic_state)

    assert isinstance(message, HumanMessage)
    assert "def test_bug():" in message.content


def test_call_method(mock_kg, fake_llm, basic_state):
    """Test the __call__ method execution."""
    node = BugReproducingFileNode(fake_llm, mock_kg, "test/path")
    result = node(basic_state)

    assert "bug_reproducing_file_messages" in result
    assert len(result["bug_reproducing_file_messages"]) == 1
    assert result["bug_reproducing_file_messages"][0].content == "test_output.py"
