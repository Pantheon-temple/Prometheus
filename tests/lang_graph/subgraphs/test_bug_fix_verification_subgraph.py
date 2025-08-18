from unittest.mock import Mock

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.subgraphs.bug_fix_verification_subgraph import BugFixVerificationSubgraph
from tests.test_utils.util import FakeListChatWithToolsModel


@pytest.fixture
def mock_container():
    return Mock(spec=BaseContainer)


@pytest.fixture
def mock_checkpointer():
    return Mock(spec=BaseCheckpointSaver)


@pytest.fixture
def mock_git_repo():
    git_repo = Mock(spec=GitRepository)
    git_repo.playground_path = "mock/playground/path"
    return git_repo


def test_bug_fix_verification_subgraph_basic_initialization(
    mock_container,
    mock_git_repo,
):
    """Test that BugFixVerificationSubgraph initializes correctly with basic components."""
    fake_model = FakeListChatWithToolsModel(responses=[])

    subgraph = BugFixVerificationSubgraph(fake_model, mock_container, mock_git_repo)

    assert subgraph.subgraph is not None
