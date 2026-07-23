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
    # ADMIN de empresa: só vê usuários com quem compartilha ao menos 1 empresa
    # (login baseado em empresa, v6.14 — usuário pode estar em várias).
    minhas = set(user.empresas_ids or [])
    return [u for u in todos if set(u.empresas_ids or []) & minhas]


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
    empresas_ids = payload.empresas_ids
    if not _eh_superuser_global(user):
        # ADMIN de empresa: só cria usuários nas próprias empresas, nunca superusuário global.
        if is_superuser:
            raise HTTPException(403, "Você não tem permissão para criar um superusuário.")
        empresas_ids = [e for e in empresas_ids if e in (user.empresas_ids or [])] or list(user.empresas_ids or [])
        empresa_id = empresa_id if empresa_id in empresas_ids else (empresas_ids[0] if empresas_ids else None)

    novo = User(
        nome=payload.nome, email=payload.email,
        hashed_password=hash_password(payload.senha),
        is_active=payload.is_active, is_superuser=is_superuser,
        empresa_id=empresa_id, empresas_ids=empresas_ids, role=payload.role,
    )
    return repo.create(novo)


def _usuario_alvo_ou_404(user_id: int, repo):
    existente = repo.get(user_id)
    if not existente:
        raise HTTPException(404, "Usuário não encontrado")
    return existente


def _garantir_acesso_ao_alvo(user: User, alvo: User) -> None:
    """403 se um ADMIN de empresa tentar mexer em usuário sem empresa em comum."""
    if _eh_superuser_global(user):
        return
    if not (set(alvo.empresas_ids or []) & set(user.empresas_ids or [])):
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
    if payload.empresas_ids is not None:
        novas_ids = payload.empresas_ids
        if not _eh_superuser_global(user):
            # ADMIN de empresa só pode vincular empresas às quais ele próprio pertence.
            novas_ids = [e for e in novas_ids if e in (user.empresas_ids or [])]
        existente.empresas_ids = novas_ids
        if existente.empresa_id not in novas_ids:
            existente.empresa_id = novas_ids[0] if novas_ids else None
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
