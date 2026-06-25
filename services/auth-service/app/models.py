"""Modelo de dados de usuarios."""
from sqlalchemy import Column, DateTime, Integer, String, func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    # Controle de acesso baseado em perfil (RNF10): "cliente" ou "admin".
    role = Column(String(20), nullable=False, default="cliente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
