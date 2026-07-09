"""V6.0 benchmark V2 (matriz OD) e soft delete de proposta

Revision ID: e8c4a1f6d3b2
Revises: d7f2b8c3e9a1
Create Date: 2026-06-24

Mudanças de schema da release 6.0.0 (Benchmark V2 — Freight Market
Intelligence). Cria três tabelas novas e adiciona uma coluna, sem alterar
dados existentes:

  • benchmark_mercado    — matriz OD de mercado (source of truth), percentis P10–P90
  • benchmark_observado  — percentis reais por OD, derivados dos CT-e de cada empresa
  • benchmark_cliente    — override de referência por empresa (R$/kg médio)
  • bid_propostas.deleted — soft delete de proposta (preserva histórico/auditoria)

As tabelas legadas (`benchmarks`, `benchmarks_corredor`) permanecem intactas
como fallback/relatório; o R$/kg da referência regional passa a ser
sobreposto a partir de `benchmark_mercado` em tempo de leitura.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8c4a1f6d3b2"
down_revision: Union[str, None] = "d7f2b8c3e9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Matriz OD de mercado (global, source of truth) ─────────────────────
    op.create_table(
        "benchmark_mercado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("origem_regiao", sa.String(length=15), nullable=False),
        sa.Column("destino_regiao", sa.String(length=15), nullable=False),
        sa.Column("modal", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("tipo_operacao", sa.String(length=15), nullable=False, server_default="TODOS"),
        sa.Column("faixa_peso_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("faixa_peso_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p10", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p25", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p50", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p75", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p90", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fonte", sa.String(length=20), nullable=False, server_default="MERCADO"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "origem_regiao", "destino_regiao", "modal", "tipo_operacao",
            "faixa_peso_min", "faixa_peso_max",
            name="uq_benchmark_mercado_od",
        ),
    )
    op.create_index("ix_benchmark_mercado_origem_regiao", "benchmark_mercado", ["origem_regiao"])
    op.create_index("ix_benchmark_mercado_destino_regiao", "benchmark_mercado", ["destino_regiao"])

    # ── Benchmark observado (por empresa, derivado dos CT-e) ───────────────
    op.create_table(
        "benchmark_observado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("origem_regiao", sa.String(length=15), nullable=False),
        sa.Column("destino_regiao", sa.String(length=15), nullable=False),
        sa.Column("modal", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("tipo_operacao", sa.String(length=15), nullable=False, server_default="TODOS"),
        sa.Column("faixa_peso_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("faixa_peso_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("qtd_embarques", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p10", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p25", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p50", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p75", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_p90", sa.Float(), nullable=False, server_default="0"),
        sa.Column("media", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desvio_padrao", sa.Float(), nullable=False, server_default="0"),
        sa.Column("periodo_ref", sa.String(length=7), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "empresa_id", "origem_regiao", "destino_regiao", "modal",
            "tipo_operacao", "faixa_peso_min", "faixa_peso_max", "periodo_ref",
            name="uq_benchmark_observado_od",
        ),
    )
    op.create_index("ix_benchmark_observado_empresa_id", "benchmark_observado", ["empresa_id"])
    op.create_index("ix_benchmark_observado_origem_regiao", "benchmark_observado", ["origem_regiao"])
    op.create_index("ix_benchmark_observado_destino_regiao", "benchmark_observado", ["destino_regiao"])

    # ── Override de referência por cliente ─────────────────────────────────
    op.create_table(
        "benchmark_cliente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("origem_regiao", sa.String(length=15), nullable=False),
        sa.Column("destino_regiao", sa.String(length=15), nullable=False),
        sa.Column("modal", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("rs_kg_medio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacoes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "empresa_id", "origem_regiao", "destino_regiao", "modal",
            name="uq_benchmark_cliente_od",
        ),
    )
    op.create_index("ix_benchmark_cliente_empresa_id", "benchmark_cliente", ["empresa_id"])
    op.create_index("ix_benchmark_cliente_origem_regiao", "benchmark_cliente", ["origem_regiao"])
    op.create_index("ix_benchmark_cliente_destino_regiao", "benchmark_cliente", ["destino_regiao"])

    # ── Soft delete de proposta (MEL-003) ──────────────────────────────────
    op.add_column(
        "bid_propostas",
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_bid_propostas_deleted", "bid_propostas", ["deleted"])


def downgrade() -> None:
    op.drop_index("ix_bid_propostas_deleted", table_name="bid_propostas")
    op.drop_column("bid_propostas", "deleted")

    op.drop_index("ix_benchmark_cliente_destino_regiao", table_name="benchmark_cliente")
    op.drop_index("ix_benchmark_cliente_origem_regiao", table_name="benchmark_cliente")
    op.drop_index("ix_benchmark_cliente_empresa_id", table_name="benchmark_cliente")
    op.drop_table("benchmark_cliente")

    op.drop_index("ix_benchmark_observado_destino_regiao", table_name="benchmark_observado")
    op.drop_index("ix_benchmark_observado_origem_regiao", table_name="benchmark_observado")
    op.drop_index("ix_benchmark_observado_empresa_id", table_name="benchmark_observado")
    op.drop_table("benchmark_observado")

    op.drop_index("ix_benchmark_mercado_destino_regiao", table_name="benchmark_mercado")
    op.drop_index("ix_benchmark_mercado_origem_regiao", table_name="benchmark_mercado")
    op.drop_table("benchmark_mercado")
