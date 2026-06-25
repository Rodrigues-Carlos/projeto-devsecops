"""Schemas Pydantic - validacao rigorosa de entrada (RNF09).

Pydantic valida tipos, tamanhos e formato de e-mail antes de qualquer
processamento, reduzindo a superficie de ataque (injecao/XSS).
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if not 10 <= len(digits) <= 13:
            raise ValueError("Informe um telefone com DDD")
        return digits


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return UserRegister.validate_phone(value)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class ProfileUpdateOut(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordReset(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class MessageOut(BaseModel):
    message: str
