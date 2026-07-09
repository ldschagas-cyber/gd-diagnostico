"""DLG — API de Diagnóstico Logístico.

Endpoints:
  POST /dlg/{empresa_id}/processar   — dispara reprocessamento do motor analítico
  GET  /dlg/{empresa_id}/analitico   — lista resultados por dimensão/período/classificação
  GET  /dlg/{empresa_id}/outliers    — lista outliers detectados
  GET  /dlg/{empresa_id}/resumo      — KPIs consolidados para dashboard
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.use_cases.dlg import DlgUseCase
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_current_user,
    get_db,
    verificar_acesso_empresa,
)
from app.presentation.schemas.dlg_schemas import (
    DlgAnaliticoOut,
    DlgOutlierOut,
    DlgProcessarOut,
    DlgResumoOut,
)

router = APIRouter(prefix="/dlg", tags=["DLG — Diagnóstico Logístico"])


def _uc(db: Session = Depends(get_db)) -> DlgUseCase:
    return DlgUseCase(db)


@router.post("/{empresa_id}/processar", response_model=DlgProcessarOut)
def processar(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None, description="Início do período (YYYY-MM-DD)"),
    data_fim:    Optional[date] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    uc: DlgUseCase = Depends(_uc),
):
    """Reprocessa o motor DLG para o período informado.
    Idempotente — pode ser chamado múltiplas vezes sem duplicar dados.
    Sem período = processa todos os CT-e da empresa."""
    return uc.processar(empresa_id, data_inicio, data_fim)


@router.get("/{empresa_id}/analitico", response_model=List[DlgAnaliticoOut])
def listar_analitico(
    empresa_id: int,
    dimensao:      Optional[str] = Query(None, description="FILIAL | ROTA | TRANSPORTADORA | REGIAO | CLIENTE_FINAL"),
    periodo_ref:   Optional[str] = Query(None, description="YYYY-MM (ignorado quando modo=consolidado)"),
    classificacao: Optional[str] = Query(None, description="EFICIENTE | ATENCAO | CRITICO | SEM_REF"),
    modo:          str = Query("consolidado", description="consolidado (1 linha/entidade) | mensal (1 linha/entidade/mês)"),
    data_inicio:   Optional[date] = Query(None, description="Início do período (YYYY-MM-DD)"),
    data_fim:      Optional[date] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    page:          Optional[int] = Query(None, ge=1, description="Página (1-based) — CA-16, opcional"),
    page_size:     Optional[int] = Query(None, ge=1, le=500, description="Itens por página — CA-16, opcional"),
    _=Depends(verificar_acesso_empresa),
    uc: DlgUseCase = Depends(_uc),
):
    """Lista resultados analíticos filtráveis por dimensão, período e classificação.

    - **consolidado**: agrega os meses do intervalo por entidade; R$/kg, % frete
      e desvio recalculados sobre os totais consolidados.
    - **mensal**: uma linha por entidade e mês.
    - O intervalo ``data_inicio``/``data_fim`` filtra por competência (mês).
    - **page**/**page_size** (CA-16): paginação server-side opcional, aplicada
      após ordenação/filtro — sobretudo relevante para ``dimensao=CLIENTE_FINAL``
      (maior cardinalidade potencial das 5 dimensões), mas disponível a todas.
      Sem esses parâmetros, comportamento idêntico ao anterior (sem paginação).
    """
    return uc.listar(empresa_id, dimensao, periodo_ref, classificacao, modo,
                     data_inicio, data_fim, page, page_size)


@router.get("/{empresa_id}/outliers", response_model=List[DlgOutlierOut])
def listar_outliers(
    empresa_id: int,
    periodo_ref: Optional[str] = Query(None, description="YYYY-MM"),
    tipo:        Optional[str] = Query(None, description="RS_KG_2DP | PCT_FRETE | VAR_MENSAL"),
    data_inicio: Optional[date] = Query(None, description="Início do período (YYYY-MM-DD)"),
    data_fim:    Optional[date] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    _=Depends(verificar_acesso_empresa),
    uc: DlgUseCase = Depends(_uc),
):
    """Lista outliers detectados no período."""
    return uc.listar_outliers(empresa_id, periodo_ref, tipo, data_inicio, data_fim)


@router.get("/{empresa_id}/resumo", response_model=DlgResumoOut)
def resumo(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None, description="Início do período (YYYY-MM-DD)"),
    data_fim:    Optional[date] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    _=Depends(verificar_acesso_empresa),
    uc: DlgUseCase = Depends(_uc),
):
    """KPIs consolidados para o dashboard DLG: distribuição de classificação,
    top filiais, rotas críticas e breakdown por dimensão.
    Respeita o intervalo de datas (sem filtro = todos os períodos)."""
    return uc.resumo(empresa_id, data_inicio, data_fim) or {}
