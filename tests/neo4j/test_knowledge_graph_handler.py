import pytest

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.neo4j.knowledge_graph_handler import KnowledgeGraphHandler
from tests.test_utils import test_project_paths
from tests.test_utils.fixtures import (  # noqa: F401
    empty_neo4j_container_fixture,
    neo4j_container_with_kg_fixture,
)


@pytest.mark.slow
async def test_num_ast_nodes(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_ast_nodes = session.execute_read(handler._read_ast_nodes, root_node_id=0)
            assert len(read_ast_nodes) == 84


@pytest.mark.slow
async def test_num_file_nodes(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_file_nodes = session.execute_read(handler._read_file_nodes, root_node_id=0)
            assert len(read_file_nodes) == 7


@pytest.mark.slow
async def test_num_text_nodes(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_text_nodes = session.execute_read(handler._read_text_nodes, root_node_id=0)
            assert len(read_text_nodes) == 2


@pytest.mark.slow
async def test_num_parent_of_edges(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_parent_of_edges = session.execute_read(
                handler._read_parent_of_edges, root_node_id=0
            )
            assert len(read_parent_of_edges) == 81


@pytest.mark.slow
async def test_num_has_file_edges(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_has_file_edges = session.execute_read(handler._read_has_file_edges, root_node_id=0)
            assert len(read_has_file_edges) == 6


@pytest.mark.slow
async def test_num_has_ast_edges(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_has_ast_edges = session.execute_read(handler._read_has_ast_edges, root_node_id=0)
            assert len(read_has_ast_edges) == 3


@pytest.mark.slow
async def test_num_has_text_edges(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_has_text_edges = session.execute_read(handler._read_has_text_edges, root_node_id=0)
            assert len(read_has_text_edges) == 2


@pytest.mark.slow
async def test_num_next_chunk_edges(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    with neo4j_container.get_driver() as driver:
        with driver.session() as session:
            read_next_chunk_edges = session.execute_read(
                handler._read_next_chunk_edges, root_node_id=0
            )
            assert len(read_next_chunk_edges) == 1


@pytest.mark.slow
async def test_knowledge_graph_exists(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    handler = KnowledgeGraphHandler(neo4j_container.get_driver(), 100)

    assert handler.knowledge_graph_exists(0)


@pytest.mark.slow
async def test_clear_knowledge_graph(empty_neo4j_container_fixture):  # noqa: F811
    kg = KnowledgeGraph(1000, 1000, 100, 0)
    await kg.build_graph(test_project_paths.TEST_PROJECT_PATH)

    driver = empty_neo4j_container_fixture.get_driver()
    handler = KnowledgeGraphHandler(driver, 100)
    handler.write_knowledge_graph(kg)

    assert handler.knowledge_graph_exists(0)

    handler.clear_knowledge_graph(0)

    assert not handler.knowledge_graph_exists(0)
