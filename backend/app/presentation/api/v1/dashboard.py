"""Router do dashboard de diagnóstico (RF011 a RF014)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.presentation.api.dependencies import (
    get_benchmark_repo,
    get_cte_repo,
    get_current_user,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
    get_transportadora_repo,
)
from app.presentation.schemas import DiagnosticoOut

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _build_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, benchmark_repo=None):
    return DiagnosticoUseCase(
        cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, benchmark_repo
    )


@router.get("/{empresa_id}", response_model=DiagnosticoOut)
def diagnostico(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    benchmark_repo=Depends(get_benchmark_repo),
):
    uc = _build_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, benchmark_repo)
    try:
        return uc.gerar(empresa_id, data_inicio, data_fim)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
