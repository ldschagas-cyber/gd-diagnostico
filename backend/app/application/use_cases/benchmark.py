"""Caso de uso: análise de Benchmark Logístico.

Compara os indicadores da empresa (já calculados pelo DiagnosticoUseCase)
contra as referências de mercado cadastradas, gerando desvio percentual e
classificação automática, conforme a Especificação Funcional do Módulo
Benchmark Logístico (seções 7, 8, 10 e 12).

Reaproveita integralmente o cálculo de indicadores do diagnóstico — não
duplica regras de agregação.
"""
from datetime import date
from typing import List, Optional

from app.application.dtos import (
    BenchmarkNacional,
    BenchmarkRegionalItem,
    BenchmarkTransportadoraItem,
    ComparacaoBenchmark,
    DashboardExecutivo,
    EconomiaRegiaoItem,
    EvolucaoMensalItem,
    PotencialEconomia,
)
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.domain.entities import Benchmark, RegiaoBenchmarkEnum
from app.domain.repositories import IBenchmarkRepository, ICTeRepository


def _desvio_pct(valor: float, referencia: float) -> float:
    """Desvio percentual do valor em relação à referência (benchmark médio)."""
    if not referencia:
        return 0.0
    return (valor - referencia) / referencia * 100.0


def classificar_frete_pct(pct: float) -> str:
    """Classificação do frete sobre mercadoria — faixas fixas (seção 12)."""
    if pct <= 0:
        return "Sem dados"
    if pct <= 5:
        return "Excelente"
    if pct <= 8:
        return "Muito Bom"
    if pct <= 12:
        return "Atenção"
    if pct <= 18:
        return "Crítico"
    return "Muito Crítico"


def classificar_frete_kg(valor: float, benchmark_medio: float) -> str:
    """Classificação do custo por kg relativa ao benchmark médio (seção 12)."""
    if not benchmark_medio:
        return "Sem referência"
    if valor <= 0:
        return "Sem dados"
    ratio = valor / benchmark_medio
    if ratio <= 1.0:
        return "Excelente"      # até o benchmark médio
    if ratio <= 1.10:
        return "Bom"            # até 10% acima
    if ratio <= 1.20:
        return "Atenção"        # até 20% acima
    return "Crítico"            # acima de 20%


def _comparar_kg(valor: float, bench: Optional[Benchmark]) -> ComparacaoBenchmark:
    if not bench:
        return ComparacaoBenchmark(valor=valor)
    return ComparacaoBenchmark(
        valor=valor,
        benchmark_min=bench.frete_kg_min,
        benchmark_medio=bench.frete_kg_medio,
        benchmark_max=bench.frete_kg_max,
        desvio_pct=_desvio_pct(valor, bench.frete_kg_medio),
        classificacao=classificar_frete_kg(valor, bench.frete_kg_medio),
        dentro_faixa=valor <= bench.frete_kg_max if bench.frete_kg_max else False,
    )


def _comparar_pct(valor: float, bench: Optional[Benchmark]) -> ComparacaoBenchmark:
    if not bench:
        return ComparacaoBenchmark(valor=valor, classificacao=classificar_frete_pct(valor))
    return ComparacaoBenchmark(
        valor=valor,
        benchmark_min=bench.frete_pct_min,
        benchmark_medio=bench.frete_pct_medio,
        benchmark_max=bench.frete_pct_max,
        desvio_pct=_desvio_pct(valor, bench.frete_pct_medio),
        classificacao=classificar_frete_pct(valor),
        dentro_faixa=valor <= bench.frete_pct_max if bench.frete_pct_max else False,
    )


# Mapeia a classificação de custo/kg para o nível de custo (seção 10).
_NIVEL_CUSTO = {
    "Excelente": "Melhor custo",
    "Bom": "Melhor custo",
    "Atenção": "Custo médio",
    "Crítico": "Pior custo",
}


