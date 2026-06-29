"""Testes do scheduling-service (RF03-RF10, RNF10)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier


def future_date(days: int) -> str:
    value = date.today() + timedelta(days=days)
    if days >= 0 and value.weekday() == 6:
        value += timedelta(days=1)
    return value.isoformat()


def next_sunday() -> str:
    value = date.today()
    while value.weekday() != 6:
        value += timedelta(days=1)
    return value.isoformat()


def test_health(client):
    assert client.get("/health").status_code == 200


def test_requires_authentication(client):
    assert client.get("/slots").status_code == 401


def test_full_booking_flow(client, admin_headers, client_headers):
    # RF07 - admin cria horario
    r = client.post(
        "/slots", json={"barber": "Nathan", "date": future_date(10), "time": "09:00"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    slot_id = r.json()["id"]

    # RNF10 - cliente nao pode criar horario
    r = client.post(
        "/slots", json={"barber": "X", "date": future_date(10), "time": "10:00"},
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
    assert r.json()["status"] == "pendente"
    assert r.json()["user_name"] == "Cliente Teste"
    assert r.json()["user_phone"] == "41999999999"
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
        "/slots", json={"barber": "Carlos", "date": future_date(11), "time": "14:00"},
        headers=admin_headers,
    ).json()["id"]

    # RF08 - editar
    r = client.put(f"/slots/{sid}", json={"time": "15:00"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["time"] == "15:00"

    # RF09 - remover
    assert client.delete(f"/slots/{sid}", headers=admin_headers).status_code == 204


def test_cannot_remove_slot_with_active_appointment(client, admin_headers, client_headers):
    slot_id = client.post(
        "/slots",
        json={"barber": "Carlos", "date": future_date(13), "time": "16:00"},
        headers=admin_headers,
    ).json()["id"]
    appointment_id = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Barba"},
        headers=client_headers,
    ).json()["id"]

    response = client.delete(f"/slots/{slot_id}", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Horario possui um agendamento ativo e nao pode ser removido"
    )
    appointments = client.get("/appointments", headers=admin_headers).json()
    assert any(appointment["id"] == appointment_id for appointment in appointments)


def test_cannot_remove_slot_with_cancelled_history(client, admin_headers, client_headers):
    slot_id = client.post(
        "/slots",
        json={"barber": "Leonardo", "date": future_date(14), "time": "14:00"},
        headers=admin_headers,
    ).json()["id"]
    appointment_id = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Corte"},
        headers=client_headers,
    ).json()["id"]
    assert (
        client.delete(f"/appointments/{appointment_id}", headers=client_headers).status_code
        == 204
    )

    response = client.delete(f"/slots/{slot_id}", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Horario possui historico de agendamento e nao pode ser removido"
    )


def test_remove_nonexistent_slot_returns_not_found(client, admin_headers):
    response = client.delete("/slots/999999", headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Horario nao encontrado"


def test_rejects_invalid_or_past_slot_date(client, admin_headers):
    invalid_dates = [
        "2026-02-30",
        "20-06-2026",
        future_date(-1),
        (date.today() + timedelta(days=366)).isoformat(),
        next_sunday(),
    ]

    for invalid_date in invalid_dates:
        response = client.post(
            "/slots",
            json={"barber": "Nathan", "date": invalid_date, "time": "09:00"},
            headers=admin_headers,
        )
        assert response.status_code == 422


def test_rejects_invalid_slot_time(client, admin_headers):
    invalid_times = ["9:00", "24:00", "12:60", "12:00:00"]

    for invalid_time in invalid_times:
        response = client.post(
            "/slots",
            json={"barber": "Nathan", "date": future_date(15), "time": invalid_time},
            headers=admin_headers,
        )
        assert response.status_code == 422


def test_rejects_invalid_date_and_time_when_updating_slot(client, admin_headers):
    slot_id = client.post(
        "/slots",
        json={"barber": "Carlos", "date": future_date(16), "time": "10:00"},
        headers=admin_headers,
    ).json()["id"]

    assert (
        client.put(
            f"/slots/{slot_id}",
            json={"date": future_date(-1)},
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/slots/{slot_id}",
            json={"time": "25:00"},
            headers=admin_headers,
        ).status_code
        == 422
    )


def test_cannot_cancel_others_appointment(client, admin_headers, client_headers, other_headers):
    sid = client.post(
        "/slots", json={"barber": "Leonardo", "date": future_date(12), "time": "09:00"},
        headers=admin_headers,
    ).json()["id"]
    appt_id = client.post(
        "/appointments", json={"slot_id": sid}, headers=client_headers
    ).json()["id"]

    # outro cliente nao pode cancelar (RNF10 / controle de acesso)
    assert client.delete(f"/appointments/{appt_id}", headers=other_headers).status_code == 403


def test_concurrent_booking_allows_only_one_appointment(
    client, admin_headers, client_headers, other_headers
):
    slot_id = client.post(
        "/slots",
        json={"barber": "Nathan", "date": future_date(20), "time": "11:00"},
        headers=admin_headers,
    ).json()["id"]
    start = Barrier(2)

    def book(headers):
        start.wait()
        return client.post(
            "/appointments",
            json={"slot_id": slot_id, "service": "Corte"},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(book, [client_headers, other_headers]))

    assert sorted(response.status_code for response in responses) == [201, 409]

    appointments = client.get("/appointments", headers=admin_headers).json()
    active_for_slot = [
        appointment
        for appointment in appointments
        if appointment["slot_id"] == slot_id
        and appointment["status"] in ("pendente", "confirmado", "ativo")
    ]
    assert len(active_for_slot) == 1


def test_working_hours_generate_full_year_without_sundays(
    client, admin_headers, client_headers
):
    payload = {
        "barber": "Agenda Anual",
        "start_time": "09:00",
        "end_time": "12:00",
        "interval_minutes": 60,
    }
    response = client.post("/working-hours", json=payload, headers=admin_headers)
    assert response.status_code == 200

    slots = client.get("/slots", headers=client_headers).json()
    annual_slots = [slot for slot in slots if slot["barber"] == "Agenda Anual"]
    assert annual_slots
    assert all(date.fromisoformat(slot["date"]).weekday() != 6 for slot in annual_slots)
    assert {slot["time"] for slot in annual_slots} == {"09:00", "10:00", "11:00"}
    assert max(date.fromisoformat(slot["date"]) for slot in annual_slots) <= (
        date.today() + timedelta(days=365)
    )

    original_count = len(annual_slots)
    assert (
        client.post("/working-hours", json=payload, headers=admin_headers).status_code
        == 200
    )
    slots_after = client.get("/slots", headers=client_headers).json()
    assert len(
        [slot for slot in slots_after if slot["barber"] == "Agenda Anual"]
    ) == original_count


def test_rejects_slot_outside_working_hours(client, admin_headers):
    barber = "Expediente Restrito"
    client.post(
        "/working-hours",
        json={
            "barber": barber,
            "start_time": "10:00",
            "end_time": "12:00",
            "interval_minutes": 60,
        },
        headers=admin_headers,
    )

    response = client.post(
        "/slots",
        json={"barber": barber, "date": future_date(30), "time": "09:00"},
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Horario fora do funcionamento configurado para o profissional"
    )


def test_rejects_invalid_working_hours(client, admin_headers):
    response = client.post(
        "/working-hours",
        json={
            "barber": "Horario Invalido",
            "start_time": "18:00",
            "end_time": "09:00",
            "interval_minutes": 60,
        },
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_admin_slot_listing_is_filtered_and_paginated(client, admin_headers):
    response = client.get(
        "/admin/slots",
        params={"barber": "Nathan", "status": "livre", "page_size": 5},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5
    assert data["page"] == 1
    assert data["pages"] >= 1
    assert all("Nathan" in slot["barber"] for slot in data["items"])
    assert all(slot["available"] for slot in data["items"])


def test_admin_can_cancel_client_appointment(
    client, admin_headers, client_headers
):
    slot_id = client.post(
        "/slots",
        json={
            "barber": "Cancelamento Admin",
            "date": future_date(40),
            "time": "10:00",
        },
        headers=admin_headers,
    ).json()["id"]
    appointment_id = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Barba"},
        headers=client_headers,
    ).json()["id"]

    listing = client.get(
        "/admin/appointments",
        params={"email": "cliente@test.local", "status": "pendente"},
        headers=admin_headers,
    )
    assert listing.status_code == 200
    assert any(item["id"] == appointment_id for item in listing.json()["items"])

    assert (
        client.delete(
            f"/appointments/{appointment_id}", headers=admin_headers
        ).status_code
        == 204
    )
    cancelled = next(
        item
        for item in client.get(
            "/admin/appointments",
            params={"email": "cliente@test.local", "status": "cancelado"},
            headers=admin_headers,
        ).json()["items"]
        if item["id"] == appointment_id
    )
    assert cancelled["status_changed_by"] == "Administrador"
    assert cancelled["status_changed_role"] == "admin"
    slot = next(
        item
        for item in client.get(
            "/admin/slots",
            params={"barber": "Cancelamento Admin"},
            headers=admin_headers,
        ).json()["items"]
        if item["id"] == slot_id
    )
    assert slot["available"] is True


def test_admin_can_permanently_delete_client_appointment(
    client, admin_headers, client_headers
):
    slot_id = client.post(
        "/slots",
        json={
            "barber": "Exclusao Admin",
            "date": future_date(41),
            "time": "10:00",
        },
        headers=admin_headers,
    ).json()["id"]
    appointment_id = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Corte"},
        headers=client_headers,
    ).json()["id"]

    response = client.delete(
        f"/admin/appointments/{appointment_id}", headers=admin_headers
    )
    assert response.status_code == 204

    appointments = client.get(
        "/admin/appointments", headers=admin_headers
    ).json()["items"]
    assert all(item["id"] != appointment_id for item in appointments)

    slots = client.get(
        "/admin/slots",
        params={"barber": "Exclusao Admin"},
        headers=admin_headers,
    ).json()["items"]
    assert next(slot for slot in slots if slot["id"] == slot_id)["available"] is True


def test_cliente_cannot_permanently_delete_appointment(
    client, client_headers
):
    response = client.delete(
        "/admin/appointments/1", headers=client_headers
    )
    assert response.status_code == 403


def test_admin_can_confirm_pending_appointment(
    client, admin_headers, client_headers
):
    slot_id = client.post(
        "/slots",
        json={
            "barber": "Confirmacao Admin",
            "date": future_date(42),
            "time": "10:00",
        },
        headers=admin_headers,
    ).json()["id"]
    appointment = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Corte"},
        headers=client_headers,
    ).json()
    assert appointment["status"] == "pendente"

    response = client.put(
        f"/admin/appointments/{appointment['id']}/confirm",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmado"
    assert response.json()["status_changed_by"] == "Administrador"
    assert response.json()["status_changed_role"] == "admin"


def test_admin_can_cancel_appointment_from_occupied_slot(
    client, admin_headers, client_headers
):
    slot_id = client.post(
        "/slots",
        json={
            "barber": "Cancelamento pelo Horario",
            "date": future_date(43),
            "time": "10:00",
        },
        headers=admin_headers,
    ).json()["id"]
    appointment_id = client.post(
        "/appointments",
        json={"slot_id": slot_id, "service": "Barba"},
        headers=client_headers,
    ).json()["id"]

    response = client.put(
        f"/admin/slots/{slot_id}/cancel-appointment",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == appointment_id
    assert response.json()["status"] == "cancelado"
    assert response.json()["status_changed_by"] == "Administrador"

    slots = client.get(
        "/admin/slots",
        params={"barber": "Cancelamento pelo Horario"},
        headers=admin_headers,
    ).json()["items"]
    assert next(slot for slot in slots if slot["id"] == slot_id)["available"] is True
