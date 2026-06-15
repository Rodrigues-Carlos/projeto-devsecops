"""Servico de Agendamento - Hora Marcada.

Requisitos atendidos:
  RF03 - Visualizar horarios disponiveis (GET /slots)
  RF04 - Realizar agendamento           (POST /appointments)
  RF05 - Cancelar agendamento           (DELETE /appointments/{id})
  RF07 - Definir horarios   (POST /slots, admin)
  RF08 - Editar horarios    (PUT /slots/{id}, admin)
  RF09 - Remover horarios   (DELETE /slots/{id}, admin)
  RF10 - Visualizar todos os agendamentos (GET /appointments, admin)
  RNF01/RNF10 - Token JWT + controle de acesso por perfil
  RNF07 - Logs de auditoria      RNF09 - Validacao (Pydantic) + ORM (anti SQLi)
"""
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text, update
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from . import models, schemas, security
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .logging_config import configure_logging

settings = get_settings()
logger = configure_logging(settings.log_level)


def _migrate_database() -> None:
    """Adiciona dados de contato e auditoria sem perder agendamentos."""
    inspector = inspect(engine)
    if not inspector.has_table("appointments"):
        return
    columns = {column["name"] for column in inspector.get_columns("appointments")}
    migrations = {
        "user_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "user_phone": "VARCHAR(20) NOT NULL DEFAULT ''",
        "status_changed_by": "VARCHAR(120)",
        "status_changed_role": "VARCHAR(20)",
        "status_changed_at": "TIMESTAMP",
    }
    with engine.begin() as connection:
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE appointments ADD COLUMN {column} {definition}"
                    )
                )


def _time_to_minutes(value: str) -> int:
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def _minutes_to_time(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _generate_slots_for_rule(db: Session, rule: models.WorkingHours) -> int:
    """Gera somente horarios ausentes para os proximos 12 meses."""
    start_minutes = _time_to_minutes(rule.start_time)
    end_minutes = _time_to_minutes(rule.end_time)
    existing = {
        (slot.date, slot.time)
        for slot in db.execute(
            select(models.Slot).where(models.Slot.barber == rule.barber)
        ).scalars()
    }
    created = 0
    current = date.today()
    last_day = current + timedelta(days=365)
    while current <= last_day:
        if current.weekday() != 6:
            minute = start_minutes
            while minute < end_minutes:
                key = (current.isoformat(), _minutes_to_time(minute))
                if key not in existing:
                    db.add(
                        models.Slot(
                            barber=rule.barber,
                            date=key[0],
                            time=key[1],
                            available=True,
                        )
                    )
                    existing.add(key)
                    created += 1
                minute += rule.interval_minutes
        current += timedelta(days=1)
    return created


def _seed_slots() -> None:
    """Configura a escala de demonstracao e garante um ano de agenda."""
    db = SessionLocal()
    try:
        barbers = ["Nathan", "Carlos", "Leonardo"]
        total = 0
        for barber in barbers:
            rule = db.execute(
                select(models.WorkingHours).where(
                    models.WorkingHours.barber == barber
                )
            ).scalar_one_or_none()
            if rule is None:
                rule = models.WorkingHours(
                    barber=barber,
                    start_time="09:00",
                    end_time="17:00",
                    interval_minutes=60,
                )
                db.add(rule)
                db.flush()
            total += _generate_slots_for_rule(db, rule)
        db.commit()
        logger.info("Agenda anual garantida: %s novos horarios.", total)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_database()
    if settings.seed_slots:
        _seed_slots()
    logger.info("Scheduling-service iniciado")
    yield


app = FastAPI(title="Hora Marcada - Scheduling Service", version="1.0.0", lifespan=lifespan)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------------------------------------------------------------------------
# Autorizacao (RNF10)
# ---------------------------------------------------------------------------
def get_current_claims(authorization: str = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecalho de autorizacao ausente ou invalido",
        )
    token = authorization.split(" ", 1)[1]
    try:
        return security.decode_token(token)
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido ou expirado"
        )


def require_admin(claims: dict = Depends(get_current_claims)) -> dict:
    if claims.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilegios de administrador necessarios",
        )
    return claims


def _actor_name(claims: dict) -> str:
    return claims.get("name") or claims.get("email") or f"Usuario {claims['sub']}"


def _appointment_out(appt: models.Appointment, slot: models.Slot) -> schemas.AppointmentOut:
    return schemas.AppointmentOut(
        id=appt.id,
        slot_id=appt.slot_id,
        barber=slot.barber if slot else "",
        date=slot.date if slot else "",
        time=slot.time if slot else "",
        service=appt.service,
        status=appt.status,
        user_name=appt.user_name,
        user_email=appt.user_email,
        user_phone=appt.user_phone,
        status_changed_by=appt.status_changed_by,
        status_changed_role=appt.status_changed_role,
        status_changed_at=appt.status_changed_at,
        created_at=appt.created_at,
    )


