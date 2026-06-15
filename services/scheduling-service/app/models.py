"""Modelos de dados da agenda e dos agendamentos."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from .database import Base


class Slot(Base):
    """Horario disponivel na agenda de um barbeiro."""

    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    barber = Column(String(120), nullable=False)
    date = Column(String(10), nullable=False)  # formato ISO YYYY-MM-DD
    time = Column(String(5), nullable=False)  # formato HH:MM
    available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkingHours(Base):
    """Regra de funcionamento usada para gerar a agenda anual."""

    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    barber = Column(String(120), unique=True, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    interval_minutes = Column(Integer, nullable=False, default=60)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Appointment(Base):
    """Agendamento realizado por um cliente sobre um horario."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    user_name = Column(String(120), nullable=False, default="")
    user_email = Column(String(255), nullable=False)
    user_phone = Column(String(20), nullable=False, default="")
    service = Column(String(120), nullable=False, default="Corte de cabelo")
    status = Column(String(20), nullable=False, default="pendente")
    status_changed_by = Column(String(120), nullable=True)
    status_changed_role = Column(String(20), nullable=True)
    status_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
