"""Caso de uso: Simulador de Hub de Origem.

PRINCÍPIO
---------
Responde "e se eu despachasse deste outro hub?" reaproveitando os dois
motores já existentes do Benchmark OD (V2.1):
  • BenchmarkODUseCase.corredores() — resolve, a partir do histórico real de
    CT-e, os corredores (hub origem → hub destino) que a empresa DE FATO
    opera hoje.
  • BenchmarkCorredorRepository — referência de mercado por par de hubs (a
    mesma tabela usada pelo Benchmark OD para pontuar corredores existentes),
    aqui consultada para um hub de origem que a empresa NÃO opera.

O "atual" de cada rota é sempre dado observado (CT-e real). O "simulado" é
sempre a referência de mercado cadastrada (BenchmarkCorredor) para o par
(hub alternativo → mesmo destino) — nunca um número inventado. Sem
referência cadastrada, a rota fica marcada `tem_referencia_alt=False` e SAI
do cálculo do delta total, na mesma disciplina do Benchmark OD ("sem
referência, sem score").

O prazo segue a mesma regra: o "atual" é a média observada
(data_entrega - data_saida) dos CT-e reais do corredor; o "simulado" só
existe se o corredor de referência tiver `prazo_dias_medio` cadastrado.

Amostra pequena (abaixo do threshold do MBL) marca `baixa_confianca=True` e
a rota nunca recebe recomendação de troca — só "dados_insuficientes". Isto
NÃO é uma recomendação de troca de hub, é um comparativo: a simulação não
inclui custo de implantação (armazém, contrato mínimo, mobilização), que
fica fora do escopo do dado disponível.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.application.dtos import SimulacaoHubResultado, SimulacaoHubRotaItem
from app.application.use_cases.benchmark_od import BenchmarkODUseCase
from app.application.use_cases.mbl import THRESHOLD_AMOSTRA_PADRAO
from app.domain.repositories import (
    IBenchmarkCorredorRepository,
    IClusterClienteRepository,
    ICTeRepository,
    IHubLogisticoRepository,
)

NOTA_ESCOPO = (
    "Simulação de custo e prazo a partir de referências de mercado por corredor. "
    "Não inclui custos de implantação do hub alternativo (armazém, contrato "
    "mínimo com transportadoras, mobilização) nem restrições operacionais."
)


class SimuladorHubUseCase:
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
        # reaproveita a resolução de hub/cluster e o cálculo de corredores
        # reais já existentes no Benchmark OD, em vez de duplicar a lógica.
        self._bod = BenchmarkODUseCase(cte_repo, cluster_repo, corredor_repo, hub_repo)

    def simular(
        self,
        empresa_id: int,
        hub_atual_codigo: str,
        hub_alt_codigo: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        threshold: int = THRESHOLD_AMOSTRA_PADRAO,
    ) -> SimulacaoHubResultado:
        hub_atual = self.hub_repo.get_by_codigo(empresa_id, hub_atual_codigo)
        hub_alt = self.hub_repo.get_by_codigo(empresa_id, hub_alt_codigo)
        if not hub_atual:
            raise ValueError(f"Hub atual '{hub_atual_codigo}' não cadastrado para esta empresa.")
        if not hub_alt:
            raise ValueError(f"Hub alternativo '{hub_alt_codigo}' não cadastrado para esta empresa.")
        if hub_atual.codigo == hub_alt.codigo:
            raise ValueError("Hub atual e hub alternativo não podem ser o mesmo.")

        resultado = SimulacaoHubResultado(
            hub_atual=hub_atual.codigo, hub_atual_nome=hub_atual.nome,
            hub_alt=hub_alt.codigo, hub_alt_nome=hub_alt.nome,
            periodo_inicio=data_inicio.isoformat() if data_inicio else None,
            periodo_fim=data_fim.isoformat() if data_fim else None,
            nota=NOTA_ESCOPO,
        )

        # corredores reais partindo do hub atual — mesmo dado (já resolvido e
        # agregado) usado pelo Benchmark OD para pontuar o hub atual hoje.
        corredores_atuais = [
            c for c in self._bod.corredores(empresa_id, data_inicio, data_fim)
            if c.hub_origem == hub_atual.codigo and c.peso_total > 0
        ]
        if not corredores_atuais:
            resultado.opera_no_hub_atual = False
            return resultado
        resultado.opera_no_hub_atual = True

        prazos_por_destino = self._prazo_real_por_destino(
            empresa_id, hub_atual.codigo, data_inicio, data_fim
        )

        rotas: List[SimulacaoHubRotaItem] = []
        ganho = perda = 0
        frete_comparavel = frete_simulado = 0.0
        prazos_atuais_pond: List[Tuple[float, float]] = []
        prazos_simulados_pond: List[Tuple[float, float]] = []

        for c in corredores_atuais:
            item = SimulacaoHubRotaItem(
                hub_destino=c.hub_destino, hub_destino_nome=c.hub_destino_nome,
                qtd_ctes=c.qtd_ctes, peso_total=c.peso_total,
                frete_atual_total=c.frete_total, frete_atual_rs_kg=c.frete_rs_kg,
                baixa_confianca=c.qtd_ctes < threshold,
            )
            prazo_atual, amostra_prazo = prazos_por_destino.get(c.hub_destino, (None, 0))
            item.prazo_atual_dias = prazo_atual
            item.amostra_prazo_atual = amostra_prazo

            ref = self.corredor_repo.get_by_corredor(empresa_id, hub_alt.codigo, c.hub_destino)
            if ref and ref.frete_kg_medio > 0:
                item.tem_referencia_alt = True
                item.frete_simulado_rs_kg = ref.frete_kg_medio
                item.frete_simulado_total = ref.frete_kg_medio * c.peso_total
                item.delta_custo_pct = (
                    (item.frete_simulado_total - c.frete_total) / c.frete_total * 100.0
                    if c.frete_total else 0.0
                )
                if ref.prazo_dias_medio > 0:
                    item.prazo_simulado_dias = ref.prazo_dias_medio
                    if prazo_atual is not None:
                        item.delta_prazo_dias = round(ref.prazo_dias_medio - prazo_atual, 1)

                frete_comparavel += c.frete_total
                frete_simulado += item.frete_simulado_total
                if item.frete_simulado_total < c.frete_total:
                    ganho += 1
                else:
                    perda += 1
                if prazo_atual is not None:
                    prazos_atuais_pond.append((prazo_atual, c.peso_total))
                if item.prazo_simulado_dias is not None:
                    prazos_simulados_pond.append((item.prazo_simulado_dias, c.peso_total))

                if item.baixa_confianca:
                    item.recomendacao = "dados_insuficientes"
                elif item.delta_custo_pct < 0:
                    item.recomendacao = "avaliar_alternativo"
                else:
                    item.recomendacao = "manter_atual"
            else:
                item.recomendacao = "dados_insuficientes"

            rotas.append(item)

        rotas.sort(key=lambda r: r.frete_atual_total, reverse=True)

        resultado.rotas = rotas
        resultado.qtd_rotas = len(rotas)
        resultado.rotas_com_referencia = sum(1 for r in rotas if r.tem_referencia_alt)
        resultado.rotas_sem_referencia = resultado.qtd_rotas - resultado.rotas_com_referencia
        resultado.rotas_com_ganho = ganho
        resultado.rotas_com_perda = perda
        resultado.frete_atual_total = sum(c.frete_total for c in corredores_atuais)
        resultado.frete_comparavel_total = frete_comparavel
        resultado.frete_simulado_total = frete_simulado
        resultado.delta_custo_total_pct = (
            (frete_simulado - frete_comparavel) / frete_comparavel * 100.0
            if frete_comparavel else 0.0
        )
        resultado.prazo_atual_medio_dias = self._media_ponderada(prazos_atuais_pond)
        resultado.prazo_simulado_medio_dias = self._media_ponderada(prazos_simulados_pond)
        return resultado

    # ------------------------------------------------------------------
    @staticmethod
    def _media_ponderada(pares: List[Tuple[float, float]]) -> Optional[float]:
        peso_total = sum(p for _, p in pares)
        if not peso_total:
            return None
        return round(sum(v * p for v, p in pares) / peso_total, 1)

    def _prazo_real_por_destino(
        self,
        empresa_id: int,
        hub_origem_codigo: str,
        data_inicio: Optional[date],
        data_fim: Optional[date],
    ) -> Dict[str, Tuple[float, int]]:
        """Prazo médio observado (data_entrega - data_saida), em dias, por hub
        de destino — só para CT-e cujo hub de origem resolvido é o hub atual.
        Reaproveita a mesma resolução hub→UF/município do Benchmark OD (regra
        de cluster da empresa; sem cadastro, a UF vira hub implícito)."""
        ctes = self.cte_repo.listar_prazos(empresa_id, data_inicio, data_fim)
        por_municipio, por_uf = self._bod._mapa_clusters(empresa_id)
        dias_por_destino: Dict[str, List[int]] = defaultdict(list)
        for cte in ctes:
            ho_cod, _ = BenchmarkODUseCase._resolver_hub(
                cte.uf_origem, cte.municipio_origem, por_municipio, por_uf
            )
            if ho_cod != hub_origem_codigo:
                continue
            hd_cod, _ = BenchmarkODUseCase._resolver_hub(
                cte.uf_destino, cte.municipio_destino, por_municipio, por_uf
            )
            if cte.data_saida and cte.data_entrega:
                dias = (cte.data_entrega - cte.data_saida).days
                if dias >= 0:
                    dias_por_destino[hd_cod].append(dias)
        return {
            destino: (round(sum(vs) / len(vs), 1), len(vs))
            for destino, vs in dias_por_destino.items()
        }
