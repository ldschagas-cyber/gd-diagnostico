"""Router de usuários (CRUD).

Autorização (R-01): `get_current_superuser` aceita tanto o superusuário
global quanto um usuário com `role == ADMIN` de uma empresa-cliente
específica. Sem escopo adicional, isso permitiria que o ADMIN de UMA
empresa listasse, editasse, excluísse ou promovesse a superusuário
usuários de QUALQUER outra empresa — inclusive a si mesmo. Este router
distingue explicitamente as duas coisas: um ADMIN de empresa só pode
gerenciar usuários da PRÓPRIA empresa e nunca pode conceder `is_superuser`.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import hash_password
from app.domain.entities import User
from app.presentation.api.dependencies import (
    get_current_superuser,
    get_user_repo,
)
from app.presentation.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


def _eh_superuser_global(user: User) -> bool:
    """Superusuário global: is_superuser=True e sem empresa_id vinculado.

    Um usuário com role=ADMIN de uma empresa-cliente também satisfaz
    `get_current_superuser`, mas NÃO é superusuário global — só pode
    gerenciar usuários da própria empresa.
    """
    return bool(user.is_superuser) and user.empresa_id is None


@router.get("", response_model=list[UserOut])
def listar(user: User = Depends(get_current_superuser), repo=Depends(get_user_repo)):
    todos = repo.list()
    if _eh_superuser_global(user):
        return todos
    return [u for u in todos if u.empresa_id == user.empresa_id]


@router.post("", response_model=UserOut, status_code=201)
def criar(
    payload: UserCreate,
    user: User = Depends(get_current_superuser),
    repo=Depends(get_user_repo),
):
    if repo.get_by_email(payload.email):
        raise HTTPException(409, "E-mail já cadastrado")

    is_superuser = payload.is_superuser
    empresa_id = payload.empresa_id
    if not _eh_superuser_global(user):
        # ADMIN de empresa: só cria usuários na própria empresa, nunca superusuário global.
        if is_superuser:
            raise HTTPException(403, "Você não tem permissão para criar um superusuário.")
        empresa_id = user.empresa_id

    novo = User(
        nome=payload.nome, email=payload.email,
        hashed_password=hash_password(payload.senha),
        is_active=payload.is_active, is_superuser=is_superuser,
        empresa_id=empresa_id, role=payload.role,
    )
    return repo.create(novo)


def _usuario_alvo_ou_404(user_id: int, repo):
    existente = repo.get(user_id)
    if not existente:
        raise HTTPException(404, "Usuário não encontrado")
    return existente


def _garantir_acesso_ao_alvo(user: User, alvo: User) -> None:
    """403 se um ADMIN de empresa tentar mexer em usuário de outra empresa."""
    if not _eh_superuser_global(user) and alvo.empresa_id != user.empresa_id:
        raise HTTPException(403, "Você não tem acesso a este usuário.")


@router.put("/{user_id}", response_model=UserOut)
def atualizar(
    user_id: int,
    payload: UserUpdate,
    user: User = Depends(get_current_superuser),
    repo=Depends(get_user_repo),
):
    existente = _usuario_alvo_ou_404(user_id, repo)
    _garantir_acesso_ao_alvo(user, existente)

    if payload.is_superuser and not _eh_superuser_global(user):
        raise HTTPException(403, "Você não tem permissão para conceder privilégio de superusuário.")

    if payload.nome is not None:
        existente.nome = payload.nome
    if payload.email is not None:
        existente.email = payload.email
    if payload.is_active is not None:
        existente.is_active = payload.is_active
    if payload.is_superuser is not None:
        existente.is_superuser = payload.is_superuser
    if payload.senha:
        existente.hashed_password = hash_password(payload.senha)
    return repo.update(user_id, existente)


@router.delete("/{user_id}", status_code=204)
def remover(
    user_id: int,
    user: User = Depends(get_current_superuser),
    repo=Depends(get_user_repo),
):
    existente = _usuario_alvo_ou_404(user_id, repo)
    _garantir_acesso_ao_alvo(user, existente)
    if not repo.delete(user_id):
        raise HTTPException(404, "Usuário não encontrado")
