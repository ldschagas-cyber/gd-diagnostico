"""V6.13 metas por empresa

Revision ID: f7a1c8e3b5d9
Revises: e1a6c9f3b8d2
Create Date: 2026-07-14

Metas (nacional e regional) deixam de ser globais e passam a ser
por empresa-cliente — cada cliente tem seu próprio conjunto de metas,
sem compartilhar com outros (mesmo padrão já usado em ClusterCliente).

  • meta_nacional: + empresa_id (FK empresas.id, not null), UNIQUE(empresa_id)
    — uma linha por empresa.
  • meta_regional: + empresa_id (FK empresas.id, not null), troca o UNIQUE
    de (macro_regiao) sozinho para (empresa_id, macro_regiao).

Decisão de produto (não há como preservar o valor global anterior de forma
significativa por-empresa): as linhas existentes são apagadas e cada
empresa já cadastrada recebe um conjunto zerado (1 nacional + 5 regionais),
igual ao que uma empresa nova recebe ao ser criada (ver
empresas.py::seed_metas_padroes). Reconfiguração manual é esperada.

Compatível apenas com PostgreSQL (produção/dev deste projeto usam Postgres
via docker-compose; os blocos DO $$ são específicos do dialeto).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a1c8e3b5d9"
down_revision: Union[str, None] = "e1a6c9f3b8d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MACRO_REGIOES = ["NORTE", "NORDESTE", "CENTRO_OESTE", "SUDESTE", "SUL"]


def upgrade() -> None:
    conn = op.get_bind()

    # ---- meta_nacional: + empresa_id -----------------------------------
    conn.execute(sa.text(
        "ALTER TABLE meta_nacional ADD COLUMN IF NOT EXISTS empresa_id INTEGER"
    ))
    conn.execute(sa.text("DELETE FROM meta_nacional"))
    conn.execute(sa.text(
        "ALTER TABLE meta_nacional ALTER COLUMN empresa_id SET NOT NULL"
    ))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_meta_nacional_empresa'
                  AND conrelid = 'meta_nacional'::regclass
            ) THEN
                ALTER TABLE meta_nacional
                ADD CONSTRAINT fk_meta_nacional_empresa
                FOREIGN KEY (empresa_id) REFERENCES empresas(id);
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_meta_nacional_empresa'
                  AND conrelid = 'meta_nacional'::regclass
            ) THEN
                ALTER TABLE meta_nacional
                ADD CONSTRAINT uq_meta_nacional_empresa UNIQUE (empresa_id);
            END IF;
        END $$;
    """))

    # ---- meta_regional: + empresa_id, troca a unicidade ------------------
    conn.execute(sa.text(
        "ALTER TABLE meta_regional ADD COLUMN IF NOT EXISTS empresa_id INTEGER"
    ))
    conn.execute(sa.text("DELETE FROM meta_regional"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_meta_regional_macro_regiao"))
    conn.execute(sa.text(
        "ALTER TABLE meta_regional ALTER COLUMN empresa_id SET NOT NULL"
    ))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_meta_regional_empresa'
                  AND conrelid = 'meta_regional'::regclass
            ) THEN
                ALTER TABLE meta_regional
                ADD CONSTRAINT fk_meta_regional_empresa
                FOREIGN KEY (empresa_id) REFERENCES empresas(id);
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_meta_regional_empresa_macro'
                  AND conrelid = 'meta_regional'::regclass
            ) THEN
                ALTER TABLE meta_regional
                ADD CONSTRAINT uq_meta_regional_empresa_macro
                UNIQUE (empresa_id, macro_regiao);
            END IF;
        END $$;
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_meta_regional_macro_regiao "
        "ON meta_regional (macro_regiao)"
    ))

    # ---- Backfill: cada empresa já cadastrada recebe metas zeradas -------
    conn.execute(sa.text(
        "INSERT INTO meta_nacional (empresa_id, meta_rs_kg, meta_pct_frete) "
        "SELECT id, 0, 0 FROM empresas"
    ))
    for macro in MACRO_REGIOES:
        conn.execute(sa.text(
            "INSERT INTO meta_regional "
            "(empresa_id, macro_regiao, meta_rs_kg, meta_pct_frete, prazo_medio_meta, orcamento_mensal) "
            "SELECT id, :macro, 0, 0, 0, 0 FROM empresas"
        ), {"macro": macro})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE meta_regional DROP CONSTRAINT IF EXISTS uq_meta_regional_empresa_macro"
    ))
    conn.execute(sa.text(
        "ALTER TABLE meta_regional DROP CONSTRAINT IF EXISTS fk_meta_regional_empresa"
    ))
    conn.execute(sa.text("DELETE FROM meta_regional"))
    conn.execute(sa.text("ALTER TABLE meta_regional DROP COLUMN IF EXISTS empresa_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_meta_regional_macro_regiao"))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_meta_regional_macro_regiao "
        "ON meta_regional (macro_regiao)"
    ))

    conn.execute(sa.text(
        "ALTER TABLE meta_nacional DROP CONSTRAINT IF EXISTS uq_meta_nacional_empresa"
    ))
    conn.execute(sa.text(
        "ALTER TABLE meta_nacional DROP CONSTRAINT IF EXISTS fk_meta_nacional_empresa"
    ))
    conn.execute(sa.text("DELETE FROM meta_nacional"))
    conn.execute(sa.text("ALTER TABLE meta_nacional DROP COLUMN IF EXISTS empresa_id"))
    conn.execute(sa.text("INSERT INTO meta_nacional (meta_rs_kg, meta_pct_frete) VALUES (0, 0)"))
