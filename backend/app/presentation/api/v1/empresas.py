"""Router de empresas (RF002) e filiais (RF003)."""
from fastapi import APIRouter, Depends, HTTPException

from app.domain.entities import Empresa, Filial, MacroRegiaoEnum, MetaNacional, MetaRegional, StatusEnum
from app.domain.repositories import IMetaNacionalRepository, IMetaRegionalRepository
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_current_user,
    get_empresa_repo,
    get_filial_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
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


def seed_metas_padroes(
    empresa_id: int,
    meta_nac_repo: IMetaNacionalRepository,
    meta_reg_repo: IMetaRegionalRepository,
) -> None:
    """Cria as metas (nacional + 5 regionais) zeradas para uma empresa nova.

    Metas são por-empresa (v6.13) — cada cliente nasce sem meta configurada
    e precisa parametrizar a sua própria, sem herdar valor de outro cliente.
    """
    meta_nac_repo.upsert(MetaNacional(empresa_id=empresa_id, meta_rs_kg=0.0, meta_pct_frete=0.0))
    for macro in MacroRegiaoEnum:
        meta_reg_repo.upsert(MetaRegional(
            empresa_id=empresa_id, macro_regiao=macro,
            meta_rs_kg=0.0, meta_pct_frete=0.0, prazo_medio_meta=0, orcamento_mensal=0.0,
        ))


# ---------------- Empresas (RF002) ----------------
@router.get("", response_model=list[EmpresaOut])
def listar(user=Depends(get_current_user), repo=Depends(get_empresa_repo)):
    todas = repo.list()
    # Multi-tenant (R-01): admin global vê todas; usuário comum vê as empresas
    # a que está vinculado (login baseado em empresa, v6.14 — usuario_empresas).
    role = getattr(user, "role", None)
    eh_admin = user.is_superuser or (getattr(role, "value", role) == "ADMIN")
    if eh_admin and user.empresa_id is None:
        return todas
    vinculadas = set(getattr(user, "empresas_ids", None) or [])
    return [e for e in todas if e.id in vinculadas]


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obter(empresa=Depends(verificar_acesso_empresa)):
    return empresa


@router.post("", response_model=EmpresaOut, status_code=201)
def criar(
    payload: EmpresaCreate,
    _=Depends(require_admin),
    repo=Depends(get_empresa_repo),
    meta_nac_repo=Depends(get_meta_nacional_repo),
    meta_reg_repo=Depends(get_meta_regional_repo),
):
    if repo.get_by_cnpj(payload.cnpj_matriz):
        raise HTTPException(409, "CNPJ de matriz já cadastrado")
    nova = repo.create(Empresa(**payload.model_dump()))
    seed_metas_padroes(nova.id, meta_nac_repo, meta_reg_repo)
    return nova


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
