"""Validacao de token JWT (segredo compartilhado com o auth-service).

A validacao local do token implementa defesa em profundidade: mesmo que o
gateway seja contornado, o servico continua exigindo um token valido (RNF01/RNF10).
"""
import jwt

from .config import get_settings

settings = get_settings()


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
