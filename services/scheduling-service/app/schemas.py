"""Schemas Pydantic - validacao de entrada (RNF09)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SlotCreate(BaseModel):
    barber: str = Field(min_length=2, max_length=120)
    date: str = Field(min_length=10, max_length=10)  # YYYY-MM-DD
    time: str = Field(min_length=5, max_length=5)  # HH:MM


class SlotUpdate(BaseModel):
    barber: Optional[str] = Field(default=None, min_length=2, max_length=120)
    date: Optional[str] = Field(default=None, min_length=10, max_length=10)
    time: Optional[str] = Field(default=None, min_length=5, max_length=5)
    available: Optional[bool] = None


class SlotOut(BaseModel):
    id: int
    barber: str
    date: str
    time: str
    available: bool
    created_at: datetime

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
    user_email: str
    created_at: datetime
