"""Configuracao de logging estruturado (RNF07 - Registro de logs / auditoria).

Segue a pratica apresentada em aula (modulo logging do Python) para registrar
acoes relevantes: autenticacao, criacao de contas e tentativas invalidas.
"""
import logging


def configure_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger("auth-service")
