# tests/unit/conftest.py
import os
import sys
import pathlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# 1.  Guarantee the project root is on sys.path  ----------------------------
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if PROJECT_ROOT.as_posix() not in map(str, sys.path):
    sys.path.insert(0, PROJECT_ROOT.as_posix())

# ---------------------------------------------------------------------------
# 2.  Supply mandatory env-vars before importing the app  -------------------
# ---------------------------------------------------------------------------
os.environ.setdefault("LLM_API_PROVIDER", "OPENAI")       # any valid provider
os.environ.setdefault("OPENAI_API_KEY", "DUMMY_KEY")      # dummy value
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/testdb")

# ---------------------------------------------------------------------------
# 3.  Import the FastAPI application (now safe)  ----------------------------
# ---------------------------------------------------------------------------
from llm.llm_app import app, conn          # noqa: E402  (import after setup)

# Make the connection object visible for tests that reference the bare name
import builtins                            # noqa: E402
builtins.conn = conn

# ---------------------------------------------------------------------------
# 4.  Pytest fixtures  -------------------------------------------------------
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_mongo():
    """Return a mocked MongoDB collection used by the application."""
    with patch.object(conn, "get_collection") as patched_get:
        mock_collection = MagicMock()
        patched_get.return_value = mock_collection
        # llm.llm_app imported earlier – overwrite its already-created var
        import llm.llm_app as _llm_app              # local import to avoid cycle
        _llm_app.articles_collection = mock_collection
        yield mock_collection


@pytest.fixture
def mock_llm():
    """Stub out heavy LLM dependencies so no real API calls are made."""
    with (
        patch("llm.agent.llm"),
        patch("llm.agent.agent"),
        patch("llm.agent.prompt"),
    ):
        yield