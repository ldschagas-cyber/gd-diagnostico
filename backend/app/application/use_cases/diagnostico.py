"""Caso de uso: cálculo do diagnóstico logístico (RF011 a RF015).

Indicadores nacionais, regionais, por transportadora e de prazo, com
comparação às metas e geração de oportunidades de melhoria.
"""
from collections import defaultdict
from datetime import date
from typing import List, Optional

from app.application.dtos import (
    Diagnostico,
    EvolucaoMensalItem,
    IndicadorNacional,
    IndicadorPrazo,
    IndicadorRegional,
    IndicadorTransportadora,
)
from app.domain.entities import CTe, MacroRegiaoEnum
from app.domain.repositories import (
    ICTeRepository,
    IEmpresaRepository,
    IMetaNacionalRepository,
    IMetaRegionalRepository,
    ITransportadoraRepository,
)


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


class DiagnosticoUseCase:
    def __init__(
        self,
        cte_repo: ICTeRepository,
        empresa_repo: IEmpresaRepository,
        transp_repo: ITransportadoraRepository,
        meta_nac_repo: IMetaNacionalRepository,
        meta_reg_repo: IMetaRegionalRepository,
        benchmark_repo=None,
    ):
        self.cte_repo = cte_repo
        self.empresa_repo = empresa_repo
        self.transp_repo = transp_repo
        self.meta_nac_repo = meta_nac_repo
        self.meta_reg_repo = meta_reg_repo
        # Opcional: usado apenas para a referência de mercado do % Frete/Mercadoria.
        self.benchmark_repo = benchmark_repo

    def gerar(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Diagnostico:
        empresa = self.empresa_repo.get(empresa_id)
        if not empresa:
            raise ValueError("Empresa não encontrada.")

        diag = Diagnostico(
            empresa_id=empresa_id,
            empresa_nome=empresa.nome_fantasia or empresa.razao_social,
            periodo_inicio=data_inicio.isoformat() if data_inicio else None,
            periodo_fim=data_fim.isoformat() if data_fim else None,
        )

        # Agregações pesadas via SQL — sem materializar todos os CT-es em Python
        diag.nacional = self._indicador_nacional_sql(empresa_id, data_inicio, data_fim)
        diag.regionais = self._indicadores_regionais_sql(empresa_id, data_inicio, data_fim)
        diag.transportadoras = self._indicadores_transportadora_sql(
            empresa_id, data_inicio, data_fim
        )
        # Prazo/OTIF e composição ainda precisam dos registros individuais (JSON / datas)
        ctes_prazo = self.cte_repo.listar_prazos(empresa_id, data_inicio, data_fim)
        diag.prazos = self._indicadores_prazo(ctes_prazo)
        ctes_comp = self.cte_repo.list_by_empresa(
            empresa_id, data_inicio, data_fim, apenas_ativos=True
        )
        diag.composicao_frete = self._composicao_frete(ctes_comp)
        diag.oportunidades = self._oportunidades(diag)
        # Série mensal do Frete Total (sparkline): últimos 6 meses, apenas CT-es
        # ATIVOS. Independe do filtro de período da tela — é a tendência de gasto.
        diag.evolucao_frete = self._evolucao_frete(empresa_id)
        return diag

    def _evolucao_frete(
        self, empresa_id: int, meses: int = 6
    ) -> List[EvolucaoMensalItem]:
        """Série mensal do Frete Total (apenas ativos) para o sparkline do card.

        Agregação no banco (ver ``CTeRepository.frete_mensal_ativos``); só o
        ``frete_total`` é usado pelo sparkline. Ordem cronológica.
        """
        linhas = self.cte_repo.frete_mensal_ativos(empresa_id, meses=meses)
        return [
            EvolucaoMensalItem(mes=l["competencia"], frete_total=l["frete_total"])
            for l in linhas
        ]

    # ── Métodos de agregação SQL (performance) ─────────────────────────────
    def _indicador_nacional_sql(
        self, empresa_id: int, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> IndicadorNacional:
        # Totais financeiros consideram apenas CT-es ATIVOS (cancelados excluídos).
        ag = self.cte_repo.agregar_nacional(empresa_id, data_inicio, data_fim,
                                            apenas_ativos=True)
        ind = IndicadorNacional(
            valor_total_frete=ag["valor_total_frete"],
            valor_total_mercadoria=ag["valor_total_mercadoria"],
            peso_total=ag["peso_total"],
            qtd_ctes=ag["qtd_ctes"],
        )
        ind.frete_rs_kg = _div(ind.valor_total_frete, ind.peso_total)
        ind.frete_pct = _div(ind.valor_total_frete, ind.valor_total_mercadoria) * 100
        # Custo Médio por Kg (MELHORIA 7) = frete ativo / peso ativo.
        ind.custo_medio_kg = ind.frete_rs_kg

        # Situação: emitidos / ativos / cancelados (MELHORIAS 3 e 4).
        sit = self.cte_repo.contar_situacao_nacional(empresa_id, data_inicio, data_fim)
        ind.qtd_ctes_emitidos = sit["emitidos"]
        ind.qtd_ctes_ativos = sit["ativos"]
        ind.qtd_ctes_cancelados = sit["cancelados"]
        ind.pct_cancelados = _div(sit["cancelados"], sit["emitidos"]) * 100

        meta = self.meta_nac_repo.get()
        if meta:
            ind.meta_rs_kg = meta.meta_rs_kg
            ind.meta_pct = meta.meta_pct_frete
            ind.desvio_rs_kg = ind.frete_rs_kg - meta.meta_rs_kg
            ind.desvio_pct = ind.frete_pct - meta.meta_pct_frete
            # Referência ideal (até X%) — usa a meta cadastrada (MELHORIA 6).
            if meta.meta_pct_frete:
                ind.ref_pct_ideal_max = meta.meta_pct_frete

        # Referência de mercado (X% a X%) — agrega os parâmetros de benchmark
        # já existentes na aplicação. Parametrizável no cadastro de benchmarks.
        self._referencia_mercado_pct(ind)
        return ind

    def _referencia_mercado_pct(self, ind: IndicadorNacional) -> None:
        """Preenche a faixa de mercado do % Frete/Mercadoria a partir dos
        benchmarks cadastrados (MELHORIA 6). Silencioso quando não há benchmark
        ou repositório disponível."""
        if not self.benchmark_repo:
            return
        try:
            linhas = self.benchmark_repo.list()
        except Exception:  # noqa: BLE001
            return
        mins = [b.frete_pct_min for b in linhas if getattr(b, "frete_pct_min", 0)]
        maxs = [b.frete_pct_max for b in linhas if getattr(b, "frete_pct_max", 0)]
        if mins:
            ind.ref_pct_mercado_min = round(min(mins), 2)
        if maxs:
            ind.ref_pct_mercado_max = round(max(maxs), 2)

    def _indicadores_regionais_sql(
        self, empresa_id: int, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[IndicadorRegional]:
        rows = self.cte_repo.agregar_por_regiao(empresa_id, data_inicio, data_fim)
        metas = {m.macro_regiao.value: m for m in self.meta_reg_repo.list()}
        resultado: List[IndicadorRegional] = []
        for r in rows:
            macro = r["macro_regiao"]
            frete = r["frete_total"]
            merc = r["mercadoria_total"]
            peso = r["peso_total"]
            ind = IndicadorRegional(
                macro_regiao=macro, frete_total=frete, mercadoria_total=merc,
                peso_total=peso, frete_rs_kg=_div(frete, peso),
                frete_pct=_div(frete, merc) * 100, qtd_ctes=r["qtd_ctes"],
            )
            meta = metas.get(macro)
            if meta:
                ind.meta_rs_kg = meta.meta_rs_kg
                ind.meta_pct = meta.meta_pct_frete
            resultado.append(ind)
        resultado.sort(key=lambda x: x.frete_total, reverse=True)
        return resultado

    def _indicadores_transportadora_sql(
        self, empresa_id: int, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[IndicadorTransportadora]:
        rows = self.cte_repo.agregar_por_transportadora(empresa_id, data_inicio, data_fim)
        total_frete = sum(r["frete_total"] for r in rows) or 1.0
        # Busca nomes no escopo da empresa (uma query, sem N+1)
        nomes = {t.id: (t.nome_fantasia or t.razao_social)
                 for t in self.transp_repo.list_by_empresa(empresa_id, limit=1000)}
        resultado: List[IndicadorTransportadora] = []
        for r in rows:
            tid = r["transportadora_id"]
            frete = r["frete_total"]
            peso = r["peso_total"]
            merc = r["mercadoria_total"]
            resultado.append(IndicadorTransportadora(
                transportadora_id=tid,
                nome=nomes.get(tid, "Não identificada") if tid else "Não identificada",
                frete_total=frete, mercadoria_total=merc,
                participacao_pct=_div(frete, total_frete) * 100,
                frete_rs_kg=_div(frete, peso),
                frete_pct=_div(frete, merc) * 100,
                custo_medio_entrega=_div(frete, r["qtd_ctes"]),
                qtd_ctes=r["qtd_ctes"], peso_transportado=peso,
            ))
        resultado.sort(key=lambda x: x.frete_total, reverse=True)
        return resultado

    # ---- RF011 ---------------------------------------------------------
    def _indicador_nacional(self, ctes: List[CTe]) -> IndicadorNacional:
        ind = IndicadorNacional(qtd_ctes=len(ctes))
        ind.valor_total_frete = sum(c.valor_frete for c in ctes)
        ind.valor_total_mercadoria = sum(c.valor_mercadoria for c in ctes)
        ind.peso_total = sum(c.peso for c in ctes)
        ind.frete_rs_kg = _div(ind.valor_total_frete, ind.peso_total)
        ind.frete_pct = _div(ind.valor_total_frete, ind.valor_total_mercadoria) * 100

        meta = self.meta_nac_repo.get()
        if meta:
            ind.meta_rs_kg = meta.meta_rs_kg
            ind.meta_pct = meta.meta_pct_frete
            ind.desvio_rs_kg = ind.frete_rs_kg - meta.meta_rs_kg
            ind.desvio_pct = ind.frete_pct - meta.meta_pct_frete
        return ind

    # ---- RF012 ---------------------------------------------------------
    def _indicadores_regionais(self, ctes: List[CTe]) -> List[IndicadorRegional]:
        grupos: dict[str, list[CTe]] = defaultdict(list)
        for c in ctes:
            macro = c.macro_regiao_destino.value if c.macro_regiao_destino else "INDEFINIDA"
            grupos[macro].append(c)

        metas = {m.macro_regiao.value: m for m in self.meta_reg_repo.list()}
        resultado: List[IndicadorRegional] = []
        for macro, lista in grupos.items():
            frete = sum(c.valor_frete for c in lista)
            merc = sum(c.valor_mercadoria for c in lista)
            peso = sum(c.peso for c in lista)
            ind = IndicadorRegional(
                macro_regiao=macro, frete_total=frete, mercadoria_total=merc,
                peso_total=peso, frete_rs_kg=_div(frete, peso),
                frete_pct=_div(frete, merc) * 100, qtd_ctes=len(lista),
            )
            meta = metas.get(macro)
            if meta:
                ind.meta_rs_kg = meta.meta_rs_kg
                ind.meta_pct = meta.meta_pct_frete
            resultado.append(ind)
        resultado.sort(key=lambda x: x.frete_total, reverse=True)
        return resultado

    # ---- RF013 ---------------------------------------------------------
    def _indicadores_transportadora(self, ctes: List[CTe], empresa_id: int) -> List[IndicadorTransportadora]:
        total_frete = sum(c.valor_frete for c in ctes) or 1.0
        grupos: dict[Optional[int], list[CTe]] = defaultdict(list)
        for c in ctes:
            grupos[c.transportadora_id].append(c)

        # Busca nomes apenas das transportadoras da empresa (isolado + sem N+1 global)
        nomes = {t.id: (t.nome_fantasia or t.razao_social)
                 for t in self.transp_repo.list_by_empresa(empresa_id, limit=1000)}

        resultado: List[IndicadorTransportadora] = []
        for tid, lista in grupos.items():
            frete = sum(c.valor_frete for c in lista)
            peso = sum(c.peso for c in lista)
            merc = sum(c.valor_mercadoria for c in lista)
            resultado.append(IndicadorTransportadora(
                transportadora_id=tid,
                nome=nomes.get(tid, "Não identificada") if tid else "Não identificada",
                frete_total=frete,
                mercadoria_total=merc,
                participacao_pct=_div(frete, total_frete) * 100,
                frete_rs_kg=_div(frete, peso),
                frete_pct=_div(frete, merc) * 100,
                custo_medio_entrega=_div(frete, len(lista)),
                qtd_ctes=len(lista),
                peso_transportado=peso,
            ))
        resultado.sort(key=lambda x: x.frete_total, reverse=True)
        return resultado

    def _composicao_frete(self, ctes: List[CTe]) -> dict:
        """Soma os componentes do frete (Frete Peso, Pedágio, GRIS...) de todos os CT-es."""
        comp: dict = {}
        for c in ctes:
            for categoria, valor in (c.composicao_frete or {}).items():
                comp[categoria] = round(comp.get(categoria, 0.0) + float(valor or 0), 2)
        return {k: v for k, v in comp.items() if v > 0}

    # ---- RF014 ---------------------------------------------------------
    def _indicadores_prazo(self, ctes: List[CTe]) -> List[IndicadorPrazo]:
        metas = {m.macro_regiao.value: m for m in self.meta_reg_repo.list()}
        grupos: dict[str, list[CTe]] = defaultdict(list)
        for c in ctes:
            if c.data_saida and c.data_entrega:
                macro = c.macro_regiao_destino.value if c.macro_regiao_destino else "INDEFINIDA"
                grupos[macro].append(c)

        resultado: List[IndicadorPrazo] = []
        for macro, lista in grupos.items():
            prazos = [(c.data_entrega - c.data_saida).days for c in lista]
            prazo_medio = _div(sum(prazos), len(prazos))
            meta = metas.get(macro)
            prazo_meta = meta.prazo_medio_meta if meta else None
            no_prazo = sum(
                1 for p in prazos
                if prazo_meta is None or p <= prazo_meta
            )
            atraso = len(prazos) - no_prazo
            resultado.append(IndicadorPrazo(
                macro_regiao=macro,
                prazo_medio=round(prazo_medio, 1),
                entregas_no_prazo=no_prazo,
                entregas_atraso=atraso,
                sla_pct=_div(no_prazo, len(prazos)) * 100,
                prazo_meta=prazo_meta,
            ))
        resultado.sort(key=lambda x: x.macro_regiao)
        return resultado

    # ---- Oportunidades de melhoria (RF015) -----------------------------
    def _oportunidades(self, diag: Diagnostico) -> List[str]:
        op: List[str] = []
        n = diag.nacional
        if n.desvio_rs_kg is not None and n.desvio_rs_kg > 0:
            op.append(
                f"Frete nacional R$/kg ({n.frete_rs_kg:.2f}) está "
                f"R$ {n.desvio_rs_kg:.2f}/kg acima da meta ({n.meta_rs_kg:.2f})."
            )
        if n.desvio_pct is not None and n.desvio_pct > 0:
            op.append(
                f"Frete sobre mercadoria ({n.frete_pct:.2f}%) excede a meta "
                f"({n.meta_pct:.2f}%) em {n.desvio_pct:.2f} p.p."
            )
        for r in diag.regionais:
            if r.meta_rs_kg and r.frete_rs_kg > r.meta_rs_kg:
                op.append(
                    f"Região {r.macro_regiao}: R$/kg {r.frete_rs_kg:.2f} "
                    f"acima da meta regional {r.meta_rs_kg:.2f}."
                )
        for p in diag.prazos:
            if p.prazo_meta and p.prazo_medio > p.prazo_meta:
                op.append(
                    f"Região {p.macro_regiao}: prazo médio {p.prazo_medio} dias "
                    f"acima da meta de {p.prazo_meta} dias (SLA {p.sla_pct:.1f}%)."
                )
        # Concentração em transportadora
        if diag.transportadoras and diag.transportadoras[0].participacao_pct > 50:
            t = diag.transportadoras[0]
            op.append(
                f"Concentração de {t.participacao_pct:.1f}% do frete em "
                f"'{t.nome}' — risco de dependência; avaliar diversificação."
            )
        if not op:
            op.append("Nenhum desvio relevante frente às metas cadastradas.")
        return op
