"""V6.14 login baseado em empresa — usuario_empresas M:N

Revision ID: b4c7d1a9e6f2
Revises: a3d6f2b9c8e1
Create Date: 2026-07-14

Um usuário deixa de estar preso a exatamente 1 empresa. Nova tabela de
associação `usuario_empresas` vira a fonte de verdade da autorização
multi-tenant (`_usuario_pode_acessar_empresa`); `users.empresa_id` é
mantido, mas passa a servir só de empresa padrão/preferida — usada para
pré-selecionar a empresa na tela de login pós-autenticação.

Backfill: cada usuário com `empresa_id` não nulo recebe 1 vínculo em
`usuario_empresas` com essa mesma empresa, preservando o acesso que já
tinha sem exigir reconfiguração manual. Usuários superusuário global
(`empresa_id IS NULL`) não recebem vínculo — continuam com acesso
irrestrito pela regra já existente em `_usuario_pode_acessar_empresa`.

Compatível apenas com PostgreSQL.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4c7d1a9e6f2"
down_revision: Union[str, None] = "a3d6f2b9c8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS usuario_empresas (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES users(id),
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT uq_usuario_empresa UNIQUE (usuario_id, empresa_id)
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_usuario_empresas_usuario_id ON usuario_empresas (usuario_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_usuario_empresas_empresa_id ON usuario_empresas (empresa_id)"
    ))

    # Backfill: preserva o acesso de todo usuário já vinculado a 1 empresa.
    conn.execute(sa.text("""
        INSERT INTO usuario_empresas (usuario_id, empresa_id)
        SELECT id, empresa_id FROM users WHERE empresa_id IS NOT NULL
        ON CONFLICT (usuario_id, empresa_id) DO NOTHING
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS usuario_empresas"))
