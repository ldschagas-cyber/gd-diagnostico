"""Router de transportadoras (RF004).

Isolamento multi-empresa: todas as operações são escopadas por empresa_id.
A listagem global (legado) permanece disponível para administradores.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.entities import Transportadora
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_transportadora_com_acesso,
    get_transportadora_repo,
    verificar_acesso_empresa,
)
from app.presentation.schemas import TransportadoraCreate, TransportadoraOut

router = APIRouter(prefix="/transportadoras", tags=["Transportadoras"])


@router.get("", response_model=list[TransportadoraOut])
def listar(
    empresa_id: int = Query(..., description="ID da empresa para filtrar transportadoras"),
    _ac=Depends(verificar_acesso_empresa),
    repo=Depends(get_transportadora_repo),
):
    """Lista transportadoras da empresa. empresa_id obrigatório (isolamento multi-tenant)."""
    return repo.list_by_empresa(empresa_id, limit=1000)


@router.get("/{tid}", response_model=TransportadoraOut)
def obter(t=Depends(get_transportadora_com_acesso)):
    return t


@router.post("", response_model=TransportadoraOut, status_code=201)
def criar(
    payload: TransportadoraCreate,
    empresa_id: int = Query(..., description="ID da empresa"),
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    repo=Depends(get_transportadora_repo),
):
    if payload.cnpj and repo.get_by_cnpj_empresa(payload.cnpj, empresa_id):
        raise HTTPException(409, "CNPJ já cadastrado para esta empresa")
    t = Transportadora(empresa_id=empresa_id, **payload.model_dump())
    return repo.create(t)


@router.put("/{tid}", response_model=TransportadoraOut)
def atualizar(
    tid: int, payload: TransportadoraCreate,
    t=Depends(get_transportadora_com_acesso), _=Depends(bloquear_visualizador),
    repo=Depends(get_transportadora_repo),
):
    return repo.update(tid, Transportadora(id=tid, empresa_id=t.empresa_id, **payload.model_dump()))


@router.delete("/{tid}", status_code=204)
def remover(
    tid: int, _t=Depends(get_transportadora_com_acesso), _=Depends(bloquear_visualizador),
    repo=Depends(get_transportadora_repo),
):
    if not repo.delete(tid):
        raise HTTPException(404, "Transportadora não encontrada")
