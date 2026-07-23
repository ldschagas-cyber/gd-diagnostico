"""Modelos ORM (SQLAlchemy). Camada de infraestrutura.

Mantidos separados das entidades de domínio para respeitar a Arquitetura Limpa.
"""
from datetime import date, datetime
from typing import ClassVar, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(20), default="ANALISTA", nullable=True)
    # Multi-tenant (R-01): empresa padrão/preferida — usada só para pré-selecionar
    # a empresa na tela de login. NULL + is_superuser = acesso global (equipe GD
    # Conecta). A fonte de verdade da autorização é `usuario_empresas` (M:N) via
    # o relationship `empresas` abaixo, não mais este campo.
    empresa_id: Mapped[int | None] = mapped_column(
        ForeignKey("empresas.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    empresas: Mapped[list["EmpresaModel"]] = relationship(
        "EmpresaModel", secondary="usuario_empresas", lazy="selectin",
    )


class UsuarioEmpresaModel(Base):
    """Vínculo M:N usuário↔empresa (login baseado em empresa, v6.11).

    Fonte de verdade da autorização multi-tenant — `UserModel.empresa_id`
    passa a servir só de empresa padrão/preferida (pré-seleção na tela de
    login), não mais de checagem de acesso.
    """
    __tablename__ = "usuario_empresas"
    __table_args__ = (
        UniqueConstraint("usuario_id", "empresa_id", name="uq_usuario_empresa"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmpresaModel(Base):
    __tablename__ = "empresas"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(200))
    nome_fantasia: Mapped[str] = mapped_column(String(200), default="")
    cnpj_matriz: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(10), default="ATIVO")
    # Setor (segmento econômico) — base para filtros, dashboards e benchmark
    # setorial. Vocabulário controlado na camada de aplicação (SetorEnum).
    # Indexado para agregações por segmento. server_default garante o
    # preenchimento das linhas já existentes na migração.
    setor: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="Outros", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    filiais: Mapped[list["FilialModel"]] = relationship(
        back_populates="empresa", cascade="all, delete-orphan"
    )


class FilialModel(Base):
    __tablename__ = "filiais"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    razao_social: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[str] = mapped_column(String(20), index=True)
    cidade: Mapped[str] = mapped_column(String(120), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")

    empresa: Mapped["EmpresaModel"] = relationship(back_populates="filiais")


class TransportadoraModel(Base):
    __tablename__ = "transportadoras"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("empresas.id"), nullable=True, index=True
    )
    razao_social: Mapped[str] = mapped_column(String(200))
    nome_fantasia: Mapped[str] = mapped_column(String(200), default="")
    cnpj: Mapped[str] = mapped_column(String(20), index=True)
    endereco: Mapped[str] = mapped_column(String(200), default="")
    cidade: Mapped[str] = mapped_column(String(120), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")
    cep: Mapped[str] = mapped_column(String(10), default="")
    contato: Mapped[str] = mapped_column(String(120), default="")
    telefone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(150), default="")
    status: Mapped[str] = mapped_column(String(10), default="ATIVO")


class RegiaoModel(Base):
    __tablename__ = "regioes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    descricao: Mapped[str] = mapped_column(String(255), default="")


class CidadeModel(Base):
    __tablename__ = "cidades"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), index=True)
    uf: Mapped[str] = mapped_column(String(2), index=True)
    regiao_id: Mapped[int | None] = mapped_column(ForeignKey("regioes.id"), nullable=True)
    macro_regiao: Mapped[str | None] = mapped_column(String(15), nullable=True)


