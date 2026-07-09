"""V6.7 dimensao Cliente no DLG

Revision ID: d4b8f2a6c1e9
Revises: c9f4a2e7b1d8
Create Date: 2026-07-08

Implementa a base de dado da v6.7.0 (Dimensão Cliente):

  • ctes: colunas de destinatário da mercadoria (RN-68)
      - destinatario_cnpj (VARCHAR(20), nullable, sem backfill)
      - destinatario_nome (VARCHAR(200), nullable, sem backfill)

  • dlg_analitico: coluna de composição do frete agregada (RN-72/RN-73)
      - composicao_frete (JSON, nullable) — genérica às 5 dimensões, não
        apenas Cliente (ver docs/specs/v6.7.0_especificacao_tecnica_dimensao_cliente.md §4.2)

Nenhum backfill de dado histórico: CT-e já importados permanecem com estes
campos nulos/vazios até reimportação (limitação documentada — ver
docs/06_regras_de_negocio.md RN-68 e docs/11_changelog.md [6.7.0]).
Compatível com PostgreSQL (produção) e SQLite (dev/testes) via
batch_alter_table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b8f2a6c1e9"
down_revision: Union[str, None] = "c9f4a2e7b1d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("destinatario_cnpj", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("destinatario_nome", sa.String(length=200), nullable=True))

    with op.batch_alter_table("dlg_analitico", schema=None) as batch_op:
        batch_op.add_column(sa.Column("composicao_frete", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("dlg_analitico", schema=None) as batch_op:
        batch_op.drop_column("composicao_frete")

    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.drop_column("destinatario_nome")
        batch_op.drop_column("destinatario_cnpj")
