"""V6.13 hubs logisticos por empresa

Revision ID: a3d6f2b9c8e1
Revises: f7a1c8e3b5d9
Create Date: 2026-07-14

O catálogo de hubs logísticos e a referência de mercado por corredor
deixam de ser globais e passam a ser próprios de cada empresa-cliente —
cada empresa cria e mantém seu próprio catálogo, sem afetar outras.

  • hubs_logisticos: + empresa_id (FK empresas.id, not null), troca o
    UNIQUE de (codigo) sozinho para (empresa_id, codigo).
  • benchmarks_corredor: + empresa_id (FK empresas.id, not null), troca o
    UNIQUE de (hub_origem_codigo, hub_destino_codigo) para
    (empresa_id, hub_origem_codigo, hub_destino_codigo).
  • clusters_cliente: seu hub_id aponta para hubs_logisticos, que serão
    recriados por empresa — a tabela é esvaziada junto (não havia dados
    reais no momento desta migração).

Decisão de produto: zerar sem reseed — cada empresa (existente ou nova)
começa sem nenhum hub cadastrado e cria os seus própios. Diferente de
Metas (v6.13, migração anterior), aqui não há backfill automático.

Compatível apenas com PostgreSQL.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d6f2b9c8e1"
down_revision: Union[str, None] = "f7a1c8e3b5d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # clusters_cliente depende de hubs_logisticos (FK hub_id) — esvazia primeiro.
    conn.execute(sa.text("DELETE FROM clusters_cliente"))
    conn.execute(sa.text("DELETE FROM benchmarks_corredor"))
    conn.execute(sa.text("DELETE FROM hubs_logisticos"))

    # ---- hubs_logisticos: + empresa_id, troca a unicidade ----------------
    conn.execute(sa.text(
        "ALTER TABLE hubs_logisticos ADD COLUMN IF NOT EXISTS empresa_id INTEGER"
    ))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_hubs_logisticos_codigo"))
    conn.execute(sa.text(
        "ALTER TABLE hubs_logisticos ALTER COLUMN empresa_id SET NOT NULL"
    ))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_hub_empresa'
                  AND conrelid = 'hubs_logisticos'::regclass
            ) THEN
                ALTER TABLE hubs_logisticos
                ADD CONSTRAINT fk_hub_empresa
                FOREIGN KEY (empresa_id) REFERENCES empresas(id);
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_hub_empresa_codigo'
                  AND conrelid = 'hubs_logisticos'::regclass
            ) THEN
                ALTER TABLE hubs_logisticos
                ADD CONSTRAINT uq_hub_empresa_codigo UNIQUE (empresa_id, codigo);
            END IF;
        END $$;
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_hubs_logisticos_codigo "
        "ON hubs_logisticos (codigo)"
    ))

    # ---- benchmarks_corredor: + empresa_id, troca a unicidade ------------
    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor ADD COLUMN IF NOT EXISTS empresa_id INTEGER"
    ))
    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor DROP CONSTRAINT IF EXISTS uq_corredor_origem_destino"
    ))
    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor ALTER COLUMN empresa_id SET NOT NULL"
    ))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_corredor_empresa'
                  AND conrelid = 'benchmarks_corredor'::regclass
            ) THEN
                ALTER TABLE benchmarks_corredor
                ADD CONSTRAINT fk_corredor_empresa
                FOREIGN KEY (empresa_id) REFERENCES empresas(id);
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_corredor_empresa_origem_destino'
                  AND conrelid = 'benchmarks_corredor'::regclass
            ) THEN
                ALTER TABLE benchmarks_corredor
                ADD CONSTRAINT uq_corredor_empresa_origem_destino
                UNIQUE (empresa_id, hub_origem_codigo, hub_destino_codigo);
            END IF;
        END $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor DROP CONSTRAINT IF EXISTS uq_corredor_empresa_origem_destino"
    ))
    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor DROP CONSTRAINT IF EXISTS fk_corredor_empresa"
    ))
    conn.execute(sa.text("DELETE FROM benchmarks_corredor"))
    conn.execute(sa.text("ALTER TABLE benchmarks_corredor DROP COLUMN IF EXISTS empresa_id"))
    conn.execute(sa.text(
        "ALTER TABLE benchmarks_corredor ADD CONSTRAINT uq_corredor_origem_destino "
        "UNIQUE (hub_origem_codigo, hub_destino_codigo)"
    ))

    conn.execute(sa.text("DELETE FROM clusters_cliente"))

    conn.execute(sa.text(
        "ALTER TABLE hubs_logisticos DROP CONSTRAINT IF EXISTS uq_hub_empresa_codigo"
    ))
    conn.execute(sa.text(
        "ALTER TABLE hubs_logisticos DROP CONSTRAINT IF EXISTS fk_hub_empresa"
    ))
    conn.execute(sa.text("DELETE FROM hubs_logisticos"))
    conn.execute(sa.text("ALTER TABLE hubs_logisticos DROP COLUMN IF EXISTS empresa_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_hubs_logisticos_codigo"))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_hubs_logisticos_codigo "
        "ON hubs_logisticos (codigo)"
    ))
