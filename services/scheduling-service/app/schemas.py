"""Schemas Pydantic - validacao de entrada (RNF09)."""
import re
from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import AfterValidator, BaseModel, Field
from typing_extensions import Annotated


def validate_slot_date(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("A data deve usar o formato YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("A data informada nao e valida") from exc
    if parsed < date.today():
        raise ValueError("A data nao pode estar no passado")
    if parsed > date.today() + timedelta(days=365):
        raise ValueError("A data deve estar dentro dos proximos 12 meses")
    if parsed.weekday() == 6:
        raise ValueError("Nao e permitido cadastrar horarios aos domingos")
    return value


def validate_slot_time(value: str) -> str:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise ValueError("O horario deve usar o formato HH:MM entre 00:00 e 23:59")
    return value


SlotDate = Annotated[str, AfterValidator(validate_slot_date)]
SlotTime = Annotated[str, AfterValidator(validate_slot_time)]


class SlotCreate(BaseModel):
    barber: str = Field(min_length=2, max_length=120)
    date: SlotDate
    time: SlotTime


class SlotUpdate(BaseModel):
    barber: Optional[str] = Field(default=None, min_length=2, max_length=120)
    date: Optional[SlotDate] = None
    time: Optional[SlotTime] = None
    available: Optional[bool] = None


class SlotOut(BaseModel):
    id: int
    barber: str
    date: str
    time: str
    available: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkingHoursUpsert(BaseModel):
    barber: str = Field(min_length=2, max_length=120)
    start_time: SlotTime
    end_time: SlotTime
    interval_minutes: int = Field(default=60, ge=15, le=240)


class WorkingHoursOut(BaseModel):
    id: int
    barber: str
    start_time: str
    end_time: str
    interval_minutes: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    slot_id: int
    service: str = Field(default="Corte de cabelo", min_length=2, max_length=120)


class AppointmentOut(BaseModel):
    id: int
    slot_id: int
    barber: str
    date: str
    time: str
    service: str
    status: str
    user_name: str
    user_email: str
    user_phone: str
    status_changed_by: str | None
    status_changed_role: str | None
    status_changed_at: datetime | None
    created_at: datetime


class AdminSlotPage(BaseModel):
    items: list[SlotOut]
    total: int
    available_total: int
    page: int
    pages: int


class AdminAppointmentPage(BaseModel):
    items: list[AppointmentOut]
    total: int
    active_total: int
    cancelled_total: int
    page: int
    pages: int
