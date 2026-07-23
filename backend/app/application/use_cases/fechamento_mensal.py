"""Fechamento de Custo de Frete — use case de fechamento mensal.

Combina o que é informado no fechamento (faturamento por região, devolução
e frete complementar nacionais) com o que já é automático (frete realizado
via CT-e, frete budget e faturamento budget via MetaRegional) para montar o
relatório completo e controlar o estado ABERTO/FECHADO de cada competência.

Frete Contratado e Frete Realizado por região nunca são digitados — vêm
sempre de `CTeRepository.agregar_nacional`/`agregar_por_regiao`
(RN já aplicada em Benchmark/Dashboard: nunca duplicar dado automático).
Faturamento Budget é derivado de `Frete Budget ÷ Meta % Frete`
(`MetaRegional.orcamento_mensal` / `MetaRegional.meta_pct_frete`), nunca
um valor solto.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Dict, List

from app.domain.entities import FechamentoMensal, MacroRegiaoEnum, StatusFechamentoEnum
from app.infrastructure.database.repositories import (
    CTeRepository,
    FechamentoMensalRepository,
    MetaRegionalRepository,
)


def _periodo(competencia: str) -> tuple[date, date]:
    ano, mes = (int(p) for p in competencia.split("-"))
    return date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1])


def _competencia_anterior(competencia: str) -> str:
    ano, mes = (int(p) for p in competencia.split("-"))
    if mes == 1:
        return f"{ano - 1}-12"
    return f"{ano}-{mes - 1:02d}"


class FechamentoMensalUseCase:
    def __init__(self, db):
        self.fechamento_repo = FechamentoMensalRepository(db)
        self.cte_repo = CTeRepository(db)
        self.meta_repo = MetaRegionalRepository(db)

    # ── leitura ──────────────────────────────────────────────────────────

    def obter(self, empresa_id: int, competencia: str) -> Dict:
        registro = self.fechamento_repo.get_by_competencia(empresa_id, competencia)
        if not registro:
            # mês ainda não lançado: pré-preenche com a competência anterior
            # (sem persistir) para poupar redigitação de números parecidos
            anterior = self.fechamento_repo.get_by_competencia(
                empresa_id, _competencia_anterior(competencia)
            )
            registro = FechamentoMensal(
                empresa_id=empresa_id,
                competencia=competencia,
                fat_norte=anterior.fat_norte if anterior else 0.0,
                fat_nordeste=anterior.fat_nordeste if anterior else 0.0,
                fat_centro_oeste=anterior.fat_centro_oeste if anterior else 0.0,
                fat_sudeste=anterior.fat_sudeste if anterior else 0.0,
                fat_sul=anterior.fat_sul if anterior else 0.0,
                devolucao=anterior.devolucao if anterior else 0.0,
                frete_complementar=anterior.frete_complementar if anterior else 0.0,
            )
        return self._montar_relatorio(empresa_id, registro)

    def historico(self, empresa_id: int, limite: int = 13) -> List[Dict]:
        registros = self.fechamento_repo.list_historico(empresa_id, limite)
        return [self._resumo_competencia(empresa_id, r) for r in registros]

    # ── escrita ──────────────────────────────────────────────────────────

    def salvar(self, empresa_id: int, competencia: str, payload: Dict) -> Dict:
        atual = self.fechamento_repo.get_by_competencia(empresa_id, competencia)
        if atual and atual.status == StatusFechamentoEnum.FECHADO:
            raise ValueError("Mês fechado. Reabra antes de editar.")
        registro = FechamentoMensal(empresa_id=empresa_id, competencia=competencia, **payload)
        salvo = self.fechamento_repo.upsert(registro)
        return self._montar_relatorio(empresa_id, salvo)

    def fechar(self, empresa_id: int, competencia: str) -> Dict:
        if not self.fechamento_repo.get_by_competencia(empresa_id, competencia):
            raise ValueError("Nada lançado nesta competência ainda.")
        salvo = self.fechamento_repo.fechar(empresa_id, competencia)
        return self._montar_relatorio(empresa_id, salvo)

    def reabrir(self, empresa_id: int, competencia: str) -> Dict:
        salvo = self.fechamento_repo.reabrir(empresa_id, competencia)
        if not salvo:
            raise ValueError("Nada lançado nesta competência ainda.")
        return self._montar_relatorio(empresa_id, salvo)

    # ── montagem do relatório ────────────────────────────────────────────

    def _frete_contratado(self, empresa_id: int, competencia: str) -> float:
        data_inicio, data_fim = _periodo(competencia)
        agregado = self.cte_repo.agregar_nacional(empresa_id, data_inicio, data_fim, apenas_ativos=True)
        return float(agregado.get("valor_total_frete") or 0.0)

    def _montar_relatorio(self, empresa_id: int, registro: FechamentoMensal) -> Dict:
        data_inicio, data_fim = _periodo(registro.competencia)
        por_regiao = {
            r["macro_regiao"]: r
            for r in self.cte_repo.agregar_por_regiao(empresa_id, data_inicio, data_fim, apenas_ativos=True)
        }
        metas = {m.macro_regiao.value: m for m in self.meta_repo.list(empresa_id)}

        fat_por_regiao = {
            MacroRegiaoEnum.NORTE: registro.fat_norte,
            MacroRegiaoEnum.NORDESTE: registro.fat_nordeste,
            MacroRegiaoEnum.CENTRO_OESTE: registro.fat_centro_oeste,
            MacroRegiaoEnum.SUDESTE: registro.fat_sudeste,
            MacroRegiaoEnum.SUL: registro.fat_sul,
        }
        tot_fat_real = sum(fat_por_regiao.values())

        linhas = []
        tot_fat_budget = 0.0
        tot_frete_real = 0.0
        tot_frete_budget = 0.0
        for macro, fat_real in fat_por_regiao.items():
            frete_real = float(por_regiao.get(macro.value, {}).get("frete_total") or 0.0)
            meta = metas.get(macro.value)
            frete_budget = meta.orcamento_mensal if meta else 0.0
            fat_budget = (frete_budget / (meta.meta_pct_frete / 100)) if meta and meta.meta_pct_frete else 0.0
            tot_fat_budget += fat_budget
            tot_frete_real += frete_real
            tot_frete_budget += frete_budget
            linhas.append({
                "macro_regiao": macro.value,
                "fat_real": round(fat_real, 2),
                "frete_real": round(frete_real, 2),
                "pct_frete_fat_real": round(frete_real / fat_real * 100, 2) if fat_real else 0.0,
                "fat_budget": round(fat_budget, 2),
                "frete_budget": round(frete_budget, 2),
                "pct_frete_fat_budget": round(frete_budget / fat_budget * 100, 2) if fat_budget else 0.0,
                "representatividade_real": 0.0,
                "representatividade_budget": 0.0,
            })

        for linha in linhas:
            linha["representatividade_real"] = (
                round(linha["fat_real"] / tot_fat_real * 100, 2) if tot_fat_real else 0.0
            )
            linha["representatividade_budget"] = (
                round(linha["fat_budget"] / tot_fat_budget * 100, 2) if tot_fat_budget else 0.0
            )

        return {
            "competencia": registro.competencia,
            "status": registro.status.value,
            "fechado_em": registro.fechado_em,
            "fat_norte": registro.fat_norte,
            "fat_nordeste": registro.fat_nordeste,
            "fat_centro_oeste": registro.fat_centro_oeste,
            "fat_sudeste": registro.fat_sudeste,
            "fat_sul": registro.fat_sul,
            "devolucao": registro.devolucao,
            "frete_complementar": registro.frete_complementar,
            "faturamento_total": round(tot_fat_real, 2),
            "frete_contratado": round(self._frete_contratado(empresa_id, registro.competencia), 2),
            "regional": linhas,
            "regional_total": {
                "fat_real": round(tot_fat_real, 2),
                "frete_real": round(tot_frete_real, 2),
                "pct_frete_fat_real": round(tot_frete_real / tot_fat_real * 100, 2) if tot_fat_real else 0.0,
                "fat_budget": round(tot_fat_budget, 2),
                "frete_budget": round(tot_frete_budget, 2),
                "pct_frete_fat_budget": round(tot_frete_budget / tot_fat_budget * 100, 2) if tot_fat_budget else 0.0,
            },
        }

    def _resumo_competencia(self, empresa_id: int, registro: FechamentoMensal) -> Dict:
        fat_total = (
            registro.fat_norte + registro.fat_nordeste + registro.fat_centro_oeste
            + registro.fat_sudeste + registro.fat_sul
        )
        return {
            "competencia": registro.competencia,
            "status": registro.status.value,
            "faturamento_total": round(fat_total, 2),
            "devolucao": registro.devolucao,
            "frete_complementar": registro.frete_complementar,
            "frete_contratado": round(self._frete_contratado(empresa_id, registro.competencia), 2),
        }
