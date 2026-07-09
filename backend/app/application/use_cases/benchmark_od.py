"""Caso de uso: Benchmark Logístico por Fluxo OD (Origem → Destino) — V2.1.

Correção estrutural do Módulo Benchmark (Especificação Funcional V2.1).

PRINCÍPIO
---------
O custo logístico mora no PAR origem→destino, não na região de chegada.
Dois fluxos que partem do mesmo lugar (ex.: Recife→Sul e Recife→Recife)
têm custos incomparáveis e NÃO podem cair no mesmo balde regional. Por
isso o benchmark passa a ser por CORREDOR (Hub origem → Hub destino).

RESOLUÇÃO DO CORREDOR
---------------------
1. Cada CT-e tem (uf_origem, municipio_origem) e (uf_destino, municipio_destino).
2. O mapa de clusters DA EMPRESA traduz UF/município → Hub.
3. Quando não há regra de cluster, a própria UF vira "hub implícito"
   (cluster de um membro só) — assim o benchmark SEMPRE roda, mesmo
   sem cadastro (fallback transparente).
4. A referência de preço do corredor é GLOBAL (tabela BenchmarkCorredor).
5. Sem referência cadastrada → o corredor é exibido com os dados da
   empresa e marcado `tem_referencia=False` (a tela mostra CTA de cadastro).

SCORE (correção matemática)
---------------------------
Substitui a penalização linear/absoluta por:
  • desvio RELATIVO por corredor (não absoluto);
  • suavização logarítmica do desvio (outliers não destroem o score);
  • ponderação por VOLUME do fluxo (corredor minúsculo pesa pouco);
  • combinação 60% R$/kg + 40% % sobre mercadoria.
Score sempre em [0, 100].
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.application.dtos import (
    BenchmarkCorredorItem,
    BenchmarkODResultado,
    ComparacaoBenchmark,
    EconomiaCorredorItem,
)
from app.domain.entities import BenchmarkCorredor, ClusterCliente, HubLogistico
from app.domain.repositories import (
    IBenchmarkCorredorRepository,
    IClusterClienteRepository,
    ICTeRepository,
    IHubLogisticoRepository,
)

# Pesos da combinação do score (R$/kg domina; % complementa).
_PESO_KG = 0.60
_PESO_PCT = 0.40

# Fator de suavização do desvio relativo no score (quanto maior, mais suave).
# Usa log1p: penalização cresce de forma decrescente conforme o desvio sobe.
_SUAVIZACAO = 1.75


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def classificar_score(score: float) -> str:
    """Classificação textual do score 0-100."""
    if score >= 90:
        return "Excelente"
    if score >= 75:
        return "Muito Bom"
    if score >= 60:
        return "Regular"
    if score >= 40:
        return "Crítico"
    return "Muito Crítico"


def _score_componente(valor: float, referencia: float, dispersao: float = 0.0) -> float:
    """Score 0-100 de um indicador vs. referência, com desvio relativo suavizado.

    - Se valor <= referência  → 100 (está no benchmark ou abaixo: ótimo).
    - Acima da referência     → cai suavemente conforme o desvio relativo.
    - `dispersao` (0-1) amplia a tolerância: corredores naturalmente
      voláteis penalizam menos um mesmo desvio.
    """
    if not referencia or valor <= 0:
        return 0.0
    if valor <= referencia:
        return 100.0
    desvio_rel = (valor - referencia) / referencia          # ex.: 0.20 = 20% acima
    tolerancia = 1.0 + max(0.0, min(dispersao, 1.0))        # 1.0 a 2.0
    desvio_aj = desvio_rel / tolerancia
    # Penalização suavizada: 100 * (1 - log1p(desvio/ k)/log1p(1/k)) limitada.
    penal = math.log1p(desvio_aj * _SUAVIZACAO) / math.log1p(_SUAVIZACAO)
    score = 100.0 * (1.0 - penal)
    return max(0.0, min(100.0, score))


class BenchmarkODUseCase:
    """Motor do benchmark por fluxo OD."""

    def __init__(
        self,
        cte_repo: ICTeRepository,
        cluster_repo: IClusterClienteRepository,
        corredor_repo: IBenchmarkCorredorRepository,
        hub_repo: IHubLogisticoRepository,
    ):
        self.cte_repo = cte_repo
        self.cluster_repo = cluster_repo
        self.corredor_repo = corredor_repo
        self.hub_repo = hub_repo

    # ------------------------------------------------------------------
    # Resolução de Hub a partir do mapa de clusters da empresa
    # ------------------------------------------------------------------
    def _mapa_clusters(self, empresa_id: int) -> Tuple[Dict[str, ClusterCliente], Dict[str, ClusterCliente]]:
        """Retorna (por_municipio, por_uf).

        Chave de município: "UF|MUNICIPIO" (maiúsculas).
        Chave de UF: "UF".
        """
        por_municipio: Dict[str, ClusterCliente] = {}
        por_uf: Dict[str, ClusterCliente] = {}
        for c in self.cluster_repo.list_by_empresa(empresa_id):
            uf = (c.uf or "").upper()
            if c.municipio:
                por_municipio[f"{uf}|{c.municipio.strip().upper()}"] = c
            else:
                por_uf[uf] = c
        return por_municipio, por_uf

    @staticmethod
    def _resolver_hub(
        uf: str, municipio: str,
        por_municipio: Dict[str, ClusterCliente],
        por_uf: Dict[str, ClusterCliente],
    ) -> Tuple[str, str]:
        """Resolve (codigo_hub, nome_hub) para uma localidade.

        Precedência: regra de município > regra de UF > hub implícito (a UF).
        """
        uf = (uf or "").upper() or "??"
        mun = (municipio or "").strip().upper()
        regra = por_municipio.get(f"{uf}|{mun}") or por_uf.get(uf)
        if regra:
            return regra.hub_codigo or f"UF_{uf}", regra.hub_nome or uf
        # Fallback transparente: a UF é seu próprio hub.
        return f"UF_{uf}", uf

    # ------------------------------------------------------------------
    # Cálculo principal — corredores
    # ------------------------------------------------------------------
    def corredores(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[BenchmarkCorredorItem]:
        pares = self.cte_repo.agregar_por_uf_od(
            empresa_id, data_inicio, data_fim, apenas_ativos=True
        )
        por_municipio, por_uf = self._mapa_clusters(empresa_id)

        # Agrupa os pares UF→UF em corredores Hub→Hub.
        grupos: Dict[Tuple[str, str], dict] = defaultdict(
            lambda: {
                "frete": 0.0, "merc": 0.0, "peso": 0.0, "qtd": 0,
                "ho_nome": "", "hd_nome": "",
                "ufs_o": set(), "ufs_d": set(),
            }
        )
        for p in pares:
            ho_cod, ho_nome = self._resolver_hub(p["uf_origem"], p["municipio_origem"], por_municipio, por_uf)
            hd_cod, hd_nome = self._resolver_hub(p["uf_destino"], p["municipio_destino"], por_municipio, por_uf)
            g = grupos[(ho_cod, hd_cod)]
            g["frete"] += p["frete_total"]
            g["merc"] += p["mercadoria_total"]
            g["peso"] += p["peso_total"]
            g["qtd"] += p["qtd_ctes"]
            g["ho_nome"] = ho_nome
            g["hd_nome"] = hd_nome
            if p["uf_origem"]:
                g["ufs_o"].add(p["uf_origem"])
            if p["uf_destino"]:
                g["ufs_d"].add(p["uf_destino"])

        itens: List[BenchmarkCorredorItem] = []
        for (ho_cod, hd_cod), g in grupos.items():
            rs_kg = _div(g["frete"], g["peso"])
            pct = _div(g["frete"], g["merc"]) * 100.0
            ref = self.corredor_repo.get_by_corredor(ho_cod, hd_cod)

            item = BenchmarkCorredorItem(
                hub_origem=ho_cod, hub_origem_nome=g["ho_nome"],
                hub_destino=hd_cod, hub_destino_nome=g["hd_nome"],
                corredor=f"{g['ho_nome']} → {g['hd_nome']}",
                frete_total=g["frete"], peso_total=g["peso"],
                mercadoria_total=g["merc"], qtd_ctes=g["qtd"],
                frete_rs_kg=rs_kg, frete_pct=pct,
                ufs_origem=sorted(g["ufs_o"]), ufs_destino=sorted(g["ufs_d"]),
            )

            if ref:
                item.tem_referencia = True
                item.frete_kg = self._comparar(rs_kg, ref.frete_kg_min, ref.frete_kg_medio, ref.frete_kg_max)
                item.frete_pct_comp = self._comparar(pct, ref.frete_pct_min, ref.frete_pct_medio, ref.frete_pct_max)
                s_kg = _score_componente(rs_kg, ref.frete_kg_medio, ref.dispersao_kg)
                s_pct = _score_componente(pct, ref.frete_pct_medio, ref.dispersao_kg)
                item.score = round(_PESO_KG * s_kg + _PESO_PCT * s_pct, 1)
                item.classificacao = classificar_score(item.score)
            else:
                item.tem_referencia = False
                item.frete_kg = ComparacaoBenchmark(valor=rs_kg)
                item.frete_pct_comp = ComparacaoBenchmark(valor=pct)
                item.score = 0.0
                item.classificacao = "Sem referência"

            itens.append(item)

        # Maior frete primeiro (corredores mais relevantes no topo).
        itens.sort(key=lambda i: i.frete_total, reverse=True)
        return itens

    @staticmethod
    def _comparar(valor: float, b_min: float, b_med: float, b_max: float) -> ComparacaoBenchmark:
        desvio = ((valor - b_med) / b_med * 100.0) if b_med else 0.0
        if not b_med:
            classif = "Sem referência"
        elif valor <= b_med:
            classif = "Excelente"
        elif valor <= b_med * 1.10:
            classif = "Bom"
        elif valor <= b_med * 1.20:
            classif = "Atenção"
        else:
            classif = "Crítico"
        return ComparacaoBenchmark(
            valor=valor, benchmark_min=b_min, benchmark_medio=b_med, benchmark_max=b_max,
            desvio_pct=desvio, classificacao=classif,
            dentro_faixa=(valor <= b_max) if b_max else False,
        )

    # ------------------------------------------------------------------
    # Resultado consolidado (corredores + score global ponderado)
    # ------------------------------------------------------------------
    def resultado(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> BenchmarkODResultado:
        corredores = self.corredores(empresa_id, data_inicio, data_fim)
        com_ref = [c for c in corredores if c.tem_referencia and c.peso_total > 0]

        # Score global = média dos scores dos corredores ponderada por volume (peso).
        peso_total_ref = sum(c.peso_total for c in com_ref)
        if peso_total_ref:
            score_global = sum(c.score * c.peso_total for c in com_ref) / peso_total_ref
        else:
            score_global = 0.0

        return BenchmarkODResultado(
            score_global=round(score_global, 1),
            classificacao_global=classificar_score(score_global) if com_ref else "Sem referência",
            qtd_corredores=len(corredores),
            corredores_sem_referencia=sum(1 for c in corredores if not c.tem_referencia),
            frete_total=sum(c.frete_total for c in corredores),
            peso_total=sum(c.peso_total for c in corredores),
            corredores=corredores,
            periodo_inicio=data_inicio.isoformat() if data_inicio else None,
            periodo_fim=data_fim.isoformat() if data_fim else None,
        )

    # ------------------------------------------------------------------
    # Frete nacional ponderado pelos corredores (sem viés de composição)
    # ------------------------------------------------------------------
    def referencia_nacional_ponderada(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> float:
        """Benchmark nacional = média ponderada por volume das referências OD.

        Pondera o benchmark médio de cada corredor pelo peso real movimentado
        pela empresa naquele corredor. Substitui a média regional simples.
        """
        corredores = self.corredores(empresa_id, data_inicio, data_fim)
        com_ref = [c for c in corredores if c.tem_referencia and c.peso_total > 0]
        peso = sum(c.peso_total for c in com_ref)
        if not peso:
            return 0.0
        return sum(c.frete_kg.benchmark_medio * c.peso_total for c in com_ref) / peso

    # ------------------------------------------------------------------
    # Economia potencial por corredor (base de cálculo OD)
    # ------------------------------------------------------------------
    def economia_por_corredor(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[EconomiaCorredorItem]:
        corredores = self.corredores(empresa_id, data_inicio, data_fim)
        itens: List[EconomiaCorredorItem] = []
        for c in corredores:
            medio = c.frete_kg.benchmark_medio if c.tem_referencia else 0.0
            # Economia só quando o custo está ACIMA da referência do corredor.
            eco = max(0.0, c.frete_rs_kg - medio) * c.peso_total if medio else 0.0
            itens.append(
                EconomiaCorredorItem(
                    corredor=c.corredor, hub_origem=c.hub_origem, hub_destino=c.hub_destino,
                    frete_total=c.frete_total, peso_total=c.peso_total,
                    frete_rs_kg=c.frete_rs_kg, benchmark_medio=medio,
                    tem_referencia=c.tem_referencia, economia=eco,
                )
            )
        itens.sort(key=lambda x: x.economia, reverse=True)
        return itens
