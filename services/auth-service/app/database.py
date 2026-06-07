"""Camada de acesso ao banco de dados (SQLAlchemy ORM).

O uso do ORM garante consultas parametrizadas, mitigando SQL Injection (RNF09).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

# SQLite (usado nos testes) exige check_same_thread=False.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args=_connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """Dependencia FastAPI: abre e fecha uma sessao por requisicao."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
