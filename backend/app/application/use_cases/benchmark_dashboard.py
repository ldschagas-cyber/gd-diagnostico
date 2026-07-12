"""Indicadores transversais e telas novas do Benchmark Logístico (v6.9 — Fase 1).

Alimentado exclusivamente pela Matriz Benchmark (OD) (``benchmark_mercado``,
via ``BenchmarkV2UseCase``/``mapa_percentis_mercado``) — fonte única de
mercado (Single Source of Truth). Não introduz nenhum cálculo de negócio
novo: reaproveita ``BenchmarkObservadoUseCase`` (percentis reais do cliente)
e ``BenchmarkV2UseCase`` (resolução de referência CLIENTE > MERCADO) já
existentes, apenas compondo o resultado para as novas telas:

- Comparativo de Mercado (cliente × mercado, P10-P90, por Nacional/Região/Corredor)
- Simulador de economia por cenário percentílico (P50/P25/P10)
- Índice de Confiabilidade e Cobertura do Benchmark (indicadores transversais)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import BenchmarkMercadoModel, CTeModel
from app.infrastructure.parsers.macro_regiao import macro_por_uf
from app.application.use_cases.benchmark_v2 import BenchmarkV2UseCase, _pct
from app.application.use_cases.benchmark_observado import BenchmarkObservadoUseCase

_CENARIOS = {"P50": "rs_kg_p50", "P25": "rs_kg_p25", "P10": "rs_kg_p10"}

# Amostra mínima para classificar a confiabilidade do benchmark (RN local a
# esta tela — mesma ordem de grandeza do limiar já usado pelo MBL, RN-31,
# adaptado à escala de CT-es em vez de segmentos).
_CONFIAB_ALTA = 1000
_CONFIAB_MEDIA = 100


def _regiao_od(cte: CTeModel) -> tuple[Optional[str], Optional[str]]:
    o = macro_por_uf(cte.uf_origem)
    o_val = o.value if o else None
    if cte.macro_regiao_destino:
        d_val = cte.macro_regiao_destino.strip().upper()
    else:
        d = macro_por_uf(cte.uf_destino)
        d_val = d.value if d else None
    return o_val, d_val


class BenchmarkDashboardUseCase:
    def __init__(self, db: Session, cte_repo):
        self.db = db
        self.cte_repo = cte_repo
        self.v2 = BenchmarkV2UseCase(db)
        self.observado = BenchmarkObservadoUseCase(db)

    def _ctes(self, empresa_id: int, data_inicio, data_fim):
        return self.cte_repo.list_by_empresa(empresa_id, data_inicio, data_fim, apenas_ativos=True)

    # ── Índice de Confiabilidade (indicador transversal, seção 9) ─────────
    def confiabilidade(
        self, empresa_id: int, data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    ) -> dict:
        qtd = len(self._ctes(empresa_id, data_inicio, data_fim))
        if qtd >= _CONFIAB_ALTA:
            nivel, mensagem = "Alta", "Benchmark robusto."
        elif qtd >= _CONFIAB_MEDIA:
            nivel, mensagem = "Média", "Benchmark representativo; amostra moderada."
        else:
            nivel, mensagem = "Baixa", "Utilizar interpretação com cautela."
        return {"nivel": nivel, "qtd_ctes": qtd, "mensagem": mensagem}

    # ── Cobertura do Benchmark (indicador transversal, seção 9) ───────────
    def cobertura(
        self, empresa_id: int, data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    ) -> dict:
        ctes = self._ctes(empresa_id, data_inicio, data_fim)
        pares_mercado = set(
            self.db.execute(
                select(BenchmarkMercadoModel.origem_regiao, BenchmarkMercadoModel.destino_regiao)
            ).all()
        )
        total_ctes = len(ctes)
        total_peso = sum(c.peso or 0.0 for c in ctes)
        ctes_cobertos = 0
        peso_coberto = 0.0
        pares_operados: set[tuple[str, str]] = set()
        for c in ctes:
            o, d = _regiao_od(c)
            if not o or not d:
                continue
            pares_operados.add((o, d))
            if (o, d) in pares_mercado:
                ctes_cobertos += 1
                peso_coberto += c.peso or 0.0
        pares_cobertos = pares_operados & pares_mercado
        return {
            "pct_ctes_cobertos": round(ctes_cobertos / total_ctes * 100, 1) if total_ctes else 0.0,
            "pct_peso_coberto": round(peso_coberto / total_peso * 100, 1) if total_peso else 0.0,
            "pct_corredores_cobertos": round(len(pares_cobertos) / len(pares_operados) * 100, 1) if pares_operados else 0.0,
            "qtd_ctes_cobertos": ctes_cobertos, "qtd_ctes_total": total_ctes,
            "qtd_corredores_cobertos": len(pares_cobertos), "qtd_corredores_operados": len(pares_operados),
        }

    # ── Comparativo de Mercado (Cliente × Mercado, P10-P90) ───────────────
    def comparativo_mercado(
        self, empresa_id: int, escopo: str = "NACIONAL",
        data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    ) -> list[dict]:
        """``escopo``: NACIONAL | REGIAO | CORREDOR. Regenera o Benchmark
        Observado do período sob o ``periodo_ref`` reservado "COMPAR"
        (idempotente — reaproveita ``BenchmarkObservadoUseCase``, não
        duplica o cálculo de percentil real do cliente).

        Nota (bug corrigido em v6.9.3): o valor original "COMPARATIVO"
        (11 caracteres) excedia ``benchmark_observado.periodo_ref``
        (``VARCHAR(7)``, pensado para "YYYY-MM"), causando
        ``StringDataRightTruncation`` em toda chamada com escopo != NACIONAL
        (a exceção interrompia o loop antes de gravar a linha NACIONAL
        também, mas o card de Confiabilidade/Cobertura, que não passa por
        este método, mascarava o erro ao continuar exibindo dado válido)."""
        self.observado.gerar(empresa_id, periodo_ref="COMPAR", data_inicio=data_inicio, data_fim=data_fim)
        linhas = self.observado.listar(empresa_id, periodo_ref="COMPAR")

        itens = []
        for o in linhas:
            ref = self.v2.resolver(empresa_id, o.origem_regiao, o.destino_regiao)
            itens.append({
                "origem_regiao": o.origem_regiao, "destino_regiao": o.destino_regiao,
                "qtd_ctes": o.qtd_embarques,
                "cliente_p10": o.rs_kg_p10, "cliente_p25": o.rs_kg_p25, "cliente_p50": o.rs_kg_p50,
                "cliente_p75": o.rs_kg_p75, "cliente_p90": o.rs_kg_p90,
                "mercado_p10": ref.rs_kg_p10 if ref.disponivel else None,
                "mercado_p25": ref.rs_kg_p25 if ref.disponivel else None,
                "mercado_p50": ref.rs_kg_p50 if ref.disponivel else None,
                "mercado_p75": ref.rs_kg_p75 if ref.disponivel else None,
                "mercado_p90": ref.rs_kg_p90 if ref.disponivel else None,
                "fonte_mercado": ref.fonte,
                "diferenca_pct": _pct(o.rs_kg_p50, ref.rs_kg_p50) if ref.disponivel else None,
                "percentil": self._bucket_percentil(o.rs_kg_p50, ref) if ref.disponivel else "SEM_REFERENCIA",
                "classificacao": BenchmarkV2UseCase.faixa_de(o.rs_kg_p50, ref.rs_kg_p50, ref.rs_kg_p75) if ref.disponivel else "SEM_REFERENCIA",
            })

        if escopo == "CORREDOR":
            return sorted(itens, key=lambda i: i["qtd_ctes"], reverse=True)
        if escopo == "REGIAO":
            return self._agregar_por_regiao(itens)
        return self._agregar_nacional(itens)

    @staticmethod
    def _bucket_percentil(valor: float, ref) -> str:
        if valor <= ref.rs_kg_p10:
            return "≤P10"
        if valor <= ref.rs_kg_p25:
            return "P10-P25"
        if valor <= ref.rs_kg_p50:
            return "P25-P50"
        if valor <= ref.rs_kg_p75:
            return "P50-P75"
        if valor <= ref.rs_kg_p90:
            return "P75-P90"
        return ">P90"

    @staticmethod
    def _media_ponderada(itens: list[dict], campo: str, peso_campo: str = "qtd_ctes") -> Optional[float]:
        pares = [(i[campo], i[peso_campo]) for i in itens if i.get(campo) is not None and i.get(peso_campo)]
        peso_total = sum(p for _, p in pares)
        if not peso_total:
            return None
        return round(sum(v * p for v, p in pares) / peso_total, 4)

    def _agregar_linha(self, itens: list[dict], label: dict) -> dict:
        campos = ["cliente_p10", "cliente_p25", "cliente_p50", "cliente_p75", "cliente_p90",
                  "mercado_p10", "mercado_p25", "mercado_p50", "mercado_p75", "mercado_p90"]
        linha = {campo: self._media_ponderada(itens, campo) for campo in campos}
        linha.update(label)
        linha["qtd_ctes"] = sum(i["qtd_ctes"] for i in itens)
        if linha["mercado_p50"]:
            linha["diferenca_pct"] = _pct(linha["cliente_p50"], linha["mercado_p50"])
            linha["classificacao"] = BenchmarkV2UseCase.faixa_de(
                linha["cliente_p50"], linha["mercado_p50"], linha["mercado_p75"]
            )
        else:
            linha["diferenca_pct"] = None
            linha["classificacao"] = "SEM_REFERENCIA"
        return linha

    def _agregar_por_regiao(self, itens: list[dict]) -> list[dict]:
        grupos: dict[str, list[dict]] = defaultdict(list)
        for i in itens:
            grupos[i["destino_regiao"]].append(i)
        return sorted(
            (self._agregar_linha(v, {"destino_regiao": r}) for r, v in grupos.items()),
            key=lambda i: i["qtd_ctes"], reverse=True,
        )

    def _agregar_nacional(self, itens: list[dict]) -> list[dict]:
        if not itens:
            return []
        return [self._agregar_linha(itens, {"destino_regiao": "NACIONAL"})]

    # ── Simulador de Economia (cenário P50/P25/P10) ────────────────────────
    def simulador_economia(
        self, empresa_id: int, cenario: str = "P50",
        data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    ) -> dict:
        if cenario not in _CENARIOS:
            cenario = "P50"
        campo = _CENARIOS[cenario]

        ctes = self._ctes(empresa_id, data_inicio, data_fim)
        grupos: dict[tuple[str, str], dict] = defaultdict(lambda: {"frete": 0.0, "peso": 0.0})
        for c in ctes:
            if not c.peso or c.peso <= 0:
                continue
            o, d = _regiao_od(c)
            if not o or not d:
                continue
            grupos[(o, d)]["frete"] += c.valor_frete
            grupos[(o, d)]["peso"] += c.peso

        por_corredor = []
        economia_total = 0.0
        for (o, d), vals in grupos.items():
            ref = self.v2.resolver(empresa_id, o, d)
            alvo = getattr(ref, campo) if ref.disponivel else 0.0
            rs_kg = vals["frete"] / vals["peso"] if vals["peso"] else 0.0
            economia = max(0.0, rs_kg - alvo) * vals["peso"] if alvo else 0.0
            economia_total += economia
            por_corredor.append({
                "origem_regiao": o, "destino_regiao": d,
                "peso_total": round(vals["peso"], 2), "frete_rs_kg": round(rs_kg, 4),
                "referencia_rs_kg": alvo, "economia": round(economia, 2),
            })

        por_regiao: dict[str, float] = defaultdict(float)
        for item in por_corredor:
            por_regiao[item["destino_regiao"]] += item["economia"]

        # Por transportadora — compara contra a referência NACIONAL do cenário.
        ref_nacional = getattr(self._referencia_nacional(), campo)
        transp = defaultdict(lambda: {"frete": 0.0, "peso": 0.0, "nome": ""})
        for c in ctes:
            if not c.peso or c.peso <= 0 or not c.transportadora_id:
                continue
            transp[c.transportadora_id]["frete"] += c.valor_frete
            transp[c.transportadora_id]["peso"] += c.peso
        por_transportadora = []
        if ref_nacional:
            for tid, vals in transp.items():
                rs_kg = vals["frete"] / vals["peso"] if vals["peso"] else 0.0
                economia = max(0.0, rs_kg - ref_nacional) * vals["peso"]
                if economia > 0:
                    por_transportadora.append({
                        "transportadora_id": tid, "peso_total": round(vals["peso"], 2),
                        "frete_rs_kg": round(rs_kg, 4), "economia": round(economia, 2),
                    })
        por_transportadora.sort(key=lambda t: t["economia"], reverse=True)

        return {
            "cenario": cenario,
            "economia_total": round(economia_total, 2),
            "por_regiao": [
                {"destino_regiao": r, "economia": round(e, 2)}
                for r, e in sorted(por_regiao.items(), key=lambda kv: kv[1], reverse=True)
            ],
            "por_corredor": sorted(por_corredor, key=lambda c: c["economia"], reverse=True),
            "por_transportadora": por_transportadora,
        }

    def _referencia_nacional(self):
        from app.application.use_cases.benchmark_v2 import mapa_percentis_mercado
        mapa = mapa_percentis_mercado(self.db).get("NACIONAL", {})

        class _Ref:
            rs_kg_p10 = mapa.get("p10", 0.0)
            rs_kg_p25 = mapa.get("p25", 0.0)
            rs_kg_p50 = mapa.get("p50", 0.0)
        return _Ref()
