"""Testes do auth-service (RF01, RF02, RNF01, RNF10)."""


def test_health(client):
    assert client.get("/health").status_code == 200


def test_register_login_me(client):
    r = client.post(
        "/register",
        json={"name": "Joao", "email": "joao@example.com", "password": "senha12345"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "cliente"  # cadastro nunca cria admin

    r = client.post("/login", json={"email": "joao@example.com", "password": "senha12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "joao@example.com"


def test_duplicate_email_rejected(client):
    body = {"name": "Ana", "email": "dup@example.com", "password": "senha12345"}
    assert client.post("/register", json=body).status_code == 201
    assert client.post("/register", json=body).status_code == 409


def test_wrong_password_rejected(client):
    client.post(
        "/register", json={"name": "Carlos", "email": "c@example.com", "password": "senha12345"}
    )
    r = client.post("/login", json={"email": "c@example.com", "password": "errada"})
    assert r.status_code == 401


def test_short_password_validation(client):
    r = client.post(
        "/register", json={"name": "Eva", "email": "e@example.com", "password": "123"}
    )
    assert r.status_code == 422  # Pydantic rejeita (RNF09)


def test_admin_can_list_users(client):
    token = client.post(
        "/login", json={"email": "admin@example.com", "password": "Admin@12345"}
    ).json()["access_token"]
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_cliente_cannot_list_users(client):
    client.post(
        "/register", json={"name": "Davi", "email": "d@example.com", "password": "senha12345"}
    )
    token = client.post(
        "/login", json={"email": "d@example.com", "password": "senha12345"}
    ).json()["access_token"]
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403  # RNF10


def test_protected_without_token(client):
    assert client.get("/me").status_code == 401
