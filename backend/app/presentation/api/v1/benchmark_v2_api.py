"""Benchmark V2 — endpoints (Freight Market Intelligence).

Expõe:
- Geração e leitura do benchmark OBSERVADO (percentis reais por OD).
- Comparação observado vs mercado.
- Leitura e EDIÇÃO da matriz de MERCADO (source of truth — Matriz OD).
- Resolver de referência (fallback cliente → mercado).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_current_superuser,
    get_current_user,
    verificar_acesso_empresa,
)
from app.application.use_cases.benchmark_v2 import BenchmarkV2UseCase
from app.application.use_cases.benchmark_observado import BenchmarkObservadoUseCase
from app.application.use_cases.indicadores_regionais import IndicadoresRegionaisUseCase
from app.infrastructure.database.models import BenchmarkMercadoModel

router = APIRouter(prefix="/benchmark-v2", tags=["Benchmark V2 — Market Intelligence"])


def _obs_dict(o) -> dict:
    return {
        "origem_regiao": o.origem_regiao, "destino_regiao": o.destino_regiao,
        "qtd_embarques": o.qtd_embarques,
        "rs_kg_p10": o.rs_kg_p10, "rs_kg_p25": o.rs_kg_p25, "rs_kg_p50": o.rs_kg_p50,
        "rs_kg_p75": o.rs_kg_p75, "rs_kg_p90": o.rs_kg_p90,
        "media": o.media, "desvio_padrao": o.desvio_padrao, "periodo_ref": o.periodo_ref,
    }


def _merc_dict(m) -> dict:
    return {
        "id": m.id, "origem_regiao": m.origem_regiao, "destino_regiao": m.destino_regiao,
        "modal": m.modal, "tipo_operacao": m.tipo_operacao,
        "faixa_peso_min": m.faixa_peso_min, "faixa_peso_max": m.faixa_peso_max,
        "rs_kg_p10": m.rs_kg_p10, "rs_kg_p25": m.rs_kg_p25, "rs_kg_p50": m.rs_kg_p50,
        "rs_kg_p75": m.rs_kg_p75, "rs_kg_p90": m.rs_kg_p90, "fonte": m.fonte,
    }


@router.post("/observado/gerar")
def gerar_observado(
    empresa_id: int = Query(...),
    periodo_ref: str = Query("TOTAL"),
    _=Depends(bloquear_visualizador),
    _ac=Depends(verificar_acesso_empresa),
    db: Session = Depends(get_db),
):
    """(Re)gera o benchmark observado da empresa a partir dos CT-e."""
    uc = BenchmarkObservadoUseCase(db)
    r = uc.gerar(empresa_id, periodo_ref=periodo_ref)
    return {
        "grupos_gerados": r.grupos_gerados,
        "embarques_considerados": r.embarques_considerados,
        "embarques_ignorados": r.embarques_ignorados,
        "periodo_ref": periodo_ref,
    }


@router.get("/observado")
def listar_observado(
    empresa_id: int = Query(...),
    periodo_ref: Optional[str] = Query(None),
    _=Depends(get_current_user),
    _ac=Depends(verificar_acesso_empresa),
    db: Session = Depends(get_db),
):
    uc = BenchmarkObservadoUseCase(db)
    return [_obs_dict(o) for o in uc.listar(empresa_id, periodo_ref)]


@router.get("/observado-vs-mercado")
def observado_vs_mercado(
    empresa_id: int = Query(...),
    periodo_ref: str = Query("TOTAL"),
    _=Depends(get_current_user),
    _ac=Depends(verificar_acesso_empresa),
    db: Session = Depends(get_db),
):
    return BenchmarkV2UseCase(db).observado_vs_mercado(empresa_id, periodo_ref)


@router.get("/mercado")
def listar_mercado(
    origem: Optional[str] = Query(None),
    destino: Optional[str] = Query(None),
    _=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(BenchmarkMercadoModel)
    if origem:
        stmt = stmt.where(BenchmarkMercadoModel.origem_regiao == origem.strip().upper())
    if destino:
        stmt = stmt.where(BenchmarkMercadoModel.destino_regiao == destino.strip().upper())
    stmt = stmt.order_by(BenchmarkMercadoModel.origem_regiao, BenchmarkMercadoModel.destino_regiao)
    return [_merc_dict(m) for m in db.execute(stmt).scalars().all()]


class BenchmarkMercadoIn(BaseModel):
    origem_regiao: str
    destino_regiao: str
    modal: str = ""
    tipo_operacao: str = "TODOS"
    faixa_peso_min: float = 0.0
    faixa_peso_max: float = 0.0
    rs_kg_p10: float = Field(0.0, ge=0)
    rs_kg_p25: float = Field(0.0, ge=0)
    rs_kg_p50: float = Field(0.0, ge=0)
    rs_kg_p75: float = Field(0.0, ge=0)
    rs_kg_p90: float = Field(0.0, ge=0)


@router.put("/mercado")
def upsert_mercado(
    payload: BenchmarkMercadoIn,
    _=Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza uma linha da matriz de mercado (chave: OD + modal +
    tipo_operacao + faixa de peso). Edição manual da source of truth."""
    o = payload.origem_regiao.strip().upper()
    d = payload.destino_regiao.strip().upper()
    if not o or not d:
        raise HTTPException(400, "Origem e destino são obrigatórios.")
    modal = (payload.modal or "").strip().upper()
    tipo = (payload.tipo_operacao or "TODOS").strip().upper()

    m = db.execute(
        select(BenchmarkMercadoModel).where(
            BenchmarkMercadoModel.origem_regiao == o,
            BenchmarkMercadoModel.destino_regiao == d,
            BenchmarkMercadoModel.modal == modal,
            BenchmarkMercadoModel.tipo_operacao == tipo,
            BenchmarkMercadoModel.faixa_peso_min == payload.faixa_peso_min,
            BenchmarkMercadoModel.faixa_peso_max == payload.faixa_peso_max,
        )
    ).scalars().first()
    if not m:
        m = BenchmarkMercadoModel(
            origem_regiao=o, destino_regiao=d, modal=modal, tipo_operacao=tipo,
            faixa_peso_min=payload.faixa_peso_min, faixa_peso_max=payload.faixa_peso_max,
        )
        db.add(m)
    m.rs_kg_p10 = payload.rs_kg_p10
    m.rs_kg_p25 = payload.rs_kg_p25
    m.rs_kg_p50 = payload.rs_kg_p50
    m.rs_kg_p75 = payload.rs_kg_p75
    m.rs_kg_p90 = payload.rs_kg_p90
    m.fonte = "MERCADO"
    db.commit()
    db.refresh(m)
    return _merc_dict(m)


