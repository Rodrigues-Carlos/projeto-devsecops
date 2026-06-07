"""Testes do scheduling-service (RF03-RF10, RNF10)."""


def test_health(client):
    assert client.get("/health").status_code == 200


def test_requires_authentication(client):
    assert client.get("/slots").status_code == 401


def test_full_booking_flow(client, admin_headers, client_headers):
    # RF07 - admin cria horario
    r = client.post(
        "/slots", json={"barber": "Nathan", "date": "2026-06-10", "time": "09:00"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    slot_id = r.json()["id"]

    # RNF10 - cliente nao pode criar horario
    r = client.post(
        "/slots", json={"barber": "X", "date": "2026-06-10", "time": "10:00"},
        headers=client_headers,
    )
    assert r.status_code == 403

    # RF03 - listar horarios disponiveis
    slots = client.get("/slots", headers=client_headers).json()
    assert any(s["id"] == slot_id for s in slots)

    # RF04 - realizar agendamento
    r = client.post(
        "/appointments", json={"slot_id": slot_id, "service": "Corte"}, headers=client_headers
    )
    assert r.status_code == 201
    appt_id = r.json()["id"]

    # horario fica indisponivel -> novo agendamento e rejeitado
    r = client.post("/appointments", json={"slot_id": slot_id}, headers=client_headers)
    assert r.status_code == 409

    # cliente ve seu agendamento
    assert len(client.get("/appointments/me", headers=client_headers).json()) >= 1

    # RF10 - admin ve todos os agendamentos
    all_appts = client.get("/appointments", headers=admin_headers).json()
    assert any(a["id"] == appt_id for a in all_appts)

    # RF05 - cancelar
    assert client.delete(f"/appointments/{appt_id}", headers=client_headers).status_code == 204

    # horario volta a ficar disponivel
    slots = client.get("/slots", headers=client_headers).json()
    assert any(s["id"] == slot_id and s["available"] for s in slots)


def test_edit_and_remove_slot(client, admin_headers):
    sid = client.post(
        "/slots", json={"barber": "Carlos", "date": "2026-06-11", "time": "14:00"},
        headers=admin_headers,
    ).json()["id"]

    # RF08 - editar
    r = client.put(f"/slots/{sid}", json={"time": "15:00"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["time"] == "15:00"

    # RF09 - remover
    assert client.delete(f"/slots/{sid}", headers=admin_headers).status_code == 204


def test_cannot_cancel_others_appointment(client, admin_headers, client_headers, other_headers):
    sid = client.post(
        "/slots", json={"barber": "Leonardo", "date": "2026-06-12", "time": "09:00"},
        headers=admin_headers,
    ).json()["id"]
    appt_id = client.post(
        "/appointments", json={"slot_id": sid}, headers=client_headers
    ).json()["id"]

    # outro cliente nao pode cancelar (RNF10 / controle de acesso)
    assert client.delete(f"/appointments/{appt_id}", headers=other_headers).status_code == 403
