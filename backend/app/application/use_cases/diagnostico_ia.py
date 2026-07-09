"""Diagnóstico IA (Fase 2 — V4).

Gera uma análise executiva da operação logística. O fluxo:
1. Coleta números via SQL (use cases existentes + Score)
2. Monta um contexto agregado (sem CT-es brutos)
3. Envia ao LLM, que produz a NARRATIVA (não calcula números)
4. Persiste, cacheia e versiona o resultado

Cache por hash(empresa + período + volume de dados): se nada mudou,
reaproveita o diagnóstico sem custo de IA.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.ai.llm_client import get_llm_client, ModeloTipo
from app.infrastructure.ai.cache_service import get_cache
from app.infrastructure.ai.usage_logger import registrar_uso
from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    DiagnosticoIAModel, DiagnosticoHistoricoModel, CTeModel,
)
from app.application.use_cases.score_logistico import ScoreLogisticoUseCase

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Você é um consultor logístico sênior da GD Conecta, especializado \
em diagnóstico de custos de frete. Analise os dados fornecidos e produza uma análise \
executiva clara e acionável em português brasileiro.

REGRAS IMPORTANTES:
- Os números já foram calculados pelo sistema. NÃO recalcule nem invente valores.
- Use apenas os dados fornecidos no contexto.
- Seja objetivo e focado em ações concretas de redução de custo.
- Formate a resposta com as seções solicitadas."""


class DiagnosticoIAUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()
        self.cache = get_cache()

    def gerar(self, empresa_id: int, periodo_inicio=None, periodo_fim=None,
              forcar: bool = False, user_id: int = None) -> DiagnosticoIAModel:
        """Gera (ou recupera do cache) o diagnóstico IA da empresa."""
        contexto = self._coletar_contexto(empresa_id)
        cache_hash = self._gerar_hash(empresa_id, contexto)

        # Verifica cache/persistência
        if not forcar:
            existente = (
                self.db.query(DiagnosticoIAModel)
                .filter(
                    DiagnosticoIAModel.empresa_id == empresa_id,
                    DiagnosticoIAModel.cache_hash == cache_hash,
                )
                .order_by(DiagnosticoIAModel.created_at.desc())
                .first()
            )
            if existente:
                logger.info("Diagnóstico recuperado do cache (empresa %s)", empresa_id)
                return existente

        # Gera via LLM
        prompt = self._montar_prompt(contexto)
        resposta = self.llm.gerar(
            prompt, system=SYSTEM_PROMPT, tipo=ModeloTipo.PRINCIPAL,
            max_tokens=2000,
            contexto_simulado={
                "tipo": "diagnostico",
                "score": contexto["score"]["total"],
                "economia_potencial": contexto["economia_potencial"],
            },
        )
        registrar_uso(self.db, resposta, feature="diagnostico",
                      empresa_id=empresa_id, user_id=user_id)

        # Faz parsing das seções (texto estruturado)
        secoes = self._parsear_secoes(resposta.texto)

        diag = DiagnosticoIAModel(
            empresa_id=empresa_id,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            resumo_executivo=secoes.get("resumo", resposta.texto[:5000]),
            pontos_fortes=secoes.get("fortes", ""),
            pontos_atencao=secoes.get("atencao", ""),
            principais_desvios=secoes.get("desvios", ""),
            economia_potencial=contexto["economia_potencial"],
            plano_acao=secoes.get("plano", ""),
            score_logistico=contexto["score"]["total"],
            modelo_usado=resposta.modelo,
            cache_hash=cache_hash,
        )
        self.db.add(diag)
        self.db.commit()
        self.db.refresh(diag)

        # Histórico
        self.db.add(DiagnosticoHistoricoModel(
            empresa_id=empresa_id, diagnostico_id=diag.id,
            score=contexto["score"]["total"],
            economia_potencial=contexto["economia_potencial"],
            resumo=diag.resumo_executivo[:2000],
        ))
        self.db.commit()

        # Indexa no RAG para consulta futura pelo assistente
        try:
            from app.application.use_cases.rag_service import RagService
            rag = RagService(self.db)
            if rag.disponivel:
                rag.indexar_diagnostico(empresa_id, diag)
        except Exception:  # noqa: BLE001
            pass  # indexação é complementar

        return diag

    # ─────────── Coleta de contexto (SQL) ───────────
    def _coletar_contexto(self, empresa_id: int) -> dict:
        score = ScoreLogisticoUseCase(self.db).calcular(empresa_id, salvar=False)

        # Frete total e por região
        regioes = (
            self.db.query(
                CTeModel.macro_regiao_destino,
                func.sum(CTeModel.valor_frete),
                func.sum(CTeModel.peso),
                func.count(CTeModel.id),
            )
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
                CTeModel.peso > 0,
            )
            .group_by(CTeModel.macro_regiao_destino)
            .all()
        )
        regioes_data = [
            {
                "regiao": r or "N/D",
                "frete_kg": round(frete / peso, 2) if peso else 0,
                "embarques": qtd,
            }
            for r, frete, peso, qtd in regioes
        ]

        frete_total = (
            self.db.query(func.sum(CTeModel.valor_frete))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )
        total_embarques = (
            self.db.query(func.count(CTeModel.id))
            .filter(
                CTeModel.empresa_id == empresa_id,
                CTeModel.status == CTE_STATUS_ATIVO,
            ).scalar() or 0
        )

        # economia potencial (do score de economia)
        economia = round(frete_total * (100 - score.score_economia) / 100 * 0.5, 2)

        return {
            "score": {
                "total": score.score_total,
                "classificacao": score.classificacao,
                "nacional": score.score_benchmark_nacional,
                "regional": score.score_benchmark_regional,
                "transportadoras": score.score_transportadoras,
                "filiais": score.score_filiais,
                "economia": score.score_economia,
            },
            "frete_total": round(frete_total, 2),
            "total_embarques": total_embarques,
            "regioes": regioes_data,
            "economia_potencial": economia,
        }

    def _montar_prompt(self, contexto: dict) -> str:
        regioes_txt = "\n".join(
            f"- {r['regiao']}: R$ {r['frete_kg']}/kg em {r['embarques']} embarques"
            for r in contexto["regioes"]
        )
        return f"""Analise a operação logística com base nestes dados já calculados:

SCORE LOGÍSTICO: {contexto['score']['total']}/100 ({contexto['score']['classificacao']})
- Benchmark Nacional: {contexto['score']['nacional']}/100
- Benchmark Regional: {contexto['score']['regional']}/100
- Transportadoras: {contexto['score']['transportadoras']}/100
- Filiais: {contexto['score']['filiais']}/100
- Economia: {contexto['score']['economia']}/100

FRETE TOTAL: R$ {contexto['frete_total']:,.2f}
EMBARQUES: {contexto['total_embarques']}
ECONOMIA POTENCIAL ESTIMADA: R$ {contexto['economia_potencial']:,.2f}/ano

FRETE POR REGIÃO:
{regioes_txt}

Produza um diagnóstico executivo com EXATAMENTE estas seções:
**Resumo Executivo**
**Pontos Fortes**
**Pontos de Atenção**
**Principais Desvios**
**Potencial de Economia**
**Plano de Ação Sugerido**"""

    def _parsear_secoes(self, texto: str) -> dict:
        """Extrai as seções do texto gerado pela IA."""
        secoes = {}
        mapa = {
            "resumo executivo": "resumo",
            "pontos fortes": "fortes",
            "pontos de atenção": "atencao",
            "principais desvios": "desvios",
            "plano de ação": "plano",
        }
        atual = None
        buffer = []
        for linha in texto.split("\n"):
            l = linha.strip().lower().replace("*", "").replace("#", "").strip()
            achou = None
            for chave, campo in mapa.items():
                if l.startswith(chave):
                    achou = campo
                    break
            if achou:
                if atual and buffer:
                    secoes[atual] = "\n".join(buffer).strip()
                atual = achou
                buffer = []
            elif atual:
                buffer.append(linha)
        if atual and buffer:
            secoes[atual] = "\n".join(buffer).strip()
        return secoes

    def _gerar_hash(self, empresa_id: int, contexto: dict) -> str:
        base = f"{empresa_id}:{contexto['frete_total']}:{contexto['total_embarques']}:{contexto['score']['total']}"
        return hashlib.sha256(base.encode()).hexdigest()[:64]

    # ─────────── Listagem ───────────
    def ultimo(self, empresa_id: int) -> DiagnosticoIAModel | None:
        return (
            self.db.query(DiagnosticoIAModel)
            .filter(DiagnosticoIAModel.empresa_id == empresa_id)
            .order_by(DiagnosticoIAModel.created_at.desc())
            .first()
        )

    def historico(self, empresa_id: int, limite: int = 12) -> list[DiagnosticoHistoricoModel]:
        return (
            self.db.query(DiagnosticoHistoricoModel)
            .filter(DiagnosticoHistoricoModel.empresa_id == empresa_id)
            .order_by(DiagnosticoHistoricoModel.created_at.desc())
            .limit(limite)
            .all()
        )
