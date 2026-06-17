"""Servico de Autenticacao - Hora Marcada.

Requisitos atendidos:
  RF01 - Cadastro de usuario      (POST /register)
  RF02 - Autenticacao de usuario  (POST /login -> JWT)
  RF06 - Suporte ao painel admin  (GET /users, perfil admin)
  RNF01 - JWT + hash de senha (bcrypt)
  RNF07 - Logs de auditoria
  RNF09 - Validacao de entrada (Pydantic) + ORM (anti SQLi)
  RNF10 - Controle de acesso por perfil (cliente/admin)
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from . import models, schemas, security
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .logging_config import configure_logging

settings = get_settings()
logger = configure_logging(settings.log_level)


def _migrate_database() -> None:
    """Adiciona campos novos sem apagar os usuarios existentes."""
    columns = {
        column["name"] for column in inspect(engine).get_columns("users")
    } if inspect(engine).has_table("users") else set()
    if columns and "phone" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT ''")
            )


def _seed_admin() -> None:
    """Cria um usuario administrador inicial (RF06) se ainda nao existir."""
    db = SessionLocal()
    try:
        existing = db.execute(
            select(models.User).where(models.User.role == "admin")
        ).scalar_one_or_none()
        if existing is None:
            admin = models.User(
                name=settings.admin_name,
                email=settings.admin_email,
                phone="",
                password_hash=security.hash_password(settings.admin_password),
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info("Usuario administrador inicial criado: %s", settings.admin_email)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_database()
    if settings.seed_admin:
        _seed_admin()
    logger.info("Auth-service iniciado")
    yield


app = FastAPI(title="Hora Marcada - Auth Service", version="1.0.0", lifespan=lifespan)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Cabecalhos de seguranca (mitigacao de XSS/clickjacking - RNF09)."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependencias de autorizacao (RNF10)
# ---------------------------------------------------------------------------
def get_current_claims(authorization: str = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecalho de autorizacao ausente ou invalido",
        )
    token = authorization.split(" ", 1)[1]
    try:
        return security.decode_token(token)
    except Exception:  # noqa: BLE001 - qualquer falha de token -> 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado",
        )


def require_admin(claims: dict = Depends(get_current_claims)) -> dict:
    if claims.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilegios de administrador necessarios",
        )
    return claims


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}


@app.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    """RF01 - Cadastro de usuario. O perfil e sempre 'cliente' (anti escalonamento)."""
    exists = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if exists is not None:
        logger.warning("Tentativa de cadastro com e-mail duplicado: %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="E-mail ja cadastrado"
        )

    user = models.User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=security.hash_password(payload.password),
        role="cliente",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Novo usuario cadastrado: id=%s email=%s", user.id, user.email)
    return user


@app.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """RF02 - Autenticacao. Retorna um token JWT assinado."""
    user = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()

    if user is None or not security.verify_password(payload.password, user.password_hash):
        # Mensagem generica evita enumeracao de usuarios (Information Disclosure).
        logger.warning("Falha de autenticacao para e-mail: %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas"
        )

    token = security.create_access_token(
        user.id, user.email, user.role, user.name, user.phone
    )
    logger.info("Autenticacao bem-sucedida: id=%s role=%s", user.id, user.role)
    return schemas.TokenOut(access_token=token, role=user.role, name=user.name)


@app.post(
    "/password-recovery/request",
    response_model=schemas.PasswordRecoveryResponse,
)
def request_password_recovery(
    payload: schemas.PasswordRecoveryRequest, db: Session = Depends(get_db)
):
    """Gera um token curto sem revelar se o e-mail esta cadastrado."""
    message = (
        "Se o e-mail estiver cadastrado, as instrucoes de recuperacao foram geradas."
    )
    user = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if user is None:
        logger.info("Recuperacao solicitada para e-mail nao cadastrado")
        return schemas.PasswordRecoveryResponse(message=message)

    token = security.create_password_reset_token(
        user.id, user.email, user.password_hash
    )
    logger.info("Token de recuperacao gerado para usuario id=%s", user.id)
    return schemas.PasswordRecoveryResponse(
        message=message,
        reset_token=token if settings.expose_password_reset_token else None,
    )


@app.post("/password-recovery/reset", response_model=schemas.MessageOut)
def reset_password(payload: schemas.PasswordReset, db: Session = Depends(get_db)):
    """Troca a senha e invalida automaticamente o token utilizado."""
    try:
        unverified = security.decode_token(payload.token)
        user = db.get(models.User, int(unverified["sub"]))
        if user is None or user.email != unverified.get("email"):
            raise ValueError("Usuario do token nao encontrado")
        security.validate_password_reset_token(payload.token, user.password_hash)
    except Exception:  # noqa: BLE001 - toda falha produz a mesma resposta
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperacao invalido ou expirado",
        )

    user.password_hash = security.hash_password(payload.new_password)
    db.commit()
    logger.info("Senha redefinida para usuario id=%s", user.id)
    return schemas.MessageOut(message="Senha redefinida com sucesso")


@app.get("/me", response_model=schemas.UserOut)
def me(claims: dict = Depends(get_current_claims), db: Session = Depends(get_db)):
    user = db.get(models.User, int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    return user


@app.get("/users", response_model=list[schemas.UserOut])
def list_users(_: dict = Depends(require_admin), db: Session = Depends(get_db)):
    """RF06 - Apoio ao painel administrativo (somente admin - RNF10)."""
    return db.execute(select(models.User)).scalars().all()
