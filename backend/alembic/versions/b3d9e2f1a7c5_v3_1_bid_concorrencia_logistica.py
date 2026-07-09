"""v3.1: BID de Frete — Concorrência Logística

- users: adiciona campo role (ADMIN/ANALISTA/VISUALIZADOR)
- cria tabelas: bids, bid_escopos, bid_transportadoras,
                bid_propostas, bid_simulacoes, bid_auditorias

Revision ID: b3d9e2f1a7c5
Revises: a2f8c1e4b9d3
Create Date: 2026-06-20
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "b3d9e2f1a7c5"
down_revision: Union[str, None] = "a2f8c1e4b9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: adiciona role ──────────────────────────────────────────────
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(20), nullable=True, server_default="ANALISTA"))

    # Promove is_superuser → ADMIN (sintaxe PostgreSQL: boolean = true)
    op.execute("UPDATE users SET role = 'ADMIN' WHERE is_superuser = true")

    # ── bids ──────────────────────────────────────────────────────────────
    op.create_table(
        "bids",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.String(2000), default=""),
        sa.Column("objetivo", sa.String(2000), default=""),
        sa.Column("observacoes", sa.String(2000), default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="RASCUNHO"),
        sa.Column("data_inicio", sa.Date, nullable=True),
        sa.Column("data_encerramento", sa.Date, nullable=True),
        sa.Column("periodo_analise_inicio", sa.Date, nullable=True),
        sa.Column("periodo_analise_fim", sa.Date, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_bids_empresa_id", "bids", ["empresa_id"])

    # ── bid_escopos ───────────────────────────────────────────────────────
    op.create_table(
        "bid_escopos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("tipo_agrupamento", sa.String(20), nullable=False),
        sa.Column("valor_grupo", sa.String(200), nullable=False),
        sa.Column("peso_total", sa.Float, default=0.0),
        sa.Column("valor_frete_total", sa.Float, default=0.0),
        sa.Column("valor_mercadoria_total", sa.Float, default=0.0),
        sa.Column("qtd_embarques", sa.Integer, default=0),
        sa.Column("frete_rs_kg", sa.Float, default=0.0),
        sa.Column("frete_pct", sa.Float, default=0.0),
    )
    op.create_index("ix_bid_escopos_bid_id", "bid_escopos", ["bid_id"])

    # ── bid_transportadoras ───────────────────────────────────────────────
    op.create_table(
        "bid_transportadoras",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("transportadora_id", sa.Integer, sa.ForeignKey("transportadoras.id"), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="CONVIDADA"),
        sa.Column("observacoes", sa.String(1000), default=""),
        sa.Column("avaliacao_usuario", sa.Float, nullable=True),
    )
    op.create_index("ix_bid_transportadoras_bid_id", "bid_transportadoras", ["bid_id"])
    op.create_index("ix_bid_transportadoras_transportadora_id", "bid_transportadoras", ["transportadora_id"])

    # ── bid_propostas ─────────────────────────────────────────────────────
    op.create_table(
        "bid_propostas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("bid_transportadora_id", sa.Integer, sa.ForeignKey("bid_transportadoras.id"), nullable=False),
        sa.Column("tipo_agrupamento", sa.String(20), nullable=False),
        sa.Column("valor_grupo", sa.String(200), nullable=False),
        sa.Column("valor_rs_kg", sa.Float, default=0.0),
        sa.Column("valor_minimo", sa.Float, default=0.0),
        sa.Column("prazo_dias", sa.Integer, default=0),
        sa.Column("cobertura_pct", sa.Float, default=100.0),
        sa.Column("observacoes", sa.String(1000), default=""),
        sa.Column("origem", sa.String(10), default="MANUAL"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_bid_propostas_bid_id", "bid_propostas", ["bid_id"])
    op.create_index("ix_bid_propostas_bt_id", "bid_propostas", ["bid_transportadora_id"])

    # ── bid_simulacoes ────────────────────────────────────────────────────
    op.create_table(
        "bid_simulacoes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.String(1000), default=""),
        sa.Column("itens", sa.JSON, nullable=True),
        sa.Column("custo_atual", sa.Float, default=0.0),
        sa.Column("custo_proposto", sa.Float, default=0.0),
        sa.Column("economia_total", sa.Float, default=0.0),
        sa.Column("reducao_pct", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_bid_simulacoes_bid_id", "bid_simulacoes", ["bid_id"])

    # ── bid_auditorias ────────────────────────────────────────────────────
    op.create_table(
        "bid_auditorias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acao", sa.String(200), nullable=False),
        sa.Column("detalhe", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_bid_auditorias_bid_id", "bid_auditorias", ["bid_id"])


def downgrade() -> None:
    op.drop_table("bid_auditorias")
    op.drop_table("bid_simulacoes")
    op.drop_table("bid_propostas")
    op.drop_table("bid_transportadoras")
    op.drop_table("bid_escopos")
    op.drop_table("bids")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
