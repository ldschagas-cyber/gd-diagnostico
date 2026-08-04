"""Endpoints internos, de serviço-a-serviço — não usam JWT de usuário.

Hoje só o CRM chama isso (Inteligência Comercial na Pesquisa de Leads: cruza
o perfil pesquisado do prospect com o Benchmark Logístico do Diagnóstico).
Autenticado por chave estática (ver `verify_internal_api_key`), não por login.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.use_cases.benchmark_setorial import BenchmarkSetorialUseCase
from app.core.database import get_db
from app.presentation.api.dependencies import verify_internal_api_key

router = APIRouter(prefix="/internal", tags=["Interno (serviço-a-serviço)"])


@router.get("/benchmark-setorial", dependencies=[Depends(verify_internal_api_key)])
def listar_benchmark_setorial(db: Session = Depends(get_db)) -> list[dict]:
    """Referências de custo/kg por segmento de mercado. Dado global (não é
    por empresa/tenant) — a mesma tabela que alimenta o Benchmark Setorial
    do próprio Diagnóstico."""
    return BenchmarkSetorialUseCase(db).listar_segmentos()
