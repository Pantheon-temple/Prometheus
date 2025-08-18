from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prometheus.app.api.routes import repository
from prometheus.app.entity.repository import Repository
from prometheus.app.exception_handler import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
app.include_router(repository.router, prefix="/repository", tags=["repository"])
client = TestClient(app)


@pytest.fixture
def mock_service():
    service = mock.MagicMock()
    app.state.service = service
    yield service


def test_upload_repository(mock_service):
    mock_service["repository_service"].clone_github_repo.return_value = "/mock/path"
    response = client.post(
        "/repository/upload",
        json={
            "github_token": "mock_token",
            "https_url": "https://github.com/Pantheon-temple/Prometheus",
        },
    )
    assert response.status_code == 200


def test_upload_repository_at_commit(mock_service):
    mock_service["repository_service"].clone_github_repo.return_value = "/mock/path"
    response = client.post(
        "/repository/upload/",
        json={
            "github_token": "mock_token",
            "https_url": "https://github.com/Pantheon-temple/Prometheus",
            "commit_id": "0c554293648a8705769fa53ec896ae24da75f4fc",
        },
    )
    assert response.status_code == 200


def test_create_branch_and_push(mock_service):
    # Mock git_repo
    git_repo_mock = MagicMock()
    git_repo_mock.create_and_push_branch = AsyncMock(return_value=None)

    # Let repository_service.get_repository return the mocked git_repo
    mock_service["repository_service"].get_repository.return_value = git_repo_mock

    response = client.post(
        "/repository/create-branch-and-push/",
        json={
            "repository_id": 1,
            "branch_name": "new_branch",
            "commit_message": "Initial commit on new branch",
            "patch": "mock_patch_content",
        },
    )

    assert response.status_code == 200


def test_delete(mock_service):
    mock_service["repository_service"].get_repository_by_id.return_value = Repository(
        id=1,
        url="https://github.com/fake/repo.git",
        commit_id=None,
        playground_path="/path/to/playground",
        kg_root_node_id=0,
        user_id=None,
        kg_max_ast_depth=100,
        kg_chunk_size=1000,
        kg_chunk_overlap=100,
    )
    mock_service["knowledge_graph_service"].clear_kg.return_value = None
    mock_service["repository_service"].clean_repository.return_value = None
    mock_service["repository_service"].delete_repository.return_value = None
    response = client.delete(
        "repository/delete",
        params={
            "repository_id": 1,
        },
    )
    assert response.status_code == 200
