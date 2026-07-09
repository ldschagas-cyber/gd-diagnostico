"""Hardening: users.empresa_id (multi-tenant) e UNIQUE no modelo OD

Revision ID: d7f2b8c3e9a1
Revises: c5e1a9f4d2b7
Create Date: 2026-06-22

Correções de auditoria:
  • R-01: coluna users.empresa_id (vínculo multi-tenant; NULL = admin global).
  • R-09: UNIQUE em clusters_cliente (empresa_id, uf, municipio) e em
          benchmarks_corredor (hub_origem_codigo, hub_destino_codigo).

IMPORTANTE: esta migração é completamente idempotente via SQL nativo.
Usa ADD COLUMN IF NOT EXISTS e DO $$ IF NOT EXISTS $$ para cada objeto,
de forma que pode ser reaplicada sem falhar mesmo quando o create_all
do startup já criou as tabelas e constraints antecipadamente.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7f2b8c3e9a1"
down_revision: Union[str, None] = "c5e1a9f4d2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # R-01 — coluna empresa_id em users (idempotente)
    conn.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "empresa_id INTEGER REFERENCES empresas(id)"
    ))

    # Índice em users.empresa_id (idempotente)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_users_empresa_id ON users (empresa_id)"
    ))

    # R-09 — UNIQUE em clusters_cliente (idempotente via DO $$)
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_cluster_empresa_uf_mun'
                  AND conrelid = 'clusters_cliente'::regclass
            ) THEN
                ALTER TABLE clusters_cliente
                ADD CONSTRAINT uq_cluster_empresa_uf_mun
                UNIQUE (empresa_id, uf, municipio);
            END IF;
        END $$;
    """))

    # R-09 — UNIQUE em benchmarks_corredor (idempotente via DO $$)
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_corredor_origem_destino'
                  AND conrelid = 'benchmarks_corredor'::regclass
            ) THEN
                ALTER TABLE benchmarks_corredor
                ADD CONSTRAINT uq_corredor_origem_destino
                UNIQUE (hub_origem_codigo, hub_destino_codigo);
            END IF;
        END $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_corredor_origem_destino'
            ) THEN
                ALTER TABLE benchmarks_corredor DROP CONSTRAINT uq_corredor_origem_destino;
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_cluster_empresa_uf_mun'
            ) THEN
                ALTER TABLE clusters_cliente DROP CONSTRAINT uq_cluster_empresa_uf_mun;
            END IF;
        END $$;
    """))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_users_empresa_id"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS empresa_id"))

