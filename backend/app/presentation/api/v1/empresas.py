"""Router de empresas (RF002) e filiais (RF003)."""
from fastapi import APIRouter, Depends, HTTPException

from app.domain.entities import Empresa, Filial, StatusEnum
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_current_user,
    get_empresa_repo,
    get_filial_repo,
    require_admin,
    verificar_acesso_empresa,
)
from app.presentation.schemas import (
    EmpresaCreate,
    EmpresaOut,
    EmpresaUpdate,
    FilialCreate,
    FilialOut,
)

router = APIRouter(prefix="/empresas", tags=["Empresas e Filiais"])


# ---------------- Empresas (RF002) ----------------
@router.get("", response_model=list[EmpresaOut])
def listar(user=Depends(get_current_user), repo=Depends(get_empresa_repo)):
    todas = repo.list()
    # Multi-tenant (R-01): admin global vê todas; usuário comum vê só a sua.
    role = getattr(user, "role", None)
    eh_admin = user.is_superuser or (getattr(role, "value", role) == "ADMIN")
    if eh_admin and user.empresa_id is None:
        return todas
    return [e for e in todas if e.id == user.empresa_id]


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obter(empresa=Depends(verificar_acesso_empresa)):
    return empresa


@router.post("", response_model=EmpresaOut, status_code=201)
def criar(payload: EmpresaCreate, _=Depends(require_admin), repo=Depends(get_empresa_repo)):
    if repo.get_by_cnpj(payload.cnpj_matriz):
        raise HTTPException(409, "CNPJ de matriz já cadastrado")
    return repo.create(Empresa(**payload.model_dump()))


@router.put("/{empresa_id}", response_model=EmpresaOut)
def atualizar(
    empresa_id: int, payload: EmpresaUpdate,
    _=Depends(verificar_acesso_empresa), __=Depends(bloquear_visualizador),
    repo=Depends(get_empresa_repo),
):
    e = repo.get(empresa_id)
    if not e:
        raise HTTPException(404, "Empresa não encontrada")
    dados = payload.model_dump(exclude_unset=True)
    for k, v in dados.items():
        setattr(e, k, v)
    return repo.update(empresa_id, e)


@router.delete("/{empresa_id}", status_code=204)
def inativar(empresa_id: int, _=Depends(require_admin), repo=Depends(get_empresa_repo)):
    """Inativação lógica do embarcador (RF002). Restrito a administrador."""
    if not repo.delete(empresa_id):
        raise HTTPException(404, "Empresa não encontrada")


# ---------------- Filiais (RF003) ----------------
@router.get("/{empresa_id}/filiais", response_model=list[FilialOut])
def listar_filiais(
    empresa_id: int, _=Depends(verificar_acesso_empresa), repo=Depends(get_filial_repo),
):
    return repo.list_by_empresa(empresa_id)


@router.post("/{empresa_id}/filiais", response_model=FilialOut, status_code=201)
def criar_filial(
    empresa_id: int, payload: FilialCreate,
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    repo=Depends(get_filial_repo),
):
    dados = payload.model_dump()
    dados["empresa_id"] = empresa_id
    return repo.create(Filial(**dados))


@router.put("/filiais/{filial_id}", response_model=FilialOut)
def atualizar_filial(
    filial_id: int, payload: FilialCreate,
    _=Depends(bloquear_visualizador), repo=Depends(get_filial_repo),
):
    if not repo.get(filial_id):
        raise HTTPException(404, "Filial não encontrada")
    return repo.update(filial_id, Filial(id=filial_id, **payload.model_dump()))


@router.delete("/filiais/{filial_id}", status_code=204)
def remover_filial(filial_id: int, _=Depends(bloquear_visualizador), repo=Depends(get_filial_repo)):
    if not repo.delete(filial_id):
        raise HTTPException(404, "Filial não encontrada")
