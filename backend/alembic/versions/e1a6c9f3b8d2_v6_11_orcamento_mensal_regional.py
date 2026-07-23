"""V6.11 orcamento mensal por macrorregiao

Revision ID: e1a6c9f3b8d2
Revises: d4b8f2a6c1e9
Create Date: 2026-07-12

Adiciona o orçamento mensal (R$) por macrorregião na Meta Regional, usado
para comparar o frete realizado da região com um orçamento — o Dashboard
multiplica esse valor pelo nº de meses do período filtrado.

  • meta_regional: orcamento_mensal (FLOAT, not null, default 0) — sem
    backfill necessário: linhas existentes assumem 0 (sem orçamento
    configurado), comportamento equivalente ao anterior à mudança.

Compatível com PostgreSQL (produção) e SQLite (dev/testes) via
batch_alter_table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a6c9f3b8d2"
down_revision: Union[str, None] = "d4b8f2a6c1e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("meta_regional", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("orcamento_mensal", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("meta_regional", schema=None) as batch_op:
        batch_op.drop_column("orcamento_mensal")
