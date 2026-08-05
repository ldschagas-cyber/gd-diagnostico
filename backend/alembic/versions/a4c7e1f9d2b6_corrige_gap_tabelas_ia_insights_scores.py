"""corrige gap: tabelas de IA/Insights/Scores nunca migradas + colunas ausentes em bids/benchmarks_corredor

Achado em 2026-08-05: 15 tabelas existem nos models SQLAlchemy desde suas
respectivas features (BID segmentação, Score Logístico, Diagnóstico IA,
Insights, Chat, Usage) mas NUNCA tiveram uma migration Alembic real —
só existiam em dev/local via create_all() (desligado em produção, R-07).
Isso causava 500 (UndefinedColumn/UndefinedTable) em produção assim que
qualquer uma dessas telas era exercitada pela primeira vez.

Tabelas criadas: benchmarks_setoriais, regras_insight, insights,
insight_execucoes, diagnosticos_ia, diagnostico_historicos,
scores_logisticos, score_historicos, oportunidades, planos_acao,
chat_sessoes, chat_mensagens, usage_logs, documentos_vetoriais,
embedding_jobs.

Colunas adicionadas: bids.segmentacao_tipo, bids.segmentacao_valor,
benchmarks_corredor.prazo_dias_medio.

Revision ID: a4c7e1f9d2b6
Revises: f3a8d2c6b9e4
Create Date: 2026-08-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4c7e1f9d2b6"
down_revision: Union[str, None] = "f3a8d2c6b9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── colunas ausentes em tabelas já existentes ───────────────────────────
    with op.batch_alter_table("bids", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("segmentacao_tipo", sa.String(20), nullable=False, server_default="GERAL")
        )
        batch_op.add_column(
            sa.Column("segmentacao_valor", sa.String(200), nullable=False, server_default="")
        )

    with op.batch_alter_table("benchmarks_corredor", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("prazo_dias_medio", sa.Float, nullable=False, server_default="0.0")
        )

    # ── benchmarks_setoriais (sem FK) ────────────────────────────────────────
    op.create_table(
        "benchmarks_setoriais",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("segmento", sa.String(20), nullable=False),
        sa.Column("frete_kg_medio", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("frete_pct_medio", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("custo_medio", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("regiao", sa.String(15), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_benchmarks_setoriais_segmento", "benchmarks_setoriais", ["segmento"])

    # ── regras_insight ───────────────────────────────────────────────────────
    op.create_table(
        "regras_insight",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column("classificacao", sa.String(20), nullable=False),
        sa.Column("expressao", sa.String(500), nullable=False),
        sa.Column("titulo_template", sa.String(300), nullable=False, server_default=""),
        sa.Column("descricao_template", sa.String(1000), nullable=False, server_default=""),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_regras_insight_empresa_id", "regras_insight", ["empresa_id"])

    # ── insights (FK regras_insight) ─────────────────────────────────────────
    op.create_table(
        "insights",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("regra_id", sa.Integer, sa.ForeignKey("regras_insight.id"), nullable=True),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column("classificacao", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("descricao", sa.String(2000), nullable=False, server_default=""),
        sa.Column("impacto_financeiro", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("prioridade", sa.Integer, nullable=False, server_default="3"),
        sa.Column("dados", sa.JSON, nullable=True),
        sa.Column("lido", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_insights_empresa_id", "insights", ["empresa_id"])
    op.create_index("ix_insights_created_at", "insights", ["created_at"])

    # ── insight_execucoes ────────────────────────────────────────────────────
    op.create_table(
        "insight_execucoes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("total_insights", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duracao_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OK"),
        sa.Column("erro", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_insight_execucoes_empresa_id", "insight_execucoes", ["empresa_id"])

    # ── diagnosticos_ia ──────────────────────────────────────────────────────
    op.create_table(
        "diagnosticos_ia",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("periodo_inicio", sa.Date, nullable=True),
        sa.Column("periodo_fim", sa.Date, nullable=True),
        sa.Column("resumo_executivo", sa.String(5000), nullable=False, server_default=""),
        sa.Column("pontos_fortes", sa.String(3000), nullable=False, server_default=""),
        sa.Column("pontos_atencao", sa.String(3000), nullable=False, server_default=""),
        sa.Column("principais_desvios", sa.String(3000), nullable=False, server_default=""),
        sa.Column("economia_potencial", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("plano_acao", sa.String(3000), nullable=False, server_default=""),
        sa.Column("score_logistico", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("modelo_usado", sa.String(50), nullable=False, server_default=""),
        sa.Column("cache_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_diagnosticos_ia_empresa_id", "diagnosticos_ia", ["empresa_id"])
    op.create_index("ix_diagnosticos_ia_cache_hash", "diagnosticos_ia", ["cache_hash"])

    # ── diagnostico_historicos (FK diagnosticos_ia) ──────────────────────────
    op.create_table(
        "diagnostico_historicos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("diagnostico_id", sa.Integer, sa.ForeignKey("diagnosticos_ia.id"), nullable=False),
        sa.Column("score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("economia_potencial", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("resumo", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_diagnostico_historicos_empresa_id", "diagnostico_historicos", ["empresa_id"])

    # ── scores_logisticos ────────────────────────────────────────────────────
    op.create_table(
        "scores_logisticos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("score_total", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("score_benchmark_nacional", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("score_benchmark_regional", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("score_transportadoras", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("score_filiais", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("score_economia", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("classificacao", sa.String(20), nullable=False, server_default=""),
        sa.Column("periodo_referencia", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_scores_logisticos_empresa_id", "scores_logisticos", ["empresa_id"])

    # ── score_historicos ─────────────────────────────────────────────────────
    op.create_table(
        "score_historicos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("score_total", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("classificacao", sa.String(20), nullable=False, server_default=""),
        sa.Column("periodo_referencia", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_score_historicos_empresa_id", "score_historicos", ["empresa_id"])

    # ── oportunidades ────────────────────────────────────────────────────────
    op.create_table(
        "oportunidades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("descricao", sa.String(2000), nullable=False, server_default=""),
        sa.Column("economia_estimada", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("impacto", sa.String(10), nullable=False, server_default="MEDIO"),
        sa.Column("complexidade", sa.String(10), nullable=False, server_default="MEDIA"),
        sa.Column("prioridade", sa.Integer, nullable=False, server_default="3"),
        sa.Column("justificativa", sa.String(2000), nullable=False, server_default=""),
        sa.Column("status", sa.String(15), nullable=False, server_default="ABERTA"),
        sa.Column("dados", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_oportunidades_empresa_id", "oportunidades", ["empresa_id"])

    # ── planos_acao (FK oportunidades) ───────────────────────────────────────
    op.create_table(
        "planos_acao",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("oportunidade_id", sa.Integer, sa.ForeignKey("oportunidades.id"), nullable=True),
        sa.Column("acao", sa.String(500), nullable=False),
        sa.Column("impacto", sa.String(10), nullable=False, server_default="MEDIO"),
        sa.Column("economia_estimada", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("prioridade", sa.String(10), nullable=False, server_default="MEDIA"),
        sa.Column("prazo_dias", sa.Integer, nullable=False, server_default="30"),
        sa.Column("status", sa.String(15), nullable=False, server_default="PENDENTE"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_planos_acao_empresa_id", "planos_acao", ["empresa_id"])

    # ── chat_sessoes ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_sessoes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("titulo", sa.String(200), nullable=False, server_default="Nova conversa"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_sessoes_empresa_id", "chat_sessoes", ["empresa_id"])

    # ── chat_mensagens (FK chat_sessoes) ─────────────────────────────────────
    op.create_table(
        "chat_mensagens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sessao_id", sa.Integer, sa.ForeignKey("chat_sessoes.id"), nullable=False),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("papel", sa.String(10), nullable=False, server_default="user"),
        sa.Column("conteudo", sa.String(5000), nullable=False, server_default=""),
        sa.Column("ferramentas_usadas", sa.JSON, nullable=True),
        sa.Column("tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_mensagens_sessao_id", "chat_mensagens", ["sessao_id"])
    op.create_index("ix_chat_mensagens_empresa_id", "chat_mensagens", ["empresa_id"])

    # ── usage_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("feature", sa.String(30), nullable=False, server_default=""),
        sa.Column("modelo", sa.String(50), nullable=False, server_default=""),
        sa.Column("tokens_input", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer, nullable=False, server_default="0"),
        sa.Column("custo_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("custo_brl", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("simulado", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_usage_logs_empresa_id", "usage_logs", ["empresa_id"])
    op.create_index("ix_usage_logs_feature", "usage_logs", ["feature"])
    op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])

    # ── documentos_vetoriais ─────────────────────────────────────────────────
    op.create_table(
        "documentos_vetoriais",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("tipo_documento", sa.String(30), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False, server_default=""),
        sa.Column("conteudo", sa.String, nullable=False, server_default=""),
        sa.Column("data_referencia", sa.Date, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("embedding", sa.JSON, nullable=True),
        sa.Column("indexado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_documentos_vetoriais_empresa_id", "documentos_vetoriais", ["empresa_id"])
    op.create_index("ix_documentos_vetoriais_tipo_documento", "documentos_vetoriais", ["tipo_documento"])

    # ── embedding_jobs (FK documentos_vetoriais) ─────────────────────────────
    op.create_table(
        "embedding_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("documento_id", sa.Integer, sa.ForeignKey("documentos_vetoriais.id"), nullable=False),
        sa.Column("status", sa.String(15), nullable=False, server_default="PENDENTE"),
        sa.Column("erro", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_embedding_jobs_empresa_id", "embedding_jobs", ["empresa_id"])


def downgrade() -> None:
    op.drop_table("embedding_jobs")
    op.drop_table("documentos_vetoriais")
    op.drop_table("usage_logs")
    op.drop_table("chat_mensagens")
    op.drop_table("chat_sessoes")
    op.drop_table("planos_acao")
    op.drop_table("oportunidades")
    op.drop_table("score_historicos")
    op.drop_table("scores_logisticos")
    op.drop_table("diagnostico_historicos")
    op.drop_table("diagnosticos_ia")
    op.drop_table("insight_execucoes")
    op.drop_table("insights")
    op.drop_table("regras_insight")
    op.drop_index("ix_benchmarks_setoriais_segmento", table_name="benchmarks_setoriais")
    op.drop_table("benchmarks_setoriais")

    with op.batch_alter_table("benchmarks_corredor", schema=None) as batch_op:
        batch_op.drop_column("prazo_dias_medio")

    with op.batch_alter_table("bids", schema=None) as batch_op:
        batch_op.drop_column("segmentacao_valor")
        batch_op.drop_column("segmentacao_tipo")
