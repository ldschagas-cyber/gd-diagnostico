#!/usr/bin/env python3
"""migrate_sqlite_to_pg.py — Migração de dados SQLite → PostgreSQL.

Uso:
    python migrate_sqlite_to_pg.py \
        --sqlite ./gd_frete.db \
        --pg "postgresql+psycopg2://gd_user:gd_pass@localhost:5432/gd_frete"

O script:
  1. Lê todas as tabelas do SQLite.
  2. Aplica as migrations Alembic no PostgreSQL (cria o schema).
  3. Copia os dados tabela a tabela, respeitando a ordem de dependências FK.

Requisitos:
    pip install sqlalchemy psycopg2-binary alembic

ATENÇÃO: Execute com PostgreSQL vazio. Se houver dados no destino,
         use --truncate para limpar antes de copiar.
"""
import argparse
import sys
from datetime import datetime

from sqlalchemy import create_engine, inspect, text


# Ordem de inserção respeita dependências FK.
TABLE_ORDER = [
    "users",
    "empresas",
    "filiais",
    "regioes",
    "cidades",
    "transportadoras",
    "meta_nacional",
    "meta_regional",
    "benchmarks",
    "ctes",
    "nfes",
]


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}")


def migrate(sqlite_url: str, pg_url: str, truncate: bool = False):
    log("Conectando ao SQLite...")
    sqlite_engine = create_engine(sqlite_url)

    log("Conectando ao PostgreSQL...")
    pg_engine = create_engine(pg_url)

    # Aplica migrations no PG para criar o schema.
    log("Aplicando migrations Alembic no PostgreSQL...")
    import subprocess, os, sys
    env = os.environ.copy()
    env["DATABASE_URL"] = pg_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f"ERRO nas migrations:\n{result.stderr}")
        sys.exit(1)
    log("Migrations aplicadas com sucesso.")

    # Descobre tabelas existentes no SQLite.
    inspector = inspect(sqlite_engine)
    sqlite_tables = set(inspector.get_table_names())

    with sqlite_engine.connect() as src, pg_engine.connect() as dst:
        for table in TABLE_ORDER:
            if table not in sqlite_tables:
                log(f"  Tabela '{table}' não encontrada no SQLite — ignorada.")
                continue

            rows = src.execute(text(f"SELECT * FROM {table}")).fetchall()
            if not rows:
                log(f"  {table}: 0 linhas — ignorada.")
                continue

            if truncate:
                dst.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                log(f"  {table}: truncada.")

            cols = inspector.get_columns(table)
            col_names = [c["name"] for c in cols]
            placeholders = ", ".join([f":{c}" for c in col_names])
            col_list = ", ".join(col_names)
            insert_sql = text(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING"
            )

            data = [dict(zip(col_names, row)) for row in rows]
            dst.execute(insert_sql, data)

            # Reajusta sequence das PKs (PostgreSQL exige após INSERT com id explícito).
            pk_cols = [c["name"] for c in cols if c.get("primary_key")]
            if pk_cols:
                pk = pk_cols[0]
                dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{pk}'), "
                    f"COALESCE((SELECT MAX({pk}) FROM {table}), 1))"
                ))

            dst.commit()
            log(f"  {table}: {len(data)} linhas copiadas.")

    log("Migração concluída com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migração SQLite → PostgreSQL")
    parser.add_argument("--sqlite", default="./gd_frete.db",
                        help="Caminho do arquivo SQLite (padrão: ./gd_frete.db)")
    parser.add_argument("--pg", required=True,
                        help="URL de conexão PostgreSQL")
    parser.add_argument("--truncate", action="store_true",
                        help="Trunca as tabelas no destino antes de copiar")
    args = parser.parse_args()

    migrate(f"sqlite:///{args.sqlite}", args.pg, args.truncate)
