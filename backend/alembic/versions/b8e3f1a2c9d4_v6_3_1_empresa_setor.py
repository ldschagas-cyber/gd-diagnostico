"""V6.3.1 setor (segmento economico) do embarcador

Revision ID: b8e3f1a2c9d4
Revises: a7c2e9f1b4d6
Create Date: 2026-06-26

Adiciona a coluna ``setor`` à tabela ``empresas`` (MELHORIA 2 — Cadastro de
Empresa). É a base para filtros, consultas SQL, dashboards e benchmarking por
segmento econômico.

  • empresas.setor — VARCHAR(40), NOT NULL, default 'Outros', indexado.

O ``server_default='Outros'`` garante o preenchimento das empresas já
cadastradas no momento do upgrade, mantendo a restrição NOT NULL satisfeita
tanto em PostgreSQL (produção) quanto em SQLite (desenvolvimento/testes). O
vocabulário controlado (SetorEnum) é validado na camada de aplicação, o que
permite acrescentar novos setores no futuro sem alterar o schema.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e3f1a2c9d4"
down_revision: Union[str, None] = "a7c2e9f1b4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table mantém compatibilidade com SQLite (recria a tabela) e
    # é transparente no PostgreSQL (ADD COLUMN nativo com backfill via default).
    with op.batch_alter_table("empresas", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "setor",
                sa.String(length=40),
                nullable=False,
                server_default="Outros",
            )
        )
    op.create_index("ix_empresas_setor", "empresas", ["setor"])


def downgrade() -> None:
    op.drop_index("ix_empresas_setor", table_name="empresas")
    with op.batch_alter_table("empresas", schema=None) as batch_op:
        batch_op.drop_column("setor")
