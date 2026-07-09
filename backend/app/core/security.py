"""Utilitários de segurança: hash de senha e geração/validação de JWT.

Usa bcrypt diretamente (sem passlib) para compatibilidade com Python 3.14+.

Tokens (R-05):
  • access  — curta duração (ACCESS_TOKEN_EXPIRE_MINUTES), usado nas chamadas.
  • refresh — longa duração (REFRESH_TOKEN_EXPIRE_DAYS), usado só para renovar.
O claim "type" distingue os dois; o endpoint de refresh só aceita "refresh".

Cookies httpOnly (S-04): o navegador nunca guarda o token em localStorage —
o backend entrega os tokens via Set-Cookie com httponly=True (JS não consegue
ler), e o navegador os reenvia automaticamente em cada chamada. A cookie de
refresh usa path restrito a /auth para reduzir a superfície de exposição.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ACCESS_COOKIE_NAME = "gd_frete_access"
REFRESH_COOKIE_NAME = "gd_frete_refresh"
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _criar_token(subject: str | int, minutos: int, tipo: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": tipo}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str | int, expires_minutes: Optional[int] = None) -> str:
    return _criar_token(
        subject, expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES, "access"
    )


def create_refresh_token(subject: str | int) -> str:
    return _criar_token(subject, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60, "refresh")


def decode_access_token(token: str) -> Optional[str]:
    """Retorna o 'sub' de um token de ACESSO válido, ou None.

    Rejeita tokens cujo type não seja 'access' (um refresh token não pode
    ser usado para autenticar chamadas comuns).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type", "access") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[str]:
    """Retorna o 'sub' de um REFRESH token válido, ou None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def definir_cookie_access(response, token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME, token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/", httponly=True, secure=settings.is_production, samesite="lax",
    )


def definir_cookie_refresh(response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME, token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=REFRESH_COOKIE_PATH, httponly=True, secure=settings.is_production, samesite="lax",
    )


def limpar_cookies_auth(response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
