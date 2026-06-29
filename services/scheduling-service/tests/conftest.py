"""Fixtures de teste do scheduling-service (SQLite isolado, tokens locais)."""
import datetime
import os
import pathlib

import jwt
import pytest

_DB = pathlib.Path(__file__).parent / "test_sched.db"
if _DB.exists():
    _DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["SEED_SLOTS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_SECRET = "test-secret"


def _token(sub, email, role):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(sub),
        "email": email,
        "role": role,
        "name": "Administrador" if role == "admin" else "Cliente Teste",
        "phone": "41999999999",
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, _SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {_token(99, 'admin@test.local', 'admin')}"}


@pytest.fixture
def client_headers():
    return {"Authorization": f"Bearer {_token(1, 'cliente@test.local', 'cliente')}"}


@pytest.fixture
def other_headers():
    return {"Authorization": f"Bearer {_token(2, 'outro@test.local', 'cliente')}"}
