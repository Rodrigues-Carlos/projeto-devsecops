"""Fixtures de teste do api-gateway."""
import os

import pytest

os.environ["JWT_SECRET"] = "test-secret"
os.environ["AUTH_SERVICE_URL"] = "http://127.0.0.1:9"
os.environ["SCHEDULING_SERVICE_URL"] = "http://127.0.0.1:9"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