@router.delete("/mercado/{mid}", status_code=204)
def deletar_mercado(
    mid: int,
    _=Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    m = db.get(BenchmarkMercadoModel, mid)
    if not m:
        raise HTTPException(404, "Linha de mercado não encontrada.")
    db.delete(m)
    db.commit()


@router.get("/indicadores-regionais")
def indicadores_regionais(
    empresa_id: int = Query(...),
    _=Depends(get_current_user),
    _ac=Depends(verificar_acesso_empresa),
    db: Session = Depends(get_db),
):
    """Indicadores regionais DERIVADOS das operações reais (CT-e) — substitui o
    antigo cadastro manual de benchmark regional."""
    ind = IndicadoresRegionaisUseCase(db).calcular(empresa_id)
    return [
        {
            "regiao": i.regiao, "qtd_embarques": i.qtd_embarques,
            "frete_medio_rs_kg": i.frete_medio_rs_kg,
            "frete_faturamento_pct": i.frete_faturamento_pct,
            "peso_medio": i.peso_medio, "custo_medio": i.custo_medio,
            "lead_time_medio_dias": i.lead_time_medio_dias,
        }
        for i in ind
    ]


@router.get("/resolver")
def resolver(
    empresa_id: int = Query(...),
    origem: str = Query(...),
    destino: str = Query(...),
    modal: str = Query(""),
    valor_rs_kg: Optional[float] = Query(None),
    _=Depends(get_current_user),
    _ac=Depends(verificar_acesso_empresa),
    db: Session = Depends(get_db),
):
    """Resolve a referência (cliente→mercado). Se valor_rs_kg for informado,
    devolve também a comparação contra P50/P75."""
    uc = BenchmarkV2UseCase(db)
    if valor_rs_kg is not None:
        c = uc.comparar(empresa_id, origem, destino, valor_rs_kg, modal)
        return {
            "fonte": c.referencia.fonte, "disponivel": c.referencia.disponivel,
            "rs_kg_p50": c.referencia.rs_kg_p50, "rs_kg_p75": c.referencia.rs_kg_p75,
            "valor": c.valor, "delta_p50_pct": c.delta_p50_pct,
            "delta_p75_pct": c.delta_p75_pct, "faixa": c.faixa,
        }
    r = uc.resolver(empresa_id, origem, destino, modal)
    return {
        "fonte": r.fonte, "disponivel": r.disponivel,
        "origem_regiao": r.origem_regiao, "destino_regiao": r.destino_regiao,
        "rs_kg_p10": r.rs_kg_p10, "rs_kg_p25": r.rs_kg_p25, "rs_kg_p50": r.rs_kg_p50,
        "rs_kg_p75": r.rs_kg_p75, "rs_kg_p90": r.rs_kg_p90,
    }
