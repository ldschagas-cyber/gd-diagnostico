"""Benchmark Setorial (Fase 4 — V4).

Compara a operação da empresa com referências de mercado por segmento:
Indústria, Distribuidor, Atacadista, Varejo, E-commerce, Agronegócio.

Os valores de referência ficam na tabela benchmarks_setoriais e podem ser
atualizados conforme a GD Conecta refina seus dados de mercado. O cálculo
do frete da empresa é feito via SQL; a comparação é determinística.
"""
from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    BenchmarkSetorialModel, CTeModel,
)

logger = logging.getLogger(__name__)


# Seed de referências setoriais (valores de mercado de partida — R$/kg)
SEED_SETORIAL = [
    {"segmento": "INDUSTRIA",    "frete_kg_medio": 0.42, "frete_pct_medio": 6.5,  "custo_medio": 2800.0},
    {"segmento": "DISTRIBUIDOR", "frete_kg_medio": 0.55, "frete_pct_medio": 8.2,  "custo_medio": 1900.0},
    {"segmento": "ATACADISTA",   "frete_kg_medio": 0.38, "frete_pct_medio": 5.8,  "custo_medio": 3200.0},
    {"segmento": "VAREJO",       "frete_kg_medio": 0.68, "frete_pct_medio": 9.5,  "custo_medio": 1400.0},
    {"segmento": "ECOMMERCE",    "frete_kg_medio": 1.25, "frete_pct_medio": 14.0, "custo_medio": 850.0},
    {"segmento": "AGRONEGOCIO",  "frete_kg_medio": 0.28, "frete_pct_medio": 4.2,  "custo_medio": 4500.0},
]

ROTULO_SEGMENTO = {
    "INDUSTRIA": "Indústria", "DISTRIBUIDOR": "Distribuidor",
    "ATACADISTA": "Atacadista", "VAREJO": "Varejo",
    "ECOMMERCE": "E-commerce", "AGRONEGOCIO": "Agronegócio",
}


class BenchmarkSetorialUseCase:
    def __init__(self, db: Session):
        self.db = db

    def garantir_seed(self) -> None:
        """Cria as referências setoriais padrão se a tabela estiver vazia."""
        existe = self.db.query(BenchmarkSetorialModel).first()
        if existe:
            return
        for s in SEED_SETORIAL:
            self.db.add(BenchmarkSetorialModel(**s))
        self.db.commit()
        logger.info("Seed de benchmarks setoriais criado.")

    def comparar(self, empresa_id: int, segmento: str = None) -> dict:
        """Compara o frete da empresa com os segmentos de mercado."""
        self.garantir_seed()

        frete_kg_empresa = self._frete_kg_medio(empresa_id)
        setoriais = self.db.query(BenchmarkSetorialModel).all()

        comparativo = []
        for s in setoriais:
            diff_pct = None
            if s.frete_kg_medio:
                diff_pct = round((frete_kg_empresa / s.frete_kg_medio - 1) * 100, 1)
            comparativo.append({
                "segmento": s.segmento,
                "segmento_rotulo": ROTULO_SEGMENTO.get(s.segmento, s.segmento),
                "frete_kg_medio": s.frete_kg_medio,
                "frete_pct_medio": s.frete_pct_medio,
                "custo_medio": s.custo_medio,
                "frete_kg_empresa": round(frete_kg_empresa, 2),
                "diferenca_pct": diff_pct,
                "posicao": self._classificar_posicao(diff_pct),
            })

        # Ordena por proximidade (segmento mais aderente primeiro)
        comparativo.sort(key=lambda c: abs(c["diferenca_pct"]) if c["diferenca_pct"] is not None else 999)

        return {
            "frete_kg_empresa": round(frete_kg_empresa, 2),
            "segmento_mais_aderente": comparativo[0]["segmento"] if comparativo else None,
            "comparativo": comparativo,
        }

    def _classificar_posicao(self, diff_pct) -> str:
        if diff_pct is None:
            return "sem_referencia"
        if diff_pct <= -10:
            return "abaixo"       # mais barato que o segmento (bom)
        if diff_pct >= 10:
            return "acima"        # mais caro que o segmento (atenção)
        return "alinhado"

    def _frete_kg_medio(self, empresa_id: int) -> float:
        row = (
            self.db.query(func.sum(CTeModel.valor_frete), func.sum(CTeModel.peso))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
                CTeModel.peso > 0,
            )
            .first()
        )
        return (row[0] / row[1]) if row and row[1] else 0.0

    def listar_segmentos(self) -> list[dict]:
        self.garantir_seed()
        return [
            {
                "segmento": s.segmento,
                "segmento_rotulo": ROTULO_SEGMENTO.get(s.segmento, s.segmento),
                "frete_kg_medio": s.frete_kg_medio,
                "frete_pct_medio": s.frete_pct_medio,
                "custo_medio": s.custo_medio,
            }
            for s in self.db.query(BenchmarkSetorialModel).all()
        ]
