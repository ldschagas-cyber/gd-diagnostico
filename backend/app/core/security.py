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

# Portal do Cliente (v6.18.0) — cookies e claim de audiência dedicados, para
# nunca colidir nem ser aceito por engano pela sessão do painel interno (e
# vice-versa). Ver Especificação Técnica v6.18.0 §3.3.
CLIENTE_ACCESS_COOKIE_NAME = "gd_frete_cliente_access"
CLIENTE_REFRESH_COOKIE_NAME = "gd_frete_cliente_refresh"
CLIENTE_REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/portal/auth"
AUD_PORTAL_CLIENTE = "portal_cliente"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _criar_token(
    subject: str | int, minutos: int, tipo: str, extra_claims: Optional[dict] = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": tipo}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_payload(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def create_access_token(subject: str | int, expires_minutes: Optional[int] = None) -> str:
    return _criar_token(
        subject, expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES, "access"
    )


def create_refresh_token(subject: str | int) -> str:
    return _criar_token(subject, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60, "refresh")


def decode_access_token(token: str) -> Optional[str]:
    """Retorna o 'sub' de um token de ACESSO interno válido, ou None.

    Rejeita tokens cujo type não seja 'access' (um refresh token não pode
    ser usado para autenticar chamadas comuns) e rejeita explicitamente
    tokens do Portal do Cliente (aud=portal_cliente) — defesa em profundidade
    contra um token de cliente ser aceito por engano numa rota interna
    (Especificação Técnica v6.18.0 §3.3, achado SEC-01 como precedente).
    """
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type", "access") != "access":
        return None
    if payload.get("aud") == AUD_PORTAL_CLIENTE:
        return None
    return payload.get("sub")


def decode_refresh_token(token: str) -> Optional[str]:
    """Retorna o 'sub' de um REFRESH token interno válido, ou None."""
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    if payload.get("aud") == AUD_PORTAL_CLIENTE:
        return None
    return payload.get("sub")


# ─────────── Portal do Cliente (v6.18.0) ───────────

def create_cliente_access_token(subject: str | int, expires_minutes: Optional[int] = None) -> str:
    return _criar_token(
        subject, expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES, "access",
        extra_claims={"aud": AUD_PORTAL_CLIENTE},
    )


def create_cliente_refresh_token(subject: str | int) -> str:
    return _criar_token(
        subject, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60, "refresh",
        extra_claims={"aud": AUD_PORTAL_CLIENTE},
    )


def decode_cliente_access_token(token: str) -> Optional[str]:
    """Retorna o 'sub' de um token de ACESSO do Portal do Cliente, ou None.

    Exige explicitamente aud=portal_cliente — um token interno (sem essa
    claim) nunca autentica uma rota do Portal, mesmo que válido.
    """
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type") != "access" or payload.get("aud") != AUD_PORTAL_CLIENTE:
        return None
    return payload.get("sub")


def decode_cliente_refresh_token(token: str) -> Optional[str]:
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh" or payload.get("aud") != AUD_PORTAL_CLIENTE:
        return None
    return payload.get("sub")


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


def definir_cookie_cliente_access(response, token: str) -> None:
    response.set_cookie(
        CLIENTE_ACCESS_COOKIE_NAME, token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/", httponly=True, secure=settings.is_production, samesite="lax",
    )


def definir_cookie_cliente_refresh(response, token: str) -> None:
    response.set_cookie(
        CLIENTE_REFRESH_COOKIE_NAME, token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=CLIENTE_REFRESH_COOKIE_PATH, httponly=True, secure=settings.is_production, samesite="lax",
    )


def limpar_cookies_cliente_auth(response) -> None:
    response.delete_cookie(CLIENTE_ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(CLIENTE_REFRESH_COOKIE_NAME, path=CLIENTE_REFRESH_COOKIE_PATH)
