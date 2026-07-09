"""Router de análise do Benchmark Logístico (V2.1 — modelo OD).

Telas analíticas que comparam os indicadores da empresa contra as
referências de mercado por CORREDOR (Hub origem → Hub destino).
Reutiliza o DiagnosticoUseCase e o BenchmarkODUseCase para os cálculos.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.benchmark import BenchmarkUseCase
from app.application.use_cases.benchmark_od import BenchmarkODUseCase
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.presentation.api.dependencies import (
    get_benchmark_corredor_repo,
    get_benchmark_repo,
    get_cluster_repo,
    get_cte_repo,
    get_current_user,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_hub_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
    get_transportadora_repo,
)
from app.presentation.schemas import (
    BenchmarkNacionalOut,
    BenchmarkODResultadoOut,
    BenchmarkRegionalItemOut,
    BenchmarkTransportadoraItemOut,
    DashboardExecutivoOut,
    PotencialEconomiaOut,
)

router = APIRouter(prefix="/benchmark", tags=["Benchmark — Análise"])


def _build_uc(
    cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo,
    cluster_repo, corredor_repo, hub_repo,
) -> BenchmarkUseCase:
    diag = DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)
    od = BenchmarkODUseCase(cte_repo, cluster_repo, corredor_repo, hub_repo)
    return BenchmarkUseCase(diag, cte_repo, bench_repo, benchmark_od_uc=od)


def _deps(
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    bench_repo=Depends(get_benchmark_repo),
    cluster_repo=Depends(get_cluster_repo),
    corredor_repo=Depends(get_benchmark_corredor_repo),
    hub_repo=Depends(get_hub_repo),
):
    return _build_uc(
        cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo,
        cluster_repo, corredor_repo, hub_repo,
    )


def _deps_od(
    cte_repo=Depends(get_cte_repo),
    cluster_repo=Depends(get_cluster_repo),
    corredor_repo=Depends(get_benchmark_corredor_repo),
    hub_repo=Depends(get_hub_repo),
) -> BenchmarkODUseCase:
    return BenchmarkODUseCase(cte_repo, cluster_repo, corredor_repo, hub_repo)


@router.get("/nacional/{empresa_id}", response_model=BenchmarkNacionalOut)
def benchmark_nacional(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    transportadora_id: Optional[int] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: BenchmarkUseCase = Depends(_deps),
    empresa_repo=Depends(get_empresa_repo),
):
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada.")
    resultado = uc.nacional(empresa_id, data_inicio, data_fim, transportadora_id)
    resultado.empresa_nome = empresa.nome_fantasia or empresa.razao_social
    return resultado


@router.get("/regional/{empresa_id}", response_model=List[BenchmarkRegionalItemOut])
def benchmark_regional(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    transportadora_id: Optional[int] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: BenchmarkUseCase = Depends(_deps),
):
    return uc.regional(empresa_id, data_inicio, data_fim, transportadora_id)


@router.get(
    "/transportadoras/{empresa_id}",
    response_model=List[BenchmarkTransportadoraItemOut],
)
def benchmark_transportadoras(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: BenchmarkUseCase = Depends(_deps),
):
    return uc.transportadoras(empresa_id, data_inicio, data_fim)

@router.get("/economia/{empresa_id}", response_model=PotencialEconomiaOut)
def potencial_economia(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: BenchmarkUseCase = Depends(_deps),
):
    """Economia potencial e projeções mensal/trimestral/semestral/anual (seção 11)."""
    return uc.potencial_economia(empresa_id, data_inicio, data_fim)


@router.get("/executivo/{empresa_id}", response_model=DashboardExecutivoOut)
def dashboard_executivo(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    uc: BenchmarkUseCase = Depends(_deps),
    empresa_repo=Depends(get_empresa_repo),
):
    """Dashboard executivo: cards estratégicos, evolução mensal e rankings (seção 13)."""
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada.")
    resultado = uc.dashboard_executivo(empresa_id, data_inicio, data_fim)
    resultado.empresa_nome = empresa.nome_fantasia or empresa.razao_social
    return resultado


@router.get("/corredores/{empresa_id}", response_model=BenchmarkODResultadoOut)
def benchmark_corredores(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    od: BenchmarkODUseCase = Depends(_deps_od),
    empresa_repo=Depends(get_empresa_repo),
):
    """Benchmark por Fluxo OD (Hub origem → Hub destino) — base do modelo V2.1.

    Cada corredor é comparado APENAS contra a referência de mercado do
    mesmo corredor. Corredores sem referência cadastrada vêm com
    `tem_referencia=false` para a tela exibir o CTA de cadastro.
    """
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada.")
    resultado = od.resultado(empresa_id, data_inicio, data_fim)
    resultado.empresa_nome = empresa.nome_fantasia or empresa.razao_social
    return resultado