def _validate_slot_against_working_hours(
    db: Session, barber: str, slot_date: str, slot_time: str
) -> None:
    parsed_date = date.fromisoformat(slot_date)
    if parsed_date.weekday() == 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nao e permitido agendar aos domingos",
        )

    rule = db.execute(
        select(models.WorkingHours).where(models.WorkingHours.barber == barber)
    ).scalar_one_or_none()
    if rule is None:
        return

    minute = _time_to_minutes(slot_time)
    start = _time_to_minutes(rule.start_time)
    end = _time_to_minutes(rule.end_time)
    if minute < start or minute >= end or (minute - start) % rule.interval_minutes != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Horario fora do funcionamento configurado para o profissional",
        )


def _slot_matches_working_hours(
    slot: models.Slot, rules: dict[str, models.WorkingHours]
) -> bool:
    parsed_date = date.fromisoformat(slot.date)
    if parsed_date.weekday() == 6:
        return False
    rule = rules.get(slot.barber)
    if rule is None:
        return True
    minute = _time_to_minutes(slot.time)
    start = _time_to_minutes(rule.start_time)
    end = _time_to_minutes(rule.end_time)
    return (
        start <= minute < end
        and (minute - start) % rule.interval_minutes == 0
    )


# ---------------------------------------------------------------------------
# Horarios (slots)
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduling-service"}


@app.get("/slots", response_model=list[schemas.SlotOut])
def list_slots(
    claims: dict = Depends(get_current_claims),
    include_all: bool = Query(default=False, alias="all"),
    db: Session = Depends(get_db),
):
    """RF03 - Lista horarios disponiveis. ?all=true (somente admin) lista todos."""
    stmt = select(models.Slot)
    if include_all:
        if claims.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Apenas admin pode listar todos"
            )
    else:
        stmt = stmt.where(models.Slot.available.is_(True))
    slots = db.execute(
        stmt.order_by(models.Slot.date, models.Slot.time)
    ).scalars().all()
    if include_all:
        return slots
    rules = {
        rule.barber: rule
        for rule in db.execute(select(models.WorkingHours)).scalars().all()
    }
    return [slot for slot in slots if _slot_matches_working_hours(slot, rules)]


