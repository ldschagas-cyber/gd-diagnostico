"""Benchmark V2 — Gerador do BENCHMARK OBSERVADO.

Varre os CT-e de uma empresa e produz, por par Origem→Destino (macrorregião),
os percentis reais de R$/kg (P10, P25, P50, P75, P90), média, desvio-padrão e
quantidade de embarques. É o "real vs mercado": dado data-driven, não editável
à mão.

Regras:
- R$/kg de um CT-e = valor_frete / peso  (ignora peso <= 0).
- Origem da região derivada de uf_origem (o CT-e não traz macro_regiao_origem).
- Destino: usa macro_regiao_destino quando existir, senão deriva de uf_destino.
- CT-e sem região identificável em ambos os lados é ignorado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    CTeModel,
    BenchmarkObservadoModel,
)
from app.infrastructure.parsers.macro_regiao import macro_por_uf


def _percentil(valores_ordenados: list[float], p: float) -> float:
    """Percentil com interpolação linear (método igual ao numpy default)."""
    if not valores_ordenados:
        return 0.0
    n = len(valores_ordenados)
    if n == 1:
        return round(valores_ordenados[0], 4)
    pos = (p / 100) * (n - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return round(valores_ordenados[int(pos)], 4)
    frac = pos - lo
    return round(valores_ordenados[lo] + (valores_ordenados[hi] - valores_ordenados[lo]) * frac, 4)


def _desvio_padrao(valores: list[float], media: float) -> float:
    if len(valores) < 2:
        return 0.0
    var = sum((v - media) ** 2 for v in valores) / len(valores)
    return round(math.sqrt(var), 4)


@dataclass
class ResultadoGeracaoObservado:
    grupos_gerados: int
    embarques_considerados: int
    embarques_ignorados: int


class BenchmarkObservadoUseCase:
    def __init__(self, db: Session):
        self.db = db

    def _regiao_origem(self, cte: CTeModel) -> Optional[str]:
        r = macro_por_uf(cte.uf_origem)
        return r.value if r else None

    def _regiao_destino(self, cte: CTeModel) -> Optional[str]:
        if cte.macro_regiao_destino:
            return cte.macro_regiao_destino.strip().upper()
        r = macro_por_uf(cte.uf_destino)
        return r.value if r else None

    def gerar(
        self,
        empresa_id: int,
        periodo_ref: str = "TOTAL",
        data_inicio=None,
        data_fim=None,
    ) -> ResultadoGeracaoObservado:
        """(Re)gera o observado para a empresa, agregando todos os CT-e do período.
        Substitui as linhas anteriores do mesmo periodo_ref (idempotente)."""
        stmt = select(CTeModel).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.status == CTE_STATUS_ATIVO,
        )
        if data_inicio is not None:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        ctes = self.db.execute(stmt).scalars().all()

        # Agrupa R$/kg por (origem, destino)
        grupos: dict[tuple[str, str], list[float]] = {}
        considerados = 0
        ignorados = 0
        for c in ctes:
            if not c.peso or c.peso <= 0:
                ignorados += 1
                continue
            o = self._regiao_origem(c)
            d = self._regiao_destino(c)
            if not o or not d:
                ignorados += 1
                continue
            grupos.setdefault((o, d), []).append(c.valor_frete / c.peso)
            considerados += 1

        # Limpa linhas anteriores do mesmo período (regeneração limpa)
        self.db.query(BenchmarkObservadoModel).filter(
            BenchmarkObservadoModel.empresa_id == empresa_id,
            BenchmarkObservadoModel.periodo_ref == periodo_ref,
        ).delete()

        gerados = 0
        for (o, d), valores in grupos.items():
            valores.sort()
            media = round(sum(valores) / len(valores), 4)
            self.db.add(BenchmarkObservadoModel(
                empresa_id=empresa_id,
                origem_regiao=o, destino_regiao=d,
                modal="", tipo_operacao="TODOS", faixa_peso_min=0.0, faixa_peso_max=0.0,
                qtd_embarques=len(valores),
                rs_kg_p10=_percentil(valores, 10),
                rs_kg_p25=_percentil(valores, 25),
                rs_kg_p50=_percentil(valores, 50),
                rs_kg_p75=_percentil(valores, 75),
                rs_kg_p90=_percentil(valores, 90),
                media=media,
                desvio_padrao=_desvio_padrao(valores, media),
                periodo_ref=periodo_ref,
            ))
            gerados += 1
        self.db.commit()
        return ResultadoGeracaoObservado(
            grupos_gerados=gerados,
            embarques_considerados=considerados,
            embarques_ignorados=ignorados,
        )

    def listar(self, empresa_id: int, periodo_ref: Optional[str] = None) -> list[BenchmarkObservadoModel]:
        stmt = select(BenchmarkObservadoModel).where(
            BenchmarkObservadoModel.empresa_id == empresa_id
        )
        if periodo_ref:
            stmt = stmt.where(BenchmarkObservadoModel.periodo_ref == periodo_ref)
        return list(self.db.execute(stmt.order_by(
            BenchmarkObservadoModel.origem_regiao, BenchmarkObservadoModel.destino_regiao
        )).scalars().all())
