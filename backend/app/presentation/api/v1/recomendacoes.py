"""Recomendações — API (MELHORIA 8).

Consolida automaticamente as oportunidades encontradas pelos indicadores em
uma lista priorizada e acionável.

Endpoints:
  POST /recomendacoes/{empresa_id}/consolidar  — (re)gera as recomendações determinísticas
  GET  /recomendacoes/{empresa_id}             — lista, filtrável por prioridade/status
  GET  /recomendacoes/{empresa_id}/resumo      — contagem por prioridade + economia total
  PATCH /recomendacoes/{empresa_id}/{rec_id}/status — atualiza o status de uma recomendação
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.recomendacoes import RecomendacoesUseCase
from app.presentation.api.dependencies import bloquear_visualizador, get_db, verificar_acesso_empresa
from app.presentation.schemas import (
    RecomendacaoOut,
    RecomendacaoStatusUpdate,
    RecomendacoesResumoOut,
)

router = APIRouter(prefix="/recomendacoes", tags=["Recomendações"])

_STATUS_VALIDOS = {"ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "DESCARTADA"}


def _uc(db: Session = Depends(get_db)) -> RecomendacoesUseCase:
    return RecomendacoesUseCase(db)


@router.post("/{empresa_id}/consolidar", response_model=RecomendacoesResumoOut)
def consolidar(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    uc: RecomendacoesUseCase = Depends(_uc),
):
    """Reprocessa as recomendações determinísticas a partir dos indicadores.
    Idempotente — preserva o status editado pelo usuário."""
    return uc.consolidar(empresa_id)


@router.get("/{empresa_id}", response_model=List[RecomendacaoOut])
def listar(
    empresa_id: int,
    prioridade: Optional[str] = Query(None, description="CRITICA | ALTA | MEDIA | BAIXA"),
    status: Optional[str] = Query(None, description="ABERTA | EM_ANDAMENTO | CONCLUIDA | DESCARTADA"),
    _=Depends(verificar_acesso_empresa),
    uc: RecomendacoesUseCase = Depends(_uc),
):
    """Lista as recomendações da empresa, ordenadas por prioridade e economia."""
    return uc.listar(empresa_id, prioridade, status)


@router.get("/{empresa_id}/resumo", response_model=RecomendacoesResumoOut)
def resumo(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    uc: RecomendacoesUseCase = Depends(_uc),
):
    """Contagem de recomendações por prioridade e economia estimada total."""
    return uc._resumo(empresa_id)


@router.patch("/{empresa_id}/{rec_id}/status", response_model=RecomendacaoOut)
def atualizar_status(
    empresa_id: int,
    rec_id: int,
    payload: RecomendacaoStatusUpdate,
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    uc: RecomendacoesUseCase = Depends(_uc),
):
    """Atualiza o status de uma recomendação (fluxo de acompanhamento)."""
    status = (payload.status or "").upper()
    if status not in _STATUS_VALIDOS:
        raise HTTPException(400, f"Status inválido. Use um de: {sorted(_STATUS_VALIDOS)}")
    if not uc.atualizar_status(rec_id, empresa_id, status):
        raise HTTPException(404, "Recomendação não encontrada.")
    itens = [r for r in uc.listar(empresa_id) if r.id == rec_id]
    return itens[0]
