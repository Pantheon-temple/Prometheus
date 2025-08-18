from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.nodes.bug_fix_verify_node import BugFixVerifyNode
from prometheus.lang_graph.subgraphs.bug_fix_verification_state import BugFixVerificationState
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.fixture
def mock_container():
    return Mock(spec=BaseContainer)


@pytest.fixture
def test_state():
    return BugFixVerificationState(
        {
            "reproduced_bug_file": "test_bug.py",
            "reproduced_bug_commands": ["python test_bug.py", "./run_test.sh"],
            "bug_fix_verify_messages": [AIMessage(content="Previous verification result")],
        }
    )


@pytest.fixture
def fake_llm():
    return FakeListChatWithToolsModel(responses=["Test execution completed"])


def test_format_human_message(mock_container, fake_llm, test_state):
    """Test human message formatting."""
    node = BugFixVerifyNode(fake_llm, mock_container)
    message = node.format_human_message(test_state)

    assert isinstance(message, HumanMessage)
    assert "test_bug.py" in message.content
    assert "python test_bug.py" in message.content
    assert "./run_test.sh" in message.content


def test_call_method(mock_container, fake_llm, test_state):
    """Test the __call__ method execution."""
    node = BugFixVerifyNode(fake_llm, mock_container)

    result = node(test_state)

    assert "bug_fix_verify_messages" in result
    assert len(result["bug_fix_verify_messages"]) == 1
    assert result["bug_fix_verify_messages"][0].content == "Test execution completed"
