"""MCL — API de Concorrência Logística (motor de decisão de BID).

Endpoints:
  POST /mcl/{bid_id}/decidir   — calcula ranking, escolhe vencedora, versiona a decisão
  GET  /mcl/{bid_id}/decidir   — prévia da decisão SEM persistir (determinística)
  POST /mcl/{bid_id}/simular   — análise de sensibilidade de preço (não persiste)
  GET  /mcl/{bid_id}/historico — versões anteriores da decisão (rastreabilidade)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.use_cases.mcl import MclUseCase
from app.presentation.api.dependencies import bloquear_visualizador, get_bid_com_acesso, get_db

router = APIRouter(prefix="/mcl", tags=["MCL — Concorrência Logística"])


class MclDecisaoHistOut(BaseModel):
    id: int
    bid_id: int
    versao: int
    vencedora_nome: str
    score_vencedora: float
    diferenca_segunda: float
    justificativa: str
    gerado_em: object

    class Config:
        from_attributes = True


def _uc(db: Session = Depends(get_db)) -> MclUseCase:
    return MclUseCase(db)


@router.get("/{bid_id}/decidir")
def previa_decisao(
    bid_id: int,
    _bid=Depends(get_bid_com_acesso),
    uc: MclUseCase = Depends(_uc),
):
    """Prévia determinística do ranking e da vencedora, SEM versionar."""
    r = uc.decidir(bid_id, persistir=False)
    if "erro" in r:
        raise HTTPException(400, r["erro"])
    return r


@router.post("/{bid_id}/decidir")
def decidir(
    bid_id: int,
    _bid=Depends(get_bid_com_acesso),
    _=Depends(bloquear_visualizador),
    uc: MclUseCase = Depends(_uc),
):
    """Calcula a decisão e a persiste como nova versão (rastreabilidade)."""
    r = uc.decidir(bid_id, persistir=True)
    if "erro" in r:
        raise HTTPException(400, r["erro"])
    return r


class SimulacaoIn(BaseModel):
    variacao_preco_pct: float = 0.0
    bid_transportadora_id: Optional[int] = None
    faturamento_mensal: Optional[float] = None


@router.post("/{bid_id}/simular")
def simular(
    bid_id: int,
    payload: SimulacaoIn,
    _bid=Depends(get_bid_com_acesso),
    uc: MclUseCase = Depends(_uc),
):
    """Simula impacto de variar a tarifa no custo total e no % frete."""
    r = uc.simular(
        bid_id,
        variacao_preco_pct=payload.variacao_preco_pct,
        bid_transportadora_id=payload.bid_transportadora_id,
        faturamento_mensal=payload.faturamento_mensal,
    )
    if "erro" in r:
        raise HTTPException(400, r["erro"])
    return r


@router.get("/{bid_id}/historico", response_model=List[MclDecisaoHistOut])
def historico(
    bid_id: int,
    _bid=Depends(get_bid_com_acesso),
    uc: MclUseCase = Depends(_uc),
):
    """Histórico versionado das decisões do BID."""
    return uc.historico(bid_id)
