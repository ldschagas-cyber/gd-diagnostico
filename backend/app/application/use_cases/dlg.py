"""DLG — Motor Analítico de Diagnóstico Logístico.

Responsabilidades:
- Calcular KPIs (R$/kg, % frete, custo/entrega) por 4 dimensões.
- Classificar eficiência: EFICIENTE / ATENÇÃO / CRÍTICO vs benchmark.
- Detectar outliers: R$/kg > média+2σ, % frete > limite CFG, variação mensal >30%.
- Persistir resultados em dlg_analitico e dlg_outliers (idempotente).
- Permitir reprocessamento completo por período sem duplicação.

Fonte de dados:
- IMP → CTeModel (CT-e normalizados)
- CAD → TransportadoraModel (nomes)
- CFG → MetaNacionalModel / MetaRegionalModel / BenchmarkMercadoModel (referências,
  via Matriz Benchmark OD — fonte única de mercado, v6.9)
"""
from __future__ import annotations

import calendar
import math
import re
import statistics
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from app.domain.entities import (
    CTE_STATUS_ATIVO,
    calc_frete_transporte_principal,
    calc_pct_componentes_adicionais,
    calc_ranking_componentes,
)
from app.infrastructure.database.models import (
    BenchmarkMercadoModel,
    CTeModel,
    DlgAnaliticoModel,
    DlgOutlierModel,
    EmpresaModel,
    FilialModel,
    MetaNacionalModel,
    MetaRegionalModel,
    TransportadoraModel,
)


def _so_digitos(v: str) -> str:
    return "".join(c for c in (v or "") if c.isdigit())


# ─── identidade real (RN-28/RN-68) ─────────────────────────────────────────────
# Extraído para nível de módulo (antes vivia só dentro de _agregar_transportadoras)
# para ser reaproveitado por _ident_cliente (RN-68) sem duplicar a lógica.
_SUFIXOS = (" ltda", " me", " epp", " eireli", " sa", " s a")


def _norm_nome(s: str) -> str:
    s = (s or "").strip().lower()
    # remove acentos (compara "rápido" == "rapido")
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = " ".join(s.split())
    mudou = True
    while mudou:
        mudou = False
        for suf in _SUFIXOS:
            if s.endswith(suf):
                s = s[: -len(suf)].strip()
                mudou = True
    return s


def _raiz(cnpj: str) -> str:
    return cnpj[:8] if cnpj and len(cnpj) >= 8 else cnpj


def _ident_cliente_str(cnpj: str, nome: str) -> tuple:
    cnpj = _so_digitos(cnpj or "")
    if cnpj:
        return ("RAIZ", _raiz(cnpj))
    nome_n = _norm_nome(nome or "")
    return ("NOME", nome_n) if nome_n else ("SEM_ID", None)


def _ident_cliente(c: "CTeModel") -> tuple:
    """RN-68: identidade real do cliente (destinatário), análoga à RN-28.

    Não há tabela mestre de cliente — a identidade é resolvida diretamente
    do próprio CTeModel: raiz de 8 dígitos do CNPJ, ou nome normalizado sem
    sufixo societário quando não há CNPJ. Sem nenhum dos dois, o CT-e cai em
    ("SEM_ID", None) — rótulo "Cliente não identificado" (CA-2), nunca
    descartado nem fundido com outro cliente.
    """
    return _ident_cliente_str(c.destinatario_cnpj, c.destinatario_nome)


def _chave_cliente_para_ident(chave: str) -> tuple:
    """Inverso da serialização `f"{tipo}:{valor}"` usada em `_agregar_clientes`."""
    if not chave or chave == "SEM_ID":
        return ("SEM_ID", None)
    tipo, _, valor = chave.partition(":")
    return (tipo, valor)


# ─── fragmentação operacional e diagnóstico causal (RN-75/RN-76) ───────────────
LIMIAR_PESO_MEDIO_BAIXO = 0.5     # RN-75: peso médio do cliente < mediana × limiar
MIN_CTES_FRAGMENTACAO = 3         # RN-75: mínimo de despachos na janela curta
JANELA_DIAS_FRAGMENTACAO = 7      # RN-75: janela de dias corridos


def _tem_janela_curta(
    datas: List[Optional[date]],
    min_ctes: int = MIN_CTES_FRAGMENTACAO,
    dias: int = JANELA_DIAS_FRAGMENTACAO,
) -> bool:
    """RN-75 (Parte B): True se existem >= ``min_ctes`` despachos cujas datas
    cabem numa janela de até ``dias`` dias corridos (limite inclusive: exatos
    ``dias`` dias conta, ``dias``+1 não conta)."""
    validas = sorted(d for d in datas if d)
    if len(validas) < min_ctes:
        return False
    for i in range(len(validas) - min_ctes + 1):
        if (validas[i + min_ctes - 1] - validas[i]).days <= dias:
            return True
    return False


def _diagnosticar_causa(
    pct_adicionais: Optional[float],
    limiar_adicionais_pct: float,
    tem_fragmentacao: bool,
    ranking_componentes: Optional[list],
) -> Dict:
    """RN-76: atribui causa dominante ao desvio de um cliente ATENÇÃO/CRÍTICO.

    Determinístico — nunca inventa causa quando nenhum sinal está presente
    (OBJ-9): retorna "NENHUMA" e o chamador usa a linguagem genérica de
    desvio de benchmark já existente (RN-25).
    """
    tem_adicionais = pct_adicionais is not None and pct_adicionais > limiar_adicionais_pct
    if tem_adicionais and tem_fragmentacao:
        causa = "AMBAS"
    elif tem_adicionais:
        causa = "ADICIONAIS"
    elif tem_fragmentacao:
        causa = "FRAGMENTACAO"
    else:
        causa = "NENHUMA"
    componente_top = ranking_componentes[0] if (tem_adicionais and ranking_componentes) else None
    return {"causa": causa, "componente_top": componente_top}


