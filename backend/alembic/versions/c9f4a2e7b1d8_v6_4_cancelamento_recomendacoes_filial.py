"""V6.4 cancelamento de CT-e, recomendacoes e dimensao FILIAL

Revision ID: c9f4a2e7b1d8
Revises: b8e3f1a2c9d4
Create Date: 2026-07-04

Implementa as melhorias v6.4:

  • ctes: colunas de situação/cancelamento (MELHORIA 1)
      - status (VARCHAR(10), NOT NULL, default 'ATIVO', indexado)
      - cancelado_em (DATE, nullable)
      - protocolo_cancelamento (VARCHAR(30), nullable)
      - numero_evento_cancelamento (VARCHAR(30), nullable)

  • cte_cancelamentos: log/auditoria de eventos de cancelamento (MELHORIA 1)
  • recomendacoes: recomendações consolidadas dos indicadores (MELHORIA 8)
  • dlg_analitico: renomeia a dimensão 'CLIENTE' para 'FILIAL' (MELHORIA 9)

O server_default='ATIVO' garante que todos os CT-es já existentes sejam
tratados como ativos no upgrade, sem alterar cálculos legados. Compatível com
PostgreSQL (produção) e SQLite (dev/testes) via batch_alter_table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f4a2e7b1d8"
down_revision: Union[str, None] = "b8e3f1a2c9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── MELHORIA 1 — colunas de cancelamento em ctes ──────────────────────────
    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=10), nullable=False,
                      server_default="ATIVO")
        )
        batch_op.add_column(sa.Column("cancelado_em", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("protocolo_cancelamento", sa.String(length=30), nullable=True)
        )
        batch_op.add_column(
            sa.Column("numero_evento_cancelamento", sa.String(length=30), nullable=True)
        )
    op.create_index("ix_ctes_status", "ctes", ["status"])

    # ── MELHORIA 1 — log de eventos de cancelamento ───────────────────────────
    op.create_table(
        "cte_cancelamentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("cte_id", sa.Integer(), sa.ForeignKey("ctes.id"), nullable=True),
        sa.Column("chave", sa.String(length=50), nullable=False),
        sa.Column("protocolo", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("numero_evento", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("tipo_evento", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("data_cancelamento", sa.Date(), nullable=True),
        sa.Column("resultado", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("mensagem", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("arquivo", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("xml_evento", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "chave", "numero_evento",
                            name="uq_cte_cancelamento_evento"),
    )
    op.create_index("ix_cte_cancelamentos_empresa_id", "cte_cancelamentos", ["empresa_id"])
    op.create_index("ix_cte_cancelamentos_cte_id", "cte_cancelamentos", ["cte_id"])
    op.create_index("ix_cte_cancelamentos_chave", "cte_cancelamentos", ["chave"])
    op.create_index("ix_cte_cancelamentos_resultado", "cte_cancelamentos", ["resultado"])
    op.create_index("ix_cte_cancelamentos_created_at", "cte_cancelamentos", ["created_at"])

    # ── MELHORIA 8 — recomendações consolidadas ───────────────────────────────
    op.create_table(
        "recomendacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("descricao", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("indicador", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("chave_origem", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("valor_encontrado", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("valor_recomendado", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("impacto", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("economia_estimada", sa.Float(), nullable=False, server_default="0"),
        sa.Column("prioridade", sa.String(length=10), nullable=False, server_default="MEDIA"),
        sa.Column("origem", sa.String(length=10), nullable=False, server_default="REGRA"),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="ABERTA"),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("gerado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "indicador", "chave_origem",
                            name="uq_recomendacao_origem"),
    )
    op.create_index("ix_recomendacoes_empresa_id", "recomendacoes", ["empresa_id"])
    op.create_index("ix_recomendacoes_indicador", "recomendacoes", ["indicador"])
    op.create_index("ix_recomendacoes_prioridade", "recomendacoes", ["prioridade"])

    # ── MELHORIA 9 — dimensão CLIENTE → FILIAL (dados existentes) ──────────────
    op.execute(
        "UPDATE dlg_analitico SET dimensao = 'FILIAL' WHERE dimensao = 'CLIENTE'"
    )


def downgrade() -> None:
    # Reverte a dimensão FILIAL → CLIENTE (dados)
    op.execute(
        "UPDATE dlg_analitico SET dimensao = 'CLIENTE' WHERE dimensao = 'FILIAL'"
    )

    op.drop_index("ix_recomendacoes_prioridade", table_name="recomendacoes")
    op.drop_index("ix_recomendacoes_indicador", table_name="recomendacoes")
    op.drop_index("ix_recomendacoes_empresa_id", table_name="recomendacoes")
    op.drop_table("recomendacoes")

    op.drop_index("ix_cte_cancelamentos_created_at", table_name="cte_cancelamentos")
    op.drop_index("ix_cte_cancelamentos_resultado", table_name="cte_cancelamentos")
    op.drop_index("ix_cte_cancelamentos_chave", table_name="cte_cancelamentos")
    op.drop_index("ix_cte_cancelamentos_cte_id", table_name="cte_cancelamentos")
    op.drop_index("ix_cte_cancelamentos_empresa_id", table_name="cte_cancelamentos")
    op.drop_table("cte_cancelamentos")

    op.drop_index("ix_ctes_status", table_name="ctes")
    with op.batch_alter_table("ctes", schema=None) as batch_op:
        batch_op.drop_column("numero_evento_cancelamento")
        batch_op.drop_column("protocolo_cancelamento")
        batch_op.drop_column("cancelado_em")
        batch_op.drop_column("status")
