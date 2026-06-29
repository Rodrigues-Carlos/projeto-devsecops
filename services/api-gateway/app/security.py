"""Validacao de token JWT no gateway (autenticacao na borda - RNF01/RNF10)."""
import jwt

from .config import get_settings

settings = get_settings()


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
