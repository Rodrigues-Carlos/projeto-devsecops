"""Configuracao do servico de agendamento (variaveis de ambiente).

O JWT_SECRET deve ser identico ao do auth-service e do gateway para que a
validacao do token funcione (segredo compartilhado, injetado via K8s Secret).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://sched:sched@localhost:5432/appointmentsdb"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    log_level: str = "INFO"
    seed_slots: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
