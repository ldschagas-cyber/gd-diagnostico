"""Router de metas nacionais e regionais (RF007), por empresa-cliente.

Leitura e edição restritas a usuários vinculados à empresa (papel ADMIN ou
ANALISTA para escrita; VISUALIZADOR só lê) ou superusuário da plataforma —
mesmo padrão de acesso usado no mapeamento de Hubs (clusters_router).
"""
from fastapi import APIRouter, Depends, HTTPException

from app.domain.entities import MetaNacional, MetaRegional
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_empresa_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
    verificar_acesso_empresa,
)
from app.presentation.schemas import (
    MetaNacionalIn,
    MetaNacionalOut,
    MetaRegionalIn,
    MetaRegionalOut,
)

router = APIRouter(prefix="/empresas/{empresa_id}/metas", tags=["Metas"])


@router.get("/nacional", response_model=MetaNacionalOut | None)
def obter_meta_nacional(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_meta_nacional_repo),
):
    return repo.get(empresa_id)


@router.put("/nacional", response_model=MetaNacionalOut)
def definir_meta_nacional(
    empresa_id: int,
    payload: MetaNacionalIn,
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    repo=Depends(get_meta_nacional_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")
    return repo.upsert(MetaNacional(empresa_id=empresa_id, **payload.model_dump()))


@router.get("/regionais", response_model=list[MetaRegionalOut])
def listar_metas_regionais(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_meta_regional_repo),
):
    return repo.list(empresa_id)


@router.put("/regionais", response_model=MetaRegionalOut)
def definir_meta_regional(
    empresa_id: int,
    payload: MetaRegionalIn,
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    repo=Depends(get_meta_regional_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")
    return repo.upsert(MetaRegional(empresa_id=empresa_id, **payload.model_dump()))
