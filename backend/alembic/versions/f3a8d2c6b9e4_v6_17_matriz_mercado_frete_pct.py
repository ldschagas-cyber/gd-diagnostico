"""V6.17 % Frete por corredor na Matriz Mercado (OD)

Revision ID: f3a8d2c6b9e4
Revises: e2b7c4a9f1d6
Create Date: 2026-07-24

Adiciona a faixa de % Frete/Mercadoria (min/médio/máx) à matriz de mercado
``benchmark_mercado`` — substitui o BenchmarkModel legado (tabela
``benchmarks``), que só modelava a faixa de % Frete por macro-região, sem
dimensão de origem. Um mesmo destino pode ter %Frete muito diferente
dependendo da origem (ex.: Sudeste→Nordeste vs. Nordeste→Nordeste); manter a
faixa presa a uma tabela region-only misturava rotas incomparáveis na mesma
média. A partir de agora %Frete vive na mesma linha de corredor
(origem×destino×setor×operação×modal×peso) que já hospeda os percentis
R$/kg, ao lado deles.

Não há migração de dado do legado: o ``benchmarks`` antigo tinha 1 linha por
região sem origem, sem correspondência 1:1 possível com uma linha de
corredor OD — os valores legados ficam preservados na tabela antiga (não
removida por esta migration) só como histórico, e as linhas de Matriz
Mercado precisam ser preenchidas de novo, por corredor, conforme a pesquisa
avançar (mesmo padrão adotado quando a dimensão ``setor`` foi introduzida em
d9a4c7b2e5f1).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a8d2c6b9e4"
down_revision: Union[str, None] = "e2b7c4a9f1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("benchmark_mercado", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("frete_pct_min", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("frete_pct_medio", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("frete_pct_max", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("benchmark_mercado", schema=None) as batch_op:
        batch_op.drop_column("frete_pct_max")
        batch_op.drop_column("frete_pct_medio")
        batch_op.drop_column("frete_pct_min")