class MetaNacionalModel(Base):
    """Meta nacional (R$/kg e % Frete), por empresa-cliente."""
    __tablename__ = "meta_nacional"
    __table_args__ = (
        UniqueConstraint("empresa_id", name="uq_meta_nacional_empresa"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    meta_rs_kg: Mapped[float] = mapped_column(Float, default=0.0)
    meta_pct_frete: Mapped[float] = mapped_column(Float, default=0.0)


class MetaRegionalModel(Base):
    """Meta por macrorregião (R$/kg, % Frete, prazo, orçamento), por empresa-cliente."""
    __tablename__ = "meta_regional"
    __table_args__ = (
        UniqueConstraint("empresa_id", "macro_regiao", name="uq_meta_regional_empresa_macro"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    macro_regiao: Mapped[str] = mapped_column(String(15), index=True)
    meta_rs_kg: Mapped[float] = mapped_column(Float, default=0.0)
    meta_pct_frete: Mapped[float] = mapped_column(Float, default=0.0)
    prazo_medio_meta: Mapped[int] = mapped_column(Integer, default=0)
    orcamento_mensal: Mapped[float] = mapped_column(Float, default=0.0)


class FechamentoMensalModel(Base):
    """Fechamento de Custo de Frete — um registro por empresa e competência.

    Faturamento informado por região, devolução e complementar nacionais.
    Frete realizado/budget não são persistidos aqui — vêm de CTeModel e
    MetaRegionalModel a cada leitura (fonte única de verdade).
    """
    __tablename__ = "fechamento_mensal"
    __table_args__ = (
        UniqueConstraint("empresa_id", "competencia", name="uq_fechamento_mensal_empresa_competencia"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    competencia: Mapped[str] = mapped_column(String(7), index=True)  # "AAAA-MM"
    fat_norte: Mapped[float] = mapped_column(Float, default=0.0)
    fat_nordeste: Mapped[float] = mapped_column(Float, default=0.0)
    fat_centro_oeste: Mapped[float] = mapped_column(Float, default=0.0)
    fat_sudeste: Mapped[float] = mapped_column(Float, default=0.0)
    fat_sul: Mapped[float] = mapped_column(Float, default=0.0)
    devolucao: Mapped[float] = mapped_column(Float, default=0.0)
    frete_complementar: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(10), default="ABERTO")
    fechado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BenchmarkModel(Base):
    __tablename__ = "benchmarks"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regiao: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    frete_kg_min: Mapped[float] = mapped_column(Float, default=0.0)
    frete_kg_medio: Mapped[float] = mapped_column(Float, default=0.0)
    frete_kg_max: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_min: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_medio: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_max: Mapped[float] = mapped_column(Float, default=0.0)


class CTeModel(Base):
    __tablename__ = "ctes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    transportadora_id: Mapped[int | None] = mapped_column(
        ForeignKey("transportadoras.id"), nullable=True
    )
    chave: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    numero: Mapped[str] = mapped_column(String(20), default="")
    serie: Mapped[str] = mapped_column(String(10), default="")
    data_emissao: Mapped[Date | None] = mapped_column(Date, nullable=True)
    tomador_cnpj: Mapped[str] = mapped_column(String(20), default="")
    # Destinatário da mercadoria (v6.7.0 — dimensão CLIENTE_FINAL do DLG).
    # Nullable/sem backfill: CT-e importados antes desta versão ficam sem
    # este dado — agregados sob "Cliente não identificado" (RN-68).
    destinatario_cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    destinatario_nome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    peso: Mapped[float] = mapped_column(Float, default=0.0)
    valor_frete: Mapped[float] = mapped_column(Float, default=0.0)
    valor_mercadoria: Mapped[float] = mapped_column(Float, default=0.0)
    municipio_origem: Mapped[str] = mapped_column(String(120), default="")
    uf_origem: Mapped[str] = mapped_column(String(2), default="")
    municipio_destino: Mapped[str] = mapped_column(String(120), default="")
    uf_destino: Mapped[str] = mapped_column(String(2), default="")
    macro_regiao_destino: Mapped[str | None] = mapped_column(String(15), nullable=True)
    data_saida: Mapped[Date | None] = mapped_column(Date, nullable=True)
    data_entrega: Mapped[Date | None] = mapped_column(Date, nullable=True)
    origem_importacao: Mapped[str] = mapped_column(String(10), default="XML")
    composicao_frete: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    # ── Situação do CT-e (MELHORIA 1 — cancelamento via XML de evento) ──
    # ATIVO | CANCELADO. server_default garante que os registros já existentes
    # sejam tratados como ativos no upgrade, sem alterar cálculos legados.
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="ATIVO", index=True
    )
    cancelado_em: Mapped[Date | None] = mapped_column(Date, nullable=True)
    protocolo_cancelamento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    numero_evento_cancelamento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    nfes: Mapped[list["NFeModel"]] = relationship(
        back_populates="cte", cascade="all, delete-orphan"
    )
    transportadora: Mapped["TransportadoraModel | None"] = relationship()


class NFeModel(Base):
    __tablename__ = "nfes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cte_id: Mapped[int | None] = mapped_column(ForeignKey("ctes.id"), nullable=True, index=True)
    chave: Mapped[str] = mapped_column(String(50), index=True)
    numero: Mapped[str] = mapped_column(String(20), default="")
    data_emissao: Mapped[Date | None] = mapped_column(Date, nullable=True)
    valor_mercadoria: Mapped[float] = mapped_column(Float, default=0.0)
    peso: Mapped[float] = mapped_column(Float, default=0.0)
    municipio_destino: Mapped[str] = mapped_column(String(120), default="")

    cte: Mapped["CTeModel | None"] = relationship(back_populates="nfes")


# ══════════ Benchmark Logístico V2.1 — Modelo OD ══════════

class HubLogisticoModel(Base):
    """Catálogo de hubs logísticos, próprio de cada empresa-cliente."""
    __tablename__ = "hubs_logisticos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_hub_empresa_codigo"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(40), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(255), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class ClusterClienteModel(Base):
    """Mapeamento UF/município → Hub, por empresa-cliente."""
    __tablename__ = "clusters_cliente"
    __table_args__ = (
        UniqueConstraint("empresa_id", "uf", "municipio", name="uq_cluster_empresa_uf_mun"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    uf: Mapped[str] = mapped_column(String(2), index=True)
    municipio: Mapped[str] = mapped_column(String(120), default="", index=True)
    hub_id: Mapped[int] = mapped_column(ForeignKey("hubs_logisticos.id"), nullable=False, index=True)


class BenchmarkCorredorModel(Base):
    """Referência de mercado por corredor (Hub origem → Hub destino), por empresa."""
    __tablename__ = "benchmarks_corredor"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "hub_origem_codigo", "hub_destino_codigo",
            name="uq_corredor_empresa_origem_destino",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    hub_origem_codigo: Mapped[str] = mapped_column(String(40), index=True)
    hub_destino_codigo: Mapped[str] = mapped_column(String(40), index=True)
    frete_kg_min: Mapped[float] = mapped_column(Float, default=0.0)
    frete_kg_medio: Mapped[float] = mapped_column(Float, default=0.0)
    frete_kg_max: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_min: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_medio: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_max: Mapped[float] = mapped_column(Float, default=0.0)
    volume_referencia: Mapped[float] = mapped_column(Float, default=0.0)
    dispersao_kg: Mapped[float] = mapped_column(Float, default=0.0)
    prazo_dias_medio: Mapped[float] = mapped_column(Float, default=0.0)
    observacoes: Mapped[str] = mapped_column(String(500), default="")


# ══════════ Módulo BID — Concorrência Logística (V3.1) ══════════

class BidModel(Base):
    __tablename__ = "bids"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(String(2000), default="")
    objetivo: Mapped[str] = mapped_column(String(2000), default="")
    observacoes: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(20), default="RASCUNHO", nullable=False)
    segmentacao_tipo: Mapped[str] = mapped_column(String(20), default="GERAL", nullable=False)
    segmentacao_valor: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    data_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_encerramento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_analise_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_analise_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    escopos: Mapped[list["BidEscopoModel"]] = relationship(back_populates="bid", cascade="all, delete-orphan")
    transportadoras: Mapped[list["BidTransportadoraModel"]] = relationship(back_populates="bid", cascade="all, delete-orphan")
    propostas: Mapped[list["BidPropostaModel"]] = relationship(back_populates="bid", cascade="all, delete-orphan")
    simulacoes: Mapped[list["BidSimulacaoModel"]] = relationship(back_populates="bid", cascade="all, delete-orphan")
    auditoria: Mapped[list["BidAuditoriaModel"]] = relationship(back_populates="bid", cascade="all, delete-orphan")


class BidEscopoModel(Base):
    __tablename__ = "bid_escopos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    tipo_agrupamento: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_grupo: Mapped[str] = mapped_column(String(200), nullable=False)
    peso_total: Mapped[float] = mapped_column(Float, default=0.0)
    valor_frete_total: Mapped[float] = mapped_column(Float, default=0.0)
    valor_mercadoria_total: Mapped[float] = mapped_column(Float, default=0.0)
    qtd_embarques: Mapped[int] = mapped_column(Integer, default=0)
    frete_rs_kg: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct: Mapped[float] = mapped_column(Float, default=0.0)

    bid: Mapped["BidModel"] = relationship(back_populates="escopos")


class BidTransportadoraModel(Base):
    __tablename__ = "bid_transportadoras"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    transportadora_id: Mapped[int] = mapped_column(ForeignKey("transportadoras.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(25), default="CONVIDADA", nullable=False)
    observacoes: Mapped[str] = mapped_column(String(1000), default="")
    avaliacao_usuario: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bid: Mapped["BidModel"] = relationship(back_populates="transportadoras")
    propostas: Mapped[list["BidPropostaModel"]] = relationship(back_populates="bid_transportadora", cascade="all, delete-orphan")


class BidPropostaModel(Base):
    __tablename__ = "bid_propostas"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    bid_transportadora_id: Mapped[int] = mapped_column(ForeignKey("bid_transportadoras.id"), nullable=False, index=True)
    tipo_agrupamento: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_grupo: Mapped[str] = mapped_column(String(200), nullable=False)
    valor_rs_kg: Mapped[float] = mapped_column(Float, default=0.0)
    valor_minimo: Mapped[float] = mapped_column(Float, default=0.0)
    prazo_dias: Mapped[int] = mapped_column(Integer, default=0)
    cobertura_pct: Mapped[float] = mapped_column(Float, default=100.0)
    observacoes: Mapped[str] = mapped_column(String(1000), default="")
    origem: Mapped[str] = mapped_column(String(10), default="MANUAL")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bid: Mapped["BidModel"] = relationship(back_populates="propostas")
    bid_transportadora: Mapped["BidTransportadoraModel"] = relationship(back_populates="propostas")


class BidSimulacaoModel(Base):
    __tablename__ = "bid_simulacoes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(String(1000), default="")
    itens: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    custo_atual: Mapped[float] = mapped_column(Float, default=0.0)
    custo_proposto: Mapped[float] = mapped_column(Float, default=0.0)
    economia_total: Mapped[float] = mapped_column(Float, default=0.0)
    reducao_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bid: Mapped["BidModel"] = relationship(back_populates="simulacoes")


class BidAuditoriaModel(Base):
    __tablename__ = "bid_auditorias"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(200), nullable=False)
    detalhe: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bid: Mapped["BidModel"] = relationship(back_populates="auditoria")


# ════════════════════════════════════════════════════════════════════
# V4 — INTELIGÊNCIA LOGÍSTICA COM IA
# ════════════════════════════════════════════════════════════════════

class RegraInsightModel(Base):
    __tablename__ = "regras_insight"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empresas.id"), nullable=True, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)
    classificacao: Mapped[str] = mapped_column(String(20), nullable=False)
    expressao: Mapped[str] = mapped_column(String(500), nullable=False)
    titulo_template: Mapped[str] = mapped_column(String(300), default="")
    descricao_template: Mapped[str] = mapped_column(String(1000), default="")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InsightModel(Base):
    __tablename__ = "insights"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    regra_id: Mapped[Optional[int]] = mapped_column(ForeignKey("regras_insight.id"), nullable=True)
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)
    classificacao: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descricao: Mapped[str] = mapped_column(String(2000), default="")
    impacto_financeiro: Mapped[float] = mapped_column(Float, default=0.0)
    prioridade: Mapped[int] = mapped_column(Integer, default=3)
    dados: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    lido: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class InsightExecucaoModel(Base):
    __tablename__ = "insight_execucoes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    total_insights: Mapped[int] = mapped_column(Integer, default=0)
    duracao_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="OK")
    erro: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DiagnosticoIAModel(Base):
    __tablename__ = "diagnosticos_ia"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    periodo_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resumo_executivo: Mapped[str] = mapped_column(String(5000), default="")
    pontos_fortes: Mapped[str] = mapped_column(String(3000), default="")
    pontos_atencao: Mapped[str] = mapped_column(String(3000), default="")
    principais_desvios: Mapped[str] = mapped_column(String(3000), default="")
    economia_potencial: Mapped[float] = mapped_column(Float, default=0.0)
    plano_acao: Mapped[str] = mapped_column(String(3000), default="")
    score_logistico: Mapped[float] = mapped_column(Float, default=0.0)
    modelo_usado: Mapped[str] = mapped_column(String(50), default="")
    cache_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DiagnosticoHistoricoModel(Base):
    __tablename__ = "diagnostico_historicos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    diagnostico_id: Mapped[int] = mapped_column(ForeignKey("diagnosticos_ia.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    economia_potencial: Mapped[float] = mapped_column(Float, default=0.0)
    resumo: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScoreLogisticoModel(Base):
    __tablename__ = "scores_logisticos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    score_total: Mapped[float] = mapped_column(Float, default=0.0)
    score_benchmark_nacional: Mapped[float] = mapped_column(Float, default=0.0)
    score_benchmark_regional: Mapped[float] = mapped_column(Float, default=0.0)
    score_transportadoras: Mapped[float] = mapped_column(Float, default=0.0)
    score_filiais: Mapped[float] = mapped_column(Float, default=0.0)
    score_economia: Mapped[float] = mapped_column(Float, default=0.0)
    classificacao: Mapped[str] = mapped_column(String(20), default="")
    periodo_referencia: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScoreHistoricoModel(Base):
    __tablename__ = "score_historicos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    score_total: Mapped[float] = mapped_column(Float, default=0.0)
    classificacao: Mapped[str] = mapped_column(String(20), default="")
    periodo_referencia: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BenchmarkSetorialModel(Base):
    __tablename__ = "benchmarks_setoriais"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    segmento: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    frete_kg_medio: Mapped[float] = mapped_column(Float, default=0.0)
    frete_pct_medio: Mapped[float] = mapped_column(Float, default=0.0)
    custo_medio: Mapped[float] = mapped_column(Float, default=0.0)
    regiao: Mapped[str] = mapped_column(String(15), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OportunidadeModel(Base):
    __tablename__ = "oportunidades"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descricao: Mapped[str] = mapped_column(String(2000), default="")
    economia_estimada: Mapped[float] = mapped_column(Float, default=0.0)
    impacto: Mapped[str] = mapped_column(String(10), default="MEDIO")
    complexidade: Mapped[str] = mapped_column(String(10), default="MEDIA")
    prioridade: Mapped[int] = mapped_column(Integer, default=3)
    justificativa: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(15), default="ABERTA")
    dados: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlanoAcaoModel(Base):
    __tablename__ = "planos_acao"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    oportunidade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("oportunidades.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(500), nullable=False)
    impacto: Mapped[str] = mapped_column(String(10), default="MEDIO")
    economia_estimada: Mapped[float] = mapped_column(Float, default=0.0)
    prioridade: Mapped[str] = mapped_column(String(10), default="MEDIA")
    prazo_dias: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(15), default="PENDENTE")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatSessaoModel(Base):
    __tablename__ = "chat_sessoes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    titulo: Mapped[str] = mapped_column(String(200), default="Nova conversa")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    mensagens: Mapped[list["ChatMensagemModel"]] = relationship(back_populates="sessao", cascade="all, delete-orphan")


class ChatMensagemModel(Base):
    __tablename__ = "chat_mensagens"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sessao_id: Mapped[int] = mapped_column(ForeignKey("chat_sessoes.id"), nullable=False, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    papel: Mapped[str] = mapped_column(String(10), default="user")
    conteudo: Mapped[str] = mapped_column(String(5000), default="")
    ferramentas_usadas: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sessao: Mapped["ChatSessaoModel"] = relationship(back_populates="mensagens")


class UsageLogModel(Base):
    __tablename__ = "usage_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empresas.id"), nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    feature: Mapped[str] = mapped_column(String(30), default="", index=True)
    modelo: Mapped[str] = mapped_column(String(50), default="")
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    custo_usd: Mapped[float] = mapped_column(Float, default=0.0)
    custo_brl: Mapped[float] = mapped_column(Float, default=0.0)
    simulado: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class DocumentoVetorialModel(Base):
    __tablename__ = "documentos_vetoriais"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    tipo_documento: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), default="")
    conteudo: Mapped[str] = mapped_column(String, default="")
    data_referencia: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    doc_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    indexado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmbeddingJobModel(Base):
    __tablename__ = "embedding_jobs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos_vetoriais.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(15), default="PENDENTE")
    erro: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ══════════ Benchmark V2 — Freight Market Intelligence (6.0.0) ══════════

class BenchmarkMercadoModel(Base):
    """Source of Truth do benchmark de MERCADO — matriz Origem→Destino por região.
    Global (não é por empresa). Suporta dimensões OD + operação + faixa de peso."""
    __tablename__ = "benchmark_mercado"
    __table_args__ = (
        UniqueConstraint(
            "origem_regiao", "destino_regiao", "modal", "tipo_operacao", "setor",
            "faixa_peso_min", "faixa_peso_max",
            name="uq_benchmark_mercado_od",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origem_regiao: Mapped[str] = mapped_column(String(15), index=True)
    destino_regiao: Mapped[str] = mapped_column(String(15), index=True)
    modal: Mapped[str] = mapped_column(String(20), default="")              # V2-ready (RODOVIARIO...)
    tipo_operacao: Mapped[str] = mapped_column(String(15), default="TODOS")  # FTL/LTL/FRACIONADO/TODOS
    # Setor (segmento econômico) do embarcador pesquisado — mesmo vocabulário
    # controlado de EmpresaModel.setor (SetorEnum). "TODOS" = referência
    # genérica, sem segmentação (comportamento anterior a esta coluna,
    # preservado como fallback — ver BenchmarkV2UseCase.resolver).
    setor: Mapped[str] = mapped_column(String(40), default="TODOS", server_default="TODOS", index=True)
    faixa_peso_min: Mapped[float] = mapped_column(Float, default=0.0)
    faixa_peso_max: Mapped[float] = mapped_column(Float, default=0.0)        # 0 = sem teto
    rs_kg_p10: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p25: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p50: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p75: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p90: Mapped[float] = mapped_column(Float, default=0.0)
    fonte: Mapped[str] = mapped_column(String(20), default="MERCADO")
    # Proveniência da pesquisa de mercado que sustenta esta linha — em
    # branco/NULL para linhas legadas ou ainda não documentadas.
    amostra_tamanho: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metodologia: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    data_pesquisa: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BenchmarkObservadoModel(Base):
    """Benchmark OBSERVADO — gerado automaticamente dos CT-e/embarques (por empresa).
    Não editável manualmente. Serve de comparação 'real vs mercado'."""
    __tablename__ = "benchmark_observado"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "origem_regiao", "destino_regiao", "modal",
            "tipo_operacao", "faixa_peso_min", "faixa_peso_max", "periodo_ref",
            name="uq_benchmark_observado_od",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    origem_regiao: Mapped[str] = mapped_column(String(15), index=True)
    destino_regiao: Mapped[str] = mapped_column(String(15), index=True)
    modal: Mapped[str] = mapped_column(String(20), default="")
    tipo_operacao: Mapped[str] = mapped_column(String(15), default="TODOS")
    faixa_peso_min: Mapped[float] = mapped_column(Float, default=0.0)
    faixa_peso_max: Mapped[float] = mapped_column(Float, default=0.0)
    qtd_embarques: Mapped[int] = mapped_column(Integer, default=0)
    rs_kg_p10: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p25: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p50: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p75: Mapped[float] = mapped_column(Float, default=0.0)
    rs_kg_p90: Mapped[float] = mapped_column(Float, default=0.0)
    media: Mapped[float] = mapped_column(Float, default=0.0)
    desvio_padrao: Mapped[float] = mapped_column(Float, default=0.0)
    periodo_ref: Mapped[str] = mapped_column(String(7), default="")  # YYYY-MM ou 'TOTAL'
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BenchmarkClienteModel(Base):
    """Override OPCIONAL por cliente (empresa). Se ativo, prevalece sobre o mercado."""
    __tablename__ = "benchmark_cliente"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "origem_regiao", "destino_regiao", "modal",
            name="uq_benchmark_cliente_od",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    origem_regiao: Mapped[str] = mapped_column(String(15), index=True)
    destino_regiao: Mapped[str] = mapped_column(String(15), index=True)
    modal: Mapped[str] = mapped_column(String(20), default="")
    rs_kg_medio: Mapped[float] = mapped_column(Float, default=0.0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ════════════════════════════════════════════════════════════════
# DLG — Diagnóstico Logístico (tabelas analíticas persistidas)
# ════════════════════════════════════════════════════════════════



class DlgAnaliticoModel(Base):
    """Tabela analítica principal (DLG_ANALYTICS).

    Uma linha por (empresa, dimensão, chave, período).
    Reprocessamento idempotente: upsert pela unique constraint.
    """
    __tablename__ = "dlg_analitico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id:    Mapped[int]   = mapped_column(Integer, ForeignKey("empresas.id"), index=True)
    dimensao:      Mapped[str]   = mapped_column(String(20), index=True)   # DlgDimensaoEnum
    chave:         Mapped[str]   = mapped_column(String(200), index=True)  # cnpj / OD / transp_id / regiao
    chave_label:   Mapped[str]   = mapped_column(String(300), default="")  # nome legível
    periodo_ref:   Mapped[str]   = mapped_column(String(7),  index=True)   # YYYY-MM ou YYYY-QN ou YYYY
    # KPIs base
    qtd_ctes:          Mapped[int]   = mapped_column(Integer, default=0)
    peso_total:        Mapped[float] = mapped_column(Float,   default=0.0)
    frete_total:       Mapped[float] = mapped_column(Float,   default=0.0)
    mercadoria_total:  Mapped[float] = mapped_column(Float,   default=0.0)
    rs_kg:             Mapped[float] = mapped_column(Float,   default=0.0)
    pct_frete:         Mapped[float] = mapped_column(Float,   default=0.0)  # % frete/fat
    custo_medio_entrega: Mapped[float] = mapped_column(Float, default=0.0)
    # Classificação
    rs_kg_ref:         Mapped[float] = mapped_column(Float,   default=0.0)  # benchmark
    desvio_pct:        Mapped[float] = mapped_column(Float,   default=0.0)  # % desvio
    classificacao:     Mapped[str]   = mapped_column(String(15), default="SEM_REF")
    # Composição do frete agregada do lote (v6.7.0) — genérica às 5 dimensões,
    # categorias RN-05/RN-73. Base para os campos derivados abaixo.
    composicao_frete: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Processamento
    processado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ── campos derivados (não persistidos) — v6.7.0 ──────────────────────
    # sinal_fragmentacao/causa_dominante são calculados sob demanda pelo
    # DlgUseCase (RN-75/RN-76) e atribuídos como atributo de instância,
    # nunca gravados em banco. Os defaults de classe abaixo garantem que
    # linhas não enriquecidas (outras dimensões, ou EFICIENTE/SEM_REF)
    # sempre exponham `None` no schema de saída.
    sinal_fragmentacao: ClassVar[Optional[bool]] = None
    causa_dominante: ClassVar[Optional[str]] = None
    causa_detalhe: ClassVar[Optional[dict]] = None
    acao_recomendada: ClassVar[Optional[str]] = None

    __table_args__ = (
        UniqueConstraint("empresa_id", "dimensao", "chave", "periodo_ref",
                         name="uq_dlg_analitico"),
    )

    # ── derivados de composicao_frete (RN-72/RN-74) — aplicável às 5 dimensões ──
    # Cálculo em funções puras do domínio (app.domain.entities) — mesma fonte
    # de verdade usada pela consolidação em memória do DlgUseCase.
    @property
    def frete_transporte_principal(self) -> Optional[float]:
        from app.domain.entities import calc_frete_transporte_principal
        return calc_frete_transporte_principal(self.composicao_frete)

    @property
    def pct_componentes_adicionais(self) -> Optional[float]:
        from app.domain.entities import calc_pct_componentes_adicionais
        return calc_pct_componentes_adicionais(self.composicao_frete, self.frete_total or 0.0)

    @property
    def ranking_componentes(self) -> Optional[list]:
        from app.domain.entities import calc_ranking_componentes
        return calc_ranking_componentes(self.composicao_frete)

    @property
    def peso_medio(self) -> Optional[float]:
        return round(self.peso_total / self.qtd_ctes, 4) if self.qtd_ctes else None

    @property
    def ticket_medio(self) -> Optional[float]:
        return round(self.mercadoria_total / self.qtd_ctes, 2) if self.qtd_ctes else None

    @property
    def impacto_financeiro_potencial(self) -> float:
        """RN-70: max(0, rs_kg - rs_kg_ref) × peso_total."""
        if not self.rs_kg_ref:
            return 0.0
        return round(max(0.0, (self.rs_kg or 0.0) - self.rs_kg_ref) * (self.peso_total or 0.0), 2)


class DlgOutlierModel(Base):
    """Registro de outliers detectados pelo motor DLG."""
    __tablename__ = "dlg_outliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id:   Mapped[int]   = mapped_column(Integer, ForeignKey("empresas.id"), index=True)
    cte_id:       Mapped[int]   = mapped_column(Integer, ForeignKey("ctes.id"), index=True)
    periodo_ref:  Mapped[str]   = mapped_column(String(7), index=True)
    tipo_outlier: Mapped[str]   = mapped_column(String(30))  # RS_KG_2DP | PCT_FRETE | VAR_MENSAL
    valor_real:   Mapped[float] = mapped_column(Float,  default=0.0)
    valor_limite: Mapped[float] = mapped_column(Float,  default=0.0)
    desvio_pct:   Mapped[float] = mapped_column(Float,  default=0.0)
    detectado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("empresa_id", "cte_id", "periodo_ref", "tipo_outlier",
                         name="uq_dlg_outlier"),
    )


# ════════════════════════════════════════════════════════════════
# MBL — Benchmark Logístico (motor estatístico versionado)
# ════════════════════════════════════════════════════════════════

class MblBenchmarkModel(Base):
    """Benchmark estatístico versionado (MBL).

    Construído a partir do DLG consolidado, EXCLUINDO outliers do DLG.
    Uma linha por (empresa, dimensão, segmento, métrica, período/versão).
    Auditável e reproduzível: cada período gera uma versão rastreável.
    """
    __tablename__ = "mbl_benchmark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id:  Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), index=True)
    dimensao:    Mapped[str] = mapped_column(String(20), index=True)   # REGIAO | CLUSTER | ROTA
    segmento:    Mapped[str] = mapped_column(String(200), index=True)  # ex.: SUDESTE / SUDESTE_HUB / SP→RS
    metrica:     Mapped[str] = mapped_column(String(20), index=True)   # RS_KG | PCT_FRETE | CUSTO_ENTREGA
    periodo_ref: Mapped[str] = mapped_column(String(7),  index=True)   # YYYY-MM
    # Estatística percentílica
    amostra:     Mapped[int]   = mapped_column(Integer, default=0)     # N de unidades na amostra
    p10:         Mapped[float] = mapped_column(Float, default=0.0)
    p25:         Mapped[float] = mapped_column(Float, default=0.0)
    p50:         Mapped[float] = mapped_column(Float, default=0.0)
    p75:         Mapped[float] = mapped_column(Float, default=0.0)
    p90:         Mapped[float] = mapped_column(Float, default=0.0)
    media:       Mapped[float] = mapped_column(Float, default=0.0)
    desvio_padrao: Mapped[float] = mapped_column(Float, default=0.0)
    # Confiança / auditoria
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    outliers_excluidos: Mapped[int] = mapped_column(Integer, default=0)
    versao:      Mapped[int]   = mapped_column(Integer, default=1)     # incrementa a cada recálculo
    gerado_em:   Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("empresa_id", "dimensao", "segmento", "metrica", "periodo_ref",
                         name="uq_mbl_benchmark"),
    )


# ════════════════════════════════════════════════════════════════
# MCL — Concorrência Logística (motor de decisão de BID versionado)
# ════════════════════════════════════════════════════════════════

class MclDecisaoModel(Base):
    """Decisão de BID versionada (MCL). Rastreabilidade completa e determinística.

    Uma linha por (bid, versão). Guarda o ranking completo em JSON, a vencedora,
    os pesos usados e a justificativa explicável.
    """
    __tablename__ = "mcl_decisoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id:      Mapped[int] = mapped_column(Integer, ForeignKey("bids.id"), index=True)
    empresa_id:  Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), index=True)
    versao:      Mapped[int] = mapped_column(Integer, default=1)
    # vencedora
    vencedora_bt_id:        Mapped[int]   = mapped_column(Integer, default=0)
    vencedora_transp_id:    Mapped[int]   = mapped_column(Integer, default=0)
    vencedora_nome:         Mapped[str]   = mapped_column(String(200), default="")
    score_vencedora:        Mapped[float] = mapped_column(Float, default=0.0)
    diferenca_segunda:      Mapped[float] = mapped_column(Float, default=0.0)
    # pesos aplicados (auditoria/determinismo)
    peso_custo:        Mapped[float] = mapped_column(Float, default=0.40)
    peso_dlg:          Mapped[float] = mapped_column(Float, default=0.25)
    peso_mbl:          Mapped[float] = mapped_column(Float, default=0.20)
    peso_sla:          Mapped[float] = mapped_column(Float, default=0.10)
    peso_estabilidade: Mapped[float] = mapped_column(Float, default=0.05)
    # ranking completo + justificativa (explicabilidade)
    ranking:        Mapped[dict] = mapped_column(JSON, default=dict)
    justificativa:  Mapped[str]  = mapped_column(String(1000), default="")
    propostas_rejeitadas: Mapped[dict] = mapped_column(JSON, default=dict)
    gerado_em:      Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ════════════════════════════════════════════════════════════════
