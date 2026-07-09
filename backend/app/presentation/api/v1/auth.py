"""Router de autenticação (login JWT + refresh).

Rate limiting: máximo 10 tentativas de login por minuto por IP (slowapi).
Protege contra brute-force de credenciais.

Tokens (R-05): o login devolve access (curto) + refresh (longo). O refresh
renova o access sem reautenticar, reduzindo a janela de exposição.

Cookies httpOnly (S-04): login/refresh também gravam os tokens em cookies
httpOnly (o navegador não os expõe a JavaScript, fechando o vetor de roubo
via XSS que existia com o token em localStorage). O corpo da resposta
continua trazendo os tokens em texto — mantido para compatibilidade com
clientes de API/scripts que não usam cookies — mas o frontend web passou a
ignorá-lo e depender só do cookie.
"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.application.use_cases.auth import AuthUseCase
from app.core.logging_config import get_logger
from app.core.security import (
    REFRESH_COOKIE_NAME,
    create_access_token,
    decode_refresh_token,
    definir_cookie_access,
    definir_cookie_refresh,
    limpar_cookies_auth,
)
from app.presentation.api.dependencies import get_current_user, get_user_repo
from app.presentation.schemas import RefreshRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticação"])
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")          # ← max 10 tentativas/min por IP
def login(
    request: Request,                # ← necessário para o slowapi ler o IP
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo=Depends(get_user_repo),
):
    """Login via OAuth2 password flow. 'username' = e-mail do usuário."""
    uc = AuthUseCase(user_repo)
    user = uc.authenticate(form_data.username, form_data.password)
    if not user:
        logger.warning("Tentativa de login falhou para %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    logger.info("Login bem-sucedido: %s", user.email)
    access, refresh = uc.gerar_tokens(user)
    definir_cookie_access(response, access)
    definir_cookie_refresh(response, refresh)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = Body(default=None),
    user_repo=Depends(get_user_repo),
):
    """Gera um novo access token a partir de um refresh token válido (R-05).

    Aceita o refresh token via cookie httpOnly (fluxo do navegador) ou no
    corpo da requisição (fluxo de API/scripts sem cookie).
    """
    refresh = request.cookies.get(REFRESH_COOKIE_NAME) or (payload.refresh_token if payload else None)
    sub = decode_refresh_token(refresh) if refresh else None
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )
    user = user_repo.get(int(sub))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inválido",
        )
    novo_access = create_access_token(subject=user.id)
    definir_cookie_access(response, novo_access)
    return Token(access_token=novo_access)


@router.post("/logout", status_code=204)
def logout(response: Response):
    """Limpa os cookies de autenticação no navegador.

    Necessário porque cookies httpOnly não podem ser apagados via
    JavaScript (document.cookie) — só um Set-Cookie do servidor os remove.
    """
    limpar_cookies_auth(response)


@router.get("/me", response_model=UserOut)
def me(current=Depends(get_current_user)):
    return current
