from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_dependencies():
    """Mock the service dependencies"""
    mock_service = MagicMock()
    with patch("prometheus.app.dependencies.initialize_services", return_value=mock_service):
        yield mock_service


@pytest.fixture
def test_client(mock_dependencies):
    """Create a TestClient instance with mocked settings and dependencies"""
    # Import app here to ensure settings are properly mocked
    from prometheus.app.main import app

    with TestClient(app) as client:
        yield client


def test_app_initialization(test_client, mock_dependencies):
    """Test that the app initializes correctly with mocked dependencies"""
    assert test_client.app.state.service is not None
    assert test_client.app.state.service == mock_dependencies