def _campo(row, nome: str):
    return row.get(nome) if isinstance(row, dict) else getattr(row, nome, None)


def _definir_campo(row, nome: str, valor) -> None:
    if isinstance(row, dict):
        row[nome] = valor
    else:
        setattr(row, nome, valor)


def _somar_composicao(lote: List["CTeModel"]) -> Dict[str, float]:
    """Soma composicao_frete por categoria entre os CT-e do lote (RN-72/§4.2).

    Genérico às 5 dimensões — custo marginal pequeno (dict já carregado por
    CT-e, mesma ordem de grandeza do resto da agregação já em memória).
    """
    comp_agregada: Dict[str, float] = defaultdict(float)
    for c in lote:
        for categoria, valor in (c.composicao_frete or {}).items():
            comp_agregada[categoria] += valor or 0.0
    return {k: round(v, 2) for k, v in comp_agregada.items()}


# ─── helpers ──────────────────────────────────────────────────────────────────

def _div(a: float, b: float, default: float = 0.0) -> float:
    return round(a / b, 4) if b else default


def _periodo(d: date) -> str:
    return d.strftime("%Y-%m")


def _classificar(rs_kg_real: float, rs_kg_ref: float) -> Tuple[str, float]:
    """Retorna (classificacao, desvio_pct)."""
    if not rs_kg_ref:
        return "SEM_REF", 0.0
    desvio = round((rs_kg_real - rs_kg_ref) / rs_kg_ref * 100, 2)
    if desvio <= 0:
        return "EFICIENTE", desvio
    if desvio <= 15:
        return "ATENCAO", desvio
    return "CRITICO", desvio


# ─── use case ─────────────────────────────────────────────────────────────────

