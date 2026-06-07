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
from datetime import date, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from . import models, schemas, security
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .logging_config import configure_logging

settings = get_settings()
logger = configure_logging(settings.log_level)


def _seed_slots() -> None:
    """Popula horarios de exemplo (escala dos 3 barbeiros) para demonstracao."""
    db = SessionLocal()
    try:
        if db.execute(select(models.Slot)).first() is not None:
            return
        barbers = ["Nathan", "Carlos", "Leonardo"]
        times = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        for day_offset in range(3):
            day = (date.today() + timedelta(days=day_offset)).isoformat()
            for barber in barbers:
                for t in times:
                    db.add(models.Slot(barber=barber, date=day, time=t, available=True))
        db.commit()
        logger.info("Horarios de exemplo criados (seed).")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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


def _appointment_out(appt: models.Appointment, slot: models.Slot) -> schemas.AppointmentOut:
    return schemas.AppointmentOut(
        id=appt.id,
        slot_id=appt.slot_id,
        barber=slot.barber if slot else "",
        date=slot.date if slot else "",
        time=slot.time if slot else "",
        service=appt.service,
        status=appt.status,
        user_email=appt.user_email,
        created_at=appt.created_at,
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
    return db.execute(stmt.order_by(models.Slot.date, models.Slot.time)).scalars().all()


@app.post("/slots", response_model=schemas.SlotOut, status_code=status.HTTP_201_CREATED)
def create_slot(
    payload: schemas.SlotCreate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """RF07 - Definir horarios (admin)."""
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
    db.delete(slot)
    db.commit()
    logger.info("Horario removido: id=%s", slot_id)
    return None


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
    slot = db.get(models.Slot, payload.slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")
    if not slot.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Horario nao esta mais disponivel"
        )

    appt = models.Appointment(
        slot_id=slot.id,
        user_id=str(claims["sub"]),
        user_email=claims.get("email", ""),
        service=payload.service,
        status="ativo",
    )
    slot.available = False
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
    slot = db.get(models.Slot, appt.slot_id)
    if slot is not None:
        slot.available = True  # libera o horario novamente
    db.commit()
    logger.info("Agendamento cancelado: id=%s por user=%s", appt.id, claims["sub"])
    return None
