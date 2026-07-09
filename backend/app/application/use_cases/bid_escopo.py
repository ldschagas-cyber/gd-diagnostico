"""Geração automática de escopo do BID a partir dos CT-es históricos.

Usa SQL GROUP BY para agregar os dados sem carregar todos os CT-es em memória.
Suporta agrupamentos: REGIAO, UF, FILIAL, TRANSPORTADORA, FAIXA_PESO.

Faixas de peso são livres — definidas pelo usuário no payload da requisição.
"""
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from app.domain.entities import (
    BidEscopo, TipoAgrupamentoEnum, Transportadora,
)
from app.domain.repositories import IBidEscopoRepository
from app.infrastructure.database.models import (
    CidadeModel, CTeModel, FilialModel, RegiaoModel,
)


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


class EscopoUseCase:
    def __init__(
        self,
        db: Session,
        escopo_repo: IBidEscopoRepository,
    ):
        self.db = db
        self.escopo_repo = escopo_repo

    def listar(self, bid_id: int) -> List[BidEscopo]:
        return self.escopo_repo.list_by_bid(bid_id)

    def gerar(
        self,
        bid_id: int,
        empresa_id: int,
        data_inicio: date,
        data_fim: date,
        tipo_agrupamento: TipoAgrupamentoEnum,
        faixas_peso: Optional[List[Dict]] = None,
        nome_transp_map: Optional[Dict[int, str]] = None,
        segmentacao_tipo: str = "GERAL",
        segmentacao_valor: str = "",
    ) -> List[BidEscopo]:
        """Gera ou atualiza o escopo do BID para o tipo de agrupamento solicitado.

        Para FAIXA_PESO, faixas_peso deve ser uma lista de dicts:
          [{"label": "0-100kg", "min": 0, "max": 100}, ...]

        Para TRANSPORTADORA, nome_transp_map deve ser {id: "Nome Transportadora"}.

        Segmentação (filtro aplicado ANTES da agregação, restringindo quais
        CT-es entram no escopo):
          - GERAL: sem filtro.
          - REGIAO: macro-região de destino == segmentacao_valor.
          - CIDADE: município de destino == segmentacao_valor.
          - REGIAO_LOGISTICA: cidade de destino pertence à região cadastrada
            de nome == segmentacao_valor (cidades.regiao_id → regioes.nome).
        """
        self._seg_tipo = (segmentacao_tipo or "GERAL").upper()
        self._seg_valor = (segmentacao_valor or "").strip()
        # Remove itens anteriores do mesmo agrupamento
        existentes = self.escopo_repo.list_by_bid(bid_id)
        for e in existentes:
            if e.tipo_agrupamento == tipo_agrupamento:
                self.escopo_repo.delete(e.id)

        itens: List[BidEscopo] = []

        if tipo_agrupamento == TipoAgrupamentoEnum.REGIAO:
            itens = self._agregar_por_campo(
                bid_id, empresa_id, data_inicio, data_fim,
                CTeModel.macro_regiao_destino, tipo_agrupamento,
            )

        elif tipo_agrupamento == TipoAgrupamentoEnum.UF:
            itens = self._agregar_por_campo(
                bid_id, empresa_id, data_inicio, data_fim,
                CTeModel.uf_destino, tipo_agrupamento,
            )

        elif tipo_agrupamento == TipoAgrupamentoEnum.TRANSPORTADORA:
            itens = self._agregar_por_transportadora(
                bid_id, empresa_id, data_inicio, data_fim,
                nome_transp_map or {},
            )

        elif tipo_agrupamento == TipoAgrupamentoEnum.FILIAL:
            itens = self._agregar_por_filial(
                bid_id, empresa_id, data_inicio, data_fim,
            )

        elif tipo_agrupamento == TipoAgrupamentoEnum.FAIXA_PESO:
            itens = self._agregar_por_faixa_peso(
                bid_id, empresa_id, data_inicio, data_fim, faixas_peso or [],
            )

        # Persiste os itens novos
        criados = []
        for item in itens:
            criados.append(self.escopo_repo.create(item))
        return criados

    # ── helpers privados ──────────────────────────────────────────────────

    def _base_query(self, empresa_id: int, data_inicio: date, data_fim: date):
        stmt = (
            select(
                func.sum(CTeModel.valor_frete).label("valor_frete_total"),
                func.sum(CTeModel.valor_mercadoria).label("valor_mercadoria_total"),
                func.sum(CTeModel.peso).label("peso_total"),
                func.count(CTeModel.id).label("qtd_embarques"),
            )
            .where(CTeModel.empresa_id == empresa_id)
            .where(CTeModel.data_emissao >= data_inicio)
            .where(CTeModel.data_emissao <= data_fim)
        )
        return self._aplicar_segmentacao(stmt)

    def _aplicar_segmentacao(self, stmt):
        """Adiciona o filtro de segmentação do BID à query (se houver)."""
        tipo = getattr(self, "_seg_tipo", "GERAL")
        valor = getattr(self, "_seg_valor", "")
        if tipo in ("", "GERAL") or not valor:
            return stmt

        if tipo == "REGIAO":
            return stmt.where(func.lower(CTeModel.macro_regiao_destino) == valor.lower())

        if tipo == "CIDADE":
            return stmt.where(func.lower(CTeModel.municipio_destino) == valor.lower())

        if tipo == "REGIAO_LOGISTICA":
            # CT-e cuja cidade de destino pertence à região logística cadastrada.
            sub = exists().where(and_(
                RegiaoModel.nome == valor,
                CidadeModel.regiao_id == RegiaoModel.id,
                func.lower(CidadeModel.nome) == func.lower(CTeModel.municipio_destino),
                CidadeModel.uf == CTeModel.uf_destino,
            ))
            return stmt.where(sub)

        return stmt

    def _agregar_por_campo(
        self, bid_id, empresa_id, data_inicio, data_fim, campo, tipo
    ) -> List[BidEscopo]:
        stmt = (
            self._base_query(empresa_id, data_inicio, data_fim)
            .add_columns(campo.label("grupo"))
            .group_by(campo)
        )
        rows = self.db.execute(stmt).all()
        return [self._linha(bid_id, tipo, r.grupo or "Não definida", r) for r in rows]

    def _agregar_por_transportadora(
        self, bid_id, empresa_id, data_inicio, data_fim, nomes
    ) -> List[BidEscopo]:
        stmt = (
            self._base_query(empresa_id, data_inicio, data_fim)
            .add_columns(CTeModel.transportadora_id.label("grupo"))
            .group_by(CTeModel.transportadora_id)
        )
        rows = self.db.execute(stmt).all()
        return [
            self._linha(
                bid_id, TipoAgrupamentoEnum.TRANSPORTADORA,
                nomes.get(r.grupo, f"Transportadora {r.grupo}"), r,
            )
            for r in rows
        ]

    def _agregar_por_filial(
        self, bid_id, empresa_id, data_inicio, data_fim
    ) -> List[BidEscopo]:
        # Agrupa por tomador_cnpj e enriquece com nome da filial
        stmt = (
            self._base_query(empresa_id, data_inicio, data_fim)
            .add_columns(CTeModel.tomador_cnpj.label("grupo"))
            .group_by(CTeModel.tomador_cnpj)
        )
        rows = self.db.execute(stmt).all()
        # Mapeia CNPJ → razão social da filial
        filiais = self.db.scalars(
            select(FilialModel).where(FilialModel.empresa_id == empresa_id)
        ).all()
        cnpj_map = {f.cnpj: f.razao_social for f in filiais}
        return [
            self._linha(
                bid_id, TipoAgrupamentoEnum.FILIAL,
                cnpj_map.get(r.grupo, r.grupo or "Matriz"), r,
            )
            for r in rows
        ]

    def _agregar_por_faixa_peso(
        self, bid_id, empresa_id, data_inicio, data_fim, faixas
    ) -> List[BidEscopo]:
        """Faixas livres: [{label, min, max}]. Sem faixas = grupo único 'Total'."""
        if not faixas:
            stmt = self._base_query(empresa_id, data_inicio, data_fim)
            row = self.db.execute(stmt).one()
            return [self._linha(bid_id, TipoAgrupamentoEnum.FAIXA_PESO, "Total", row)]

        itens = []
        for faixa in faixas:
            stmt = (
                self._base_query(empresa_id, data_inicio, data_fim)
                .where(CTeModel.peso >= faixa.get("min", 0))
            )
            if faixa.get("max") is not None:
                stmt = stmt.where(CTeModel.peso < faixa["max"])
            row = self.db.execute(stmt).one()
            itens.append(
                self._linha(bid_id, TipoAgrupamentoEnum.FAIXA_PESO,
                            faixa.get("label", f">{faixa.get('min',0)}kg"), row)
            )
        return itens

    def _linha(self, bid_id, tipo, grupo, row) -> BidEscopo:
        frete = float(row.valor_frete_total or 0)
        merc = float(row.valor_mercadoria_total or 0)
        peso = float(row.peso_total or 0)
        qtd = int(row.qtd_embarques or 0)
        return BidEscopo(
            bid_id=bid_id, tipo_agrupamento=tipo, valor_grupo=grupo,
            peso_total=peso, valor_frete_total=frete,
            valor_mercadoria_total=merc, qtd_embarques=qtd,
            frete_rs_kg=_div(frete, peso), frete_pct=_div(frete, merc) * 100,
        )
