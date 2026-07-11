"""Motor de Insights Automáticos (Fase 1 — V4).

Engine configurável: as regras ficam no banco (tabela regras_insight),
não hardcoded. Cada regra tem uma expressão avaliada contra métricas
calculadas via SQL. Quando a expressão é verdadeira, gera um Insight.

Os NÚMEROS vêm sempre do backend (SQL). A IA não participa do cálculo
de insights — apenas regras determinísticas.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    InsightModel, InsightExecucaoModel, RegraInsightModel,
    CTeModel, TransportadoraModel,
)
from app.application.use_cases.benchmark_v2 import mapa_medio_por_regiao_destino

logger = logging.getLogger(__name__)


# ─────────── Regras padrão (seed inicial) ───────────
REGRAS_PADRAO = [
    {
        "nome": "Frete regional acima do benchmark",
        "categoria": "BENCHMARK",
        "classificacao": "ATENCAO",
        "expressao": "frete_kg_regiao > benchmark_kg * 1.15",
        "titulo_template": "Frete na região {regiao} está {excesso_pct}% acima do benchmark",
        "descricao_template": "O custo por kg na região {regiao} é R$ {frete_kg_regiao}, "
                              "enquanto o benchmark de mercado é R$ {benchmark_kg}. "
                              "Há oportunidade de renegociação.",
    },
    {
        "nome": "Concentração excessiva em transportadora",
        "categoria": "TRANSPORTADORAS",
        "classificacao": "CRITICO",
        "expressao": "concentracao_transportadora > 60",
        "titulo_template": "Alta dependência da transportadora {transportadora}",
        "descricao_template": "A transportadora {transportadora} concentra "
                              "{concentracao_transportadora}% do seu volume. "
                              "Diversificar reduz risco operacional.",
    },
    {
        "nome": "Potencial de economia elevado",
        "categoria": "CUSTO",
        "classificacao": "OPORTUNIDADE",
        "expressao": "economia_potencial > 50000",
        "titulo_template": "Potencial de economia de R$ {economia_potencial}",
        "descricao_template": "A análise identificou economia potencial de "
                              "R$ {economia_potencial} ao ano com otimização logística.",
    },
    {
        "nome": "Aumento de custo mês a mês",
        "categoria": "CUSTO",
        "classificacao": "ATENCAO",
        "expressao": "variacao_custo_mensal > 10",
        "titulo_template": "Custo logístico subiu {variacao_custo_mensal}% no mês",
        "descricao_template": "O custo logístico aumentou {variacao_custo_mensal}% "
                              "em relação ao período anterior.",
    },
]


class InsightsUseCase:
    def __init__(self, db: Session):
        self.db = db

    # ─────────── Execução do motor ───────────
    def executar(self, empresa_id: int) -> int:
        """Executa todas as regras ativas para a empresa e gera insights."""
        inicio = time.time()
        total = 0
        erro = ""
        status = "OK"

        try:
            metricas = self._coletar_metricas(empresa_id)
            regras = self._regras_ativas(empresa_id)

            # Limpa insights antigos não lidos da mesma execução diária
            self.db.query(InsightModel).filter(
                InsightModel.empresa_id == empresa_id,
                InsightModel.lido == False,  # noqa: E712
            ).delete()

            for regra in regras:
                resultado = self._avaliar_regra(regra, metricas)
                if resultado:
                    for ocorrencia in resultado:
                        self._criar_insight(empresa_id, regra, ocorrencia)
                        total += 1

            self.db.commit()
        except Exception as e:  # noqa: BLE001
            status = "ERRO"
            erro = str(e)
            logger.exception("Erro no motor de insights")

        duracao = int((time.time() - inicio) * 1000)
        execucao = InsightExecucaoModel(
            empresa_id=empresa_id, total_insights=total,
            duracao_ms=duracao, status=status, erro=erro[:1000],
        )
        self.db.add(execucao)
        self.db.commit()
        return total

    # ─────────── Coleta de métricas (SQL) ───────────
    def _coletar_metricas(self, empresa_id: int) -> dict[str, Any]:
        """Calcula todas as métricas usadas pelas regras — via SQL agregado."""
        metricas: dict[str, Any] = {"empresa_id": empresa_id}

        # Frete por kg por região + benchmark
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
        bench = mapa_medio_por_regiao_destino(self.db)
        metricas["regioes"] = []
        for regiao, frete, peso in regioes:
            if not regiao or not peso:
                continue
            frete_kg = round(frete / peso, 2)
            benchmark_kg = bench.get(regiao, 0)
            metricas["regioes"].append({
                "regiao": regiao,
                "frete_kg_regiao": frete_kg,
                "benchmark_kg": benchmark_kg,
                "excesso_pct": round((frete_kg / benchmark_kg - 1) * 100, 1) if benchmark_kg else 0,
            })

        # Concentração por transportadora
        total_peso = (
            self.db.query(func.sum(CTeModel.peso))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )
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
        metricas["transportadoras"] = []
        for nome, peso in transp:
            if not peso or not total_peso:
                continue
            metricas["transportadoras"].append({
                "transportadora": nome,
                "concentracao_transportadora": round(peso / total_peso * 100, 1),
            })

        # Economia potencial (estimativa simples: excesso sobre benchmark)
        economia = 0.0
        for r in metricas["regioes"]:
            if r["benchmark_kg"] and r["frete_kg_regiao"] > r["benchmark_kg"]:
                # peso da região
                peso_regiao = next(
                    (p for reg, _, p in regioes if reg == r["regiao"]), 0
                )
                economia += (r["frete_kg_regiao"] - r["benchmark_kg"]) * (peso_regiao or 0)
        metricas["economia_potencial"] = round(economia * 12, 2)  # anualizado

        # Variação de custo mensal (placeholder — exige histórico)
        metricas["variacao_custo_mensal"] = 0

        return metricas

    # ─────────── Avaliação de regras ───────────
    def _avaliar_regra(self, regra: RegraInsightModel, metricas: dict) -> list[dict]:
        """Avalia uma regra. Retorna lista de ocorrências (pode ser múltipla)."""
        ocorrencias = []
        expr = regra.expressao

        # Regras sobre regiões (uma ocorrência por região)
        if "frete_kg_regiao" in expr or "benchmark_kg" in expr:
            for r in metricas.get("regioes", []):
                if self._eval_seguro(expr, r):
                    ocorrencias.append(r)

        # Regras sobre transportadoras
        elif "concentracao_transportadora" in expr:
            for t in metricas.get("transportadoras", []):
                if self._eval_seguro(expr, t):
                    ocorrencias.append(t)

        # Regras globais (economia, variação)
        else:
            if self._eval_seguro(expr, metricas):
                ocorrencias.append(metricas)

        return ocorrencias

    def _eval_seguro(self, expressao: str, contexto: dict) -> bool:
        """Avalia a expressão de forma restrita (sem builtins perigosos)."""
        try:
            # Apenas variáveis do contexto e operadores aritméticos/comparação
            ctx = {k: v for k, v in contexto.items() if isinstance(v, (int, float))}
            return bool(eval(expressao, {"__builtins__": {}}, ctx))  # noqa: S307
        except Exception:  # noqa: BLE001
            return False

    def _criar_insight(self, empresa_id: int, regra: RegraInsightModel, dados: dict) -> None:
        titulo = self._formatar(regra.titulo_template, dados)
        descricao = self._formatar(regra.descricao_template, dados)
        impacto = float(dados.get("economia_potencial", 0) or 0)

        prioridade = {"CRITICO": 1, "OPORTUNIDADE": 2, "ATENCAO": 3, "INFORMATIVO": 4}.get(
            regra.classificacao, 3
        )

        insight = InsightModel(
            empresa_id=empresa_id,
            regra_id=regra.id,
            categoria=regra.categoria,
            classificacao=regra.classificacao,
            titulo=titulo[:300],
            descricao=descricao[:2000],
            impacto_financeiro=impacto,
            prioridade=prioridade,
            dados=dados,
        )
        self.db.add(insight)

    def _formatar(self, template: str, dados: dict) -> str:
        try:
            return template.format(**dados)
        except (KeyError, ValueError):
            return template

    # ─────────── Regras ───────────
    def _regras_ativas(self, empresa_id: int) -> list[RegraInsightModel]:
        regras = (
            self.db.query(RegraInsightModel)
            .filter(
                RegraInsightModel.ativa == True,  # noqa: E712
                (RegraInsightModel.empresa_id == empresa_id) | (RegraInsightModel.empresa_id.is_(None)),
            )
            .all()
        )
        if not regras:
            self._seed_regras_padrao()
            return self._regras_ativas(empresa_id)
        return regras

    def _seed_regras_padrao(self) -> None:
        """Cria as regras padrão globais se nenhuma existir."""
        for r in REGRAS_PADRAO:
            existe = self.db.query(RegraInsightModel).filter(
                RegraInsightModel.nome == r["nome"]
            ).first()
            if not existe:
                self.db.add(RegraInsightModel(empresa_id=None, ativa=True, **r))
        self.db.commit()

    # ─────────── Listagem ───────────
    def listar(self, empresa_id: int, apenas_nao_lidos: bool = False) -> list[InsightModel]:
        q = self.db.query(InsightModel).filter(InsightModel.empresa_id == empresa_id)
        if apenas_nao_lidos:
            q = q.filter(InsightModel.lido == False)  # noqa: E712
        return q.order_by(InsightModel.prioridade, InsightModel.created_at.desc()).all()

    def marcar_lido(self, insight_id: int, empresa_id: int) -> bool:
        insight = self.db.query(InsightModel).filter(
            InsightModel.id == insight_id, InsightModel.empresa_id == empresa_id
        ).first()
        if not insight:
            return False
        insight.lido = True
        self.db.commit()
        return True
