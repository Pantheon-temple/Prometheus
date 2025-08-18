from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prometheus.app.api.routes import auth
from prometheus.app.exception_handler import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
client = TestClient(app)


@pytest.fixture
def mock_service():
    service = mock.MagicMock()
    app.state.service = service
    yield service


def test_login(mock_service):
    mock_service["user_service"].login.return_value = "your_access_token"
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "email": "test@gmail.com",
            "password": "passwordpassword",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": {"access_token": "your_access_token"},
    }
