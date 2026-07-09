"""Benchmark V2 — INDICADORES REGIONAIS (derivados).

Substitui o antigo cadastro manual de benchmark regional por um cálculo
derivado das operações reais (CT-e) da empresa. Por macrorregião de destino,
produz: frete médio (R$/kg), participação do frete no faturamento (%),
peso médio, custo médio e lead time médio.

É a materialização da "vw_indicadores_regionais" como cálculo (portável e
testável), e não como VIEW de banco.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import CTeModel
from app.infrastructure.parsers.macro_regiao import macro_por_uf


@dataclass
class IndicadorRegional:
    regiao: str
    qtd_embarques: int
    frete_medio_rs_kg: float          # sum(frete)/sum(peso) — ponderado
    frete_faturamento_pct: float      # sum(frete)/sum(mercadoria) * 100
    peso_medio: float
    custo_medio: float                # frete médio por embarque
    lead_time_medio_dias: float       # média de (entrega - saída), quando há datas


class IndicadoresRegionaisUseCase:
    def __init__(self, db: Session):
        self.db = db

    def _regiao_destino(self, c: CTeModel) -> str | None:
        if c.macro_regiao_destino:
            return c.macro_regiao_destino.strip().upper()
        r = macro_por_uf(c.uf_destino)
        return r.value if r else None

    def calcular(self, empresa_id: int, data_inicio=None, data_fim=None) -> list[IndicadorRegional]:
        stmt = select(CTeModel).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.status == CTE_STATUS_ATIVO,
        )
        if data_inicio is not None:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        ctes = self.db.execute(stmt).scalars().all()

        # Acumuladores por região
        acc: dict[str, dict] = {}
        for c in ctes:
            r = self._regiao_destino(c)
            if not r:
                continue
            a = acc.setdefault(r, {
                "n": 0, "peso": 0.0, "frete": 0.0, "merc": 0.0,
                "lt_soma": 0.0, "lt_n": 0,
            })
            a["n"] += 1
            a["peso"] += c.peso or 0.0
            a["frete"] += c.valor_frete or 0.0
            a["merc"] += c.valor_mercadoria or 0.0
            if c.data_saida and c.data_entrega:
                dias = (c.data_entrega - c.data_saida).days
                if dias >= 0:
                    a["lt_soma"] += dias
                    a["lt_n"] += 1

        resultado = []
        for regiao, a in acc.items():
            frete_kg = round(a["frete"] / a["peso"], 4) if a["peso"] else 0.0
            pct = round(a["frete"] / a["merc"] * 100, 2) if a["merc"] else 0.0
            peso_medio = round(a["peso"] / a["n"], 2) if a["n"] else 0.0
            custo_medio = round(a["frete"] / a["n"], 2) if a["n"] else 0.0
            lt = round(a["lt_soma"] / a["lt_n"], 1) if a["lt_n"] else 0.0
            resultado.append(IndicadorRegional(
                regiao=regiao, qtd_embarques=a["n"],
                frete_medio_rs_kg=frete_kg, frete_faturamento_pct=pct,
                peso_medio=peso_medio, custo_medio=custo_medio,
                lead_time_medio_dias=lt,
            ))
        resultado.sort(key=lambda x: x.regiao)
        return resultado
