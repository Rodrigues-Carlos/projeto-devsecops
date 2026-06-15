"""Funcoes de seguranca: hash de senha (bcrypt) e tokens JWT (RNF01).

- As senhas nunca sao armazenadas em texto plano (mitiga Information Disclosure).
- O token JWT e assinado com HS256 e possui expiracao (mitiga Spoofing).
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    user_id: int, email: str, role: str, name: str, phone: str
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "name": name,
        "phone": phone,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _password_version(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_password_reset_token(
    user_id: int, email: str, password_hash: str
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "purpose": "password_reset",
        "password_version": _password_version(password_hash),
        "iat": now,
        "exp": now + timedelta(minutes=settings.password_reset_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def validate_password_reset_token(token: str, password_hash: str) -> dict:
    payload = decode_token(token)
    if payload.get("purpose") != "password_reset":
        raise jwt.InvalidTokenError("Token com finalidade invalida")
    if not hmac.compare_digest(
        str(payload.get("password_version", "")),
        _password_version(password_hash),
    ):
        raise jwt.InvalidTokenError("Token ja utilizado")
    return payload
