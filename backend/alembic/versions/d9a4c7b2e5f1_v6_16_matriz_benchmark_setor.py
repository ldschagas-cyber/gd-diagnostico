"""V6.16 setor + proveniência da pesquisa na Matriz Benchmark (OD)

Revision ID: d9a4c7b2e5f1
Revises: c2f6a9e1b7d4
Create Date: 2026-07-19

Adiciona a dimensão setor (segmento econômico) e campos de proveniência à
matriz de mercado ``benchmark_mercado`` (fonte única de referência R$/kg —
ver ``docs/07_modulos_do_sistema.md``):

  • benchmark_mercado.setor            — VARCHAR(40), NOT NULL, default
    'TODOS'. Mesmo vocabulário controlado de ``empresas.setor`` (SetorEnum).
    'TODOS' preserva o comportamento atual (referência genérica) para toda
    linha já cadastrada e para toda linha nova que não pesquisar por setor.
  • benchmark_mercado.amostra_tamanho  — INTEGER, nullable (nº de cotações
    que sustentam a linha).
  • benchmark_mercado.metodologia      — VARCHAR(200), nullable (como o dado
    foi coletado).
  • benchmark_mercado.data_pesquisa    — DATE, nullable (quando o dado de
    mercado foi coletado — distinto de ``updated_at``, que é só o timestamp
    de edição do registro no sistema).

A ``UniqueConstraint`` da tabela passa a incluir ``setor`` (uma mesma
combinação origem+destino+modal+operação+faixa de peso pode ter uma linha
'TODOS' e uma ou mais linhas específicas por setor, coexistindo).

``server_default='TODOS'`` garante o preenchimento das linhas já
cadastradas no momento do upgrade, mantendo a restrição NOT NULL satisfeita
tanto em PostgreSQL (produção) quanto em SQLite (dev/testes) — mesmo padrão
já usado em b8e3f1a2c9d4 (empresas.setor).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9a4c7b2e5f1"
down_revision: Union[str, None] = "c2f6a9e1b7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table mantém compatibilidade com SQLite (recria a tabela)
    # e é transparente no PostgreSQL — necessário aqui porque, além de
    # adicionar colunas, a UniqueConstraint muda de forma (setor entra na
    # chave), o que exige recriar a constraint.
    with op.batch_alter_table("benchmark_mercado", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("setor", sa.String(length=40), nullable=False, server_default="TODOS")
        )
        batch_op.add_column(sa.Column("amostra_tamanho", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("metodologia", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("data_pesquisa", sa.Date(), nullable=True))

        batch_op.drop_constraint("uq_benchmark_mercado_od", type_="unique")
        batch_op.create_unique_constraint(
            "uq_benchmark_mercado_od",
            ["origem_regiao", "destino_regiao", "modal", "tipo_operacao", "setor",
             "faixa_peso_min", "faixa_peso_max"],
        )

    op.create_index("ix_benchmark_mercado_setor", "benchmark_mercado", ["setor"])


def downgrade() -> None:
    op.drop_index("ix_benchmark_mercado_setor", table_name="benchmark_mercado")

    with op.batch_alter_table("benchmark_mercado", schema=None) as batch_op:
        batch_op.drop_constraint("uq_benchmark_mercado_od", type_="unique")
        batch_op.create_unique_constraint(
            "uq_benchmark_mercado_od",
            ["origem_regiao", "destino_regiao", "modal", "tipo_operacao",
             "faixa_peso_min", "faixa_peso_max"],
        )
        batch_op.drop_column("data_pesquisa")
        batch_op.drop_column("metodologia")
        batch_op.drop_column("amostra_tamanho")
        batch_op.drop_column("setor")
