from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prometheus.app.api.routes import issue
from prometheus.app.entity.repository import Repository
from prometheus.app.exception_handler import register_exception_handlers
from prometheus.lang_graph.graphs.issue_state import IssueType

app = FastAPI()
register_exception_handlers(app)
app.include_router(issue.router, prefix="/issue", tags=["issue"])
client = TestClient(app)


@pytest.fixture
def mock_service():
    service = mock.MagicMock()
    app.state.service = service
    yield service


def test_answer_issue(mock_service):
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
    mock_service["issue_service"].answer_issue.return_value = (
        "test patch",  # patch
        True,  # passed_reproducing_test
        True,  # passed_build
        True,  # passed_regression_test
        True,  # passed_existing_test
        "Issue fixed",  # issue_response
        IssueType.BUG,  # issue_type
    )

    response = client.post(
        "/issue/answer/",
        json={
            "repository_id": 1,
            "issue_title": "Test Issue",
            "issue_body": "Test description",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": {
            "patch": "test patch",
            "passed_reproducing_test": True,
            "passed_build": True,
            "passed_regression_test": True,
            "passed_existing_test": True,
            "issue_response": "Issue fixed",
            "issue_type": "bug",
        },
    }


def test_answer_issue_no_repository(mock_service):
    mock_service["repository_service"].get_repository_by_id.return_value = None

    response = client.post(
        "/issue/answer/",
        json={
            "repository_id": 1,
            "issue_title": "Test Issue",
            "issue_body": "Test description",
        },
    )

    assert response.status_code == 404


def test_answer_issue_invalid_container_config(mock_service):
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

    response = client.post(
        "/issue/answer/",
        json={
            "repository_id": 1,
            "issue_title": "Test Issue",
            "issue_body": "Test description",
            "dockerfile_content": "FROM python:3.11",
            "workdir": None,
        },
    )

    assert response.status_code == 400


def test_answer_issue_with_container(mock_service):
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

    mock_service["issue_service"].answer_issue.return_value = (
        "test patch",
        True,
        True,
        True,
        True,
        "Issue fixed",
        IssueType.BUG,
    )

    test_payload = {
        "repository_id": 1,
        "issue_title": "Test Issue",
        "issue_body": "Test description",
        "dockerfile_content": "FROM python:3.11",
        "run_reproduce_test": True,
        "workdir": "/app",
        "build_commands": ["pip install -r requirements.txt"],
        "test_commands": ["pytest ."],
    }

    response = client.post("/issue/answer/", json=test_payload)

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": {
            "patch": "test patch",
            "passed_reproducing_test": True,
            "passed_build": True,
            "passed_regression_test": True,
            "passed_existing_test": True,
            "issue_response": "Issue fixed",
            "issue_type": "bug",
        },
    }
