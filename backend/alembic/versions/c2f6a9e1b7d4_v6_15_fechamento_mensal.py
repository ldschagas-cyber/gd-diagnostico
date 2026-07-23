"""V6.15 fechamento mensal de custo de frete

Revision ID: c2f6a9e1b7d4
Revises: b4c7d1a9e6f2
Create Date: 2026-07-18

Cria a tabela `fechamento_mensal` — um registro por empresa e competência
(AAAA-MM) com o faturamento informado por região, devolução e frete
complementar nacionais, e o estado de trava (ABERTO/FECHADO) do mês.

Frete realizado e budget não são persistidos aqui: seguem calculados a
partir de `ctes` (CTeRepository.agregar_por_regiao/agregar_nacional) e de
`meta_regional` a cada leitura — fonte única de verdade, sem duplicar dado
que já existe automático (RN já aplicada em Metas/Benchmark).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2f6a9e1b7d4"
down_revision: Union[str, None] = "b4c7d1a9e6f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fechamento_mensal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("competencia", sa.String(length=7), nullable=False),
        sa.Column("fat_norte", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_nordeste", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_centro_oeste", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_sudeste", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_sul", sa.Float(), nullable=False, server_default="0"),
        sa.Column("devolucao", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frete_complementar", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="ABERTO"),
        sa.Column("fechado_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "competencia", name="uq_fechamento_mensal_empresa_competencia"),
    )
    op.create_index("ix_fechamento_mensal_empresa_id", "fechamento_mensal", ["empresa_id"])
    op.create_index("ix_fechamento_mensal_competencia", "fechamento_mensal", ["competencia"])


def downgrade() -> None:
    op.drop_index("ix_fechamento_mensal_competencia", table_name="fechamento_mensal")
    op.drop_index("ix_fechamento_mensal_empresa_id", table_name="fechamento_mensal")
    op.drop_table("fechamento_mensal")
