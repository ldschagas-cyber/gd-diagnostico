"""MBL — API de Benchmark Logístico (motor estatístico versionado).

Endpoints:
  POST /mbl/{empresa_id}/processar  — recalcula o benchmark (exclui outliers DLG)
  GET  /mbl/{empresa_id}/benchmark  — consulta datasets percentílicos
  GET  /mbl/{empresa_id}/comparar   — compara um valor real vs benchmark oficial
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.use_cases.mbl import MblUseCase, THRESHOLD_AMOSTRA_PADRAO
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_db,
    verificar_acesso_empresa,
)

router = APIRouter(prefix="/mbl", tags=["MBL — Benchmark Logístico"])


# ─── schemas ──────────────────────────────────────────────────────────────────

class MblBenchmarkOut(BaseModel):
    id: int
    empresa_id: int
    dimensao: str
    segmento: str
    metrica: str
    periodo_ref: str
    amostra: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    media: float
    desvio_padrao: float
    low_confidence: bool
    outliers_excluidos: int
    versao: int

    class Config:
        from_attributes = True


class MblProcessarOut(BaseModel):
    status: str
    ctes: int = 0
    periodos: List[str] = []
    linhas_benchmark: int = 0


# ─── endpoints ────────────────────────────────────────────────────────────────

def _uc(db: Session = Depends(get_db)) -> MblUseCase:
    return MblUseCase(db)


@router.post("/{empresa_id}/processar", response_model=MblProcessarOut)
def processar(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim:    Optional[date] = Query(None),
    threshold:   int = Query(THRESHOLD_AMOSTRA_PADRAO, ge=1,
                             description="Amostra mínima por segmento; abaixo disso = low_confidence"),
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    uc: MblUseCase = Depends(_uc),
):
    """Recalcula o benchmark estatístico por período mensal, excluindo os
    outliers detectados pelo DLG. Idempotente e versionado (auditável)."""
    return uc.processar(empresa_id, data_inicio, data_fim, threshold)


@router.get("/{empresa_id}/benchmark", response_model=List[MblBenchmarkOut])
def listar_benchmark(
    empresa_id: int,
    dimensao:    Optional[str] = Query(None, description="REGIAO | CLUSTER | ROTA"),
    metrica:     Optional[str] = Query(None, description="RS_KG | PCT_FRETE | CUSTO_ENTREGA"),
    periodo_ref: Optional[str] = Query(None, description="YYYY-MM"),
    segmento:    Optional[str] = Query(None, description="Segmento específico, ex.: SUDESTE ou SP→RS"),
    apenas_confiavel: bool = Query(False, description="Exclui segmentos low_confidence"),
    _=Depends(verificar_acesso_empresa),
    uc: MblUseCase = Depends(_uc),
):
    """Consulta os datasets percentílicos do benchmark."""
    return uc.listar(
        empresa_id, dimensao, metrica, periodo_ref, segmento,
        incluir_low_confidence=not apenas_confiavel,
    )


@router.get("/{empresa_id}/comparar")
def comparar(
    empresa_id: int,
    dimensao:    str = Query(..., description="REGIAO | CLUSTER | ROTA"),
    segmento:    str = Query(..., description="Ex.: SUDESTE ou SP→RS"),
    metrica:     str = Query("RS_KG", description="RS_KG | PCT_FRETE | CUSTO_ENTREGA"),
    valor:       float = Query(..., description="Valor real a comparar"),
    periodo_ref: Optional[str] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: MblUseCase = Depends(_uc),
):
    """Compara um valor real contra o benchmark oficial do segmento:
    retorna faixa (EFICIENTE/NORMAL/INEFICIENTE) e desvio vs P50."""
    r = uc.comparar(empresa_id, dimensao, segmento, metrica, valor, periodo_ref)
    if r is None:
        raise HTTPException(404, "Benchmark não encontrado para este segmento.")
    return r
