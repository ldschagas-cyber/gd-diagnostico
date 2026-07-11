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
from app.application.use_cases.benchmark_v2 import mapa_percentis_mercado
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
        db=None,
    ):
        self.diagnostico = diagnostico_uc
        self.cte_repo = cte_repo
        self.benchmark_repo = benchmark_repo
        # Motor OD (V2.1). Opcional para retrocompatibilidade dos testes.
        self.od = benchmark_od_uc
        # Sessão de banco para ler a Matriz Benchmark (OD) — fonte única de
        # mercado em R$/kg (v6.9). Opcional para retrocompatibilidade dos
        # testes que não montam sessão; nesse caso a comparação de R$/kg
        # fica sem referência (Benchmark ausente), igual a região não
        # cadastrada.
        self.db = db
        self._mapa_v2_cache: Optional[dict] = None

    # ------------------------------------------------------------------
    def _ctes(self, empresa_id, data_inicio, data_fim, transportadora_id):
        ctes = self.cte_repo.list_by_empresa(
            empresa_id, data_inicio, data_fim, apenas_ativos=True
        )
        if transportadora_id:
            ctes = [c for c in ctes if c.transportadora_id == transportadora_id]
        return ctes

    def _mapa_v2(self) -> dict:
        if self._mapa_v2_cache is None:
            self._mapa_v2_cache = mapa_percentis_mercado(self.db) if self.db is not None else {}
        return self._mapa_v2_cache

    def _bench_kg(self, regiao) -> Optional[Benchmark]:
        """Referência de R$/kg (min=P10, médio=P50, max=P90) lida da Matriz
        Benchmark (OD) — fonte única de mercado (v6.9). Substitui a antiga
        leitura direta de ``benchmark_repo`` (tabela ``benchmarks``, V1).

        Nota: o schema da Matriz Benchmark (OD) só modela R$/kg — não há
        equivalente para % Frete/Mercadoria (ver ``benchmark_v2.py``), por
        isso as comparações de % continuam usando somente a classificação
        por faixa fixa (RN-14), sem valor numérico de referência."""
        chave = regiao.value if hasattr(regiao, "value") else str(regiao)
        v = self._mapa_v2().get(chave)
        if not v or not v.get("medio"):
            return None
        return Benchmark(
            regiao=regiao,
            frete_kg_min=v["min"], frete_kg_medio=v["medio"], frete_kg_max=v["max"],
        )

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

        # v6.9 — a Matriz Benchmark (OD) é a única fonte de referência de
        # R$/kg (Fase 1, Single Source of Truth). O antigo override pela
        # referência de corredor Hub-OD (BenchmarkCorredor, V1-OD) foi
        # removido — era uma segunda fonte de mercado concorrendo com a
        # Matriz Benchmark (OD); mantê-las as duas violaria a diretriz de
        # eliminar referências duplicadas.
        bench_kg = self._bench_kg(RegiaoBenchmarkEnum.NACIONAL)
        comp_kg = _comparar_kg(ind.frete_rs_kg, bench_kg)
        # % Frete/Mercadoria: sem equivalente no schema da Matriz Benchmark
        # (OD) — ver docstring de `_bench_kg`. Classificação por faixa fixa
        # (RN-14) continua funcionando; não há benchmark_min/medio/max.
        comp_pct = _comparar_pct(ind.frete_pct, None)

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
            # cada região comparada contra a Matriz Benchmark (OD) da própria região
            bench_kg = self._bench_kg(ind.macro_regiao)
            itens.append(
                BenchmarkRegionalItem(
                    macro_regiao=ind.macro_regiao,
                    frete_total=ind.frete_total,
                    peso_total=ind.peso_total,
                    qtd_ctes=ind.qtd_ctes,
                    frete_kg=_comparar_kg(ind.frete_rs_kg, bench_kg),
                    frete_pct=_comparar_pct(ind.frete_pct, None),
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
        # Transportadora é comparada contra a Matriz Benchmark (OD) NACIONAL (não é regional).
        bench_kg = self._bench_kg(RegiaoBenchmarkEnum.NACIONAL)
        itens: List[BenchmarkTransportadoraItem] = []
        for ind in indicadores:
            comp_kg = _comparar_kg(ind.frete_rs_kg, bench_kg)
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
                    frete_pct=_comparar_pct(ind.frete_pct, None),
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
            bench_kg = self._bench_kg(ind.macro_regiao)
            medio = bench_kg.frete_kg_medio if bench_kg else 0.0
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

        # v6.9 — a economia "oficial" do período vem exclusivamente da Matriz
        # Benchmark (OD) por região (acima), fonte única de mercado (Fase 1,
        # Single Source of Truth). A quebra por corredor Hub-OD legado
        # (BenchmarkCorredor) continua disponível como detalhamento
        # informativo, mas não sobrescreve mais o total oficial — antes disso
        # era uma segunda fonte de mercado concorrendo com a Matriz Benchmark
        # (OD), o que a diretriz de eliminar referências duplicadas proíbe.
        por_corredor = []
        if self.od is not None:
            por_corredor = self.od.economia_por_corredor(empresa_id, data_inicio, data_fim)

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
