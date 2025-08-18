import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from git import Repo
from testcontainers.neo4j import Neo4jContainer
from testcontainers.postgres import PostgresContainer

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.neo4j.knowledge_graph_handler import KnowledgeGraphHandler
from tests.test_utils import test_project_paths

NEO4J_IMAGE = "neo4j:5.20.0"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "password"

POSTGRES_IMAGE = "postgres"
POSTGRES_USERNAME = "postgres"
POSTGRES_PASSWORD = "password"
POSTGRES_DB = "postgres"


@pytest.fixture(scope="session")
async def neo4j_container_with_kg_fixture():
    kg = KnowledgeGraph(1000, 100, 10, 0)
    await kg.build_graph(test_project_paths.TEST_PROJECT_PATH)
    container = (
        Neo4jContainer(image=NEO4J_IMAGE, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
        .with_env("NEO4J_PLUGINS", '["apoc"]')
        .with_name(f"neo4j_container_with_kg_{uuid.uuid4().hex[:12]}")
    )
    with container as neo4j_container:
        driver = neo4j_container.get_driver()
        handler = KnowledgeGraphHandler(driver, 100)
        handler.write_knowledge_graph(kg)
        yield neo4j_container, kg


@pytest.fixture(scope="function")
def empty_neo4j_container_fixture():
    container = (
        Neo4jContainer(image=NEO4J_IMAGE, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
        .with_env("NEO4J_PLUGINS", '["apoc"]')
        .with_name(f"empty_neo4j_container_{uuid.uuid4().hex[:12]}")
    )
    with container as neo4j_container:
        yield neo4j_container


@pytest.fixture(scope="session")
def postgres_container_fixture():
    container = PostgresContainer(
        image=POSTGRES_IMAGE,
        username=POSTGRES_USERNAME,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
        port=5432,
    ).with_name(f"postgres_container_{uuid.uuid4().hex[:12]}")
    with container as postgres_container:
        yield postgres_container


@pytest.fixture(scope="function")
def git_repo_fixture():
    temp_dir = Path(tempfile.mkdtemp())
    temp_project_dir = temp_dir / "test_project"
    original_project_path = test_project_paths.TEST_PROJECT_PATH

    try:
        shutil.copytree(original_project_path, temp_project_dir)
        shutil.move(temp_project_dir / test_project_paths.GIT_DIR.name, temp_project_dir / ".git")

        repo = Repo(temp_project_dir)
        yield repo
    finally:
        shutil.rmtree(temp_project_dir)


@pytest.fixture
def temp_test_dir(tmp_path):
    """Create a temporary test directory."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    yield test_dir
    # Cleanup happens automatically after tests due to tmp_path fixture
