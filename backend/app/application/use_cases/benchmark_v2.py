"""Benchmark V2 — Freight Market Intelligence.

Resolve a referência de benchmark para um par Origem→Destino (por região),
aplicando a hierarquia de prioridade:

    1. benchmark_cliente (override ativo da empresa)      → vence
    2. benchmark_mercado, linha do setor da empresa        → fallback fino
    3. benchmark_mercado, linha "TODOS" (genérica)          → fallback amplo
    4. indisponível

O degrau 2 só existe quando há uma linha pesquisada especificamente para o
setor cadastrado em ``EmpresaModel.setor`` (mesmo vocabulário controlado —
SetorEnum); na ausência dela, cai para "TODOS" exatamente como o
comportamento anterior a essa dimensão.

E compara o valor de uma transportadora contra os percentis de mercado
(P50 mediana, P75) conforme as regras de uso do BID/Simulação.

Esta camada NÃO calcula benchmark observado (isso é a Fase 2); apenas lê as
referências já persistidas e resolve qual vale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    BenchmarkClienteModel,
    BenchmarkMercadoModel,
    BenchmarkObservadoModel,
    EmpresaModel,
)


@dataclass
class ReferenciaBenchmark:
    """Referência resolvida para um par OD."""
    origem_regiao: str
    destino_regiao: str
    fonte: str                       # CLIENTE | MERCADO | MERCADO_LEGADO | INDISPONIVEL
    setor: str = "TODOS"             # setor da linha efetivamente usada (ou "TODOS" no fallback genérico)
    rs_kg_p10: float = 0.0
    rs_kg_p25: float = 0.0
    rs_kg_p50: float = 0.0           # mediana — referência principal
    rs_kg_p75: float = 0.0
    rs_kg_p90: float = 0.0
    disponivel: bool = True


@dataclass
class ComparacaoMercado:
    """Resultado de comparar um valor (R$/kg) contra a referência de mercado."""
    valor: float
    referencia: ReferenciaBenchmark
    delta_p50_pct: float = 0.0       # quanto acima(+)/abaixo(-) da mediana
    delta_p75_pct: float = 0.0
    faixa: str = "SEM_REFERENCIA"    # ABAIXO_P50 | ENTRE_P50_P75 | ACIMA_P75 | SEM_REFERENCIA


def _pct(valor: float, base: float) -> float:
    return round((valor - base) / base * 100, 2) if base else 0.0


# ─────────────────────────────────────────────────────────────────────────
# Consolidação SSoT (v6.9 — Fase 1 da refatoração do Benchmark Logístico):
# a Matriz Benchmark (OD) / benchmark_mercado passa a ser a única fonte de
# referência de mercado em R$/kg lida pelos demais módulos (Diagnóstico,
# Benchmark Logístico, Score, Insights, Oportunidades, Assistente IA).
# Estas funções substituem as leituras diretas do antigo `BenchmarkModel`
# (V1, tabela `benchmarks`) por região.
#
# Limitação conhecida: `benchmark_mercado` só modela R$/kg (percentis
# P10-P90). O antigo V1 também trazia uma faixa de % Frete/Mercadoria
# (frete_pct_min/medio/max), que não tem equivalente no schema V2 — os
# consumidores de %Frete continuam usando a classificação por faixa fixa
# (RN-14), sem um "benchmark de %" numérico. Ver relatório de Fase 1.
# ─────────────────────────────────────────────────────────────────────────
_PERCENTIS = ("p10", "p25", "p50", "p75", "p90")


def mapa_percentis_mercado(db: Session) -> dict[str, dict[str, float]]:
    """Percentis de referência (P10-P90) em R$/kg por macrorregião de
    destino, agregando todos os pares OD da Matriz Benchmark (OD) que
    terminam nessa região. Inclui a chave especial "NACIONAL" com a média
    de todo o país. Cada entrada traz as chaves "p10".."p90" e os apelidos
    "min"/"medio"/"max" (= p10/p50/p90), compatíveis com o antigo
    ``Benchmark.frete_kg_min/medio/max`` (V1).

    Só considera linhas com ``setor == "TODOS"`` — esta é a referência
    genérica consumida por Score Logístico, Insights, Oportunidades e
    Assistente IA (nenhum tem empresa/setor no contexto desta chamada);
    misturar linhas pesquisadas para um setor específico aqui inflaria ou
    distorceria a média nacional/regional para todo mundo."""
    rows = db.execute(
        select(BenchmarkMercadoModel).where(BenchmarkMercadoModel.setor == "TODOS")
    ).scalars().all()
    grupos: dict[str, dict[str, list[float]]] = {}
    todos = {p: [] for p in _PERCENTIS}
    for r in rows:
        if not r.rs_kg_p50:
            continue
        g = grupos.setdefault(r.destino_regiao, {p: [] for p in _PERCENTIS})
        for p in _PERCENTIS:
            valor = getattr(r, f"rs_kg_{p}")
            g[p].append(valor)
            todos[p].append(valor)

    def _media(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def _linha(v: dict[str, list[float]]) -> dict[str, float]:
        linha = {p: _media(v[p]) for p in _PERCENTIS}
        linha["min"], linha["medio"], linha["max"] = linha["p10"], linha["p50"], linha["p90"]
        return linha

    resultado = {regiao: _linha(v) for regiao, v in grupos.items()}
    resultado["NACIONAL"] = _linha(todos)
    return resultado


def mapa_medio_por_regiao_destino(db: Session) -> dict[str, float]:
    """Mapa macrorregião de destino → R$/kg de referência (P50 médio),
    substituindo o antigo ``{b.regiao: b.frete_kg_medio for b in ...}`` (V1)
    usado por Score Logístico, Insights, Oportunidades e Assistente IA."""
    return {k: v["medio"] for k, v in mapa_percentis_mercado(db).items()}


def media_nacional_rs_kg_p50(db: Session) -> float:
    """Média nacional de R$/kg (P50) — substitui
    ``func.avg(BenchmarkModel.frete_kg_medio)`` (V1)."""
    return mapa_percentis_mercado(db).get("NACIONAL", {}).get("medio", 0.0)


def destino_regiao_de_grupo(tipo_agrupamento: str, valor_grupo: str) -> Optional[str]:
    """Mapeia um grupo do escopo do BID para a macrorregião de destino, quando
    possível. REGIAO já é a região; UF é convertida; demais agrupamentos
    (FILIAL/TRANSPORTADORA/FAIXA_PESO) não têm destino OD definido."""
    from app.infrastructure.parsers.macro_regiao import macro_por_uf
    t = (tipo_agrupamento or "").strip().upper()
    v = (valor_grupo or "").strip()
    if t == "REGIAO":
        return v.upper()
    if t == "UF":
        r = macro_por_uf(v)
        return r.value if r else None
    return None


class BenchmarkV2UseCase:
    def __init__(self, db: Session):
        self.db = db

    # ── Resolução com fallback cliente → mercado ──────────────────────────
    def resolver(
        self,
        empresa_id: int,
        origem_regiao: str,
        destino_regiao: str,
        modal: str = "",
    ) -> ReferenciaBenchmark:
        o = (origem_regiao or "").strip().upper()
        d = (destino_regiao or "").strip().upper()

        # 1. Override do cliente (empresa), se ativo
        cli = self.db.execute(
            select(BenchmarkClienteModel).where(
                BenchmarkClienteModel.empresa_id == empresa_id,
                BenchmarkClienteModel.origem_regiao == o,
                BenchmarkClienteModel.destino_regiao == d,
                BenchmarkClienteModel.modal == (modal or ""),
                BenchmarkClienteModel.ativo.is_(True),
            )
        ).scalars().first()
        if cli:
            v = cli.rs_kg_medio
            # Cliente informa só um médio; usamos como P50 e replicamos nos demais
            return ReferenciaBenchmark(
                origem_regiao=o, destino_regiao=d, fonte="CLIENTE",
                rs_kg_p10=v, rs_kg_p25=v, rs_kg_p50=v, rs_kg_p75=v, rs_kg_p90=v,
            )

        # 2. Mercado (source of truth global). Tenta primeiro a linha
        #    pesquisada para o setor da empresa; sem ela, cai para "TODOS"
        #    (referência genérica — comportamento anterior a esta dimensão).
        #    Dentro de cada setor, preferimos a linha mais genérica
        #    (tipo_operacao TODOS, sem faixa de peso) quando houver várias.
        setor_empresa = self.db.execute(
            select(EmpresaModel.setor).where(EmpresaModel.id == empresa_id)
        ).scalar()
        setores_tentativa = list(dict.fromkeys(s for s in (setor_empresa, "TODOS") if s))

        for setor in setores_tentativa:
            merc = self.db.execute(
                select(BenchmarkMercadoModel).where(
                    BenchmarkMercadoModel.origem_regiao == o,
                    BenchmarkMercadoModel.destino_regiao == d,
                    BenchmarkMercadoModel.setor == setor,
                ).order_by(
                    BenchmarkMercadoModel.faixa_peso_max.asc(),
                )
            ).scalars().first()
            if merc:
                return ReferenciaBenchmark(
                    origem_regiao=o, destino_regiao=d, fonte=merc.fonte, setor=merc.setor,
                    rs_kg_p10=merc.rs_kg_p10, rs_kg_p25=merc.rs_kg_p25,
                    rs_kg_p50=merc.rs_kg_p50, rs_kg_p75=merc.rs_kg_p75,
                    rs_kg_p90=merc.rs_kg_p90,
                )

        # 3. Sem referência
        return ReferenciaBenchmark(
            origem_regiao=o, destino_regiao=d, fonte="INDISPONIVEL", disponivel=False,
        )

    # ── Comparação de um valor vs mercado (P50/P75) ───────────────────────
    def comparar(
        self,
        empresa_id: int,
        origem_regiao: str,
        destino_regiao: str,
        valor_rs_kg: float,
        modal: str = "",
    ) -> ComparacaoMercado:
        ref = self.resolver(empresa_id, origem_regiao, destino_regiao, modal)
        if not ref.disponivel:
            return ComparacaoMercado(valor=valor_rs_kg, referencia=ref)

        d50 = _pct(valor_rs_kg, ref.rs_kg_p50)
        d75 = _pct(valor_rs_kg, ref.rs_kg_p75)
        if valor_rs_kg <= ref.rs_kg_p50:
            faixa = "ABAIXO_P50"          # competitivo
        elif valor_rs_kg <= ref.rs_kg_p75:
            faixa = "ENTRE_P50_P75"       # dentro do mercado
        else:
            faixa = "ACIMA_P75"           # caro
        return ComparacaoMercado(
            valor=valor_rs_kg, referencia=ref,
            delta_p50_pct=d50, delta_p75_pct=d75, faixa=faixa,
        )

    # ── Referência de mercado por REGIÃO DE DESTINO (agregada) ────────────
    def referencia_destino(self, destino_regiao: str) -> ReferenciaBenchmark:
        """Para um BID agrupado por destino, a referência de mercado é a média
        dos pares OD que terminam naquela região (não há origem fixa no grupo,
        nem empresa para resolver setor — usa sempre a linha genérica
        "TODOS", nunca mistura com linhas pesquisadas por setor)."""
        d = (destino_regiao or "").strip().upper()
        rows = self.db.execute(
            select(BenchmarkMercadoModel).where(
                BenchmarkMercadoModel.destino_regiao == d,
                BenchmarkMercadoModel.setor == "TODOS",
            )
        ).scalars().all()
        if not rows:
            return ReferenciaBenchmark(
                origem_regiao="*", destino_regiao=d, fonte="INDISPONIVEL", disponivel=False,
            )

        def media(attr):
            vals = [getattr(r, attr) for r in rows if getattr(r, attr)]
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        return ReferenciaBenchmark(
            origem_regiao="*", destino_regiao=d, fonte="MERCADO",
            rs_kg_p10=media("rs_kg_p10"), rs_kg_p25=media("rs_kg_p25"),
            rs_kg_p50=media("rs_kg_p50"), rs_kg_p75=media("rs_kg_p75"),
            rs_kg_p90=media("rs_kg_p90"),
        )

    @staticmethod
    def faixa_de(valor: float, p50: float, p75: float) -> str:
        if not p50:
            return "SEM_REFERENCIA"
        if valor <= p50:
            return "ABAIXO_P50"
        if valor <= p75:
            return "ENTRE_P50_P75"
        return "ACIMA_P75"

    # ── Real (observado) vs Mercado, por OD ───────────────────────────────
    def observado_vs_mercado(
        self,
        empresa_id: int,
        periodo_ref: str = "TOTAL",
    ) -> list[dict]:
        """Para cada OD que a empresa opera (observado), confronta o P50 real
        com o P50 de mercado, indicando se a operação está acima/abaixo."""
        obs = self.db.execute(
            select(BenchmarkObservadoModel).where(
                BenchmarkObservadoModel.empresa_id == empresa_id,
                BenchmarkObservadoModel.periodo_ref == periodo_ref,
            )
        ).scalars().all()

        linhas = []
        for o in obs:
            ref = self.resolver(empresa_id, o.origem_regiao, o.destino_regiao)
            p50_merc = ref.rs_kg_p50 if ref.disponivel else 0.0
            delta = _pct(o.rs_kg_p50, p50_merc) if p50_merc else 0.0
            linhas.append({
                "origem_regiao": o.origem_regiao,
                "destino_regiao": o.destino_regiao,
                "qtd_embarques": o.qtd_embarques,
                "real_p50": o.rs_kg_p50,
                "mercado_p50": p50_merc,
                "fonte_mercado": ref.fonte,
                "delta_pct": delta,
                "situacao": (
                    "SEM_MERCADO" if not ref.disponivel
                    else "ACIMA_MERCADO" if o.rs_kg_p50 > p50_merc
                    else "ABAIXO_MERCADO"
                ),
            })
        return linhas
