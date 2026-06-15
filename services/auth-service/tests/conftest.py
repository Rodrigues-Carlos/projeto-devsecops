"""Fixtures de teste do auth-service. Usa SQLite isolado (sem Postgres)."""
import os
import pathlib

import pytest

_DB = pathlib.Path(__file__).parent / "test_auth.db"
if _DB.exists():
    _DB.unlink()

# Variaveis de ambiente devem ser definidas ANTES de importar o app.
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["SEED_ADMIN"] = "true"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "Admin@12345"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
