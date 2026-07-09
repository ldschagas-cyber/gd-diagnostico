"""V6.3 MCL (concorrencia logistica) decisao de BID versionada

Revision ID: a7c2e9f1b4d6
Revises: f3a9d6b2c1e8
Create Date: 2026-06-24

Cria a tabela mcl_decisoes (motor de decisão de BID versionado, rastreável).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c2e9f1b4d6"
down_revision: Union[str, None] = "f3a9d6b2c1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mcl_decisoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bid_id", sa.Integer(), sa.ForeignKey("bids.id"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vencedora_bt_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vencedora_transp_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vencedora_nome", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("score_vencedora", sa.Float(), nullable=False, server_default="0"),
        sa.Column("diferenca_segunda", sa.Float(), nullable=False, server_default="0"),
        sa.Column("peso_custo", sa.Float(), nullable=False, server_default="0.40"),
        sa.Column("peso_dlg", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("peso_mbl", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("peso_sla", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("peso_estabilidade", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("ranking", sa.JSON(), nullable=True),
        sa.Column("justificativa", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("propostas_rejeitadas", sa.JSON(), nullable=True),
        sa.Column("gerado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcl_decisoes_bid_id", "mcl_decisoes", ["bid_id"])
    op.create_index("ix_mcl_decisoes_empresa_id", "mcl_decisoes", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_mcl_decisoes_empresa_id", table_name="mcl_decisoes")
    op.drop_index("ix_mcl_decisoes_bid_id", table_name="mcl_decisoes")
    op.drop_table("mcl_decisoes")
