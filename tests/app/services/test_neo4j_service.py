import pytest

from prometheus.app.services.neo4j_service import Neo4jService
from tests.test_utils.fixtures import neo4j_container_with_kg_fixture  # noqa: F401


@pytest.mark.slow
async def test_neo4j_service(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    neo4j_service = Neo4jService(
        neo4j_container.get_connection_url(), neo4j_container.username, neo4j_container.password
    )
    assert neo4j_service.neo4j_driver is not None
    try:
        neo4j_service.neo4j_driver.verify_connectivity()
    except Exception as e:
        pytest.fail(f"Connection verification failed: {e}")
