"""Portal do Cliente (v6.18.0) — tabelas de autenticação e sinalização

Duas tabelas novas, sem alterar nenhuma tabela do motor analítico:

- clientes_portal_users: usuário-executivo da empresa cliente, audiência
  separada de `users` (empresa_id obrigatório, e-mail globalmente único).
- portal_oportunidade_flags: estado "priorizada pelo cliente" de uma
  recomendação — desacoplada de `recomendacoes`, não altera o fluxo de
  trabalho do analista.

Ver Especificação Técnica v6.18.0 (docs/specs/v6.18.0/) §3.2, §3.7, §4.

Revision ID: b7e2f4a9c1d5
Revises: a4c7e1f9d2b6
Create Date: 2026-08-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2f4a9c1d5"
down_revision: Union[str, None] = "a4c7e1f9d2b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes_portal_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("ultimo_acesso", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_clientes_portal_users_empresa_id", "clientes_portal_users", ["empresa_id"])
    op.create_index(
        "ix_clientes_portal_users_email", "clientes_portal_users", ["email"], unique=True
    )

    op.create_table(
        "portal_oportunidade_flags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recomendacao_id", sa.Integer, sa.ForeignKey("recomendacoes.id"), nullable=False),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column(
            "cliente_portal_user_id", sa.Integer, sa.ForeignKey("clientes_portal_users.id"), nullable=False
        ),
        sa.Column("priorizada", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("atualizado_em", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "recomendacao_id", "cliente_portal_user_id", name="uq_portal_flag_recomendacao_cliente"
        ),
    )
    op.create_index(
        "ix_portal_oportunidade_flags_recomendacao_id", "portal_oportunidade_flags", ["recomendacao_id"]
    )
    op.create_index(
        "ix_portal_oportunidade_flags_empresa_id", "portal_oportunidade_flags", ["empresa_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_portal_oportunidade_flags_empresa_id", table_name="portal_oportunidade_flags")
    op.drop_index("ix_portal_oportunidade_flags_recomendacao_id", table_name="portal_oportunidade_flags")
    op.drop_table("portal_oportunidade_flags")

    op.drop_index("ix_clientes_portal_users_email", table_name="clientes_portal_users")
    op.drop_index("ix_clientes_portal_users_empresa_id", table_name="clientes_portal_users")
    op.drop_table("clientes_portal_users")
