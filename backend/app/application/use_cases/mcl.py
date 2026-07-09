"""MCL — Motor de Decisão de Concorrência Logística (BID).

Score ponderado multi-critério (spec 8.5.2):
    Score = 0.40·custo + 0.25·DLG + 0.20·MBL + 0.10·SLA + 0.05·estabilidade

Cada componente é normalizado para [0, 1] (maior = melhor) de forma determinística:
- custo:        menor R$/kg → score maior (normalização min-max invertida).
- performance DLG: melhor classificação histórica da transportadora → maior.
- benchmark MBL: quão melhor que o P50 do mercado → maior (clamp em [0,1]).
- SLA:          menor prazo → maior.
- estabilidade: menor variabilidade histórica (desvio DLG) → maior.

Restrições (spec 8.6):
- Rejeita proposta acima de +20% do benchmark MBL (não entra no ranking).
- Penaliza alta variabilidade (via componente estabilidade).
- Vencedora = maior score entre as elegíveis.

Determinístico, reprocessável, versionado e rastreável.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    BidModel,
    BidPropostaModel,
    BidTransportadoraModel,
    DlgAnaliticoModel,
    MblBenchmarkModel,
    MclDecisaoModel,
    TransportadoraModel,
)

# Pesos oficiais (spec 8.5.2). Somam 1.0.
PESOS = {
    "custo": 0.40,
    "dlg": 0.25,
    "mbl": 0.20,
    "sla": 0.10,
    "estabilidade": 0.05,
}
# Restrição comercial: rejeitar acima de +N% do benchmark MBL (spec 8.6.2).
LIMITE_ACIMA_MBL_PCT = 20.0

# Mapa de classificação DLG → score de performance [0,1].
_SCORE_CLF = {"EFICIENTE": 1.0, "ATENCAO": 0.6, "CRITICO": 0.2, "SEM_REF": 0.5}


def _norm_menor_melhor(valor: float, vmin: float, vmax: float) -> float:
    """Normaliza para [0,1] onde MENOR valor = score maior."""
    if vmax <= vmin:
        return 1.0
    return round(1.0 - (valor - vmin) / (vmax - vmin), 4)


@dataclass
class PropostaScore:
    bid_transportadora_id: int
    transportadora_id: int
    nome: str
    rs_kg: float
    prazo_dias: int
    # componentes normalizados
    score_custo: float = 0.0
    score_dlg: float = 0.0
    score_mbl: float = 0.0
    score_sla: float = 0.0
    score_estabilidade: float = 0.0
    score_final: float = 0.0
    # transparência
    elegivel: bool = True
    motivo_rejeicao: str = ""
    desvio_mbl_pct: Optional[float] = None
    dlg_classificacao: str = "SEM_REF"


class MclUseCase:
    def __init__(self, db: Session):
        self.db = db

    # ── ponto de entrada ────────────────────────────────────────────────────

    def decidir(self, bid_id: int, persistir: bool = True) -> Dict:
        """Calcula o ranking, escolhe a vencedora e (opcionalmente) versiona a
        decisão. Determinístico: mesmo input → mesmo output."""
        bid = self.db.get(BidModel, bid_id)
        if not bid:
            return {"erro": "BID não encontrado."}

        propostas = self._melhores_propostas(bid_id)
        if not propostas:
            return {"erro": "Nenhuma proposta para avaliar."}

        dlg = self._perf_dlg(bid.empresa_id)
        scores = self._calcular_scores(bid, propostas, dlg)

        elegiveis = [s for s in scores if s.elegivel]
        elegiveis.sort(key=lambda s: (-s.score_final, s.bid_transportadora_id))  # determinístico

        vencedora = elegiveis[0] if elegiveis else None
        diff = round(elegiveis[0].score_final - elegiveis[1].score_final, 4) if len(elegiveis) > 1 else 0.0

        resultado = {
            "bid_id": bid_id,
            "vencedora": self._dump(vencedora) if vencedora else None,
            "diferenca_segunda": diff,
            "ranking": [self._dump(s) for s in elegiveis],
            "rejeitadas": [self._dump(s) for s in scores if not s.elegivel],
            "pesos": PESOS,
            "justificativa": self._justificar(vencedora, elegiveis, diff) if vencedora else "Nenhuma proposta elegível.",
        }

        if persistir and vencedora:
            resultado["versao"] = self._persistir(bid, resultado, vencedora, diff)

        return resultado

    # ── coleta de dados ─────────────────────────────────────────────────────

    def _melhores_propostas(self, bid_id: int) -> List[Dict]:
        """Melhor (menor R$/kg) proposta por transportadora, ignorando deletadas."""
        rows = self.db.execute(
            select(BidPropostaModel, BidTransportadoraModel, TransportadoraModel)
            .join(BidTransportadoraModel, BidPropostaModel.bid_transportadora_id == BidTransportadoraModel.id)
            .join(TransportadoraModel, BidTransportadoraModel.transportadora_id == TransportadoraModel.id)
            .where(
                BidPropostaModel.bid_id == bid_id,
                BidPropostaModel.deleted.is_(False),
                BidPropostaModel.valor_rs_kg > 0,
            )
        ).all()
        melhor: Dict[int, Dict] = {}
        for prop, bt, transp in rows:
            atual = melhor.get(bt.id)
            if atual is None or prop.valor_rs_kg < atual["rs_kg"]:
                melhor[bt.id] = {
                    "bid_transportadora_id": bt.id,
                    "transportadora_id": transp.id,
                    "nome": transp.nome_fantasia or transp.razao_social,
                    "rs_kg": prop.valor_rs_kg,
                    "prazo_dias": prop.prazo_dias or 0,
                }
        return list(melhor.values())

    def _perf_dlg(self, empresa_id: int) -> Dict[int, Dict]:
        """Performance histórica por transportadora a partir do DLG (mais recente).
        Retorna {transportadora_id: {classificacao, desvio_pct, rs_kg}}."""
        rows = self.db.execute(
            select(DlgAnaliticoModel)
            .where(
                DlgAnaliticoModel.empresa_id == empresa_id,
                DlgAnaliticoModel.dimensao == "TRANSPORTADORA",
            )
            .order_by(DlgAnaliticoModel.periodo_ref.desc())
        ).scalars().all()
        perf: Dict[int, Dict] = {}
        for r in rows:
            try:
                tid = int(r.chave)
            except (ValueError, TypeError):
                continue
            if tid not in perf:  # mantém o período mais recente
                perf[tid] = {
                    "classificacao": r.classificacao,
                    "desvio_pct": r.desvio_pct,
                    "rs_kg": r.rs_kg,
                }
        return perf

    def _mbl_p50(self, empresa_id: int) -> Optional[float]:
        """P50 nacional de R$/kg (média dos P50 de região) como referência MBL."""
        rows = self.db.execute(
            select(MblBenchmarkModel.p50).where(
                MblBenchmarkModel.empresa_id == empresa_id,
                MblBenchmarkModel.dimensao == "REGIAO",
                MblBenchmarkModel.metrica == "RS_KG",
                MblBenchmarkModel.p50 > 0,
            )
        ).scalars().all()
        return round(statistics.mean(rows), 4) if rows else None

    # ── cálculo do score ────────────────────────────────────────────────────

    def _calcular_scores(self, bid, propostas: List[Dict], dlg: Dict) -> List[PropostaScore]:
        mbl_p50 = self._mbl_p50(bid.empresa_id)

        # limites para normalização (determinístico, sobre o conjunto de propostas)
        rs_kgs = [p["rs_kg"] for p in propostas]
        prazos = [p["prazo_dias"] for p in propostas if p["prazo_dias"] > 0]
        rs_min, rs_max = min(rs_kgs), max(rs_kgs)
        pz_min = min(prazos) if prazos else 0
        pz_max = max(prazos) if prazos else 0

        out: List[PropostaScore] = []
        for p in propostas:
            ps = PropostaScore(
                bid_transportadora_id=p["bid_transportadora_id"],
                transportadora_id=p["transportadora_id"],
                nome=p["nome"], rs_kg=p["rs_kg"], prazo_dias=p["prazo_dias"],
            )

            # restrição CFG: rejeitar acima de +20% do benchmark MBL
            if mbl_p50:
                desvio = round((p["rs_kg"] - mbl_p50) / mbl_p50 * 100, 2)
                ps.desvio_mbl_pct = desvio
                if desvio > LIMITE_ACIMA_MBL_PCT:
                    ps.elegivel = False
                    ps.motivo_rejeicao = f"R$/kg {desvio:.1f}% acima do benchmark (limite +{LIMITE_ACIMA_MBL_PCT:.0f}%)"

            # 1) custo (40%): menor R$/kg = melhor
            ps.score_custo = _norm_menor_melhor(p["rs_kg"], rs_min, rs_max)

            # 2) performance DLG (25%)
            d = dlg.get(p["transportadora_id"])
            if d:
                ps.dlg_classificacao = d["classificacao"]
                ps.score_dlg = _SCORE_CLF.get(d["classificacao"], 0.5)
            else:
                ps.score_dlg = 0.5  # neutro quando sem histórico

            # 3) benchmark MBL (20%): quão abaixo do P50 (clamp [0,1])
            if mbl_p50 and ps.desvio_mbl_pct is not None:
                # desvio -20% → 1.0 ; +20% → 0.0
                ps.score_mbl = max(0.0, min(1.0, round(0.5 - ps.desvio_mbl_pct / 40.0, 4)))
            else:
                ps.score_mbl = 0.5

            # 4) SLA (10%): menor prazo = melhor
            if p["prazo_dias"] > 0:
                ps.score_sla = _norm_menor_melhor(p["prazo_dias"], pz_min, pz_max)
            else:
                ps.score_sla = 0.5

            # 5) estabilidade (5%): menor |desvio DLG| = mais estável
            if d:
                # |desvio| 0% → 1.0 ; ≥50% → 0.0
                ps.score_estabilidade = max(0.0, min(1.0, round(1.0 - abs(d["desvio_pct"]) / 50.0, 4)))
            else:
                ps.score_estabilidade = 0.5

            ps.score_final = round(
                PESOS["custo"] * ps.score_custo +
                PESOS["dlg"] * ps.score_dlg +
                PESOS["mbl"] * ps.score_mbl +
                PESOS["sla"] * ps.score_sla +
                PESOS["estabilidade"] * ps.score_estabilidade,
                4,
            )
            out.append(ps)
        return out

    # ── persistência / versionamento ────────────────────────────────────────

    def _persistir(self, bid, resultado: Dict, vencedora: PropostaScore, diff: float) -> int:
        versao_atual = self.db.scalar(
            select(func.max(MclDecisaoModel.versao)).where(MclDecisaoModel.bid_id == bid.id)
        )
        nova = (versao_atual or 0) + 1
        self.db.add(MclDecisaoModel(
            bid_id=bid.id, empresa_id=bid.empresa_id, versao=nova,
            vencedora_bt_id=vencedora.bid_transportadora_id,
            vencedora_transp_id=vencedora.transportadora_id,
            vencedora_nome=vencedora.nome,
            score_vencedora=vencedora.score_final,
            diferenca_segunda=diff,
            peso_custo=PESOS["custo"], peso_dlg=PESOS["dlg"], peso_mbl=PESOS["mbl"],
            peso_sla=PESOS["sla"], peso_estabilidade=PESOS["estabilidade"],
            ranking=resultado["ranking"],
            justificativa=resultado["justificativa"],
            propostas_rejeitadas={"itens": resultado["rejeitadas"]},
        ))
        self.db.commit()
        return nova

    # ── simulação de cenários ───────────────────────────────────────────────

    def simular(
        self,
        bid_id: int,
        variacao_preco_pct: float = 0.0,
        bid_transportadora_id: Optional[int] = None,
        faturamento_mensal: Optional[float] = None,
    ) -> Dict:
        """Simula impacto de variar a tarifa (de uma transportadora ou todas) no
        custo total e no % frete. Não persiste — análise de sensibilidade."""
        bid = self.db.get(BidModel, bid_id)
        if not bid:
            return {"erro": "BID não encontrado."}
        propostas = self._melhores_propostas(bid_id)
        if not propostas:
            return {"erro": "Nenhuma proposta para simular."}

        # custo base usa peso dos escopos do BID (volume estimado)
        from app.infrastructure.database.models import BidEscopoModel
        peso_bid = self.db.scalar(
            select(func.coalesce(func.sum(BidEscopoModel.peso_total), 0.0)).where(
                BidEscopoModel.bid_id == bid_id
            )
        ) or 0.0

        fator = 1.0 + variacao_preco_pct / 100.0
        itens = []
        custo_base_total = 0.0
        custo_sim_total = 0.0
        for p in propostas:
            aplica = (bid_transportadora_id is None or p["bid_transportadora_id"] == bid_transportadora_id)
            rs_base = p["rs_kg"]
            rs_sim = round(rs_base * fator, 4) if aplica else rs_base
            custo_base = round(rs_base * peso_bid, 2)
            custo_sim = round(rs_sim * peso_bid, 2)
            custo_base_total += custo_base
            custo_sim_total += custo_sim
            itens.append({
                "bid_transportadora_id": p["bid_transportadora_id"],
                "transportadora": p["nome"],
                "rs_kg_base": rs_base, "rs_kg_simulado": rs_sim,
                "custo_base": custo_base, "custo_simulado": custo_sim,
                "delta": round(custo_sim - custo_base, 2),
            })

        out = {
            "bid_id": bid_id,
            "peso_total_kg": round(peso_bid, 2),
            "variacao_preco_pct": variacao_preco_pct,
            "custo_total_base": round(custo_base_total, 2),
            "custo_total_simulado": round(custo_sim_total, 2),
            "delta_custo": round(custo_sim_total - custo_base_total, 2),
            "delta_custo_pct": round((custo_sim_total - custo_base_total) / custo_base_total * 100, 2) if custo_base_total else 0.0,
            "itens": itens,
        }
        if faturamento_mensal and faturamento_mensal > 0:
            out["pct_frete_base"] = round(custo_base_total / faturamento_mensal * 100, 2)
            out["pct_frete_simulado"] = round(custo_sim_total / faturamento_mensal * 100, 2)
        return out

    # ── leitura ─────────────────────────────────────────────────────────────

    def historico(self, bid_id: int) -> List[MclDecisaoModel]:
        return list(self.db.scalars(
            select(MclDecisaoModel)
            .where(MclDecisaoModel.bid_id == bid_id)
            .order_by(MclDecisaoModel.versao.desc())
        ).all())

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _dump(s: Optional[PropostaScore]) -> Optional[Dict]:
        if s is None:
            return None
        return {
            "bid_transportadora_id": s.bid_transportadora_id,
            "transportadora_id": s.transportadora_id,
            "nome": s.nome,
            "rs_kg": s.rs_kg,
            "prazo_dias": s.prazo_dias,
            "score_final": s.score_final,
            "score_custo": s.score_custo,
            "score_dlg": s.score_dlg,
            "score_mbl": s.score_mbl,
            "score_sla": s.score_sla,
            "score_estabilidade": s.score_estabilidade,
            "dlg_classificacao": s.dlg_classificacao,
            "desvio_mbl_pct": s.desvio_mbl_pct,
            "elegivel": s.elegivel,
            "motivo_rejeicao": s.motivo_rejeicao,
        }

    @staticmethod
    def _justificar(vencedora: PropostaScore, ranking: List[PropostaScore], diff: float) -> str:
        partes = [
            f"{vencedora.nome} venceu com score {vencedora.score_final:.3f}",
        ]
        if len(ranking) > 1:
            partes.append(f"({diff:+.3f} vs 2ª colocada {ranking[1].nome})")
        # componente dominante
        comps = {
            "custo competitivo": vencedora.score_custo,
            "performance histórica (DLG)": vencedora.score_dlg,
            "alinhamento ao benchmark (MBL)": vencedora.score_mbl,
            "prazo (SLA)": vencedora.score_sla,
            "estabilidade": vencedora.score_estabilidade,
        }
        forte = max(comps, key=comps.get)
        partes.append(f"— destaque em {forte}")
        if vencedora.desvio_mbl_pct is not None:
            sinal = "abaixo" if vencedora.desvio_mbl_pct < 0 else "acima"
            partes.append(f"({abs(vencedora.desvio_mbl_pct):.1f}% {sinal} do benchmark)")
        return " ".join(partes) + "."
