"""Oportunidades Automáticas (Fase 5 — V4).

Detecta oportunidades de economia analisando os dados via SQL:
- BID: regiões/rotas caras que justificam concorrência
- Consolidação: muitas transportadoras com baixo volume
- Redistribuição: desequilíbrio de volume
- Renegociação: custo acima do benchmark
- Concentração: dependência excessiva de uma transportadora

Cada oportunidade gera economia estimada, impacto, complexidade e prioridade.
Os números vêm do SQL; a IA não participa do cálculo.
"""
from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    OportunidadeModel, PlanoAcaoModel, CTeModel,
    TransportadoraModel, BenchmarkModel,
)

logger = logging.getLogger(__name__)


class OportunidadesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def detectar(self, empresa_id: int) -> int:
        """Detecta e registra oportunidades. Retorna a quantidade encontrada."""
        # Limpa oportunidades abertas anteriores (recalculadas)
        self.db.query(OportunidadeModel).filter(
            OportunidadeModel.empresa_id == empresa_id,
            OportunidadeModel.status == "ABERTA",
        ).delete()

        total = 0
        total += self._detectar_renegociacao(empresa_id)
        total += self._detectar_concentracao(empresa_id)
        total += self._detectar_consolidacao(empresa_id)
        total += self._detectar_bid(empresa_id)

        self.db.commit()
        return total

    def _detectar_renegociacao(self, empresa_id: int) -> int:
        """Regiões com frete acima do benchmark → renegociar."""
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
        count = 0
        for regiao, frete, peso in regioes:
            bk = bench.get(regiao)
            if not bk or not peso:
                continue
            fk = frete / peso
            if fk > bk * 1.15:
                economia = (fk - bk) * peso * 12
                self.db.add(OportunidadeModel(
                    empresa_id=empresa_id, tipo="RENEGOCIACAO",
                    titulo=f"Renegociar frete na região {regiao}",
                    descricao=f"Frete de R$ {fk:.2f}/kg está {(fk/bk-1)*100:.0f}% acima do "
                              f"benchmark de R$ {bk:.2f}/kg.",
                    economia_estimada=round(economia, 2),
                    impacto="ALTO" if economia > 100000 else "MEDIO",
                    complexidade="MEDIA", prioridade=1 if economia > 100000 else 2,
                    justificativa=f"Diferença de R$ {fk-bk:.2f}/kg sobre {peso:.0f} kg movimentados.",
                ))
                count += 1
        return count

    def _detectar_concentracao(self, empresa_id: int) -> int:
        """Transportadora com mais de 60% do volume → diversificar."""
        total_peso = (
            self.db.query(func.sum(CTeModel.peso))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )
        if not total_peso:
            return 0
        transp = (
            self.db.query(
                TransportadoraModel.razao_social,
                func.sum(CTeModel.peso),
            )
            .join(CTeModel, CTeModel.transportadora_id == TransportadoraModel.id)
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            )
            .group_by(TransportadoraModel.razao_social)
            .all()
        )
        count = 0
        for nome, peso in transp:
            pct = (peso or 0) / total_peso * 100
            if pct > 60:
                self.db.add(OportunidadeModel(
                    empresa_id=empresa_id, tipo="CONCENTRACAO",
                    titulo=f"Reduzir dependência de {nome}",
                    descricao=f"A transportadora {nome} concentra {pct:.0f}% do volume. "
                              "Diversificar reduz risco e aumenta poder de negociação.",
                    economia_estimada=0.0,
                    impacto="ALTO", complexidade="MEDIA", prioridade=2,
                    justificativa=f"Concentração de {pct:.0f}% representa risco operacional.",
                ))
                count += 1
        return count

    def _detectar_consolidacao(self, empresa_id: int) -> int:
        """Muitas transportadoras com volume baixo → consolidar."""
        transp = (
            self.db.query(
                TransportadoraModel.id,
                func.sum(CTeModel.peso),
            )
            .join(CTeModel, CTeModel.transportadora_id == TransportadoraModel.id)
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            )
            .group_by(TransportadoraModel.id)
            .all()
        )
        if len(transp) <= 3:
            return 0
        total_peso = sum((t[1] or 0) for t in transp)
        pequenas = [t for t in transp if total_peso and (t[1] or 0) / total_peso < 0.05]
        if len(pequenas) >= 3:
            self.db.add(OportunidadeModel(
                empresa_id=empresa_id, tipo="CONSOLIDACAO",
                titulo=f"Consolidar {len(pequenas)} transportadoras de baixo volume",
                descricao=f"Há {len(pequenas)} transportadoras com menos de 5% do volume cada. "
                          "Consolidar pode reduzir custos administrativos e melhorar tarifas.",
                economia_estimada=0.0,
                impacto="MEDIO", complexidade="BAIXA", prioridade=3,
                justificativa="Consolidação aumenta volume por parceiro e poder de barganha.",
            ))
            return 1
        return 0

    def _detectar_bid(self, empresa_id: int) -> int:
        """Maior região por volume com custo elevado → realizar BID."""
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
            .order_by(func.sum(CTeModel.peso).desc())
            .all()
        )
        bench = {b.regiao: b.frete_kg_medio for b in self.db.query(BenchmarkModel).all()}
        count = 0
        for regiao, frete, peso in regioes[:2]:  # top 2 regiões por volume
            bk = bench.get(regiao)
            fk = frete / peso if peso else 0
            if bk and fk > bk:
                economia = (fk - bk) * peso * 12
                op = OportunidadeModel(
                    empresa_id=empresa_id, tipo="BID",
                    titulo=f"Realizar BID de frete para a região {regiao}",
                    descricao=f"A região {regiao} movimenta {peso:.0f} kg com custo acima do "
                              "benchmark. Um BID competitivo pode capturar economia significativa.",
                    economia_estimada=round(economia, 2),
                    impacto="ALTO" if economia > 200000 else "MEDIO",
                    complexidade="MEDIA", prioridade=1,
                    justificativa=f"Volume alto ({peso:.0f} kg) com margem de economia.",
                )
                self.db.add(op)
                self.db.flush()
                # plano de ação automático
                self.db.add(PlanoAcaoModel(
                    empresa_id=empresa_id, oportunidade_id=op.id,
                    acao=f"Realizar BID {regiao}", impacto=op.impacto,
                    economia_estimada=op.economia_estimada,
                    prioridade="ALTA", prazo_dias=60,
                ))
                count += 1
        return count

    def listar(self, empresa_id: int) -> list[OportunidadeModel]:
        return (
            self.db.query(OportunidadeModel)
            .filter(OportunidadeModel.empresa_id == empresa_id)
            .order_by(OportunidadeModel.prioridade, OportunidadeModel.economia_estimada.desc())
            .all()
        )
