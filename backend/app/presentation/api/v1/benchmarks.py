"""Router de benchmarks de mercado (Módulo Benchmark Logístico).

Permite ao administrador manter os indicadores de referência por região,
sem necessidade de alteração de código (Configurações > Benchmarks).
Parâmetro global da plataforma — leitura e edição restritas a
administradores (tela "Parâmetros de Mercado").
"""
from fastapi import APIRouter, Depends, HTTPException

from app.domain.entities import Benchmark, RegiaoBenchmarkEnum
from app.presentation.api.dependencies import (
    get_benchmark_repo,
    get_current_superuser,
)
from app.presentation.schemas import BenchmarkIn, BenchmarkOut

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


@router.get("", response_model=list[BenchmarkOut])
def listar_benchmarks(_=Depends(get_current_superuser), repo=Depends(get_benchmark_repo)):
    """Lista os benchmarks de todas as regiões (e o nacional). Apenas admin."""
    return repo.list()


@router.put("/{regiao}", response_model=BenchmarkOut)
def definir_benchmark(
    regiao: str,
    payload: BenchmarkIn,
    _=Depends(get_current_superuser),
    repo=Depends(get_benchmark_repo),
):
    """Cria ou atualiza o benchmark de uma região (upsert). Apenas admin."""
    try:
        regiao_enum = RegiaoBenchmarkEnum(regiao.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Região inválida: {regiao}")
    dados = payload.model_dump()
    dados["regiao"] = regiao_enum  # a região vem da URL como fonte da verdade
    return repo.upsert(Benchmark(**dados))
