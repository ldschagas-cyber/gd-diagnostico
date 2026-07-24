"""Cria tabela benchmarks (legado, tela Referência de Frete) ausente em produção

Revision ID: e2b7c4a9f1d6
Revises: d9a4c7b2e5f1
Create Date: 2026-07-24

A tabela `benchmarks` (BenchmarkModel) nunca teve uma migration própria —
existia só via `Base.metadata.create_all()` em dev/SQLite, que é desativado
em produção (ENVIRONMENT=production). Resultado: GET /benchmarks sempre
retornava 500 (UndefinedTable) em produção, travando a tela "Referência de
Frete" ao repetir toast de erro. Migration criada agora para fechar o gap.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2b7c4a9f1d6"
down_revision: Union[str, None] = "d9a4c7b2e5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("regiao", sa.String(length=15), nullable=False),
        sa.Column("frete_kg_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_kg_medio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_kg_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_min", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_medio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_pct_max", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_benchmarks_regiao", "benchmarks", ["regiao"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_benchmarks_regiao", table_name="benchmarks")
    op.drop_table("benchmarks")
