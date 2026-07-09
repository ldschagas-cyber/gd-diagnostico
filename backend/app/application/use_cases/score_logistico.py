"""Score Logístico (Fase 3 — V4).

Calcula uma nota 0-100 da operação logística. Composição:
- Benchmark Nacional: 30%
- Benchmark Regional: 20%
- Transportadoras: 20%
- Filiais: 15%
- Economia Potencial: 15%

Todo o cálculo é feito no backend (SQL). A IA não participa.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    ScoreLogisticoModel, ScoreHistoricoModel,
    CTeModel, BenchmarkModel, TransportadoraModel, FilialModel,
)

logger = logging.getLogger(__name__)


def classificar(score: float) -> str:
    if score >= 90:
        return "Excelente"
    if score >= 75:
        return "Muito Bom"
    if score >= 60:
        return "Regular"
    if score >= 40:
        return "Crítico"
    return "Muito Crítico"


class ScoreLogisticoUseCase:
    def __init__(self, db: Session):
        self.db = db

    def calcular(self, empresa_id: int, salvar: bool = True) -> ScoreLogisticoModel:
        """Calcula o score logístico completo da empresa."""
        s_nacional = self._score_benchmark_nacional(empresa_id)
        s_regional = self._score_benchmark_regional(empresa_id)
        s_transp = self._score_transportadoras(empresa_id)
        s_filiais = self._score_filiais(empresa_id)
        s_economia = self._score_economia(empresa_id)

        total = (
            s_nacional * 0.30 +
            s_regional * 0.20 +
            s_transp * 0.20 +
            s_filiais * 0.15 +
            s_economia * 0.15
        )
        total = round(total, 1)

        score = ScoreLogisticoModel(
            empresa_id=empresa_id,
            score_total=total,
            score_benchmark_nacional=round(s_nacional, 1),
            score_benchmark_regional=round(s_regional, 1),
            score_transportadoras=round(s_transp, 1),
            score_filiais=round(s_filiais, 1),
            score_economia=round(s_economia, 1),
            classificacao=classificar(total),
            periodo_referencia=date.today(),
        )

        if salvar:
            self.db.add(score)
            self.db.commit()
            self.db.refresh(score)
            # histórico
            self.db.add(ScoreHistoricoModel(
                empresa_id=empresa_id, score_total=total,
                classificacao=score.classificacao, periodo_referencia=date.today(),
            ))
            self.db.commit()

        return score

    # ─────────── Componentes do score ───────────
    def _score_benchmark_nacional(self, empresa_id: int) -> float:
        """Compara frete médio nacional da empresa com o benchmark nacional."""
        frete_kg = self._frete_kg_medio(empresa_id)
        if not frete_kg:
            return 50.0  # neutro sem dados

        bench_medio = (
            self.db.query(func.avg(BenchmarkModel.frete_kg_medio)).scalar() or frete_kg
        )
        # Quanto menor o frete vs benchmark, maior o score
        return self._score_por_razao(frete_kg, bench_medio)

    def _score_benchmark_regional(self, empresa_id: int) -> float:
        """Média dos scores por região vs benchmark regional."""
        regioes = (
            self.db.query(
                CTeModel.macro_regiao_destino,
                func.sum(CTeModel.valor_frete),
                func.sum(CTeModel.peso),
            )
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
                CTeModel.peso > 0,
            )
            .group_by(CTeModel.macro_regiao_destino)
            .all()
        )
        bench = {b.regiao: b.frete_kg_medio for b in self.db.query(BenchmarkModel).all()}

        scores = []
        for regiao, frete, peso in regioes:
            if not regiao or not peso:
                continue
            frete_kg = frete / peso
            benchmark_kg = bench.get(regiao)
            if benchmark_kg:
                scores.append(self._score_por_razao(frete_kg, benchmark_kg))
        return sum(scores) / len(scores) if scores else 50.0

    def _score_transportadoras(self, empresa_id: int) -> float:
        """Penaliza concentração excessiva; premia diversificação saudável."""
        total_peso = (
            self.db.query(func.sum(CTeModel.peso))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )
        if not total_peso:
            return 50.0

        concentracoes = (
            self.db.query(func.sum(CTeModel.peso))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            )
            .group_by(CTeModel.transportadora_id)
            .all()
        )
        if not concentracoes:
            return 50.0

        maior = max((c[0] or 0) for c in concentracoes) / total_peso * 100
        # 0-40% concentração = ótimo; >70% = ruim
        if maior <= 40:
            return 100.0
        if maior >= 80:
            return 30.0
        return round(100 - (maior - 40) * 1.75, 1)

    def _score_filiais(self, empresa_id: int) -> float:
        """Avalia dispersão de custo entre filiais (tomadores)."""
        filiais = (
            self.db.query(
                CTeModel.tomador_cnpj,
                func.sum(CTeModel.valor_frete),
                func.sum(CTeModel.peso),
            )
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
                CTeModel.peso > 0,
            )
            .group_by(CTeModel.tomador_cnpj)
            .all()
        )
        custos = [f / p for _, f, p in filiais if p]
        if len(custos) < 2:
            return 70.0  # poucos dados → neutro-positivo

        media = sum(custos) / len(custos)
        if media == 0:
            return 50.0
        # menor dispersão (desvio) = melhor controle = maior score
        desvio = (sum((c - media) ** 2 for c in custos) / len(custos)) ** 0.5
        cv = desvio / media  # coeficiente de variação
        return round(max(30, 100 - cv * 100), 1)

    def _score_economia(self, empresa_id: int) -> float:
        """Quanto menor o potencial de economia desperdiçado, maior o score."""
        frete_total = (
            self.db.query(func.sum(CTeModel.valor_frete))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )
        if not frete_total:
            return 50.0

        # estima excesso sobre benchmark
        regioes = (
            self.db.query(
                CTeModel.macro_regiao_destino,
                func.sum(CTeModel.valor_frete),
                func.sum(CTeModel.peso),
            )
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
                CTeModel.peso > 0,
            )
            .group_by(CTeModel.macro_regiao_destino)
            .all()
        )
        bench = {b.regiao: b.frete_kg_medio for b in self.db.query(BenchmarkModel).all()}
        excesso = 0.0
        for regiao, frete, peso in regioes:
            bk = bench.get(regiao)
            if bk and peso:
                fk = frete / peso
                if fk > bk:
                    excesso += (fk - bk) * peso
        pct_excesso = excesso / frete_total * 100 if frete_total else 0
        return round(max(20, 100 - pct_excesso * 2), 1)

    # ─────────── Helpers ───────────
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
        if not row or not row[1]:
            return 0.0
        return row[0] / row[1]

    def _score_por_razao(self, valor: float, referencia: float) -> float:
        """Score 0-100: valor igual à referência = 75; abaixo melhora, acima piora."""
        if not referencia:
            return 50.0
        razao = valor / referencia
        # razao 0.8 → ~95, razao 1.0 → 75, razao 1.2 → ~50, razao 1.5+ → ~20
        score = 75 - (razao - 1) * 125
        return max(0, min(100, score))

    # ─────────── Histórico ───────────
    def historico(self, empresa_id: int, limite: int = 12) -> list[ScoreHistoricoModel]:
        return (
            self.db.query(ScoreHistoricoModel)
            .filter(ScoreHistoricoModel.empresa_id == empresa_id)
            .order_by(ScoreHistoricoModel.created_at.desc())
            .limit(limite)
            .all()
        )

    def ultimo(self, empresa_id: int) -> ScoreLogisticoModel | None:
        return (
            self.db.query(ScoreLogisticoModel)
            .filter(ScoreLogisticoModel.empresa_id == empresa_id)
            .order_by(ScoreLogisticoModel.created_at.desc())
            .first()
        )