# MELHORIA 1 — Log de eventos de cancelamento de CT-e (via XML)
# ════════════════════════════════════════════════════════════════

class CteCancelamentoModel(Base):
    """Registro (log) de cada ocorrência de importação de evento de cancelamento.

    Guarda TODA tentativa — bem-sucedida, duplicada ou de CT-e inexistente —
    para auditoria completa (RF008 — evolução). O vínculo com o CT-e é opcional
    porque o evento pode chegar antes do próprio CT-e existir na base.
    """
    __tablename__ = "cte_cancelamentos"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    cte_id: Mapped[int | None] = mapped_column(ForeignKey("ctes.id"), nullable=True, index=True)
    chave: Mapped[str] = mapped_column(String(50), index=True)          # chave de acesso do CT-e
    protocolo: Mapped[str] = mapped_column(String(30), default="")       # nProt do evento
    numero_evento: Mapped[str] = mapped_column(String(30), default="")   # nSeqEvento
    tipo_evento: Mapped[str] = mapped_column(String(10), default="")      # tpEvento (110111 = cancelamento)
    data_cancelamento: Mapped[Date | None] = mapped_column(Date, nullable=True)
    # Resultado da ocorrência: CANCELADO | DUPLICADO | CTE_NAO_ENCONTRADO | ERRO
    resultado: Mapped[str] = mapped_column(String(20), default="", index=True)
    mensagem: Mapped[str] = mapped_column(String(500), default="")
    arquivo: Mapped[str] = mapped_column(String(255), default="")
    xml_evento: Mapped[str | None] = mapped_column(String, nullable=True)  # XML do evento (auditoria)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


