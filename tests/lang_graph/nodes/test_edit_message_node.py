from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from prometheus.lang_graph.nodes.edit_message_node import EditMessageNode
from prometheus.models.context import Context


@pytest.fixture
def edit_node():
    return EditMessageNode()


@pytest.fixture
def base_state():
    return {
        "issue_title": "Test Bug",
        "issue_body": "This is a test bug description",
        "issue_comments": [
            {"username": "user1", "comment": "Comment 1"},
            {"username": "user2", "comment": "Comment 2"},
        ],
        "bug_fix_context": [
            Context(
                relative_path="foobar.py",
                content="# Context 1",
                start_line_number=1,
                end_line_number=1,
            )
        ],
        "issue_bug_analyzer_messages": ["Analysis message"],
    }


def test_first_message_formatting(edit_node, base_state):
    # Using context managers for patching
    with patch(
        "prometheus.lang_graph.nodes.edit_message_node.format_issue_info"
    ) as mock_format_issue:
        with patch(
            "prometheus.lang_graph.nodes.edit_message_node.get_last_message_content"
        ) as mock_last_message:
            mock_format_issue.return_value = "Formatted Issue Info"
            mock_last_message.return_value = "Last Analysis Message"

            result = edit_node(base_state)

            assert isinstance(result, dict)
            assert "edit_messages" in result
            assert len(result["edit_messages"]) == 1
            assert isinstance(result["edit_messages"][0], HumanMessage)

            message_content = result["edit_messages"][0].content
            assert "Formatted Issue Info" in message_content
            assert "# Context 1" in message_content
            assert "Last Analysis Message" in message_content


def test_followup_message_with_build_fail(edit_node, base_state):
    # Add build failure to state
    base_state["build_fail_log"] = "Build failed: error in compilation"

    with patch(
        "prometheus.lang_graph.nodes.edit_message_node.get_last_message_content"
    ) as mock_last_message:
        mock_last_message.return_value = "Last Analysis Message"

        result = edit_node(base_state)
        message_content = result["edit_messages"][0].content

        assert "Build failed: error in compilation" in message_content
        assert "Please implement these revised changes carefully" in message_content


def test_followup_message_with_test_fail(edit_node, base_state):
    # Add test failure to state
    base_state["reproducing_test_fail_log"] = "Test failed: assertion error"

    with patch(
        "prometheus.lang_graph.nodes.edit_message_node.get_last_message_content"
    ) as mock_last_message:
        mock_last_message.return_value = "Last Analysis Message"

        result = edit_node(base_state)
        message_content = result["edit_messages"][0].content

        assert "Test failed: assertion error" in message_content
        assert "Please implement these revised changes carefully" in message_content


def test_followup_message_with_existing_test_fail(edit_node, base_state):
    # Add existing test failure to state
    base_state["existing_test_fail_log"] = "Existing test failed"

    with patch(
        "prometheus.lang_graph.nodes.edit_message_node.get_last_message_content"
    ) as mock_last_message:
        mock_last_message.return_value = "Last Analysis Message"

        result = edit_node(base_state)
        message_content = result["edit_messages"][0].content

        assert "Existing test failed" in message_content
        assert "Please implement these revised changes carefully" in message_content


def test_error_priority(edit_node, base_state):
    # Add multiple error types to test priority handling
    base_state["reproducing_test_fail_log"] = "Test failed"
    base_state["build_fail_log"] = "Build failed"
    base_state["existing_test_fail_log"] = "Existing test failed"

    with patch(
        "prometheus.lang_graph.nodes.edit_message_node.get_last_message_content"
    ) as mock_last_message:
        mock_last_message.return_value = "Last Analysis Message"

        result = edit_node(base_state)
        message_content = result["edit_messages"][0].content

        # Should prioritize reproducing test failure
        assert "Test failed" in message_content
        assert "Build failed" not in message_content
        assert "Existing test failed" not in message_content
