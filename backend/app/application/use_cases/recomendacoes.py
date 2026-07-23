"""Caso de uso: consolidação automática de Recomendações (MELHORIA 8).

Percorre os indicadores já existentes (Dashboard/Diagnóstico e DLG) e converte
os desvios relevantes em recomendações acionáveis, com título, descrição,
indicador relacionado, valor encontrado, valor recomendado, impacto e
prioridade.

A geração é DETERMINÍSTICA (origem='REGRA') e idempotente: reconsolidar não
duplica registros e preserva o status editado pelo usuário. A estrutura está
preparada para receber, no futuro, recomendações geradas por IA (origem='IA')
— basta gravá-las com a mesma chave natural e origem distinta.
"""
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.core.logging_config import get_logger
from app.infrastructure.database.models import DlgAnaliticoModel
from app.infrastructure.database.repositories import (
    BenchmarkRepository,
    CTeRepository,
    EmpresaRepository,
    MetaNacionalRepository,
    MetaRegionalRepository,
    RecomendacaoRepository,
    TransportadoraRepository,
)

logger = get_logger(__name__)

# Limiar de cancelamento acima do qual vira recomendação (percentual).
LIMIAR_CANCELAMENTO_PCT = 3.0
# Concentração de frete em uma única transportadora (percentual).
LIMIAR_CONCENTRACAO_PCT = 50.0
# Concentração de frete em um único cliente (RN-71, v6.7.0) — limiar próprio
# e mais sensível que o de transportadora (LIMIAR_CONCENTRACAO_PCT): uma
# empresa tipicamente tem muito mais clientes que transportadoras, então a
# mesma parcela de frete concentrada em 1 cliente já é um sinal mais forte.
LIMIAR_CONCENTRACAO_CLIENTE_PCT = 25.0


def _moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _rs_kg(v: float) -> str:
    return f"R$ {v:,.2f}/kg".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return f"{v:.2f}%".replace(".", ",")


def _nomes_componentes(ranking, n: int = 2) -> str:
    """RN-74/RN-77: top-N nomes de componente ofensor, para texto narrativo."""
    if not ranking:
        return "componentes adicionais"
    nomes = [cat for cat, _valor in ranking[:n]]
    return " e ".join(nomes) if len(nomes) > 1 else nomes[0]


class RecomendacoesUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RecomendacaoRepository(db)

    # ── consolidação ──────────────────────────────────────────────────────────

    def consolidar(self, empresa_id: int) -> Dict:
        """Gera/atualiza as recomendações determinísticas da empresa.
        Retorna um resumo com a contagem por prioridade."""
        diag = self._diagnostico(empresa_id)
        chaves_vigentes: set = set()

        def registrar(indicador, chave_origem, **campos):
            self.repo.upsert(empresa_id, indicador, chave_origem,
                             origem="REGRA", **campos)
            chaves_vigentes.add((indicador, chave_origem))

        # 1) Cancelamentos acima do limiar (qualidade de emissão)
        nac = diag.nacional
        if nac.pct_cancelados > LIMIAR_CANCELAMENTO_PCT and nac.qtd_ctes_cancelados:
            registrar(
                "CANCELAMENTOS", "nacional",
                titulo="Taxa de cancelamento de CT-e acima do saudável",
                descricao=(
                    f"{nac.qtd_ctes_cancelados} de {nac.qtd_ctes_emitidos} CT-es "
                    f"emitidos foram cancelados ({_pct(nac.pct_cancelados)}). "
                    "Cancelamentos elevados indicam retrabalho na emissão e ruído "
                    "nos indicadores de custo."
                ),
                valor_encontrado=_pct(nac.pct_cancelados),
                valor_recomendado="até 3,00%",
                impacto="Reduz retrabalho e melhora a acurácia do diagnóstico.",
                prioridade="ALTA" if nac.pct_cancelados > 6 else "MEDIA",
            )

        # 2) Custo por kg nacional acima da meta
        if nac.desvio_rs_kg and nac.desvio_rs_kg > 0 and nac.meta_rs_kg:
            economia = max(nac.desvio_rs_kg, 0) * nac.peso_total
            registrar(
                "CUSTO_KG", "nacional",
                titulo="Custo por kg acima da meta nacional",
                descricao=(
                    f"O custo médio de {_rs_kg(nac.frete_rs_kg)} está "
                    f"{_rs_kg(nac.desvio_rs_kg)} acima da meta de "
                    f"{_rs_kg(nac.meta_rs_kg)}."
                ),
                valor_encontrado=_rs_kg(nac.frete_rs_kg),
                valor_recomendado=_rs_kg(nac.meta_rs_kg),
                impacto=f"Economia potencial estimada de {_moeda(economia)}.",
                economia_estimada=round(economia, 2),
                prioridade="ALTA",
            )

        # 3) % Frete/Mercadoria acima da meta
        if nac.desvio_pct and nac.desvio_pct > 0 and nac.meta_pct:
            registrar(
                "PCT_FRETE", "nacional",
                titulo="% Frete sobre mercadoria acima da meta",
                descricao=(
                    f"O frete representa {_pct(nac.frete_pct)} do valor da "
                    f"mercadoria, acima da meta de {_pct(nac.meta_pct)}."
                ),
                valor_encontrado=_pct(nac.frete_pct),
                valor_recomendado=f"até {_pct(nac.meta_pct)}",
                impacto="Melhora a competitividade do preço posto ao cliente.",
                prioridade="MEDIA",
            )

        # 4) Concentração em uma única transportadora (risco de dependência)
        if diag.transportadoras and diag.transportadoras[0].participacao_pct > LIMIAR_CONCENTRACAO_PCT:
            t = diag.transportadoras[0]
            registrar(
                "CONCENTRACAO", f"transp:{t.transportadora_id}",
                titulo="Concentração excessiva em uma transportadora",
                descricao=(
                    f"{_pct(t.participacao_pct)} do frete está concentrado em "
                    f"'{t.nome}'. Alta dependência aumenta o risco operacional e "
                    "reduz poder de negociação."
                ),
                valor_encontrado=_pct(t.participacao_pct),
                valor_recomendado="até 50,00%",
                impacto="Reduz risco de dependência e amplia poder de barganha.",
                prioridade="MEDIA",
            )

        # 5) Regiões acima da meta regional
        for r in diag.regionais:
            if r.meta_rs_kg and r.frete_rs_kg > r.meta_rs_kg:
                economia = (r.frete_rs_kg - r.meta_rs_kg) * r.peso_total
                registrar(
                    "REGIAO", f"regiao:{r.macro_regiao}",
                    titulo=f"Custo por kg acima da meta na região {r.macro_regiao}",
                    descricao=(
                        f"{_rs_kg(r.frete_rs_kg)} vs. meta {_rs_kg(r.meta_rs_kg)} "
                        f"na região {r.macro_regiao}."
                    ),
                    valor_encontrado=_rs_kg(r.frete_rs_kg),
                    valor_recomendado=_rs_kg(r.meta_rs_kg),
                    impacto=f"Economia potencial estimada de {_moeda(economia)}.",
                    economia_estimada=round(economia, 2),
                    prioridade="MEDIA",
                )

        # 6) Rotas críticas do DLG (maior severidade) + rotas sem referência (upsell)
        self._recomendacoes_dlg(empresa_id, registrar)

        # 7) Clientes (destinatário) — causal (RN-71/RN-77, v6.7.0)
        self._recomendacoes_dlg_clientes(empresa_id, registrar)

        # Remove recomendações de REGRA que deixaram de existir (mantém IA e
        # o que o usuário concluiu/descartou).
        self.repo.remover_orfas(empresa_id, "REGRA", chaves_vigentes)
        self.repo.commit()

        return self._resumo(empresa_id)

    def _recomendacoes_dlg(self, empresa_id: int, registrar) -> None:
        """Deriva recomendações das rotas analisadas pelo DLG."""
        rotas = self.db.scalars(
            select(DlgAnaliticoModel).where(
                DlgAnaliticoModel.empresa_id == empresa_id,
                DlgAnaliticoModel.dimensao == "ROTA",
            )
        ).all()

        # Rotas críticas — ordena por desvio e limita às 5 mais severas.
        criticas = sorted(
            [r for r in rotas if r.classificacao == "CRITICO"],
            key=lambda x: x.desvio_pct, reverse=True,
        )[:5]
        for r in criticas:
            economia = 0.0
            if r.rs_kg_ref and r.rs_kg > r.rs_kg_ref:
                economia = (r.rs_kg - r.rs_kg_ref) * r.peso_total
            registrar(
                "DLG_ROTA", f"rota:{r.chave}",
                titulo=f"Rota crítica {r.chave_label}",
                descricao=(
                    f"A rota {r.chave_label} está {_pct(abs(r.desvio_pct))} acima "
                    f"da referência ({_rs_kg(r.rs_kg)} vs. {_rs_kg(r.rs_kg_ref)})."
                ),
                valor_encontrado=_rs_kg(r.rs_kg),
                valor_recomendado=_rs_kg(r.rs_kg_ref),
                impacto=(
                    f"Economia potencial estimada de {_moeda(economia)}."
                    if economia else "Renegociar a rota ou redistribuir volume."
                ),
                economia_estimada=round(economia, 2),
                prioridade="CRITICA",
            )

        # Rotas sem referência de mercado — oportunidade de consultoria (upsell).
        sem_ref = [r for r in rotas if r.classificacao == "SEM_REF"]
        sem_ref = sorted(sem_ref, key=lambda x: x.frete_total, reverse=True)[:3]
        for r in sem_ref:
            registrar(
                "DLG_SEM_REF", f"rota:{r.chave}",
                titulo=f"Rota sem referência de mercado: {r.chave_label}",
                descricao=(
                    f"A rota {r.chave_label} movimenta {_moeda(r.frete_total)} em "
                    "frete, mas ainda não possui referência de mercado cadastrada. "
                    "Um estudo de benchmark dedicado permite avaliar se há economia."
                ),
                valor_encontrado="sem referência",
                valor_recomendado="cadastrar benchmark do corredor",
                impacto="Habilita diagnóstico comparativo e potencial de economia.",
                prioridade="BAIXA",
            )

    def _recomendacoes_dlg_clientes(self, empresa_id: int, registrar) -> None:
        """RN-71/RN-77: recomendações causais da dimensão Cliente (destinatário).

        Reaproveita o motor DLG (``DlgUseCase``, modo consolidado) — nunca
        recalcula agregação, composição ou diagnóstico causal em paralelo
        (mesma filosofia de reuso da Opção B, Especificação Técnica §2). O
        texto usa exatamente a causa já atribuída por ``_diagnosticar_causa``
        (RN-76); a IA/este motor nunca inventam causa (OBJ-9).
        """
        from app.application.use_cases.dlg import DlgUseCase, JANELA_DIAS_FRAGMENTACAO

        clientes = DlgUseCase(self.db).listar(
            empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")
        if not clientes:
            return

        # Concentração de frete em um único cliente (RN-71).
        frete_total_geral = sum(c["frete_total"] for c in clientes)
        if frete_total_geral:
            maior = max(clientes, key=lambda c: c["frete_total"])
            pct_concentracao = maior["frete_total"] / frete_total_geral * 100
            if pct_concentracao > LIMIAR_CONCENTRACAO_CLIENTE_PCT:
                registrar(
                    "DLG_CLIENTE_CONCENTRACAO", f"cliente:{maior['chave']}",
                    titulo=f"Concentração de frete no cliente {maior['chave_label']}",
                    descricao=(
                        f"O cliente {maior['chave_label']} responde por "
                        f"{_pct(pct_concentracao)} do frete total do período — "
                        "concentração elevada de risco financeiro em um único destinatário."
                    ),
                    valor_encontrado=_pct(pct_concentracao),
                    valor_recomendado=f"até {_pct(LIMIAR_CONCENTRACAO_CLIENTE_PCT)}",
                    impacto="Reduz risco de dependência de receita/frete em um único cliente.",
                    prioridade="MEDIA",
                )

        # Top-5 CRÍTICO por desvio, com diagnóstico causal (RN-76/RN-77).
        criticos = sorted(
            [c for c in clientes if c["classificacao"] == "CRITICO"],
            key=lambda c: c["desvio_pct"], reverse=True,
        )[:5]
        for c in criticos:
            causa = c.get("causa_dominante")
            detalhe = c.get("causa_detalhe") or {}
            impacto_rs = c.get("impacto_financeiro_potencial") or 0.0
            nome = c["chave_label"]
            janela = detalhe.get("janela_dias", JANELA_DIAS_FRAGMENTACAO)
            despachos = detalhe.get("qtd_despachos", c["qtd_ctes"])

            if causa == "ADICIONAIS":
                comps = _nomes_componentes(c.get("ranking_componentes"))
                verbo = "são os principais ofensores" if " e " in comps else "é o principal ofensor"
                descricao = (
                    f"O cliente {nome} apresenta custo de frete {_pct(abs(c['desvio_pct']))} "
                    "acima do benchmark, com componentes adicionais representando "
                    f"{_pct(c.get('pct_componentes_adicionais') or 0)} do frete total — "
                    f"{comps} {verbo}. Impacto financeiro potencial: {_moeda(impacto_rs)}."
                )
            elif causa == "FRAGMENTACAO":
                descricao = (
                    f"O cliente {nome} gerou {despachos} despachos no período com peso "
                    f"médio {_pct(detalhe.get('pct_peso_abaixo_mediana') or 0)} abaixo do "
                    f"padrão da empresa, concentrados em janelas de até {janela} dias — "
                    "sinal de fragmentação operacional aumentando o custo por kg."
                )
            elif causa == "AMBAS":
                comp_top = _nomes_componentes(c.get("ranking_componentes"), n=1)
                descricao = (
                    f"O cliente {nome} combina fragmentação de despachos ({despachos} "
                    f"CT-es em {janela} dias) com alta incidência de {comp_top} — "
                    "ambos elevando o custo de frete acima do benchmark."
                )
            else:
                descricao = (
                    f"O cliente {nome} está {_pct(abs(c['desvio_pct']))} acima do "
                    f"benchmark ({_rs_kg(c['rs_kg'])} vs. {_rs_kg(c['rs_kg_ref'])}), sem "
                    "causa específica identificada pelo motor (adicionais ou fragmentação)."
                )

            registrar(
                "DLG_CLIENTE_CRITICO", f"cliente:{c['chave']}",
                titulo=f"Cliente crítico: {nome}",
                descricao=descricao,
                valor_encontrado=_rs_kg(c["rs_kg"]),
                valor_recomendado=_rs_kg(c["rs_kg_ref"]),
                impacto=(
                    f"Economia potencial estimada de {_moeda(impacto_rs)}."
                    if impacto_rs else "Investigar causa e avaliar ação comercial."
                ),
                economia_estimada=round(impacto_rs, 2),
                prioridade="CRITICA",
                dados={"acao_recomendada": detalhe.get("acao_recomendada")} if detalhe.get("acao_recomendada") else None,
            )

        # Top-3 clientes SEM_REF — oportunidade de cadastro (mesmo padrão de
        # RN-56 já usado para Rota).
        sem_ref = [c for c in clientes if c["classificacao"] == "SEM_REF"]
        sem_ref = sorted(sem_ref, key=lambda c: c["frete_total"], reverse=True)[:3]
        for c in sem_ref:
            registrar(
                "DLG_CLIENTE_SEM_REF", f"cliente:{c['chave']}",
                titulo=f"Cliente sem referência de benchmark: {c['chave_label']}",
                descricao=(
                    f"O cliente {c['chave_label']} não possui referência de benchmark "
                    "configurada para o período."
                ),
                valor_encontrado="sem referência",
                valor_recomendado="cadastrar benchmark do corredor",
                impacto="Habilita diagnóstico comparativo e potencial de economia.",
                prioridade="BAIXA",
            )

    # ── consultas ─────────────────────────────────────────────────────────────

    def listar(self, empresa_id: int, prioridade: Optional[str] = None,
               status: Optional[str] = None) -> List["object"]:
        return self.repo.listar(empresa_id, prioridade, status)

    def atualizar_status(self, rec_id: int, empresa_id: int, status: str) -> bool:
        return self.repo.atualizar_status(rec_id, empresa_id, status)

    def _resumo(self, empresa_id: int) -> Dict:
        itens = self.repo.listar(empresa_id)
        contagem = {"CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAIXA": 0}
        economia = 0.0
        for i in itens:
            contagem[i.prioridade] = contagem.get(i.prioridade, 0) + 1
            economia += i.economia_estimada or 0
        return {
            "total": len(itens),
            "por_prioridade": contagem,
            "economia_estimada_total": round(economia, 2),
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _diagnostico(self, empresa_id: int):
        uc = DiagnosticoUseCase(
            CTeRepository(self.db),
            EmpresaRepository(self.db),
            TransportadoraRepository(self.db),
            MetaNacionalRepository(self.db),
            MetaRegionalRepository(self.db),
            BenchmarkRepository(self.db),
        )
        return uc.gerar(empresa_id)
