"""Caso de uso de autenticação."""
from typing import Optional

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.domain.entities import User
from app.domain.repositories import IUserRepository


class AuthUseCase:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    def authenticate(self, email: str, senha: str) -> Optional[User]:
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(senha, user.hashed_password):
            return None
        return user

    def gerar_token(self, user: User) -> str:
        return create_access_token(subject=user.id)

    def gerar_tokens(self, user: User) -> tuple[str, str]:
        """Retorna (access_token, refresh_token) — R-05."""
        return create_access_token(subject=user.id), create_refresh_token(subject=user.id)