@app.get("/admin/slots", response_model=schemas.AdminSlotPage)
def admin_slots(
    barber: str | None = None,
    slot_date: str | None = Query(default=None, alias="date"),
    slot_status: str = Query(default="todos", alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    filters = []
    if barber:
        filters.append(models.Slot.barber.ilike(f"%{barber}%"))
    if slot_date:
        filters.append(models.Slot.date == slot_date)
    if slot_status == "livre":
        filters.append(models.Slot.available.is_(True))
    elif slot_status == "ocupado":
        filters.append(models.Slot.available.is_(False))

    total = db.execute(
        select(func.count(models.Slot.id)).where(*filters)
    ).scalar_one()
    available_total = db.execute(
        select(func.count(models.Slot.id)).where(models.Slot.available.is_(True))
    ).scalar_one()
    pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, pages)
    items = (
        db.execute(
            select(models.Slot)
            .where(*filters)
            .order_by(models.Slot.date, models.Slot.time, models.Slot.barber)
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return schemas.AdminSlotPage(
        items=items,
        total=total,
        available_total=available_total,
        page=current_page,
        pages=pages,
    )


@app.post("/slots", response_model=schemas.SlotOut, status_code=status.HTTP_201_CREATED)
def create_slot(
    payload: schemas.SlotCreate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """RF07 - Definir horarios (admin)."""
    _validate_slot_against_working_hours(
        db, payload.barber, payload.date, payload.time
    )
    duplicate = db.execute(
        select(models.Slot.id).where(
            models.Slot.barber == payload.barber,
            models.Slot.date == payload.date,
            models.Slot.time == payload.time,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horario ja cadastrado para este profissional",
        )
    slot = models.Slot(barber=payload.barber, date=payload.date, time=payload.time, available=True)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    logger.info("Horario criado: id=%s %s %s %s", slot.id, slot.barber, slot.date, slot.time)
    return slot


@app.put("/slots/{slot_id}", response_model=schemas.SlotOut)
def update_slot(
    slot_id: int,
    payload: schemas.SlotUpdate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """RF08 - Editar horarios (admin)."""
    slot = db.get(models.Slot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")
    data = payload.model_dump(exclude_unset=True)
    next_barber = data.get("barber", slot.barber)
    next_date = data.get("date", slot.date)
    next_time = data.get("time", slot.time)
    _validate_slot_against_working_hours(db, next_barber, next_date, next_time)
    for field, value in data.items():
        setattr(slot, field, value)
    db.commit()
    db.refresh(slot)
    logger.info("Horario atualizado: id=%s", slot.id)
    return slot


@app.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    slot_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """RF09 - Remover horarios (admin)."""
    slot = db.get(models.Slot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")

    active_appointment = db.execute(
        select(models.Appointment.id)
        .where(
            models.Appointment.slot_id == slot_id,
            models.Appointment.status.in_(("ativo", "pendente", "confirmado")),
        )
        .limit(1)
    ).scalar_one_or_none()
    if active_appointment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horario possui um agendamento ativo e nao pode ser removido",
        )

    appointment_history = db.execute(
        select(models.Appointment.id)
        .where(models.Appointment.slot_id == slot_id)
        .limit(1)
    ).scalar_one_or_none()
    if appointment_history is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horario possui historico de agendamento e nao pode ser removido",
        )

    db.delete(slot)
    db.commit()
    logger.info("Horario removido: id=%s", slot_id)
    return None


@app.put(
    "/admin/slots/{slot_id}/cancel-appointment",
    response_model=schemas.AppointmentOut,
)
def cancel_slot_appointment(
    slot_id: int,
    claims: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Cancela o agendamento ativo diretamente pela lista de horarios."""
    slot = db.get(models.Slot, slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario nao encontrado",
        )

    appt = db.execute(
        select(models.Appointment)
        .where(
            models.Appointment.slot_id == slot_id,
            models.Appointment.status.in_(("ativo", "pendente", "confirmado")),
        )
        .order_by(models.Appointment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento ativo nao encontrado para este horario",
        )

    appt.status = "cancelado"
    appt.status_changed_by = _actor_name(claims)
    appt.status_changed_role = claims.get("role", "")
    appt.status_changed_at = datetime.now()
    slot.available = True
    db.commit()
    db.refresh(appt)
    logger.info(
        "Agendamento cancelado pelo horario: id=%s slot=%s por=%s",
        appt.id,
        slot.id,
        appt.status_changed_by,
    )
    return _appointment_out(appt, slot)


# ---------------------------------------------------------------------------
# Funcionamento
# ---------------------------------------------------------------------------
@app.get("/working-hours", response_model=list[schemas.WorkingHoursOut])
def list_working_hours(
    _: dict = Depends(require_admin), db: Session = Depends(get_db)
):
    return (
        db.execute(select(models.WorkingHours).order_by(models.WorkingHours.barber))
        .scalars()
        .all()
    )


@app.post("/working-hours", response_model=schemas.WorkingHoursOut)
def set_working_hours(
    payload: schemas.WorkingHoursUpsert,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if _time_to_minutes(payload.start_time) >= _time_to_minutes(payload.end_time):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O horario inicial deve ser anterior ao horario final",
        )

    rule = db.execute(
        select(models.WorkingHours).where(
            models.WorkingHours.barber == payload.barber
        )
    ).scalar_one_or_none()
    if rule is None:
        rule = models.WorkingHours(barber=payload.barber)
        db.add(rule)

    rule.start_time = payload.start_time
    rule.end_time = payload.end_time
    rule.interval_minutes = payload.interval_minutes
    rule.updated_at = datetime.now()
    db.flush()
    created = _generate_slots_for_rule(db, rule)
    db.commit()
    db.refresh(rule)
    logger.info(
        "Funcionamento atualizado: %s %s-%s, %s minutos, %s slots criados",
        rule.barber,
        rule.start_time,
        rule.end_time,
        rule.interval_minutes,
        created,
    )
    return rule


# ---------------------------------------------------------------------------
# Agendamentos (appointments)
# ---------------------------------------------------------------------------
@app.post("/appointments", response_model=schemas.AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: schemas.AppointmentCreate,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """RF04 - Realizar agendamento."""
    slot_for_validation = db.get(models.Slot, payload.slot_id)
    if slot_for_validation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario nao encontrado",
        )
    _validate_slot_against_working_hours(
        db,
        slot_for_validation.barber,
        slot_for_validation.date,
        slot_for_validation.time,
    )
    reservation = db.execute(
        update(models.Slot)
        .where(
            models.Slot.id == payload.slot_id,
            models.Slot.available.is_(True),
        )
        .values(available=False)
        .execution_options(synchronize_session=False)
    )

    if reservation.rowcount == 0:
        slot_exists = db.execute(
            select(models.Slot.id).where(models.Slot.id == payload.slot_id)
        ).scalar_one_or_none()
        if slot_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario nao encontrado",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Horario nao esta mais disponivel"
        )

    slot = db.get(models.Slot, payload.slot_id)
    appt = models.Appointment(
        slot_id=slot.id,
        user_id=str(claims["sub"]),
        user_name=claims.get("name", ""),
        user_email=claims.get("email", ""),
        user_phone=claims.get("phone", ""),
        service=payload.service,
        status="pendente",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    logger.info("Agendamento criado: id=%s user=%s slot=%s", appt.id, appt.user_id, slot.id)
    return _appointment_out(appt, slot)


@app.get("/appointments/me", response_model=list[schemas.AppointmentOut])
def my_appointments(claims: dict = Depends(get_current_claims), db: Session = Depends(get_db)):
    """Lista os agendamentos do proprio cliente."""
    appts = (
        db.execute(
            select(models.Appointment).where(models.Appointment.user_id == str(claims["sub"]))
        )
        .scalars()
        .all()
    )
    return [_appointment_out(a, db.get(models.Slot, a.slot_id)) for a in appts]


@app.get("/appointments", response_model=list[schemas.AppointmentOut])
def all_appointments(_: dict = Depends(require_admin), db: Session = Depends(get_db)):
    """RF10 - Visualizar todos os agendamentos (admin)."""
    appts = db.execute(select(models.Appointment)).scalars().all()
    return [_appointment_out(a, db.get(models.Slot, a.slot_id)) for a in appts]


@app.get("/admin/appointments", response_model=schemas.AdminAppointmentPage)
def admin_appointments(
    email: str | None = None,
    appointment_status: str = Query(default="todos", alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    filters = []
    if email:
        filters.append(models.Appointment.user_email.ilike(f"%{email}%"))
    if appointment_status in ("pendente", "confirmado", "cancelado"):
        filters.append(models.Appointment.status == appointment_status)

    total = db.execute(
        select(func.count(models.Appointment.id)).where(*filters)
    ).scalar_one()
    active_total = db.execute(
        select(func.count(models.Appointment.id)).where(
            models.Appointment.status.in_(("ativo", "pendente", "confirmado"))
        )
    ).scalar_one()
    cancelled_total = db.execute(
        select(func.count(models.Appointment.id)).where(
            models.Appointment.status == "cancelado"
        )
    ).scalar_one()
    pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, pages)
    appointments = (
        db.execute(
            select(models.Appointment)
            .where(*filters)
            .order_by(models.Appointment.created_at.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    items = [
        _appointment_out(appointment, db.get(models.Slot, appointment.slot_id))
        for appointment in appointments
    ]
    return schemas.AdminAppointmentPage(
        items=items,
        total=total,
        active_total=active_total,
        cancelled_total=cancelled_total,
        page=current_page,
        pages=pages,
    )


@app.put(
    "/admin/appointments/{appointment_id}/confirm",
    response_model=schemas.AppointmentOut,
)
def confirm_appointment(
    appointment_id: int,
    claims: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    appt = db.get(models.Appointment, appointment_id)
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento nao encontrado",
        )
    if appt.status == "cancelado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agendamento cancelado nao pode ser confirmado",
        )
    appt.status = "confirmado"
    appt.status_changed_by = _actor_name(claims)
    appt.status_changed_role = claims.get("role", "")
    appt.status_changed_at = datetime.now()
    db.commit()
    db.refresh(appt)
    logger.info(
        "Agendamento confirmado: id=%s por=%s",
        appt.id,
        appt.status_changed_by,
    )
    return _appointment_out(appt, db.get(models.Slot, appt.slot_id))


@app.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: int,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """RF05 - Cancelar agendamento (dono do agendamento ou admin)."""
    appt = db.get(models.Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento nao encontrado")

    is_owner = appt.user_id == str(claims["sub"])
    is_admin = claims.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Voce nao pode cancelar este agendamento"
        )
    if appt.status == "cancelado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agendamento ja cancelado")

    appt.status = "cancelado"
    appt.status_changed_by = _actor_name(claims)
    appt.status_changed_role = claims.get("role", "")
    appt.status_changed_at = datetime.now()
    slot = db.get(models.Slot, appt.slot_id)
    if slot is not None:
        slot.available = True  # libera o horario novamente
    db.commit()
    logger.info(
        "Agendamento cancelado: id=%s por=%s",
        appt.id,
        appt.status_changed_by,
    )
    return None


@app.delete(
    "/admin/appointments/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_appointment(
    appointment_id: int,
    claims: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Exclusao definitiva de agendamento, restrita ao administrador."""
    appt = db.get(models.Appointment, appointment_id)
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento nao encontrado",
        )

    slot = db.get(models.Slot, appt.slot_id)
    if slot is not None and appt.status in ("ativo", "pendente", "confirmado"):
        slot.available = True

    db.delete(appt)
    db.commit()
    logger.warning(
        "Agendamento excluido definitivamente: id=%s por admin=%s",
        appointment_id,
        claims["sub"],
    )
    return None
