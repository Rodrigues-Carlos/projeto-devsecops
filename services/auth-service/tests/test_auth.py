"""Testes do auth-service (RF01, RF02, RNF01, RNF10)."""


def test_health(client):
    assert client.get("/health").status_code == 200


def test_register_login_me(client):
    r = client.post(
        "/register",
        json={
            "name": "Joao",
            "email": "joao@example.com",
            "phone": "41999999999",
            "password": "senha12345",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "cliente"  # cadastro nunca cria admin

    r = client.post("/login", json={"email": "joao@example.com", "password": "senha12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "joao@example.com"
    assert r.json()["phone"] == "41999999999"


def test_duplicate_email_rejected(client):
    body = {
        "name": "Ana",
        "email": "dup@example.com",
        "phone": "41988888888",
        "password": "senha12345",
    }
    assert client.post("/register", json=body).status_code == 201
    assert client.post("/register", json=body).status_code == 409


def test_wrong_password_rejected(client):
    client.post(
        "/register",
        json={
            "name": "Carlos",
            "email": "c@example.com",
            "phone": "41977777777",
            "password": "senha12345",
        },
    )
    r = client.post("/login", json={"email": "c@example.com", "password": "errada"})
    assert r.status_code == 401


def test_short_password_validation(client):
    r = client.post(
        "/register",
        json={
            "name": "Eva",
            "email": "e@example.com",
            "phone": "41966666666",
            "password": "123",
        },
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
        "/register",
        json={
            "name": "Davi",
            "email": "d@example.com",
            "phone": "41955555555",
            "password": "senha12345",
        },
    )
    token = client.post(
        "/login", json={"email": "d@example.com", "password": "senha12345"}
    ).json()["access_token"]
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403  # RNF10


def test_protected_without_token(client):
    assert client.get("/me").status_code == 401


def test_password_recovery_changes_password_and_invalidates_token(client):
    email = "recuperar@example.com"
    old_password = "senha-antiga"
    new_password = "senha-nova-123"
    client.post(
        "/register",
        json={
            "name": "Recuperar",
            "email": email,
            "phone": "41944444444",
            "password": old_password,
        },
    )

    response = client.post("/password-recovery/request", json={"email": email})
    assert response.status_code == 200
    token = response.json()["reset_token"]
    assert token

    response = client.post(
        "/password-recovery/reset",
        json={"token": token, "new_password": new_password},
    )
    assert response.status_code == 200
    assert client.post(
        "/login", json={"email": email, "password": old_password}
    ).status_code == 401
    assert client.post(
        "/login", json={"email": email, "password": new_password}
    ).status_code == 200

    reused = client.post(
        "/password-recovery/reset",
        json={"token": token, "new_password": "outra-senha-123"},
    )
    assert reused.status_code == 400


def test_password_recovery_does_not_reveal_unknown_email(client):
    response = client.post(
        "/password-recovery/request", json={"email": "inexistente@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["reset_token"] is None
    assert "Se o e-mail estiver cadastrado" in response.json()["message"]


def test_access_token_cannot_reset_password(client):
    access_token = client.post(
        "/login", json={"email": "admin@example.com", "password": "Admin@12345"}
    ).json()["access_token"]
    response = client.post(
        "/password-recovery/reset",
        json={"token": access_token, "new_password": "nova-senha-123"},
    )
    assert response.status_code == 400


def test_invalid_phone_rejected(client):
    response = client.post(
        "/register",
        json={
            "name": "Telefone",
            "email": "telefone@example.com",
            "phone": "123",
            "password": "senha12345",
        },
    )
    assert response.status_code == 422