class BenchmarkUseCase:
    def __init__(
        self,
        diagnostico_uc: DiagnosticoUseCase,
        cte_repo: ICTeRepository,
        benchmark_repo: IBenchmarkRepository,
        benchmark_od_uc=None,
    ):
        self.diagnostico = diagnostico_uc
        self.cte_repo = cte_repo
        self.benchmark_repo = benchmark_repo
        # Motor OD (V2.1). Opcional para retrocompatibilidade dos testes.
        self.od = benchmark_od_uc

    # ------------------------------------------------------------------
    def _ctes(self, empresa_id, data_inicio, data_fim, transportadora_id):
        ctes = self.cte_repo.list_by_empresa(
            empresa_id, data_inicio, data_fim, apenas_ativos=True
        )
        if transportadora_id:
            ctes = [c for c in ctes if c.transportadora_id == transportadora_id]
        return ctes

    def _bench(self, regiao) -> Optional[Benchmark]:
        return self.benchmark_repo.get_by_regiao(regiao)

    # ------- Benchmark Nacional (seção 7) ------------------------------
    def nacional(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        transportadora_id: Optional[int] = None,
    ) -> BenchmarkNacional:
        ctes = self._ctes(empresa_id, data_inicio, data_fim, transportadora_id)
        ind = self.diagnostico._indicador_nacional(ctes)
        bench = self._bench(RegiaoBenchmarkEnum.NACIONAL)

        comp_kg = _comparar_kg(ind.frete_rs_kg, bench)
        comp_pct = _comparar_pct(ind.frete_pct, bench)

        # V2.1 — o benchmark nacional de R$/kg passa a ser a média ponderada
        # por volume das referências de corredor (sem viés de composição).
        # Sem filtro de transportadora, pois a ponderação é da malha OD.
        if self.od is not None and transportadora_id is None:
            ref_od = self.od.referencia_nacional_ponderada(empresa_id, data_inicio, data_fim)
            if ref_od > 0:
                comp_kg = ComparacaoBenchmark(
                    valor=ind.frete_rs_kg,
                    benchmark_min=comp_kg.benchmark_min,
                    benchmark_medio=ref_od,
                    benchmark_max=comp_kg.benchmark_max,
                    desvio_pct=_desvio_pct(ind.frete_rs_kg, ref_od),
                    classificacao=classificar_frete_kg(ind.frete_rs_kg, ref_od),
                    dentro_faixa=comp_kg.dentro_faixa,
                )

        return BenchmarkNacional(
            periodo_inicio=data_inicio.isoformat() if data_inicio else None,
            periodo_fim=data_fim.isoformat() if data_fim else None,
            valor_total_frete=ind.valor_total_frete,
            peso_total=ind.peso_total,
            valor_total_mercadoria=ind.valor_total_mercadoria,
            qtd_ctes=ind.qtd_ctes,
            frete_kg=comp_kg,
            frete_pct=comp_pct,
        )

    # ------- Benchmark Regional (seção 8) ------------------------------
    def regional(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        transportadora_id: Optional[int] = None,
    ) -> List[BenchmarkRegionalItem]:
        ctes = self._ctes(empresa_id, data_inicio, data_fim, transportadora_id)
        indicadores = self.diagnostico._indicadores_regionais(ctes)
        itens: List[BenchmarkRegionalItem] = []
        for ind in indicadores:
            # cada região comparada contra o benchmark da própria região
            bench = self._bench(ind.macro_regiao)
            itens.append(
                BenchmarkRegionalItem(
                    macro_regiao=ind.macro_regiao,
                    frete_total=ind.frete_total,
                    peso_total=ind.peso_total,
                    qtd_ctes=ind.qtd_ctes,
                    frete_kg=_comparar_kg(ind.frete_rs_kg, bench),
                    frete_pct=_comparar_pct(ind.frete_pct, bench),
                )
            )
        return itens

    # ------- Benchmark por Transportadora (seção 10) -------------------
    def transportadoras(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[BenchmarkTransportadoraItem]:
        ctes = self._ctes(empresa_id, data_inicio, data_fim, None)
        indicadores = self.diagnostico._indicadores_transportadora(ctes, empresa_id)
        # Transportadora é comparada contra o benchmark NACIONAL (não é regional).
        bench = self._bench(RegiaoBenchmarkEnum.NACIONAL)
        itens: List[BenchmarkTransportadoraItem] = []
        for ind in indicadores:
            comp_kg = _comparar_kg(ind.frete_rs_kg, bench)
            itens.append(
                BenchmarkTransportadoraItem(
                    transportadora_id=ind.transportadora_id,
                    nome=ind.nome,
                    frete_total=ind.frete_total,
                    peso_transportado=ind.peso_transportado,
                    participacao_pct=ind.participacao_pct,
                    qtd_ctes=ind.qtd_ctes,
                    nivel_custo=_NIVEL_CUSTO.get(comp_kg.classificacao, "Custo médio"),
                    frete_kg=comp_kg,
                    frete_pct=_comparar_pct(ind.frete_pct, bench),
                )
            )
        # ranking automático: menor custo por kg primeiro
        itens.sort(key=lambda i: (i.frete_kg.valor if i.frete_kg.valor > 0 else 9e9))
        return itens

    # ------- Potencial de Economia (seção 11) --------------------------
    def potencial_economia(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> PotencialEconomia:
        ctes = self._ctes(empresa_id, data_inicio, data_fim, None)
        regionais = self.diagnostico._indicadores_regionais(ctes)

        por_regiao: List[EconomiaRegiaoItem] = []
        economia_total = 0.0
        peso_total = 0.0
        frete_total = 0.0
        for ind in regionais:
            bench = self._bench(ind.macro_regiao)
            medio = bench.frete_kg_medio if bench else 0.0
            # Economia só quando o custo está ACIMA do benchmark médio.
            eco = max(0.0, ind.frete_rs_kg - medio) * ind.peso_total if medio else 0.0
            economia_total += eco
            peso_total += ind.peso_total
            frete_total += ind.frete_total
            por_regiao.append(
                EconomiaRegiaoItem(
                    macro_regiao=ind.macro_regiao,
                    frete_total=ind.frete_total,
                    peso_total=ind.peso_total,
                    frete_rs_kg=ind.frete_rs_kg,
                    benchmark_medio=medio,
                    economia=eco,
                )
            )

        economia_pct = (economia_total / frete_total * 100.0) if frete_total else 0.0

        # V2.1 — base de cálculo passa a ser o corredor OD. A visão regional
        # acima é mantida por compatibilidade, mas a economia "oficial" do
        # período vem da soma por corredor (sem viés de composição regional).
        por_corredor = []
        if self.od is not None:
            por_corredor = self.od.economia_por_corredor(empresa_id, data_inicio, data_fim)
            eco_od = sum(c.economia for c in por_corredor)
            if eco_od > 0 or any(c.tem_referencia for c in por_corredor):
                economia_total = eco_od
                economia_pct = (economia_total / frete_total * 100.0) if frete_total else 0.0

        # Nº de meses cobertos pelos dados (base da projeção).
        datas = [c.data_emissao for c in ctes if c.data_emissao]
        if datas:
            dias = (max(datas) - min(datas)).days + 1
            meses = max(1.0, dias / 30.0)
        else:
            meses = 1.0
        economia_mensal = economia_total / meses

        return PotencialEconomia(
            economia_total=economia_total,
            economia_pct=economia_pct,
            frete_total=frete_total,
            peso_total=peso_total,
            meses_periodo=round(meses, 1),
            economia_mensal=economia_mensal,
            proj_mensal=economia_mensal,
            proj_trimestral=economia_mensal * 3,
            proj_semestral=economia_mensal * 6,
            proj_anual=economia_mensal * 12,
            por_regiao=sorted(por_regiao, key=lambda r: r.economia, reverse=True),
            por_corredor=por_corredor,
        )

    # ------- Evolução mensal (Dashboard Executivo) ---------------------
    def evolucao_mensal(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[EvolucaoMensalItem]:
        from collections import defaultdict

        ctes = self._ctes(empresa_id, data_inicio, data_fim, None)
        meses = defaultdict(lambda: {"frete": 0.0, "peso": 0.0, "merc": 0.0})
        for c in ctes:
            if not c.data_emissao:
                continue
            chave = c.data_emissao.strftime("%Y-%m")
            meses[chave]["frete"] += c.valor_frete
            meses[chave]["peso"] += c.peso
            meses[chave]["merc"] += c.valor_mercadoria

        itens: List[EvolucaoMensalItem] = []
        for mes in sorted(meses.keys()):
            d = meses[mes]
            rs_kg = d["frete"] / d["peso"] if d["peso"] else 0.0
            pct = d["frete"] / d["merc"] * 100.0 if d["merc"] else 0.0
            itens.append(
                EvolucaoMensalItem(
                    mes=mes, frete_total=d["frete"], frete_rs_kg=rs_kg, frete_pct=pct
                )
            )
        return itens

    # ------- Dashboard Executivo (seção 13) ----------------------------
    def dashboard_executivo(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> DashboardExecutivo:
        nacional = self.nacional(empresa_id, data_inicio, data_fim, None)
        regionais = self.regional(empresa_id, data_inicio, data_fim, None)
        transportadoras = self.transportadoras(empresa_id, data_inicio, data_fim)
        economia = self.potencial_economia(empresa_id, data_inicio, data_fim)
        evolucao = self.evolucao_mensal(empresa_id, data_inicio, data_fim)

        # Benchmark regional médio ponderado pelo peso de cada região.
        peso_total = sum(r.peso_total for r in regionais)
        if peso_total:
            bench_reg = (
                sum(r.frete_kg.benchmark_medio * r.peso_total for r in regionais)
                / peso_total
            )
        else:
            bench_reg = 0.0

        # Melhor e pior transportadora (lista já ordenada por custo/kg asc).
        validas = [t for t in transportadoras if t.frete_kg.valor > 0]
        melhor = validas[0] if validas else None
        pior = validas[-1] if len(validas) > 1 else None

        return DashboardExecutivo(
            frete_kg_atual=nacional.frete_kg.valor,
            benchmark_nacional_kg=nacional.frete_kg.benchmark_medio,
            benchmark_regional_kg=bench_reg,
            economia_mensal=economia.economia_mensal,
            economia_total=economia.economia_total,
            melhor_transportadora=melhor.nome if melhor else "",
            melhor_transportadora_kg=melhor.frete_kg.valor if melhor else 0.0,
            pior_transportadora=pior.nome if pior else "",
            pior_transportadora_kg=pior.frete_kg.valor if pior else 0.0,
            evolucao=evolucao,
            regionais=regionais,
            transportadoras=transportadoras,
        )
