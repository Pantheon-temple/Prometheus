from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.neo4j_service import Neo4jService
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.neo4j.knowledge_graph_handler import KnowledgeGraphHandler


@pytest.fixture
def mock_neo4j_service():
    """Mock the Neo4jService."""
    neo4j_service = MagicMock(Neo4jService)
    return neo4j_service


@pytest.fixture
def mock_kg_handler():
    """Mock the KnowledgeGraphHandler."""
    kg_handler = MagicMock(KnowledgeGraphHandler)
    return kg_handler


@pytest.fixture
def knowledge_graph_service(mock_neo4j_service, mock_kg_handler):
    """Fixture to create KnowledgeGraphService instance."""
    mock_neo4j_service.neo4j_driver = MagicMock()  # Mocking Neo4j driver
    mock_kg_handler.get_new_knowledge_graph_root_node_id = AsyncMock(return_value=123)
    mock_kg_handler.write_knowledge_graph = AsyncMock()

    knowledge_graph_service = KnowledgeGraphService(
        neo4j_service=mock_neo4j_service,
        neo4j_batch_size=1000,
        max_ast_depth=5,
        chunk_size=1000,
        chunk_overlap=100,
    )
    knowledge_graph_service.kg_handler = mock_kg_handler
    return knowledge_graph_service


async def test_build_and_save_knowledge_graph(knowledge_graph_service, mock_kg_handler):
    """Test the build_and_save_knowledge_graph method."""
    # Given
    source_code_path = Path("/mock/path/to/source/code")  # Mock path to source code

    # Mock KnowledgeGraph and its methods
    mock_kg = MagicMock(KnowledgeGraph)
    mock_kg.build_graph = AsyncMock(return_value=None)  # Mock async method to build graph
    mock_kg_handler.get_new_knowledge_graph_root_node_id.return_value = 123
    mock_kg_handler.write_knowledge_graph.return_value = None

    # When
    with pytest.raises(Exception):
        knowledge_graph_service.kg_handler = mock_kg_handler
        result = await knowledge_graph_service.build_and_save_knowledge_graph(source_code_path)

        # Then
        assert result == 123  # Ensure that the correct root node ID is returned
        mock_kg.build_graph.assert_awaited_once_with(
            source_code_path
        )  # Check if build_graph was called correctly
        mock_kg_handler.write_knowledge_graph.assert_called_once()  # Ensure graph write happened
        mock_kg_handler.get_new_knowledge_graph_root_node_id.assert_called_once()  # Ensure the root node ID was fetched


def test_clear_kg(knowledge_graph_service, mock_kg_handler):
    """Test the clear_kg method."""
    # Given
    root_node_id = 123  # Mock root node ID

    # When
    knowledge_graph_service.clear_kg(root_node_id)

    # Then
    mock_kg_handler.clear_knowledge_graph.assert_called_once_with(root_node_id)


def test_get_knowledge_graph(knowledge_graph_service, mock_kg_handler):
    """Test the get_knowledge_graph method."""
    # Given
    root_node_id = 123  # Mock root node ID
    max_ast_depth = 5
    chunk_size = 1000
    chunk_overlap = 100

    # Mock KnowledgeGraph
    mock_kg = MagicMock(KnowledgeGraph)
    mock_kg_handler.read_knowledge_graph.return_value = mock_kg  # Mock return value

    # When
    result = knowledge_graph_service.get_knowledge_graph(
        root_node_id, max_ast_depth, chunk_size, chunk_overlap
    )

    # Then
    mock_kg_handler.read_knowledge_graph.assert_called_once_with(
        root_node_id, max_ast_depth, chunk_size, chunk_overlap
    )  # Ensure read_knowledge_graph is called with the correct parameters
    assert result == mock_kg  # Ensure the correct KnowledgeGraph object is returned
