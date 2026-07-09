"""Router de metas nacionais e regionais (RF007).

Leitura liberada a qualquer usuário autenticado; edição restrita a
administradores — são metas globais da plataforma, não por empresa-cliente.
"""
from fastapi import APIRouter, Depends

from app.domain.entities import MetaNacional, MetaRegional
from app.presentation.api.dependencies import (
    get_current_superuser,
    get_current_user,
    get_meta_nacional_repo,
    get_meta_regional_repo,
)
from app.presentation.schemas import (
    MetaNacionalIn,
    MetaNacionalOut,
    MetaRegionalIn,
    MetaRegionalOut,
)

router = APIRouter(prefix="/metas", tags=["Metas"])


@router.get("/nacional", response_model=MetaNacionalOut | None)
def obter_meta_nacional(_=Depends(get_current_user), repo=Depends(get_meta_nacional_repo)):
    return repo.get()


@router.put("/nacional", response_model=MetaNacionalOut)
def definir_meta_nacional(
    payload: MetaNacionalIn, _=Depends(get_current_superuser), repo=Depends(get_meta_nacional_repo),
):
    return repo.upsert(MetaNacional(**payload.model_dump()))


@router.get("/regionais", response_model=list[MetaRegionalOut])
def listar_metas_regionais(_=Depends(get_current_user), repo=Depends(get_meta_regional_repo)):
    return repo.list()


@router.put("/regionais", response_model=MetaRegionalOut)
def definir_meta_regional(
    payload: MetaRegionalIn, _=Depends(get_current_superuser), repo=Depends(get_meta_regional_repo),
):
    return repo.upsert(MetaRegional(**payload.model_dump()))
