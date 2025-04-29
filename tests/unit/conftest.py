# tests/unit/conftest.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from llm.llm_app import app, conn

@pytest.fixture
def client():
    """Fixture for FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def mock_mongo():
    """Mock MongoDB connection"""
    with patch.object(conn, 'get_collection') as mock:
        mock_collection = MagicMock()
        mock.return_value = mock_collection
        yield mock_collection

@pytest.fixture
def mock_llm():
    """Mock LLM dependencies"""
    with patch('llm.agent.llm'), \
         patch('llm.agent.agent'), \
         patch('llm.agent.prompt'):
        yield