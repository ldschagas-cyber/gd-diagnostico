"""Ferramentas do Assistente Logístico (Tool-Calling — Fase 6).

Cada ferramenta encapsula uma consulta SQL real. A IA escolhe qual chamar;
o backend executa e retorna o número verdadeiro. A IA nunca calcula.

Todas as ferramentas recebem empresa_id implícito (isolamento multi-empresa).
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    CTeModel, TransportadoraModel, FilialModel,
)
from app.application.use_cases.score_logistico import ScoreLogisticoUseCase
from app.application.use_cases.benchmark_v2 import mapa_medio_por_regiao_destino


# ─────────── Definições das ferramentas (schema para o LLM) ───────────
DEFINICOES_FERRAMENTAS = [
    {
        "name": "get_score_logistico",
        "description": "Retorna o score logístico geral (0-100) da operação e seus componentes.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_transportadora_mais_cara",
        "description": "Retorna a transportadora com maior custo médio por kg.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_regiao_mais_cara",
        "description": "Retorna a região com maior frete por kg, comparada ao benchmark.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pior_filial",
        "description": "Retorna a filial (tomador) com pior desempenho de custo.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_economia_potencial",
        "description": "Retorna o potencial de economia anual estimado.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_oportunidades",
        "description": "Lista as oportunidades de economia identificadas para a empresa.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_benchmark_setorial",
        "description": "Compara a operação com o benchmark do segmento de mercado.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recomendacao_bid",
        "description": "Recomenda quais transportadoras convidar para um BID de frete.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pior_cliente",
        "description": "Retorna o cliente (destinatário) com maior impacto financeiro potencial de frete.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_ofensor_cliente",
        "description": (
            "Retorna a causa dominante (adicionais, fragmentação, ambas ou nenhuma) já "
            "diagnosticada pelo motor DLG para um cliente, com os números que a sustentam. "
            "Quando nenhum cliente é informado, usa o pior cliente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cliente": {"type": "string", "description": "Nome (ou trecho do nome) do cliente. Opcional."},
            },
        },
    },
]


class FerramentasLogisticas:
    """Executor das ferramentas. Cada método faz uma consulta SQL real."""

    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def executar(self, nome: str, args: dict) -> dict:
        """Roteia a chamada para o método correspondente."""
        metodo = getattr(self, nome, None)
        if not metodo:
            return {"erro": f"Ferramenta '{nome}' não encontrada"}
        try:
            return metodo(**(args or {}))
        except Exception as e:  # noqa: BLE001
            return {"erro": str(e)}

    # ─────────── Ferramentas ───────────
    def get_score_logistico(self) -> dict:
        score = ScoreLogisticoUseCase(self.db).calcular(self.empresa_id, salvar=False)
        return {
            "score_total": score.score_total,
            "classificacao": score.classificacao,
            "componentes": {
                "benchmark_nacional": score.score_benchmark_nacional,
                "benchmark_regional": score.score_benchmark_regional,
                "transportadoras": score.score_transportadoras,
                "filiais": score.score_filiais,
                "economia": score.score_economia,
            },
        }

    def get_transportadora_mais_cara(self) -> dict:
        row = (
            self.db.query(
                TransportadoraModel.razao_social,
                (func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso)).label("custo_kg"),
                func.sum(CTeModel.valor_frete).label("total"),
            )
            .join(CTeModel, CTeModel.transportadora_id == TransportadoraModel.id)
            .filter(CTeModel.empresa_id == self.empresa_id, CTeModel.peso > 0)
            .group_by(TransportadoraModel.razao_social)
            .order_by(func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso))
            .all()
        )
        if not row:
            return {"mensagem": "Sem dados de transportadoras."}
        mais_cara = row[-1]
        return {
            "transportadora": mais_cara[0],
            "custo_por_kg": round(mais_cara[1], 2),
            "frete_total": round(mais_cara[2], 2),
        }

    def get_regiao_mais_cara(self) -> dict:
        regioes = (
            self.db.query(
                CTeModel.macro_regiao_destino,
                (func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso)).label("custo_kg"),
            )
            .filter(CTeModel.empresa_id == self.empresa_id, CTeModel.peso > 0)
            .group_by(CTeModel.macro_regiao_destino)
            .all()
        )
        if not regioes:
            return {"mensagem": "Sem dados de regiões."}
        bench = mapa_medio_por_regiao_destino(self.db)
        mais_cara = max(regioes, key=lambda r: r[1] or 0)
        benchmark = bench.get(mais_cara[0], 0)
        return {
            "regiao": mais_cara[0],
            "custo_por_kg": round(mais_cara[1], 2),
            "benchmark_kg": round(benchmark, 2) if benchmark else None,
            "acima_do_benchmark_pct": round((mais_cara[1] / benchmark - 1) * 100, 1) if benchmark else None,
        }

    def get_pior_filial(self) -> dict:
        filiais = (
            self.db.query(
                CTeModel.tomador_cnpj,
                (func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso)).label("custo_kg"),
            )
            .filter(CTeModel.empresa_id == self.empresa_id, CTeModel.peso > 0)
            .group_by(CTeModel.tomador_cnpj)
            .all()
        )
        if not filiais:
            return {"mensagem": "Sem dados de filiais."}
        pior = max(filiais, key=lambda f: f[1] or 0)
        # tenta achar o nome da filial
        filial = (
            self.db.query(FilialModel)
            .filter(FilialModel.empresa_id == self.empresa_id, FilialModel.cnpj == pior[0])
            .first()
        )
        return {
            "filial": filial.razao_social if filial else pior[0],
            "cnpj": pior[0],
            "custo_por_kg": round(pior[1], 2),
        }

    def get_economia_potencial(self) -> dict:
        frete_total = (
            self.db.query(func.sum(CTeModel.valor_frete))
            .filter(CTeModel.empresa_id == self.empresa_id).scalar() or 0
        )
        score = ScoreLogisticoUseCase(self.db).calcular(self.empresa_id, salvar=False)
        economia = round(frete_total * (100 - score.score_economia) / 100 * 0.5, 2)
        return {
            "economia_potencial_anual": economia,
            "frete_total_periodo": round(frete_total, 2),
            "score_economia": score.score_economia,
        }

    def get_oportunidades(self) -> dict:
        from app.infrastructure.database.models import OportunidadeModel
        ops = (
            self.db.query(OportunidadeModel)
            .filter(OportunidadeModel.empresa_id == self.empresa_id,
                    OportunidadeModel.status == "ABERTA")
            .order_by(OportunidadeModel.prioridade)
            .limit(5)
            .all()
        )
        return {
            "total": len(ops),
            "oportunidades": [
                {"tipo": o.tipo, "titulo": o.titulo,
                 "economia_estimada": o.economia_estimada, "impacto": o.impacto}
                for o in ops
            ],
        }

    def get_benchmark_setorial(self) -> dict:
        from app.infrastructure.database.models import BenchmarkSetorialModel
        frete_kg = self._frete_kg_medio()
        setoriais = self.db.query(BenchmarkSetorialModel).all()
        return {
            "frete_kg_empresa": round(frete_kg, 2),
            "segmentos_disponiveis": [s.segmento for s in setoriais],
            "comparativo": [
                {"segmento": s.segmento, "frete_kg_medio": s.frete_kg_medio,
                 "diferenca_pct": round((frete_kg / s.frete_kg_medio - 1) * 100, 1) if s.frete_kg_medio else None}
                for s in setoriais
            ],
        }

    def get_recomendacao_bid(self) -> dict:
        # Transportadoras ordenadas por custo (melhores candidatas primeiro)
        transp = (
            self.db.query(
                TransportadoraModel.razao_social,
                (func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso)).label("custo_kg"),
            )
            .join(CTeModel, CTeModel.transportadora_id == TransportadoraModel.id)
            .filter(CTeModel.empresa_id == self.empresa_id, CTeModel.peso > 0)
            .group_by(TransportadoraModel.razao_social)
            .order_by(func.sum(CTeModel.valor_frete) / func.sum(CTeModel.peso))
            .limit(5)
            .all()
        )
        return {
            "recomendacao": "Convide as transportadoras com melhor custo histórico e diversifique.",
            "transportadoras_sugeridas": [
                {"nome": t[0], "custo_kg": round(t[1], 2)} for t in transp
            ],
        }

    # ─────────── v6.7.0 — dimensão Cliente (destinatário) ───────────
    def _clientes_dlg(self) -> list:
        """Consulta o motor DLG já existente (nunca recalcula em paralelo —
        mesmo princípio de reuso da Opção B da Especificação Técnica)."""
        from app.application.use_cases.dlg import DlgUseCase
        return DlgUseCase(self.db).listar(
            self.empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")

    def get_pior_cliente(self) -> dict:
        clientes = self._clientes_dlg()
        if not clientes:
            return {"mensagem": "Sem dados de clientes (destinatário) no período."}
        pior = max(clientes, key=lambda c: c.get("impacto_financeiro_potencial") or 0)
        return {
            "cliente": pior["chave_label"],
            "classificacao": pior["classificacao"],
            "rs_kg": round(pior["rs_kg"], 4),
            "rs_kg_ref": round(pior["rs_kg_ref"], 4),
            "impacto_financeiro_potencial": round(pior.get("impacto_financeiro_potencial") or 0, 2),
        }

    def get_ofensor_cliente(self, cliente: str | None = None) -> dict:
        """RN-76: nunca recalcula a causa — só retorna o que
        ``_diagnosticar_causa`` já atribuiu ao cliente (o LLM narra, não infere)."""
        clientes = self._clientes_dlg()
        if not clientes:
            return {"mensagem": "Sem dados de clientes (destinatário) no período."}

        alvo = None
        if cliente:
            termo = cliente.strip().lower()
            alvo = next((c for c in clientes if termo in (c["chave_label"] or "").lower()), None)
            if alvo is None:
                return {"mensagem": f"Cliente '{cliente}' não encontrado no período."}
        else:
            alvo = max(clientes, key=lambda c: c.get("impacto_financeiro_potencial") or 0)

        causa = alvo.get("causa_dominante")
        if causa is None:
            return {
                "cliente": alvo["chave_label"],
                "classificacao": alvo["classificacao"],
                "mensagem": "Cliente EFICIENTE/sem referência — diagnóstico causal não se aplica (RN-76).",
            }

        detalhe = alvo.get("causa_detalhe") or {}
        return {
            "cliente": alvo["chave_label"],
            "classificacao": alvo["classificacao"],
            "causa_dominante": causa,
            "pct_componentes_adicionais": alvo.get("pct_componentes_adicionais"),
            "componente_ofensor": (detalhe.get("componente_top") or [None])[0],
            "sinal_fragmentacao": alvo.get("sinal_fragmentacao"),
            "qtd_despachos_janela_curta": detalhe.get("qtd_despachos"),
            "janela_dias": detalhe.get("janela_dias"),
            "impacto_financeiro_potencial": round(alvo.get("impacto_financeiro_potencial") or 0, 2),
        }

    def _frete_kg_medio(self) -> float:
        row = (
            self.db.query(func.sum(CTeModel.valor_frete), func.sum(CTeModel.peso))
            .filter(CTeModel.empresa_id == self.empresa_id, CTeModel.peso > 0)
            .first()
        )
        return (row[0] / row[1]) if row and row[1] else 0.0
