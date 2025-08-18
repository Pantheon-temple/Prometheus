from unittest.mock import Mock

import neo4j
import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_graph import IssueGraph


@pytest.fixture
def mock_advanced_model():
    return Mock(spec=BaseChatModel)


@pytest.fixture
def mock_base_model():
    return Mock(spec=BaseChatModel)


@pytest.fixture
def mock_kg():
    kg = Mock(spec=KnowledgeGraph)
    kg.get_all_ast_node_types.return_value = ["FunctionDef", "ClassDef", "Module", "Import", "Call"]
    kg.root_node_id = 0
    return kg


@pytest.fixture
def mock_git_repo():
    git_repo = Mock(spec=GitRepository)
    git_repo.playground_path = "mock/playground/path"
    return git_repo


@pytest.fixture
def mock_neo4j_driver():
    return Mock(spec=neo4j.Driver)


@pytest.fixture
def mock_container():
    return Mock(spec=BaseContainer)


def test_issue_graph_basic_initialization(
    mock_advanced_model,
    mock_base_model,
    mock_kg,
    mock_git_repo,
    mock_neo4j_driver,
    mock_container,
):
    """Test that IssueGraph initializes correctly with basic components."""
    graph = IssueGraph(
        advanced_model=mock_advanced_model,
        base_model=mock_base_model,
        kg=mock_kg,
        git_repo=mock_git_repo,
        neo4j_driver=mock_neo4j_driver,
        max_token_per_neo4j_result=1000,
        container=mock_container,
    )

    assert graph.graph is not None
    assert graph.git_repo == mock_git_repo
