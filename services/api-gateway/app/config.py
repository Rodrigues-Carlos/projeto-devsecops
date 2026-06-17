"""Configuracao do API Gateway."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Servicos internos (resolvidos por DNS do Kubernetes / docker-compose)
    auth_service_url: str = "http://localhost:8001"
    scheduling_service_url: str = "http://localhost:8002"

    # Validacao de token (segredo compartilhado)
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"

    # Rate limiting (mitigacao de DoS / forca-bruta - STRIDE: Denial of Service)
    rate_limit: str = "120/minute"
    login_rate_limit: str = "10/minute"

    cors_origins: str = "*"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
