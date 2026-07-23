"""MBL — Motor Estatístico de Benchmark Logístico.

Constrói o "Source of Truth de custo logístico esperado" a partir do histórico
real (CT-e), EXCLUINDO os outliers já detectados pelo DLG, e calcula a
distribuição percentílica (P10–P90) por dimensão e período.

Princípios da spec (Parte 3):
- Estatístico: percentis P10/P25/P50/P75/P90 + média + desvio-padrão.
- Auditável: cada linha registra amostra, outliers excluídos e versão.
- Reproduzível: recálculo idempotente por período (mesmo input → mesmo output).
- Segmentação: REGIÃO, CLUSTER logístico e ROTA OD.
- Métricas: R$/kg, % frete sobre faturamento, custo médio por entrega.
- Consistência: threshold de amostra mínima → low_confidence; outliers do DLG
  NÃO entram no cálculo.

Faixas de eficiência (derivadas na leitura):
- eficiente   → valor ≤ P25
- normal      → P25 < valor < P75
- ineficiente → valor ≥ P75
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.entities import CTE_STATUS_ATIVO
from app.infrastructure.database.models import (
    ClusterClienteModel,
    CTeModel,
    DlgOutlierModel,
    FilialModel,
    HubLogisticoModel,
    MblBenchmarkModel,
    TransportadoraModel,
)
from app.application.use_cases.dlg import _ident_cliente

# Amostra mínima por segmento (configurável via processar()). Abaixo disso o
# segmento entra como low_confidence e não deve compor ranking oficial.
THRESHOLD_AMOSTRA_PADRAO = 5

# Corte de cardinalidade para dimensões potencialmente numerosas (CLIENTE,
# FILIAL) — sem isso, centenas de clientes distintos × 3 métricas × N
# períodos geram milhares de linhas persistidas por empresa. Mantém só os
# top-N segmentos por tamanho de amostra em cada período; TRANSPORTADORA não
# precisa de corte (cardinalidade naturalmente baixa).
TOP_N_DIMENSAO_PADRAO = 100

METRICAS = ("RS_KG", "PCT_FRETE", "CUSTO_ENTREGA")


def _percentil(valores_ordenados: List[float], p: float) -> float:
    """Percentil por interpolação linear (método reproduzível e auditável)."""
    if not valores_ordenados:
        return 0.0
    if len(valores_ordenados) == 1:
        return round(valores_ordenados[0], 4)
    k = (len(valores_ordenados) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(valores_ordenados) - 1)
    d = k - f
    val = valores_ordenados[f] + (valores_ordenados[c] - valores_ordenados[f]) * d
    return round(val, 4)


class MblUseCase:
    def __init__(self, db: Session):
        self.db = db

    # ── ponto de entrada ────────────────────────────────────────────────────

    def processar(
        self,
        empresa_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        threshold: int = THRESHOLD_AMOSTRA_PADRAO,
        top_n_dimensao: int = TOP_N_DIMENSAO_PADRAO,
    ) -> Dict:
        """Recalcula o benchmark MBL por período mensal, excluindo outliers do
        DLG. Idempotente: substitui as versões anteriores do mesmo período,
        incrementando o número de versão (auditoria)."""
        ctes = self._carregar_ctes(empresa_id, data_inicio, data_fim)
        if not ctes:
            return {"status": "sem_dados", "ctes": 0}

        ids_outliers_por_periodo = self._outliers_por_periodo(empresa_id)
        clusters = self._mapa_clusters(empresa_id)
        transportadoras = self._mapa_transportadoras(empresa_id)
        filiais = self._mapa_filiais(empresa_id)

        # agrupa por período (mensal)
        por_periodo: Dict[str, List[CTeModel]] = defaultdict(list)
        for c in ctes:
            por_periodo[c.data_emissao.strftime("%Y-%m")].append(c)

        total_linhas = 0
        periodos = []
        for periodo, lote in por_periodo.items():
            outliers_ids = ids_outliers_por_periodo.get(periodo, set())
            linhas = self._processar_periodo(
                empresa_id, periodo, lote, outliers_ids, clusters,
                transportadoras, filiais, threshold, top_n_dimensao,
            )
            total_linhas += linhas
            periodos.append(periodo)

        self.db.commit()
        return {
            "status": "ok",
            "ctes": len(ctes),
            "periodos": sorted(periodos),
            "linhas_benchmark": total_linhas,
        }

    # ── carregamento ────────────────────────────────────────────────────────

    def _carregar_ctes(self, empresa_id, data_inicio, data_fim) -> List[CTeModel]:
        stmt = select(CTeModel).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.status == CTE_STATUS_ATIVO,
        )
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        return list(self.db.scalars(stmt).all())

    def _outliers_por_periodo(self, empresa_id: int) -> Dict[str, set]:
        """IDs de CT-e marcados como outlier pelo DLG, indexados por período.
        Estes são EXCLUÍDOS do cálculo do benchmark (spec 7.7)."""
        rows = self.db.execute(
            select(DlgOutlierModel.cte_id, DlgOutlierModel.periodo_ref).where(
                DlgOutlierModel.empresa_id == empresa_id
            )
        ).all()
        mapa: Dict[str, set] = defaultdict(set)
        for cte_id, periodo in rows:
            mapa[periodo].add(cte_id)
        return mapa

    def _mapa_clusters(self, empresa_id: int) -> Dict[Tuple[str, str], str]:
        """(uf, municipio) → código do hub/cluster. Município vazio = regra da UF."""
        rows = self.db.execute(
            select(ClusterClienteModel, HubLogisticoModel.codigo)
            .join(HubLogisticoModel, ClusterClienteModel.hub_id == HubLogisticoModel.id)
            .where(ClusterClienteModel.empresa_id == empresa_id)
        ).all()
        mapa: Dict[Tuple[str, str], str] = {}
        for cluster, hub_codigo in rows:
            mapa[(cluster.uf.upper(), (cluster.municipio or "").strip().lower())] = hub_codigo
        return mapa

    def _cluster_do_cte(self, cte: CTeModel, mapa: Dict) -> Optional[str]:
        uf = (cte.uf_destino or "").upper()
        mun = (cte.municipio_destino or "").strip().lower()
        # match exato UF+município, depois fallback UF inteira
        return mapa.get((uf, mun)) or mapa.get((uf, "")) or None

    def _mapa_transportadoras(self, empresa_id: int) -> Dict[int, str]:
        """id → nome, mesmo padrão de `_mapa_clusters` (carregado uma vez,
        fora do loop por CT-e, evitando N+1)."""
        rows = self.db.execute(
            select(TransportadoraModel).where(TransportadoraModel.empresa_id == empresa_id)
        ).scalars().all()
        return {t.id: (t.nome_fantasia or t.razao_social) for t in rows}

    def _mapa_filiais(self, empresa_id: int) -> Dict[str, str]:
        """CNPJ (só dígitos, já persistido assim) → razão social da filial.
        Não há FK direta filial↔CT-e; o cruzamento é por `tomador_cnpj`."""
        rows = self.db.execute(
            select(FilialModel).where(FilialModel.empresa_id == empresa_id)
        ).scalars().all()
        return {f.cnpj: f.razao_social for f in rows if f.cnpj}

    # ── processamento de um período ─────────────────────────────────────────

    def _processar_periodo(
        self,
        empresa_id: int,
        periodo: str,
        ctes: List[CTeModel],
        outliers_ids: set,
        clusters: Dict,
        transportadoras: Dict[int, str],
        filiais: Dict[str, str],
        threshold: int,
        top_n_dimensao: int = TOP_N_DIMENSAO_PADRAO,
    ) -> int:
        # próxima versão (auditoria): MAX(versao)+1 do período
        versao_atual = self.db.scalar(
            select(func.max(MblBenchmarkModel.versao)).where(
                MblBenchmarkModel.empresa_id == empresa_id,
                MblBenchmarkModel.periodo_ref == periodo,
            )
        )
        nova_versao = (versao_atual or 0) + 1

        # idempotência: remove a versão anterior do período antes de gravar
        self.db.execute(
            delete(MblBenchmarkModel).where(
                MblBenchmarkModel.empresa_id == empresa_id,
                MblBenchmarkModel.periodo_ref == periodo,
            )
        )

        # coleta valores por (dimensao, segmento, metrica), excluindo outliers
        # estrutura: amostras[(dim, seg, metrica)] = [valores...]
        amostras: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
        outliers_excluidos = 0

        # nome do cliente por identidade RN-68 (raiz de CNPJ ou nome
        # normalizado) — pré-carregado para que o mesmo cliente sempre vire
        # o mesmo `segmento` (string), independentemente de variação de
        # grafia do destinatário entre CT-es (primeiro nome não vazio vence).
        nomes_cliente: Dict[Tuple[str, Optional[str]], str] = {}
        for c in ctes:
            ident = _ident_cliente(c)
            if ident not in nomes_cliente and c.destinatario_nome:
                nomes_cliente[ident] = c.destinatario_nome

        for c in ctes:
            if c.id in outliers_ids:
                outliers_excluidos += 1
                continue
            if not c.peso or c.peso <= 0:
                continue

            rs_kg = c.valor_frete / c.peso
            pct_frete = (c.valor_frete / c.valor_mercadoria * 100) if c.valor_mercadoria else None
            custo_entrega = c.valor_frete  # custo por entrega = frete do CT-e

            # dimensão REGIÃO (destino)
            regiao = c.macro_regiao_destino
            if hasattr(regiao, "value"):
                regiao = regiao.value
            regiao = regiao or "INDEFINIDA"
            # dimensão ROTA (OD por UF)
            rota = f"{c.uf_origem or '??'}→{c.uf_destino or '??'}"
            # dimensão CLUSTER
            cluster = self._cluster_do_cte(c, clusters)

            segmentos = [("REGIAO", regiao), ("ROTA", rota)]
            if cluster:
                segmentos.append(("CLUSTER", cluster))
            nome_transportadora = transportadoras.get(c.transportadora_id) if c.transportadora_id else None
            if nome_transportadora:
                segmentos.append(("TRANSPORTADORA", nome_transportadora))
            nome_filial = filiais.get(c.tomador_cnpj) if c.tomador_cnpj else None
            if nome_filial:
                segmentos.append(("FILIAL", nome_filial))
            tipo_cliente, valor_cliente = _ident_cliente(c)
            if tipo_cliente == "SEM_ID":
                label_cliente = "Cliente não identificado"
            else:
                label_cliente = nomes_cliente.get((tipo_cliente, valor_cliente)) or valor_cliente
            segmentos.append(("CLIENTE", label_cliente))

            for dim, seg in segmentos:
                amostras[(dim, seg, "RS_KG")].append(rs_kg)
                amostras[(dim, seg, "CUSTO_ENTREGA")].append(custo_entrega)
                if pct_frete is not None:
                    amostras[(dim, seg, "PCT_FRETE")].append(pct_frete)

        self._aplicar_top_n(amostras, top_n_dimensao)

        # grava as estatísticas
        linhas = 0
        for (dim, seg, metrica), valores in amostras.items():
            if not valores:
                continue
            valores.sort()
            media = round(statistics.mean(valores), 4)
            dp = round(statistics.stdev(valores), 4) if len(valores) > 1 else 0.0
            self.db.add(MblBenchmarkModel(
                empresa_id=empresa_id,
                dimensao=dim, segmento=seg, metrica=metrica,
                periodo_ref=periodo,
                amostra=len(valores),
                p10=_percentil(valores, 10),
                p25=_percentil(valores, 25),
                p50=_percentil(valores, 50),
                p75=_percentil(valores, 75),
                p90=_percentil(valores, 90),
                media=media, desvio_padrao=dp,
                low_confidence=len(valores) < threshold,
                outliers_excluidos=outliers_excluidos,
                versao=nova_versao,
            ))
            linhas += 1
        return linhas

    def _aplicar_top_n(
        self, amostras: Dict[Tuple[str, str, str], List[float]], top_n: int
    ) -> None:
        """Corta CLIENTE/FILIAL para os top-N segmentos por tamanho de
        amostra (referência: métrica RS_KG, sempre populada para todo
        segmento), mutando `amostras` in-place antes da gravação. Evita
        persistir milhares de linhas quando há centenas de clientes/filiais
        distintos num único período."""
        tamanho_por_segmento: Dict[Tuple[str, str], int] = {}
        for (dim, seg, metrica), valores in amostras.items():
            if metrica == "RS_KG":
                tamanho_por_segmento[(dim, seg)] = len(valores)

        for dim in ("CLIENTE", "FILIAL"):
            segmentos_dim = [(seg, n) for (d, seg), n in tamanho_por_segmento.items() if d == dim]
            if len(segmentos_dim) <= top_n:
                continue
            manter = {
                seg for seg, _ in sorted(segmentos_dim, key=lambda x: x[1], reverse=True)[:top_n]
            }
            for chave in list(amostras.keys()):
                d, seg, _ = chave
                if d == dim and seg not in manter:
                    del amostras[chave]

    # ── leitura / consulta ──────────────────────────────────────────────────

    def listar(
        self,
        empresa_id: int,
        dimensao: Optional[str] = None,
        metrica: Optional[str] = None,
        periodo_ref: Optional[str] = None,
        segmento: Optional[str] = None,
        segmento_contains: Optional[str] = None,
        incluir_low_confidence: bool = True,
    ) -> List[MblBenchmarkModel]:
        stmt = select(MblBenchmarkModel).where(
            MblBenchmarkModel.empresa_id == empresa_id
        )
        if dimensao:
            stmt = stmt.where(MblBenchmarkModel.dimensao == dimensao.upper())
        if metrica:
            stmt = stmt.where(MblBenchmarkModel.metrica == metrica.upper())
        if periodo_ref:
            stmt = stmt.where(MblBenchmarkModel.periodo_ref == periodo_ref)
        if segmento:
            stmt = stmt.where(MblBenchmarkModel.segmento == segmento)
        if segmento_contains:
            stmt = stmt.where(MblBenchmarkModel.segmento.ilike(f"%{segmento_contains}%"))
        if not incluir_low_confidence:
            stmt = stmt.where(MblBenchmarkModel.low_confidence.is_(False))
        stmt = stmt.order_by(
            MblBenchmarkModel.periodo_ref.desc(),
            MblBenchmarkModel.dimensao,
            MblBenchmarkModel.segmento,
        )
        return list(self.db.scalars(stmt).all())

    def faixa(self, valor: float, bench: MblBenchmarkModel) -> str:
        """Classifica um valor real contra o benchmark (spec 7.6.2)."""
        if valor <= bench.p25:
            return "EFICIENTE"
        if valor >= bench.p75:
            return "INEFICIENTE"
        return "NORMAL"

    def comparar(
        self,
        empresa_id: int,
        dimensao: str,
        segmento: str,
        metrica: str,
        valor: float,
        periodo_ref: Optional[str] = None,
    ) -> Optional[Dict]:
        """Compara um valor real contra o benchmark oficial do segmento.
        Usado pelo DLG e pelo MCL como referência."""
        stmt = select(MblBenchmarkModel).where(
            MblBenchmarkModel.empresa_id == empresa_id,
            MblBenchmarkModel.dimensao == dimensao.upper(),
            MblBenchmarkModel.segmento == segmento,
            MblBenchmarkModel.metrica == metrica.upper(),
        )
        if periodo_ref:
            stmt = stmt.where(MblBenchmarkModel.periodo_ref == periodo_ref)
        stmt = stmt.order_by(MblBenchmarkModel.periodo_ref.desc())
        bench = self.db.scalars(stmt).first()
        if not bench:
            return None
        desvio_p50 = round((valor - bench.p50) / bench.p50 * 100, 2) if bench.p50 else 0.0
        return {
            "valor": valor,
            "faixa": self.faixa(valor, bench),
            "desvio_p50_pct": desvio_p50,
            "p10": bench.p10, "p25": bench.p25, "p50": bench.p50,
            "p75": bench.p75, "p90": bench.p90,
            "amostra": bench.amostra,
            "low_confidence": bench.low_confidence,
            "periodo_ref": bench.periodo_ref,
            "versao": bench.versao,
        }
