"""Configuracao do servico carregada a partir de variaveis de ambiente.

Nenhum segredo fica embutido no codigo. Em producao, JWT_SECRET e as
credenciais de banco sao injetados via Kubernetes Secret (RNF01).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco de dados de usuarios
    database_url: str = "postgresql+psycopg://auth:auth@localhost:5432/usersdb"

    # Autenticacao / JWT (RNF01)
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_expire_minutes: int = 15
    expose_password_reset_token: bool = False

    # Observabilidade (RNF07)
    log_level: str = "INFO"

    # Admin inicial (seed) para o painel administrativo (RF06)
    seed_admin: bool = True
    admin_name: str = "Administrador"
    admin_email: str = "admin@horamarcada.com"
    admin_password: str = "Admin@12345"


@lru_cache
def get_settings() -> Settings:
    return Settings()
