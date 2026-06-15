"""Testes do API Gateway (autenticacao na borda - RNF01/RNF10).

Validam que o gateway rejeita acessos sem token valido ANTES de encaminhar
para os servicos internos.
"""


def test_health(client):
    assert client.get("/health").status_code == 200


def test_scheduling_requires_token(client):
    assert client.get("/api/scheduling/slots").status_code == 401


def test_invalid_token_rejected(client):
    r = client.get(
        "/api/scheduling/slots", headers={"Authorization": "Bearer token-invalido"}
    )
    assert r.status_code == 401


def test_auth_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
