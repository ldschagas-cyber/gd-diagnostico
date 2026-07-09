"""Motor de economia, comparativo, score de transportadoras e simulação de distribuição.

Fórmula central (spec §11):
    Economia = (frete_rs_kg_atual − proposta_rs_kg) × peso_movimentado

Score de transportadora (spec §13):
    Preço 40%  | Prazo 30%  | Cobertura 20%  | Avaliação usuário 10%
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.domain.entities import (
    BidEscopo, BidProposta, BidSimulacao, BidTransportadora,
    BidTransportadoraStatusEnum, PropostaOrigemEnum, TipoAgrupamentoEnum,
)
from app.domain.repositories import (
    IBidEscopoRepository, IBidPropostaRepository,
    IBidSimulacaoRepository, IBidTransportadoraRepository,
)


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _norm_grupo(s: str) -> str:
    """Normaliza o nome do grupo para casamento robusto entre escopo e propostas
    (ignora caixa e espaços nas bordas). Ex.: 'Sudeste' == ' SUDESTE '."""
    return (s or "").strip().upper()


# ── DTOs de resultado (sem persistência) ──────────────────────────────────

@dataclass
class LinhaComparativa:
    valor_grupo: str = ""
    peso_total: float = 0.0
    frete_atual_rs_kg: float = 0.0
    custo_atual_total: float = 0.0
    propostas: List[dict] = field(default_factory=list)  # [{transportadora, rs_kg, economia, economia_pct, prazo}]
    melhor_proposta_rs_kg: Optional[float] = None
    melhor_economia: float = 0.0


@dataclass
class ResultadoEconomia:
    economia_total_periodo: float = 0.0
    frete_atual_total: float = 0.0
    economia_pct: float = 0.0
    meses_periodo: float = 1.0
    ritmo_mensal: float = 0.0
    proj_trimestral: float = 0.0
    proj_semestral: float = 0.0
    proj_anual: float = 0.0
    por_grupo: List[dict] = field(default_factory=list)


@dataclass
class ScoreTransportadora:
    bid_transportadora_id: int = 0
    transportadora_id: int = 0
    nome: str = ""
    score: float = 0.0
    classificacao: str = ""
    score_preco: float = 0.0
    score_prazo: float = 0.0
    score_cobertura: float = 0.0
    score_avaliacao: float = 0.0
    proposta_media_rs_kg: float = 0.0
    prazo_medio: float = 0.0
    cobertura_media: float = 0.0


@dataclass
class ResultadoSimulacao:
    nome: str = ""
    custo_atual: float = 0.0
    custo_proposto: float = 0.0
    economia_total: float = 0.0
    reducao_pct: float = 0.0
    itens: List[dict] = field(default_factory=list)


# ── Use Case ──────────────────────────────────────────────────────────────

class EconomiaUseCase:
    def __init__(
        self,
        escopo_repo: IBidEscopoRepository,
        proposta_repo: IBidPropostaRepository,
        bt_repo: IBidTransportadoraRepository,
        simulacao_repo: IBidSimulacaoRepository,
        transp_nomes: Dict[int, str],
    ):
        self.escopos = escopo_repo
        self.propostas = proposta_repo
        self.bts = bt_repo
        self.simulacoes = simulacao_repo
        self.nomes = transp_nomes

    # ── Comparativo ───────────────────────────────────────────────────────

    def comparativo(self, bid_id: int) -> List[LinhaComparativa]:
        escopos = self.escopos.list_by_bid(bid_id)
        propostas = self.propostas.list_by_bid(bid_id)
        bts = self.bts.list_by_bid(bid_id)
        bt_map = {bt.id: bt for bt in bts}
        bt_nome = {
            bt.id: self.nomes.get(bt.transportadora_id, f"Transp. {bt.transportadora_id}")
            for bt in bts
        }

        # Agrupa propostas por valor_grupo (normalizado: sem espaços e sem caixa,
        # para casar "Sudeste" com "SUDESTE" etc.)
        props_por_grupo: Dict[str, List[BidProposta]] = {}
        for p in propostas:
            props_por_grupo.setdefault(_norm_grupo(p.valor_grupo), []).append(p)

        linhas = []
        for e in escopos:
            linha = LinhaComparativa(
                valor_grupo=e.valor_grupo,
                peso_total=e.peso_total,
                frete_atual_rs_kg=e.frete_rs_kg,
                custo_atual_total=e.valor_frete_total,
            )
            for p in props_por_grupo.get(_norm_grupo(e.valor_grupo), []):
                economia = max(0.0, (e.frete_rs_kg - p.valor_rs_kg) * e.peso_total)
                economia_pct = _div(economia, e.valor_frete_total) * 100
                linha.propostas.append({
                    "bid_transportadora_id": p.bid_transportadora_id,
                    "transportadora": bt_nome.get(p.bid_transportadora_id, "?"),
                    "rs_kg": p.valor_rs_kg,
                    "valor_minimo": p.valor_minimo,
                    "prazo_dias": p.prazo_dias,
                    "cobertura_pct": p.cobertura_pct,
                    "economia_rs": round(economia, 2),
                    "economia_pct": round(economia_pct, 2),
                })
            if linha.propostas:
                linha.propostas.sort(key=lambda x: x["rs_kg"])
                linha.melhor_proposta_rs_kg = linha.propostas[0]["rs_kg"]
                linha.melhor_economia = linha.propostas[0]["economia_rs"]
            linhas.append(linha)
        return linhas

    # ── Motor de Economia (spec §11) ──────────────────────────────────────

    def economia(
        self, bid_id: int, bid_data_inicio, bid_data_fim
    ) -> ResultadoEconomia:
        escopos = self.escopos.list_by_bid(bid_id)
        propostas = self.propostas.list_by_bid(bid_id)

        # Melhor proposta por grupo (chave normalizada)
        melhor: Dict[str, float] = {}
        for p in propostas:
            k = _norm_grupo(p.valor_grupo)
            if k not in melhor or p.valor_rs_kg < melhor[k]:
                melhor[k] = p.valor_rs_kg

        total_atual = sum(e.valor_frete_total for e in escopos)
        eco_total = 0.0
        por_grupo = []

        for e in escopos:
            chave_e = _norm_grupo(e.valor_grupo)
            if chave_e in melhor:
                eco = max(0.0, (e.frete_rs_kg - melhor[chave_e]) * e.peso_total)
                eco_total += eco
                por_grupo.append({
                    "valor_grupo": e.valor_grupo,
                    "frete_atual_rs_kg": e.frete_rs_kg,
                    "melhor_proposta_rs_kg": melhor[chave_e],
                    "peso_total": e.peso_total,
                    "economia": round(eco, 2),
                })

        # Número de meses no período
        if bid_data_inicio and bid_data_fim:
            dias = (bid_data_fim - bid_data_inicio).days
            n_meses = max(1.0, dias / 30)
        else:
            n_meses = 1.0

        mensal = _div(eco_total, n_meses)
        return ResultadoEconomia(
            economia_total_periodo=round(eco_total, 2),
            frete_atual_total=round(total_atual, 2),
            economia_pct=round(_div(eco_total, total_atual) * 100, 2),
            meses_periodo=round(n_meses, 1),
            ritmo_mensal=round(mensal, 2),
            proj_trimestral=round(mensal * 3, 2),
            proj_semestral=round(mensal * 6, 2),
            proj_anual=round(mensal * 12, 2),
            por_grupo=por_grupo,
        )

    # ── Score de Transportadora (spec §13) ────────────────────────────────

    def scores(self, bid_id: int) -> List[ScoreTransportadora]:
        bts = self.bts.list_by_bid(bid_id)
        propostas = self.propostas.list_by_bid(bid_id)

        # Indexa propostas por bid_transportadora_id
        props: Dict[int, List[BidProposta]] = {}
        for p in propostas:
            props.setdefault(p.bid_transportadora_id, []).append(p)

        # Ranges globais para normalizar preço
        todos_rs_kg = [p.valor_rs_kg for p in propostas if p.valor_rs_kg > 0]
        min_kg = min(todos_rs_kg) if todos_rs_kg else 1.0
        max_kg = max(todos_rs_kg) if todos_rs_kg else 1.0

        todos_prazo = [p.prazo_dias for p in propostas if p.prazo_dias > 0]
        min_prazo = min(todos_prazo) if todos_prazo else 1
        max_prazo = max(todos_prazo) if todos_prazo else 1

        resultado = []
        for bt in bts:
            ps = props.get(bt.id, [])
            if not ps:
                continue  # sem propostas, sem score

            media_rs_kg = _div(sum(p.valor_rs_kg for p in ps), len(ps))
            media_prazo = _div(sum(p.prazo_dias for p in ps), len(ps))
            media_cobertura = _div(sum(p.cobertura_pct for p in ps), len(ps))

            # Preço 40%: menor preço → 100; maior → 0
            if max_kg > min_kg:
                s_preco = (1 - (media_rs_kg - min_kg) / (max_kg - min_kg)) * 100
            else:
                s_preco = 100.0

            # Prazo 30%: menor prazo → 100
            if max_prazo > min_prazo:
                s_prazo = (1 - (media_prazo - min_prazo) / (max_prazo - min_prazo)) * 100
            else:
                s_prazo = 100.0

            # Cobertura 20%: cobertura_pct direto
            s_cobertura = min(100.0, media_cobertura)

            # Avaliação usuário 10%: nota 0-10 → 0-100
            s_aval = (bt.avaliacao_usuario or 5.0) * 10

            score = (
                s_preco * 0.40 +
                s_prazo * 0.30 +
                s_cobertura * 0.20 +
                s_aval * 0.10
            )

            if score >= 80:
                classif = "Excelente"
            elif score >= 65:
                classif = "Boa"
            elif score >= 50:
                classif = "Regular"
            else:
                classif = "Crítica"

            resultado.append(ScoreTransportadora(
                bid_transportadora_id=bt.id,
                transportadora_id=bt.transportadora_id,
                nome=self.nomes.get(bt.transportadora_id, f"Transp. {bt.transportadora_id}"),
                score=round(score, 1),
                classificacao=classif,
                score_preco=round(s_preco, 1),
                score_prazo=round(s_prazo, 1),
                score_cobertura=round(s_cobertura, 1),
                score_avaliacao=round(s_aval, 1),
                proposta_media_rs_kg=round(media_rs_kg, 4),
                prazo_medio=round(media_prazo, 1),
                cobertura_media=round(media_cobertura, 1),
            ))

        resultado.sort(key=lambda x: x.score, reverse=True)
        return resultado

    # ── Simulação de Distribuição (spec §12) ──────────────────────────────

    def calcular_simulacao(
        self, bid_id: int, itens: List[dict]
    ) -> ResultadoSimulacao:
        """Calcula cenário sem persistir.

        itens: [{bid_transportadora_id, valor_grupo, pct_alocado}]
        """
        escopos = self.escopos.list_by_bid(bid_id)
        propostas = self.propostas.list_by_bid(bid_id)

        # Mapa bid_transportadora_id → nome real (corrige "Transportadora N")
        bt_nome = {
            bt.id: self.nomes.get(bt.transportadora_id, f"Transp. {bt.transportadora_id}")
            for bt in self.bts.list_by_bid(bid_id)
        }

        esc_map = {e.valor_grupo: e for e in escopos}
        melhor_prop: Dict[tuple, BidProposta] = {}
        for p in propostas:
            k = (p.bid_transportadora_id, p.valor_grupo)
            if k not in melhor_prop or p.valor_rs_kg < melhor_prop[k].valor_rs_kg:
                melhor_prop[k] = p

        custo_atual = sum(e.valor_frete_total for e in escopos)
        custo_prop = 0.0
        itens_resultado = []

        for item in itens:
            bt_id = item.get("bid_transportadora_id")
            grupo = item.get("valor_grupo")
            pct = item.get("pct_alocado", 100.0) / 100
            esc = esc_map.get(grupo)
            if not esc:
                continue
            prop = melhor_prop.get((bt_id, grupo))
            rs_kg = prop.valor_rs_kg if prop else esc.frete_rs_kg
            custo_item = max(
                rs_kg * esc.peso_total * pct,
                (prop.valor_minimo if prop else 0),
            )
            custo_prop += custo_item
            itens_resultado.append({
                "valor_grupo": grupo,
                "bid_transportadora_id": bt_id,
                "transportadora": bt_nome.get(bt_id, f"Transp. {bt_id}"),
                "pct_alocado": item.get("pct_alocado"),
                "rs_kg": rs_kg,
                "custo": round(custo_item, 2),
            })

        economia = max(0.0, custo_atual - custo_prop)
        return ResultadoSimulacao(
            custo_atual=round(custo_atual, 2),
            custo_proposto=round(custo_prop, 2),
            economia_total=round(economia, 2),
            reducao_pct=round(_div(economia, custo_atual) * 100, 2),
            itens=itens_resultado,
        )

    def salvar_simulacao(self, sim: BidSimulacao) -> BidSimulacao:
        return self.simulacoes.create(sim)

    def listar_simulacoes(self, bid_id: int) -> List[BidSimulacao]:
        return self.simulacoes.list_by_bid(bid_id)

    def deletar_simulacao(self, sim_id: int) -> bool:
        return self.simulacoes.delete(sim_id)
