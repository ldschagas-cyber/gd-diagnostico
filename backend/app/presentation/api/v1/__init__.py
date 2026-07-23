"""Agrega todos os routers da API v1."""
from fastapi import APIRouter

from app.presentation.api.v1 import (
    dlg,
    mbl,
    mcl,
    auth,
    benchmark_analise,
    benchmark_od_config,
    benchmark_v2_api,
    benchmarks,
    bid,
    dashboard,
    empresas,
    fechamento_mensal,
    importacao,
    inteligencia,
    metas,
    recomendacoes,
    regioes,
    relatorios,
    transportadoras,
    usuarios,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(empresas.router)
api_router.include_router(transportadoras.router)
api_router.include_router(regioes.router)
api_router.include_router(metas.router)
api_router.include_router(fechamento_mensal.router)
api_router.include_router(benchmarks.router)
api_router.include_router(benchmark_analise.router)
api_router.include_router(benchmark_od_config.hubs_router)
api_router.include_router(benchmark_od_config.clusters_router)
api_router.include_router(benchmark_od_config.corredor_router)
api_router.include_router(benchmark_v2_api.router)
api_router.include_router(bid.router)
api_router.include_router(importacao.router)
api_router.include_router(dashboard.router)
api_router.include_router(relatorios.router)
api_router.include_router(inteligencia.router)
api_router.include_router(dlg.router)
api_router.include_router(mbl.router)
api_router.include_router(mcl.router)
api_router.include_router(recomendacoes.router)
