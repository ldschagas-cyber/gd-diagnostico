"""V6.1 DLG (diagnostico logistico) e MBL (benchmark logistico)

Revision ID: f3a9d6b2c1e8
Revises: e8c4a1f6d3b2
Create Date: 2026-06-24

Mudanças de schema da release 6.1.0. Cria três tabelas analíticas novas,
sem alterar dados existentes:

  • dlg_analitico  — KPIs e classificação de eficiência por dimensão/período (DLG)
  • dlg_outliers   — registro de outliers detectados pelo motor DLG
  • mbl_benchmark  — benchmark estatístico versionado (percentis P10–P90) por
                     dimensão/segmento/métrica/período (MBL)

Todas idempotentes em runtime (o startup já cria via CREATE TABLE IF NOT EXISTS);
esta migration é o caminho formal para produção gerida por Alembic.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a9d6b2c1e8"
down_revision: Union[str, None] = "e8c4a1f6d3b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── DLG — analítico por dimensão/período ───────────────────────────────
    op.create_table(
        "dlg_analitico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("dimensao", sa.String(length=20), nullable=False),
        sa.Column("chave", sa.String(length=200), nullable=False),
        sa.Column("chave_label", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("periodo_ref", sa.String(length=7), nullable=False),
        sa.Column("qtd_ctes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("peso_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mercadoria_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pct_frete", sa.Float(), nullable=False, server_default="0"),
        sa.Column("custo_medio_entrega", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rs_kg_ref", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desvio_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("classificacao", sa.String(length=15), nullable=False, server_default="SEM_REF"),
        sa.Column("processado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "dimensao", "chave", "periodo_ref",
                            name="uq_dlg_analitico"),
    )
    op.create_index("ix_dlg_analitico_empresa_id", "dlg_analitico", ["empresa_id"])
    op.create_index("ix_dlg_analitico_dimensao", "dlg_analitico", ["dimensao"])
    op.create_index("ix_dlg_analitico_chave", "dlg_analitico", ["chave"])
    op.create_index("ix_dlg_analitico_periodo_ref", "dlg_analitico", ["periodo_ref"])

    # ── DLG — outliers ─────────────────────────────────────────────────────
    op.create_table(
        "dlg_outliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("cte_id", sa.Integer(), sa.ForeignKey("ctes.id"), nullable=False),
        sa.Column("periodo_ref", sa.String(length=7), nullable=False),
        sa.Column("tipo_outlier", sa.String(length=30), nullable=False),
        sa.Column("valor_real", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_limite", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desvio_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detectado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "cte_id", "periodo_ref", "tipo_outlier",
                            name="uq_dlg_outlier"),
    )
    op.create_index("ix_dlg_outliers_empresa_id", "dlg_outliers", ["empresa_id"])
    op.create_index("ix_dlg_outliers_cte_id", "dlg_outliers", ["cte_id"])
    op.create_index("ix_dlg_outliers_periodo_ref", "dlg_outliers", ["periodo_ref"])

    # ── MBL — benchmark estatístico versionado ─────────────────────────────
    op.create_table(
        "mbl_benchmark",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("dimensao", sa.String(length=20), nullable=False),
        sa.Column("segmento", sa.String(length=200), nullable=False),
        sa.Column("metrica", sa.String(length=20), nullable=False),
        sa.Column("periodo_ref", sa.String(length=7), nullable=False),
        sa.Column("amostra", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("p10", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p25", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p50", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p75", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p90", sa.Float(), nullable=False, server_default="0"),
        sa.Column("media", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desvio_padrao", sa.Float(), nullable=False, server_default="0"),
        sa.Column("low_confidence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("outliers_excluidos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("gerado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "dimensao", "segmento", "metrica", "periodo_ref",
                            name="uq_mbl_benchmark"),
    )
    op.create_index("ix_mbl_benchmark_empresa_id", "mbl_benchmark", ["empresa_id"])
    op.create_index("ix_mbl_benchmark_dimensao", "mbl_benchmark", ["dimensao"])
    op.create_index("ix_mbl_benchmark_segmento", "mbl_benchmark", ["segmento"])
    op.create_index("ix_mbl_benchmark_metrica", "mbl_benchmark", ["metrica"])
    op.create_index("ix_mbl_benchmark_periodo_ref", "mbl_benchmark", ["periodo_ref"])
    op.create_index("ix_mbl_benchmark_low_confidence", "mbl_benchmark", ["low_confidence"])


def downgrade() -> None:
    op.drop_index("ix_mbl_benchmark_low_confidence", table_name="mbl_benchmark")
    op.drop_index("ix_mbl_benchmark_periodo_ref", table_name="mbl_benchmark")
    op.drop_index("ix_mbl_benchmark_metrica", table_name="mbl_benchmark")
    op.drop_index("ix_mbl_benchmark_segmento", table_name="mbl_benchmark")
    op.drop_index("ix_mbl_benchmark_dimensao", table_name="mbl_benchmark")
    op.drop_index("ix_mbl_benchmark_empresa_id", table_name="mbl_benchmark")
    op.drop_table("mbl_benchmark")

    op.drop_index("ix_dlg_outliers_periodo_ref", table_name="dlg_outliers")
    op.drop_index("ix_dlg_outliers_cte_id", table_name="dlg_outliers")
    op.drop_index("ix_dlg_outliers_empresa_id", table_name="dlg_outliers")
    op.drop_table("dlg_outliers")

    op.drop_index("ix_dlg_analitico_periodo_ref", table_name="dlg_analitico")
    op.drop_index("ix_dlg_analitico_chave", table_name="dlg_analitico")
    op.drop_index("ix_dlg_analitico_dimensao", table_name="dlg_analitico")
    op.drop_index("ix_dlg_analitico_empresa_id", table_name="dlg_analitico")
    op.drop_table("dlg_analitico")
