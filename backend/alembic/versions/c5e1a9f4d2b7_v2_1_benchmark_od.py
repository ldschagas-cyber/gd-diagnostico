"""V2.1 benchmark OD — hubs, clusters por cliente e referencia por corredor

Revision ID: c5e1a9f4d2b7
Revises: b3d9e2f1a7c5
Create Date: 2026-06-21

Modelo Origem -> Destino do Benchmark Logístico (V2.1).
Cria três tabelas, sem alterar nada de V3/V4 nem dados existentes:

  • hubs_logisticos      — catálogo global de hubs (vocabulário controlado)
  • clusters_cliente     — mapa UF/município → hub, por empresa-cliente
  • benchmarks_corredor  — referência de mercado global por par de hubs

A tabela `benchmarks` (por região) permanece intacta como legado/fallback.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5e1a9f4d2b7"
down_revision: Union[str, None] = "b3d9e2f1a7c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Catálogo global de hubs ────────────────────────────────────────────
    op.create_table(
        "hubs_logisticos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_hubs_logisticos_codigo", "hubs_logisticos", ["codigo"], unique=True)

    # ── Mapa UF/município → hub, por empresa-cliente ───────────────────────
    op.create_table(
        "clusters_cliente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("hub_id", sa.Integer(), sa.ForeignKey("hubs_logisticos.id"), nullable=False),
    )
    op.create_index("ix_clusters_cliente_empresa_id", "clusters_cliente", ["empresa_id"])
    op.create_index("ix_clusters_cliente_uf", "clusters_cliente", ["uf"])
    op.create_index("ix_clusters_cliente_municipio", "clusters_cliente", ["municipio"])
    op.create_index("ix_clusters_cliente_hub_id", "clusters_cliente", ["hub_id"])

    # ── Referência de mercado por corredor (global) ────────────────────────
    op.create_table(
        "benchmarks_corredor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hub_origem_codigo", sa.String(length=40), nullable=False),
        sa.Column("hub_destino_codigo", sa.String(length=40), nullable=False),
        sa.Column("frete_kg_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_kg_medio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_kg_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_medio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("volume_referencia", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dispersao_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.String(length=500), nullable=False, server_default=""),
    )
    op.create_index("ix_benchmarks_corredor_origem", "benchmarks_corredor", ["hub_origem_codigo"])
    op.create_index("ix_benchmarks_corredor_destino", "benchmarks_corredor", ["hub_destino_codigo"])

    # ── Seed dos hubs padrão (5 macrorregiões) ─────────────────────────────
    hubs = sa.table(
        "hubs_logisticos",
        sa.column("codigo", sa.String),
        sa.column("nome", sa.String),
        sa.column("descricao", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(
        hubs,
        [
            {"codigo": "SUDESTE_HUB", "nome": "Sudeste Hub", "descricao": "Cluster logístico da região Sudeste", "ativo": True},
            {"codigo": "SUL_HUB", "nome": "Sul Hub", "descricao": "Cluster logístico da região Sul", "ativo": True},
            {"codigo": "NORDESTE_HUB", "nome": "Nordeste Hub", "descricao": "Cluster logístico da região Nordeste", "ativo": True},
            {"codigo": "NORTE_HUB", "nome": "Norte Hub", "descricao": "Cluster logístico da região Norte", "ativo": True},
            {"codigo": "CENTRO_OESTE_HUB", "nome": "Centro-Oeste Hub", "descricao": "Cluster logístico da região Centro-Oeste", "ativo": True},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_benchmarks_corredor_destino", table_name="benchmarks_corredor")
    op.drop_index("ix_benchmarks_corredor_origem", table_name="benchmarks_corredor")
    op.drop_table("benchmarks_corredor")

    op.drop_index("ix_clusters_cliente_hub_id", table_name="clusters_cliente")
    op.drop_index("ix_clusters_cliente_municipio", table_name="clusters_cliente")
    op.drop_index("ix_clusters_cliente_uf", table_name="clusters_cliente")
    op.drop_index("ix_clusters_cliente_empresa_id", table_name="clusters_cliente")
    op.drop_table("clusters_cliente")

    op.drop_index("ix_hubs_logisticos_codigo", table_name="hubs_logisticos")
    op.drop_table("hubs_logisticos")
