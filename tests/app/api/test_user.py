from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prometheus.app.api.routes import user
from prometheus.app.entity.user import User
from prometheus.app.exception_handler import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
app.include_router(user.router, prefix="/user", tags=["user"])
client = TestClient(app)


@pytest.fixture
def mock_service():
    service = mock.MagicMock()
    app.state.service = service
    yield service


def test_list(mock_service):
    # Mock user as admin and return a list of users
    mock_service["user_service"].list_users.return_value = [
        User(
            id=1,
            username="testuser",
            email="test@gmail.com",
            password_hash="hashedpassword",
            github_token="ghp_1234567890abcdef1234567890abcdef1234",
            issue_credit=10,
            is_superuser=False,
        )
    ]

    # Test the list endpoint
    response = client.get("user/list/")
    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": [
            {
                "id": 1,
                "username": "testuser",
                "email": "test@gmail.com",
                "issue_credit": 10,
                "is_superuser": False,
            }
        ],
    }
