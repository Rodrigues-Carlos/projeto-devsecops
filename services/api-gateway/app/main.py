"""API Gateway - Hora Marcada.

Ponto unico de entrada para o cliente externo (requisito de arquitetura).
Responsabilidades:
  - Rotear requisicoes REST para os servicos internos (auth e scheduling);
  - Validar o token JWT na borda (autenticacao - RNF01/RNF10);
  - Aplicar rate limiting (mitigacao de DoS / forca-bruta - STRIDE);
  - Adicionar cabecalhos de seguranca.

Mapa de rotas:
  /api/auth/*        -> auth-service
  /api/scheduling/*  -> scheduling-service
"""
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from . import security
from .config import get_settings
from .logging_config import configure_logging

settings = get_settings()
logger = configure_logging(settings.log_level)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

app = FastAPI(title="Hora Marcada - API Gateway", version="1.0.0")
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit excedido para %s", get_remote_address(request))
    return Response(content='{"detail":"Muitas requisicoes"}', status_code=429, media_type="application/json")


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cabecalhos hop-by-hop que nao devem ser repassados.
_EXCLUDED_RESPONSE_HEADERS = {
    "content-encoding",
    "transfer-encoding",
    "connection",
    "content-length",
}


def _require_auth(request: Request) -> dict:
    """Valida o token JWT presente no cabecalho Authorization."""
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticacao ausente"
        )
    token = auth.split(" ", 1)[1]
    try:
        return security.decode_token(token)
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido ou expirado"
        )


async def _proxy(request: Request, base_url: str, path: str) -> Response:
    """Encaminha a requisicao para o servico interno e devolve a resposta."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    fwd_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            upstream = await client.request(
                request.method,
                url,
                params=dict(request.query_params),
                content=body,
                headers=fwd_headers,
            )
    except httpx.RequestError as exc:
        logger.error("Falha ao contatar servico interno %s: %s", url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Servico interno indisponivel"
        )

    resp_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _EXCLUDED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=upstream.headers.get("content-type"),
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}


@app.post("/api/auth/login")
@limiter.limit(settings.login_rate_limit)
async def proxy_login(request: Request):
    """Login com rate limit mais restrito (anti forca-bruta)."""
    return await _proxy(request, settings.auth_service_url, "login")


@app.post("/api/auth/password-recovery/request")
@limiter.limit(settings.login_rate_limit)
async def proxy_password_recovery_request(request: Request):
    return await _proxy(request, settings.auth_service_url, "password-recovery/request")


@app.post("/api/auth/password-recovery/reset")
@limiter.limit(settings.login_rate_limit)
async def proxy_password_recovery_reset(request: Request):
    return await _proxy(request, settings.auth_service_url, "password-recovery/reset")


@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit(settings.rate_limit)
async def proxy_auth(request: Request, path: str):
    # Rotas publicas do auth: cadastro e health. As demais exigem token.
    if path not in ("register", "health"):
        _require_auth(request)
    return await _proxy(request, settings.auth_service_url, path)


@app.api_route("/api/scheduling/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit(settings.rate_limit)
async def proxy_scheduling(request: Request, path: str):
    # Todo o servico de agendamento exige autenticacao.
    if path != "health":
        _require_auth(request)
    return await _proxy(request, settings.scheduling_service_url, path)
