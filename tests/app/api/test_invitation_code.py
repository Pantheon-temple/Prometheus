import datetime
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prometheus.app.api.routes import invitation_code
from prometheus.app.entity.invitation_code import InvitationCode
from prometheus.app.exception_handler import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
app.include_router(invitation_code.router, prefix="/invitation-code", tags=["invitation_code"])
client = TestClient(app)


@pytest.fixture
def mock_service():
    service = mock.MagicMock()
    app.state.service = service
    yield service


def test_create_invitation_code(mock_service):
    # Mock the return value of create_invitation_code
    mock_service["invitation_code_service"].create_invitation_code.return_value = InvitationCode(
        id=1,
        code="testcode",
        is_used=False,
        expiration_time=datetime.datetime(year=2025, month=1, day=1, hour=0, minute=0, second=0),
    )

    # Test the creation endpoint
    response = client.post("invitation-code/create/")
    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "code": "testcode",
            "is_used": False,
            "expiration_time": "2025-01-01T00:00:00",
        },
    }


def test_list(mock_service):
    # Mock user as admin and return a list of invitation codes
    mock_service["invitation_code_service"].list_invitation_codes.return_value = [
        InvitationCode(
            id=1,
            code="testcode",
            is_used=False,
            expiration_time=datetime.datetime(
                year=2025, month=1, day=1, hour=0, minute=0, second=0
            ),
        )
    ]

    # Test the list endpoint
    response = client.get("invitation-code/list/")
    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "success",
        "data": [
            {
                "id": 1,
                "code": "testcode",
                "is_used": False,
                "expiration_time": "2025-01-01T00:00:00",
            }
        ],
    }
