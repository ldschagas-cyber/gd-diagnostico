"""v3: segurança + isolamento multiempresa + performance

- Transportadoras: adiciona empresa_id (FK + índice)
- Transportadoras: remove unique constraint global de CNPJ
- Transportadoras: adiciona unique constraint composto (empresa_id, cnpj)
- CT-es: adiciona índice composto (empresa_id, data_emissao) para filtros de período
- CT-es: adiciona índice em (empresa_id, transportadora_id) para N+1 resolution

Revision ID: a2f8c1e4b9d3
Revises: faa05e1d23e5
Create Date: 2026-06-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a2f8c1e4b9d3"
down_revision: Union[str, None] = "faa05e1d23e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Transportadoras: adiciona empresa_id ──────────────────────────────
    with op.batch_alter_table("transportadoras", schema=None) as batch_op:
        batch_op.add_column(sa.Column("empresa_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_transportadoras_empresa_id",
            "empresas",
            ["empresa_id"],
            ["id"],
        )
        batch_op.create_index("ix_transportadoras_empresa_id", ["empresa_id"])
        # Remove unique constraint global de CNPJ — o isolamento agora é por (empresa_id, cnpj)
        # SQLAlchemy nomeia o index como ix_transportadoras_cnpj
        batch_op.drop_index("ix_transportadoras_cnpj")
        # Cria índice composto (empresa_id, cnpj) — única dentro da empresa
        batch_op.create_index(
            "ix_transportadoras_empresa_cnpj",
            ["empresa_id", "cnpj"],
            unique=False,          # unique=True causaria problema com NULLs legados
        )

    # ── CT-es: índice composto para filtros de período (maior impacto de performance) ──
    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.create_index(
            "ix_ctes_empresa_data_emissao",
            ["empresa_id", "data_emissao"],
        )
        batch_op.create_index(
            "ix_ctes_empresa_transportadora",
            ["empresa_id", "transportadora_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.drop_index("ix_ctes_empresa_transportadora")
        batch_op.drop_index("ix_ctes_empresa_data_emissao")

    with op.batch_alter_table("transportadoras", schema=None) as batch_op:
        batch_op.drop_index("ix_transportadoras_empresa_cnpj")
        batch_op.create_index("ix_transportadoras_cnpj", ["cnpj"], unique=True)
        batch_op.drop_index("ix_transportadoras_empresa_id")
        batch_op.drop_constraint("fk_transportadoras_empresa_id", type_="foreignkey")
        batch_op.drop_column("empresa_id")
