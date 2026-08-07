"""Caso de uso de autenticação do Portal do Cliente (v6.18.0).

Espelha `AuthUseCase` (autenticação interna), mas emite tokens com a claim
de audiência `portal_cliente` (app.core.security) — nunca aceitos pela
autenticação interna, e vice-versa. Ver Especificação Técnica v6.18.0 §3.3.
"""
from typing import Optional

from app.core.security import (
    create_cliente_access_token,
    create_cliente_refresh_token,
    verify_password,
)
from app.domain.entities import ClientePortalUser
from app.domain.repositories import IClientePortalUserRepository


class PortalAuthUseCase:
    def __init__(self, cliente_repo: IClientePortalUserRepository):
        self.cliente_repo = cliente_repo

    def authenticate(self, email: str, senha: str) -> Optional[ClientePortalUser]:
        user = self.cliente_repo.get_by_email(email)
        if not user or not user.ativo:
            return None
        if not verify_password(senha, user.hashed_password):
            return None
        return user

    def gerar_tokens(self, user: ClientePortalUser) -> tuple[str, str]:
        """Retorna (access_token, refresh_token), ambos com aud=portal_cliente."""
        return (
            create_cliente_access_token(subject=user.id),
            create_cliente_refresh_token(subject=user.id),
        )