class DlgUseCase:
    """Motor principal do DLG. Use `processar()` para acionar o reprocessamento."""

    def __init__(self, db: Session):
        self.db = db

    # ── ponto de entrada público ───────────────────────────────────────────────

    def processar(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict:
        """Reprocessa o DLG para o período. Idempotente: apaga e recria os
        registros do período antes de gravar os novos."""
        ctes = self._carregar_ctes(empresa_id, data_inicio, data_fim)
        if not ctes:
            return {"status": "sem_dados", "ctes": 0}

        periodos_afetados = sorted({_periodo(c.data_emissao) for c in ctes})
        refs = self._carregar_referencias(empresa_id)
        limit_pct = self._limite_pct_frete(empresa_id)

        # idempotência: remove registros anteriores do mesmo período
        for p in periodos_afetados:
            self.db.execute(
                delete(DlgAnaliticoModel).where(
                    DlgAnaliticoModel.empresa_id == empresa_id,
                    DlgAnaliticoModel.periodo_ref == p,
                )
            )
            self.db.execute(
                delete(DlgOutlierModel).where(
                    DlgOutlierModel.empresa_id == empresa_id,
                    DlgOutlierModel.periodo_ref == p,
                )
            )

        # agrupa por período para detecção de outliers e variação mensal
        ctes_por_periodo: Dict[str, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            ctes_por_periodo[_periodo(c.data_emissao)].append(c)

        total_analiticos = 0
        total_outliers   = 0
        nomes_transp     = self._nomes_transportadoras(empresa_id)
        cnpjs_transp     = self._cnpjs_transportadoras(empresa_id)
        nomes_filiais    = self._nomes_filiais(empresa_id)

        for periodo, lote in ctes_por_periodo.items():
            rows_a, rows_o = self._processar_periodo(
                empresa_id, periodo, lote, refs, limit_pct,
                nomes_transp, cnpjs_transp, nomes_filiais,
            )
            self.db.add_all(rows_a)
            self.db.add_all(rows_o)
            total_analiticos += len(rows_a)
            total_outliers   += len(rows_o)

        self.db.commit()
        return {
            "status": "ok",
            "ctes": len(ctes),
            "periodos": periodos_afetados,
            "analiticos": total_analiticos,
            "outliers": total_outliers,
        }

    # ── carregamento ──────────────────────────────────────────────────────────

    def _carregar_ctes(
        self,
        empresa_id: int,
        data_inicio: Optional[date],
        data_fim: Optional[date],
    ) -> List[CTeModel]:
        # Considera apenas CT-es ATIVOS — cancelados não entram no diagnóstico.
        stmt = select(CTeModel).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.status == CTE_STATUS_ATIVO,
        )
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        return list(self.db.scalars(stmt).all())

    def _carregar_referencias(self, empresa_id: int) -> Dict:
        """Retorna refs de benchmark indexadas por dimensão/chave."""
        meta_nac = self.db.scalar(select(MetaNacionalModel))
        metas_reg = {
            (m.macro_regiao.value if hasattr(m.macro_regiao, "value") else m.macro_regiao): m
            for m in self.db.scalars(select(MetaRegionalModel)).all()
        }
        # benchmark_mercado (Matriz Benchmark OD): p50 por região de destino —
        # fonte única de mercado (v6.9); substitui o antigo dict de BenchmarkModel (V1).
        mercado = defaultdict(list)
        for bm in self.db.scalars(select(BenchmarkMercadoModel)).all():
            mercado[bm.destino_regiao].append(bm.rs_kg_p50)
        mercado_p50 = {r: statistics.mean(vs) for r, vs in mercado.items() if vs}

        return {
            "meta_nac": meta_nac,
            "metas_reg": metas_reg,
            "mercado_p50": mercado_p50,
        }

    def _limite_pct_frete(self, empresa_id: int) -> float:
        """Limite de % frete para outlier (CFG = meta_pct_frete nacional × 1,5)."""
        meta = self.db.scalar(select(MetaNacionalModel))
        return (meta.meta_pct_frete * 1.5) if meta and meta.meta_pct_frete else 15.0

    def _nomes_transportadoras(self, empresa_id: int) -> Dict[int, str]:
        rows = self.db.scalars(
            select(TransportadoraModel).where(
                TransportadoraModel.empresa_id == empresa_id
            )
        ).all()
        return {t.id: t.nome_fantasia or t.razao_social for t in rows}

    def _cnpjs_transportadoras(self, empresa_id: int) -> Dict[int, str]:
        """Mapa id → CNPJ (somente dígitos) das transportadoras da empresa.

        Usado para deduplicar a dimensão TRANSPORTADORA pela identidade real
        (CNPJ) e não pelo id substituto — ver ``_agregar_transportadoras``.
        """
        rows = self.db.scalars(
            select(TransportadoraModel).where(
                TransportadoraModel.empresa_id == empresa_id
            )
        ).all()
        return {t.id: _so_digitos(t.cnpj) for t in rows}

    def _nomes_filiais(self, empresa_id: int) -> Dict[str, str]:
        """Mapa CNPJ (somente dígitos) → nome da matriz/filial (MELHORIA 9).

        A dimensão de análise passa a ser a FILIAL: o tomador do CT-e (uma das
        inscrições da própria empresa-cliente) é resolvido para a razão social
        da matriz ou filial correspondente.
        """
        mapa: Dict[str, str] = {}
        empresa = self.db.get(EmpresaModel, empresa_id)
        if empresa:
            cnpj = _so_digitos(empresa.cnpj_matriz)
            if cnpj:
                mapa[cnpj] = (empresa.nome_fantasia or empresa.razao_social
                              or "Matriz") + " (Matriz)"
        for f in self.db.scalars(
            select(FilialModel).where(FilialModel.empresa_id == empresa_id)
        ).all():
            cnpj = _so_digitos(f.cnpj)
            if cnpj:
                rotulo = f.razao_social or "Filial"
                if f.cidade or f.uf:
                    rotulo = f"{rotulo} — {f.cidade}/{f.uf}".rstrip("/")
                mapa[cnpj] = rotulo
        return mapa

    # ── processamento por período ─────────────────────────────────────────────

    def _processar_periodo(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        refs: Dict,
        limit_pct: float,
        nomes_transp: Dict[int, str],
        cnpjs_transp: Dict[int, str] | None = None,
        nomes_filiais: Dict[str, str] | None = None,
    ) -> Tuple[List[DlgAnaliticoModel], List[DlgOutlierModel]]:
        analiticos: List[DlgAnaliticoModel] = []
        outliers:   List[DlgOutlierModel]   = []

        # ── estatísticas globais do lote (para cálculo de outlier 2σ) ─────────
        rs_kgs_validos = [
            _div(c.valor_frete, c.peso)
            for c in ctes if c.peso and c.valor_frete
        ]
        media_rs_kg = statistics.mean(rs_kgs_validos) if rs_kgs_validos else 0.0
        dp_rs_kg    = statistics.stdev(rs_kgs_validos) if len(rs_kgs_validos) > 1 else 0.0
        limite_2dp  = media_rs_kg + 2 * dp_rs_kg

        # ── outliers por CT-e ─────────────────────────────────────────────────
        for c in ctes:
            rs_kg  = _div(c.valor_frete, c.peso)
            pct_fr = _div(c.valor_frete, c.valor_mercadoria) * 100

            if limite_2dp and rs_kg > limite_2dp:
                outliers.append(DlgOutlierModel(
                    empresa_id=empresa_id, cte_id=c.id, periodo_ref=periodo,
                    tipo_outlier="RS_KG_2DP",
                    valor_real=rs_kg, valor_limite=limite_2dp,
                    desvio_pct=round((rs_kg - limite_2dp) / limite_2dp * 100, 2),
                ))
            if limit_pct and c.valor_mercadoria and pct_fr > limit_pct:
                outliers.append(DlgOutlierModel(
                    empresa_id=empresa_id, cte_id=c.id, periodo_ref=periodo,
                    tipo_outlier="PCT_FRETE",
                    valor_real=pct_fr, valor_limite=limit_pct,
                    desvio_pct=round((pct_fr - limit_pct) / limit_pct * 100, 2),
                ))

        # ── agregações por dimensão ───────────────────────────────────────────
        # referência nacional
        ref_nac = refs["meta_nac"].meta_rs_kg if refs["meta_nac"] else 0.0

        analiticos += self._agregar_filiais(
            empresa_id, periodo, ctes, ref_nac, nomes_filiais or {})
        analiticos += self._agregar_rotas(
            empresa_id, periodo, ctes, refs, ref_nac)
        analiticos += self._agregar_transportadoras(
            empresa_id, periodo, ctes, ref_nac, nomes_transp, cnpjs_transp or {})
        analiticos += self._agregar_regioes(
            empresa_id, periodo, ctes, refs)
        analiticos += self._agregar_clientes(
            empresa_id, periodo, ctes, ref_nac)

        return analiticos, outliers

    # ── agregação: FILIAL (MELHORIA 9) ────────────────────────────────────────

    def _agregar_filiais(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        ref_rs_kg: float,
        nomes_filiais: Dict[str, str],
    ) -> List[DlgAnaliticoModel]:
        """Agrega por FILIAL (tomador do CT-e resolvido para a razão social da
        matriz/filial). Substitui a antiga dimensão CLIENTE."""
        grupos: Dict[str, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            grupos[_so_digitos(c.tomador_cnpj) or "SEM_CNPJ"].append(c)

        rows = []
        for cnpj, lote in grupos.items():
            frete = sum(c.valor_frete or 0 for c in lote)
            peso  = sum(c.peso or 0 for c in lote)
            merc  = sum(c.valor_mercadoria or 0 for c in lote)
            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0
            clf, dev = _classificar(rs_kg, ref_rs_kg)
            label = nomes_filiais.get(cnpj)
            if not label:
                label = "Filial não identificada" if cnpj == "SEM_CNPJ" else cnpj
            rows.append(DlgAnaliticoModel(
                empresa_id=empresa_id, dimensao="FILIAL",
                chave=cnpj, chave_label=label,
                periodo_ref=periodo,
                qtd_ctes=len(lote), peso_total=round(peso, 2),
                frete_total=round(frete, 2), mercadoria_total=round(merc, 2),
                rs_kg=rs_kg, pct_frete=round(pct, 4),
                custo_medio_entrega=_div(frete, len(lote)),
                rs_kg_ref=ref_rs_kg, desvio_pct=dev, classificacao=clf,
                composicao_frete=_somar_composicao(lote),
            ))
        return rows

    # ── agregação: ROTA (OD) ──────────────────────────────────────────────────

    def _agregar_rotas(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        refs: Dict,
        ref_nac: float,
    ) -> List[DlgAnaliticoModel]:
        grupos: Dict[str, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            od = f"{c.uf_origem or '??'}→{c.uf_destino or '??'}"
            grupos[od].append(c)

        rows = []
        for od, lote in grupos.items():
            frete = sum(c.valor_frete or 0 for c in lote)
            peso  = sum(c.peso or 0 for c in lote)
            merc  = sum(c.valor_mercadoria or 0 for c in lote)
            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0
            # referência: mercado p50 da região destino > meta nacional
            regiao_dst = (lote[0].macro_regiao_destino or "").upper() if lote else ""
            ref = refs["mercado_p50"].get(regiao_dst) or ref_nac
            clf, dev = _classificar(rs_kg, ref)
            rows.append(DlgAnaliticoModel(
                empresa_id=empresa_id, dimensao="ROTA",
                chave=od, chave_label=od,
                periodo_ref=periodo,
                qtd_ctes=len(lote), peso_total=round(peso, 2),
                frete_total=round(frete, 2), mercadoria_total=round(merc, 2),
                rs_kg=rs_kg, pct_frete=round(pct, 4),
                custo_medio_entrega=_div(frete, len(lote)),
                rs_kg_ref=ref, desvio_pct=dev, classificacao=clf,
                composicao_frete=_somar_composicao(lote),
            ))
        return rows

    # ── agregação: TRANSPORTADORA ─────────────────────────────────────────────

    def _agregar_transportadoras(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        ref_rs_kg: float,
        nomes: Dict[int, str],
        cnpjs: Dict[int, str],
    ) -> List[DlgAnaliticoModel]:
        """Agrega por TRANSPORTADORA usando a IDENTIDADE REAL do transportador.

        Causa raiz da duplicidade: a tabela ``transportadoras`` não tem
        unicidade em empresa_id+cnpj, e a importação resolve por CNPJ (fluxo
        XML) ou por nome (fluxo Excel). O mesmo transportador acaba com vários
        cadastros — matriz e filiais (CNPJ completo diferente, mas MESMA RAIZ de
        8 dígitos), além de variações de nome ("LOGGO..." vs "LOGGO... LTDA").
        Como os CT-e apontam para ids distintos, a agregação os exibia repetidos.

        Correção (causa raiz, sem DISTINCT):
        1. Identidade = RAIZ do CNPJ (8 primeiros dígitos) — consolida
           matriz + filiais do mesmo transportador numa única linha.
        2. Para cadastros SEM CNPJ, identidade = nome normalizado (minúsculas,
           sem pontuação e sem sufixos societários: LTDA/ME/EPP/EIRELI/SA).
        3. O id canônico de cada identidade é calculado GLOBALMENTE (sobre todos
           os cadastros da empresa, não só os do mês), garantindo uma ``chave``
           ESTÁVEL entre competências — essencial para o modo Consolidado não
           voltar a duplicar. A ``chave`` continua sendo um id inteiro de
           transportadora, preservando consumidores como ``mcl._perf_dlg``.

        ``_norm_nome``/``_raiz`` vivem a nível de módulo (reaproveitadas por
        ``_ident_cliente``, RN-68) — apenas ``_ident`` permanece local, pois é
        específica de identidade por *id de cadastro* (transportadora tem
        cadastro; cliente não, RN-68 lê direto do CTeModel).
        """

        def _ident(tid: int) -> tuple:
            cnpj = cnpjs.get(tid, "")
            if cnpj:
                return ("RAIZ", _raiz(cnpj))
            nome = _norm_nome(nomes.get(tid, ""))
            return ("NOME", nome) if nome else ("ID", tid)

        # ── canônico GLOBAL por identidade (estável entre meses) ──────────────
        canonico_por_ident: Dict[tuple, int] = {}
        for tid in set(cnpjs) | set(nomes):
            ident = _ident(tid)
            atual = canonico_por_ident.get(ident)
            # prefere cadastro com CNPJ; desempata pelo menor id
            if atual is None or (0 if cnpjs.get(tid) else 1, tid) < (
                0 if cnpjs.get(atual) else 1, atual
            ):
                canonico_por_ident[ident] = tid

        # ── agrega os CT-e do mês pelo canônico da identidade ─────────────────
        grupos: Dict[int, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            tid = c.transportadora_id
            if not tid:
                continue
            canon = canonico_por_ident.get(_ident(tid), tid)
            grupos[canon].append(c)

        rows = []
        for canon, lote in grupos.items():
            frete = sum(c.valor_frete or 0 for c in lote)
            peso  = sum(c.peso or 0 for c in lote)
            merc  = sum(c.valor_mercadoria or 0 for c in lote)
            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0
            clf, dev = _classificar(rs_kg, ref_rs_kg)
            label = nomes.get(canon) or f"Transp. {canon}"
            rows.append(DlgAnaliticoModel(
                empresa_id=empresa_id, dimensao="TRANSPORTADORA",
                chave=str(canon), chave_label=label,
                periodo_ref=periodo,
                qtd_ctes=len(lote), peso_total=round(peso, 2),
                frete_total=round(frete, 2), mercadoria_total=round(merc, 2),
                rs_kg=rs_kg, pct_frete=round(pct, 4),
                custo_medio_entrega=_div(frete, len(lote)),
                rs_kg_ref=ref_rs_kg, desvio_pct=dev, classificacao=clf,
                composicao_frete=_somar_composicao(lote),
            ))
        return rows

    # ── agregação: REGIÃO ─────────────────────────────────────────────────────

    def _agregar_regioes(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        refs: Dict,
    ) -> List[DlgAnaliticoModel]:
        grupos: Dict[str, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            r = (c.macro_regiao_destino or "INDEFINIDA")
            if hasattr(r, "value"):
                r = r.value
            grupos[r].append(c)

        rows = []
        for regiao, lote in grupos.items():
            frete = sum(c.valor_frete or 0 for c in lote)
            peso  = sum(c.peso or 0 for c in lote)
            merc  = sum(c.valor_mercadoria or 0 for c in lote)
            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0
            # referência: meta regional > mercado p50 > meta nacional
            meta_reg = refs["metas_reg"].get(regiao)
            ref = (
                (meta_reg.meta_rs_kg if meta_reg else 0)
                or refs["mercado_p50"].get(regiao)
                or (refs["meta_nac"].meta_rs_kg if refs["meta_nac"] else 0)
            )
            clf, dev = _classificar(rs_kg, ref)
            rows.append(DlgAnaliticoModel(
                empresa_id=empresa_id, dimensao="REGIAO",
                chave=regiao, chave_label=regiao,
                periodo_ref=periodo,
                qtd_ctes=len(lote), peso_total=round(peso, 2),
                frete_total=round(frete, 2), mercadoria_total=round(merc, 2),
                rs_kg=rs_kg, pct_frete=round(pct, 4),
                custo_medio_entrega=_div(frete, len(lote)),
                rs_kg_ref=ref, desvio_pct=dev, classificacao=clf,
                composicao_frete=_somar_composicao(lote),
            ))
        return rows

    # ── agregação: CLIENTE_FINAL (v6.7.0) ─────────────────────────────────────

    def _agregar_clientes(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        ref_rs_kg: float,
    ) -> List[DlgAnaliticoModel]:
        """Agrega por CLIENTE_FINAL — o destinatário da mercadoria (RN-67).

        5ª dimensão do motor genérico: mesma classificação (RN-25) e mesma
        referência nacional das demais dimensões financeiras. Identidade real
        via RN-68 (``_ident_cliente``) — raiz de CNPJ ou nome normalizado,
        nunca um id de cadastro (não existe tabela mestre de cliente nesta
        versão, OBJ-3/§2 da Especificação Técnica).
        """
        grupos: Dict[tuple, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            grupos[_ident_cliente(c)].append(c)

        rows = []
        for ident, lote in grupos.items():
            tipo, valor = ident
            frete = sum(c.valor_frete or 0 for c in lote)
            peso  = sum(c.peso or 0 for c in lote)
            merc  = sum(c.valor_mercadoria or 0 for c in lote)
            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0
            clf, dev = _classificar(rs_kg, ref_rs_kg)

            if tipo == "SEM_ID":
                chave, label = "SEM_ID", "Cliente não identificado"
            else:
                chave = f"{tipo}:{valor}"
                # Rótulo de exibição: nome real do primeiro CT-e do lote que
                # o traz (não o nome normalizado usado só para identidade).
                label = next(
                    (c.destinatario_nome for c in lote if c.destinatario_nome), None
                ) or (valor if tipo == "RAIZ" else "Cliente não identificado")

            rows.append(DlgAnaliticoModel(
                empresa_id=empresa_id, dimensao="CLIENTE_FINAL",
                chave=chave, chave_label=label,
                periodo_ref=periodo,
                qtd_ctes=len(lote), peso_total=round(peso, 2),
                frete_total=round(frete, 2), mercadoria_total=round(merc, 2),
                rs_kg=rs_kg, pct_frete=round(pct, 4),
                custo_medio_entrega=_div(frete, len(lote)),
                rs_kg_ref=ref_rs_kg, desvio_pct=dev, classificacao=clf,
                composicao_frete=_somar_composicao(lote),
            ))
        return rows

    # ── leitura ───────────────────────────────────────────────────────────────

    def listar(
        self,
        empresa_id: int,
        dimensao: Optional[str] = None,
        periodo_ref: Optional[str] = None,
        classificacao: Optional[str] = None,
        modo: str = "mensal",
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List:
        """Lista o analítico do DLG em um de dois modos:

        - ``mensal``      → uma linha por (entidade, mês).
        - ``consolidado`` → uma linha por entidade, agregando os meses do
          período. R$/kg, % frete e desvio são RECALCULADOS sobre os totais
          consolidados (não são médias dos meses).

        Ambos respeitam o intervalo ``data_inicio``/``data_fim``: como o
        analítico é persistido por competência (``periodo_ref`` = "YYYY-MM"),
        o intervalo é convertido em faixa de meses [AAAA-MM inicial, final].
        Sem intervalo = todos os períodos.

        No modo consolidado retorna dicts com o mesmo shape de
        ``DlgAnaliticoOut`` (id=0, periodo_ref="CONSOLIDADO").

        ``page``/``page_size`` (CA-16, v6.7.0): paginação server-side opcional,
        aplicada DEPOIS da ordenação/filtro e do enriquecimento causal —
        genérica às 5 dimensões (não exclusiva de CLIENTE_FINAL), mas sobretudo
        relevante para ela, que tem a maior cardinalidade potencial. Sem
        ``page``/``page_size`` = comportamento inalterado (sem paginação),
        preservando 100% do comportamento das 4 dimensões existentes (CA-11).
        """
        def _paginar(itens: List) -> List:
            if not page_size:
                return itens
            p = max(1, page or 1)
            ini = (p - 1) * page_size
            return itens[ini: ini + page_size]

        modo = (modo or "mensal").lower()
        mes_ini = data_inicio.strftime("%Y-%m") if data_inicio else None
        mes_fim = data_fim.strftime("%Y-%m") if data_fim else None

        def _aplicar_periodo(stmt):
            if mes_ini:
                stmt = stmt.where(DlgAnaliticoModel.periodo_ref >= mes_ini)
            if mes_fim:
                stmt = stmt.where(DlgAnaliticoModel.periodo_ref <= mes_fim)
            return stmt

        if modo == "consolidado":
            base = select(DlgAnaliticoModel).where(
                DlgAnaliticoModel.empresa_id == empresa_id
            )
            if dimensao:
                base = base.where(DlgAnaliticoModel.dimensao == dimensao.upper())
            base = _aplicar_periodo(base)
            rows = list(self.db.scalars(base).all())
            consolidados = self._consolidar(rows)
            # Enriquecimento ANTES do filtro de classificação: a mediana de
            # RN-75/RN-76 precisa da população completa de clientes do
            # período, não apenas do subconjunto filtrado (ex.: filtrar por
            # CRITICO não pode enviesar a mediana calculada só entre críticos).
            self._enriquecer_diagnostico_clientes(
                empresa_id, consolidados, data_inicio, data_fim)
            if classificacao:
                alvo = classificacao.upper()
                consolidados = [c for c in consolidados if c["classificacao"] == alvo]
            return _paginar(consolidados)

        # ── modo mensal ────────────────────────────────────────────────────────
        stmt = select(DlgAnaliticoModel).where(
            DlgAnaliticoModel.empresa_id == empresa_id
        )
        if dimensao:
            stmt = stmt.where(DlgAnaliticoModel.dimensao == dimensao.upper())
        if periodo_ref:
            stmt = stmt.where(DlgAnaliticoModel.periodo_ref == periodo_ref)
        stmt = _aplicar_periodo(stmt)
        stmt = stmt.order_by(
            DlgAnaliticoModel.periodo_ref.desc(),
            DlgAnaliticoModel.frete_total.desc(),
        )
        rows = list(self.db.scalars(stmt).all())
        # Mesmo motivo do modo consolidado: enriquece antes de filtrar por
        # classificação, para não enviesar a mediana usada por RN-75/RN-76.
        self._enriquecer_diagnostico_clientes(empresa_id, rows, data_inicio, data_fim)
        if classificacao:
            alvo = classificacao.upper()
            rows = [r for r in rows if r.classificacao == alvo]
        return _paginar(rows)

    # ── diagnóstico causal (RN-75/RN-76) ──────────────────────────────────────

    def _enriquecer_diagnostico_clientes(
        self,
        empresa_id: int,
        linhas: List,
        data_inicio: Optional[date],
        data_fim: Optional[date],
    ) -> None:
        """Calcula fragmentação (RN-75) e causa dominante (RN-76) in-place para
        as linhas CLIENTE_FINAL classificadas ATENÇÃO/CRÍTICO.

        Restrito a esse subconjunto (RN-76 passo 1 — EFICIENTE/SEM_REF não têm
        desvio a explicar), e a Parte B (a única que exige consulta extra a
        `ctes`) fica ainda mais restrita aos candidatos já filtrados pela
        Parte A (peso médio baixo) — nunca roda para todos os clientes do
        período (Especificação Técnica §3.4/§6).
        """
        clientes = [r for r in linhas if _campo(r, "dimensao") == "CLIENTE_FINAL"]
        if not clientes:
            return

        por_periodo: Dict[str, list] = defaultdict(list)
        for r in clientes:
            por_periodo[_campo(r, "periodo_ref") or "CONSOLIDADO"].append(r)

        for periodo, grupo in por_periodo.items():
            pesos_medios = [
                (_campo(r, "peso_total") or 0) / _campo(r, "qtd_ctes")
                for r in grupo if _campo(r, "qtd_ctes")
            ]
            mediana_peso = statistics.median(pesos_medios) if pesos_medios else 0.0

            pcts_validos = [
                _campo(r, "pct_componentes_adicionais") for r in grupo
                if _campo(r, "pct_componentes_adicionais") is not None
            ]
            limiar_adicionais = statistics.median(pcts_validos) if pcts_validos else 100.0

            alvo = [r for r in grupo if _campo(r, "classificacao") in ("ATENCAO", "CRITICO")]
            if not alvo:
                continue

            # Parte A — barata: já temos as linhas agregadas em memória.
            # Fragmentação pressupõe múltiplos despachos (cliente com 1 CT-e
            # nunca é sinalizado).
            candidatos = [
                r for r in alvo
                if (_campo(r, "qtd_ctes") or 0) > 1
                and mediana_peso > 0
                and (_campo(r, "peso_total") / _campo(r, "qtd_ctes")) < mediana_peso * LIMIAR_PESO_MEDIO_BAIXO
            ]

            # Parte B — só para quem passou na Parte A.
            fragmentados: set = set()
            if candidatos:
                identidades = {_chave_cliente_para_ident(_campo(r, "chave")) for r in candidatos}
                datas_por_ident = self._datas_por_cliente(
                    empresa_id, identidades, periodo, data_inicio, data_fim)
                for r in candidatos:
                    ident = _chave_cliente_para_ident(_campo(r, "chave"))
                    if _tem_janela_curta(datas_por_ident.get(ident, [])):
                        fragmentados.add(id(r))

            for r in alvo:
                tem_fragmentacao = id(r) in fragmentados
                diag = _diagnosticar_causa(
                    _campo(r, "pct_componentes_adicionais"), limiar_adicionais,
                    tem_fragmentacao, _campo(r, "ranking_componentes"),
                )
                if tem_fragmentacao:
                    qtd = _campo(r, "qtd_ctes") or 0
                    peso_medio_cliente = (_campo(r, "peso_total") or 0) / qtd if qtd else 0.0
                    diag["qtd_despachos"] = qtd
                    diag["janela_dias"] = JANELA_DIAS_FRAGMENTACAO
                    diag["pct_peso_abaixo_mediana"] = (
                        round(max(0.0, 1 - peso_medio_cliente / mediana_peso) * 100, 1)
                        if mediana_peso else None
                    )
                _definir_campo(r, "sinal_fragmentacao", tem_fragmentacao)
                _definir_campo(r, "causa_dominante", diag["causa"])
                _definir_campo(r, "causa_detalhe", diag)

    def _datas_por_cliente(
        self,
        empresa_id: int,
        identidades: set,
        periodo: str,
        data_inicio: Optional[date],
        data_fim: Optional[date],
    ) -> Dict[tuple, List[date]]:
        """RN-75 Parte B: datas de emissão dos CT-e ATIVOS de cada identidade,
        na janela do período (mês, em modo mensal; intervalo selecionado, em
        modo consolidado). Uma única query — os candidatos já chegam filtrados
        pela Parte A, tipicamente um subconjunto pequeno."""
        if periodo == "CONSOLIDADO":
            d_ini, d_fim = data_inicio, data_fim
        else:
            ano, mes = (int(x) for x in periodo.split("-"))
            d_ini = date(ano, mes, 1)
            d_fim = date(ano, mes, calendar.monthrange(ano, mes)[1])

        stmt = select(
            CTeModel.destinatario_cnpj, CTeModel.destinatario_nome, CTeModel.data_emissao,
        ).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.status == CTE_STATUS_ATIVO,
        )
        if d_ini:
            stmt = stmt.where(CTeModel.data_emissao >= d_ini)
        if d_fim:
            stmt = stmt.where(CTeModel.data_emissao <= d_fim)

        datas_por_ident: Dict[tuple, List[date]] = defaultdict(list)
        for cnpj, nome, data_emissao in self.db.execute(stmt).all():
            ident = _ident_cliente_str(cnpj, nome)
            if ident in identidades:
                datas_por_ident[ident].append(data_emissao)
        return datas_por_ident

    # ── consolidação (função pura sobre linhas mensais persistidas) ───────────

    @staticmethod
    def _consolidar(rows: List[DlgAnaliticoModel]) -> List[dict]:
        """Agrega as linhas mensais por (dimensão, chave) → uma linha por
        entidade. Não reprocessa CT-e: opera sobre o que já está em
        ``dlg_analitico``, evitando duplicação da lógica de agregação.

        O benchmark (``rs_kg_ref``) é invariante no tempo para cada entidade;
        ainda assim usamos MÉDIA PONDERADA POR PESO do ref, para que — quando o
        MBL passar a popular P50 mensal — o consolidado continue correto sem
        refatoração. Quando o ref é constante, a ponderação devolve o próprio
        valor.
        """
        grupos: Dict[Tuple[str, str], List[DlgAnaliticoModel]] = defaultdict(list)
        for r in rows:
            grupos[(r.dimensao, r.chave)].append(r)

        consolidados: List[dict] = []
        for (dim, chave), lote in grupos.items():
            peso  = sum(r.peso_total or 0 for r in lote)
            frete = sum(r.frete_total or 0 for r in lote)
            merc  = sum(r.mercadoria_total or 0 for r in lote)
            qtd   = sum(r.qtd_ctes or 0 for r in lote)

            rs_kg = _div(frete, peso)
            pct   = _div(frete, merc) * 100 if merc else 0.0

            soma_ref_pond = sum((r.rs_kg_ref or 0) * (r.peso_total or 0) for r in lote)
            ref = (
                _div(soma_ref_pond, peso) if peso
                else next((r.rs_kg_ref for r in lote if r.rs_kg_ref), 0.0)
            )
            clf, dev = _classificar(rs_kg, ref)

            # Composição do frete consolidada: soma das composições mensais
            # por categoria (v6.7.0, genérico às 5 dimensões — §4.2).
            comp_consolidada: Dict[str, float] = defaultdict(float)
            for r in lote:
                for categoria, valor in (r.composicao_frete or {}).items():
                    comp_consolidada[categoria] += valor or 0.0
            comp_consolidada = {k: round(v, 2) for k, v in comp_consolidada.items()} or None

            frete_total_r = round(frete, 2)
            base = max(lote, key=lambda r: r.frete_total or 0)  # rótulo do dominante
            consolidados.append({
                "id": 0,
                "empresa_id": base.empresa_id,
                "dimensao": dim,
                "chave": chave,
                "chave_label": base.chave_label,
                "periodo_ref": "CONSOLIDADO",
                "qtd_ctes": qtd,
                "peso_total": round(peso, 2),
                "frete_total": frete_total_r,
                "mercadoria_total": round(merc, 2),
                "rs_kg": rs_kg,
                "pct_frete": round(pct, 4),
                "custo_medio_entrega": _div(frete, qtd),
                "rs_kg_ref": round(ref, 4),
                "desvio_pct": dev,
                "classificacao": clf,
                "composicao_frete": comp_consolidada,
                "frete_transporte_principal": calc_frete_transporte_principal(comp_consolidada),
                "pct_componentes_adicionais": calc_pct_componentes_adicionais(comp_consolidada, frete_total_r),
                "ranking_componentes": calc_ranking_componentes(comp_consolidada),
                "peso_medio": round(peso / qtd, 4) if qtd else None,
                "ticket_medio": round(merc / qtd, 2) if qtd else None,
                "impacto_financeiro_potencial": (
                    round(max(0.0, rs_kg - ref) * peso, 2) if ref else 0.0
                ),
                "sinal_fragmentacao": None,
                "causa_dominante": None,
                "causa_detalhe": None,
            })

        consolidados.sort(key=lambda d: d["frete_total"], reverse=True)
        return consolidados

    def listar_outliers(
        self,
        empresa_id: int,
        periodo_ref: Optional[str] = None,
        tipo: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[DlgOutlierModel]:
        stmt = select(DlgOutlierModel).where(
            DlgOutlierModel.empresa_id == empresa_id
        )
        if periodo_ref:
            stmt = stmt.where(DlgOutlierModel.periodo_ref == periodo_ref)
        if data_inicio:
            stmt = stmt.where(DlgOutlierModel.periodo_ref >= data_inicio.strftime("%Y-%m"))
        if data_fim:
            stmt = stmt.where(DlgOutlierModel.periodo_ref <= data_fim.strftime("%Y-%m"))
        if tipo:
            stmt = stmt.where(DlgOutlierModel.tipo_outlier == tipo.upper())
        stmt = stmt.order_by(DlgOutlierModel.desvio_pct.desc())
        return list(self.db.scalars(stmt).all())

    def resumo(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict:
        """KPIs consolidados para o dashboard DLG, respeitando o intervalo de
        datas selecionado (sem intervalo = todos os períodos)."""
        rows = self.listar(empresa_id, data_inicio=data_inicio, data_fim=data_fim)
        if not rows:
            return {}
        por_dim: Dict[str, list] = defaultdict(list)
        for r in rows:
            por_dim[r.dimensao].append(r)

        def _top(lst, n=5):
            return sorted(lst, key=lambda x: x.frete_total, reverse=True)[:n]

        def _dist(lst):
            clf = defaultdict(int)
            for r in lst:
                clf[r.classificacao] += 1
            return dict(clf)

        return {
            "distribuicao_classificacao": _dist(rows),
            "top_filiais": [
                {"chave": r.chave_label, "frete": r.frete_total,
                 "rs_kg": r.rs_kg, "classificacao": r.classificacao}
                for r in _top(por_dim.get("FILIAL", []))
            ],
            # compatibilidade retroativa: mantém a chave antiga apontando para filiais
            "top_clientes": [
                {"chave": r.chave_label, "frete": r.frete_total,
                 "rs_kg": r.rs_kg, "classificacao": r.classificacao}
                for r in _top(por_dim.get("FILIAL", []))
            ],
            # v6.7.0 — dimensão CLIENTE_FINAL (destinatário real, não a filial
            # tomadora). Chave nova para não colidir com a retrocompatibilidade
            # de "top_clientes" acima (Especificação Técnica §2, decisão 2).
            "top_clientes_finais": [
                {"chave": r.chave_label, "frete": r.frete_total,
                 "rs_kg": r.rs_kg, "classificacao": r.classificacao}
                for r in _top(por_dim.get("CLIENTE_FINAL", []))
            ],
            "top_rotas_criticas": [
                {"rota": r.chave_label, "frete": r.frete_total,
                 "rs_kg": r.rs_kg, "desvio_pct": r.desvio_pct}
                for r in sorted(
                    [r for r in por_dim.get("ROTA", []) if r.classificacao == "CRITICO"],
                    key=lambda x: x.desvio_pct, reverse=True
                )[:5]
            ],
            "por_dimensao": {
                dim: _dist(lst) for dim, lst in por_dim.items()
            },
        }