# ════════════════════════════════════════════════════════════════
# MELHORIA 8 — Recomendações consolidadas dos indicadores
# ════════════════════════════════════════════════════════════════

class RecomendacaoModel(Base):
    """Recomendação consolidada automaticamente a partir dos indicadores.

    Estrutura preparada para receber tanto recomendações determinísticas
    (origem='REGRA') quanto geradas por IA (origem='IA') no futuro. A chave
    natural (empresa_id, indicador, chave_origem) permite upsert idempotente
    ao reconsolidar, preservando o status editado pelo usuário.
    """
    __tablename__ = "recomendacoes"
    __table_args__ = (
        UniqueConstraint("empresa_id", "indicador", "chave_origem",
                         name="uq_recomendacao_origem"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descricao: Mapped[str] = mapped_column(String(2000), default="")
    indicador: Mapped[str] = mapped_column(String(40), default="", index=True)   # indicador relacionado
    chave_origem: Mapped[str] = mapped_column(String(200), default="")           # identifica a origem (rota/transp/etc)
    valor_encontrado: Mapped[str] = mapped_column(String(120), default="")
    valor_recomendado: Mapped[str] = mapped_column(String(120), default="")
    impacto: Mapped[str] = mapped_column(String(200), default="")
    economia_estimada: Mapped[float] = mapped_column(Float, default=0.0)
    # Prioridade: CRITICA | ALTA | MEDIA | BAIXA
    prioridade: Mapped[str] = mapped_column(String(10), default="MEDIA", index=True)
    origem: Mapped[str] = mapped_column(String(10), default="REGRA")             # REGRA | IA
    status: Mapped[str] = mapped_column(String(15), default="ABERTA")            # ABERTA | EM_ANDAMENTO | CONCLUIDA | DESCARTADA
    dados: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gerado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
