"""Ponto de entrada da aplicação FastAPI — GD Diagnóstico Logístico.

Configura logging (RNF002), CORS (RNF003), documentação Swagger (RNF005),
registra todos os routers da API v1 e executa a rotina de seed na inicialização.

Segurança ativa:
  - Rate limiting (slowapi): brute-force protection no login
  - defusedxml: proteção XXE no parser de CT-e
  - Swagger/Redoc desabilitados em ENVIRONMENT=production
  - CORS restritivo (métodos e headers explícitos)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging_config import get_logger, setup_logging
from app.core.security import hash_password
from app.infrastructure.database.models import (  # noqa: F401
    BenchmarkCorredorModel,
    BenchmarkModel,
    BidAuditoriaModel,
    BidEscopoModel,
    BidModel,
    BidPropostaModel,
    BidSimulacaoModel,
    BidTransportadoraModel,
    ClusterClienteModel,
    CTeModel,
    CidadeModel,
    EmpresaModel,
    FilialModel,
    HubLogisticoModel,
    MetaNacionalModel,
    MetaRegionalModel,
    NFeModel,
    RegiaoModel,
    TransportadoraModel,
    UserModel,
)
from app.presentation.api.v1 import api_router

setup_logging()
logger = get_logger(__name__)

# ── Rate Limiter (slowapi) ────────────────────────────────────────────────────
# Instância global — injetada nos endpoints via Depends ou usado como state.
# Por padrão usa o IP remoto como chave de identificação.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

BENCHMARKS_SEED = [
    ("NACIONAL", 1.30, 1.65, 2.00, 8.0, 10.0, 12.0),
    ("NORTE", 2.50, 3.75, 5.00, 15.0, 22.0, 30.0),
    ("NORDESTE", 1.50, 2.15, 2.80, 10.0, 14.0, 18.0),
    ("CENTRO_OESTE", 1.20, 1.60, 2.00, 7.0, 9.5, 12.0),
    ("SUDESTE", 0.70, 0.95, 1.20, 4.0, 6.0, 8.0),
    ("SUL", 0.80, 1.10, 1.40, 5.0, 7.0, 9.0),
]


def criar_tabelas() -> None:
    """Cria as tabelas no banco. Usa checkfirst por tabela para evitar
    o erro 'index already exists' que ocorre quando extend_existing=True
    e índices são registrados duas vezes no metadata do SQLAlchemy."""
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            table.create(bind=conn, checkfirst=True)
    logger.info("Tabelas verificadas/criadas com sucesso.")


def _aplicar_alteracoes_incrementais() -> None:
    """Aplica alterações de schema em tabelas já existentes (colunas novas, etc).

    O create_all só cria tabelas inexistentes — não adiciona colunas novas
    a tabelas que já existiam. Este método cobre esse gap usando
    ADD COLUMN IF NOT EXISTS, tornando o startup idempotente mesmo sem
    rodar o Alembic manualmente.

    Mantém paridade com a migração d7f2b8c3e9a1 (hardening multi-tenant).
    """
    from sqlalchemy import select, text

    alteracoes = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresas(id)",
        "CREATE INDEX IF NOT EXISTS ix_users_empresa_id ON users (empresa_id)",
        # Setor (segmento econômico) do embarcador — paridade com a migração
        # b8e3f1a2c9d4 (v6.3.1). server/DEFAULT 'Outros' preenche linhas legadas.
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS setor VARCHAR(40) NOT NULL DEFAULT 'Outros'",
        "CREATE INDEX IF NOT EXISTS ix_empresas_setor ON empresas (setor)",
        "ALTER TABLE bids ADD COLUMN IF NOT EXISTS segmentacao_tipo VARCHAR(20) NOT NULL DEFAULT 'GERAL'",
        "ALTER TABLE bids ADD COLUMN IF NOT EXISTS segmentacao_valor VARCHAR(200) NOT NULL DEFAULT ''",
        "ALTER TABLE bid_propostas ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE",
        # DLG — Diagnóstico Logístico (tabelas analíticas)
        """CREATE TABLE IF NOT EXISTS dlg_analitico (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            dimensao VARCHAR(20) NOT NULL,
            chave VARCHAR(200) NOT NULL,
            chave_label VARCHAR(300) NOT NULL DEFAULT '',
            periodo_ref VARCHAR(7) NOT NULL,
            qtd_ctes INTEGER NOT NULL DEFAULT 0,
            peso_total FLOAT NOT NULL DEFAULT 0,
            frete_total FLOAT NOT NULL DEFAULT 0,
            mercadoria_total FLOAT NOT NULL DEFAULT 0,
            rs_kg FLOAT NOT NULL DEFAULT 0,
            pct_frete FLOAT NOT NULL DEFAULT 0,
            custo_medio_entrega FLOAT NOT NULL DEFAULT 0,
            rs_kg_ref FLOAT NOT NULL DEFAULT 0,
            desvio_pct FLOAT NOT NULL DEFAULT 0,
            classificacao VARCHAR(15) NOT NULL DEFAULT 'SEM_REF',
            processado_em TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_dlg_analitico UNIQUE (empresa_id, dimensao, chave, periodo_ref)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_dlg_analitico_empresa_id ON dlg_analitico (empresa_id)",
        "CREATE INDEX IF NOT EXISTS ix_dlg_analitico_dimensao ON dlg_analitico (dimensao)",
        "CREATE INDEX IF NOT EXISTS ix_dlg_analitico_chave ON dlg_analitico (chave)",
        "CREATE INDEX IF NOT EXISTS ix_dlg_analitico_periodo_ref ON dlg_analitico (periodo_ref)",
        """CREATE TABLE IF NOT EXISTS dlg_outliers (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            cte_id INTEGER NOT NULL REFERENCES ctes(id),
            periodo_ref VARCHAR(7) NOT NULL,
            tipo_outlier VARCHAR(30) NOT NULL,
            valor_real FLOAT NOT NULL DEFAULT 0,
            valor_limite FLOAT NOT NULL DEFAULT 0,
            desvio_pct FLOAT NOT NULL DEFAULT 0,
            detectado_em TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_dlg_outlier UNIQUE (empresa_id, cte_id, periodo_ref, tipo_outlier)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_dlg_outliers_empresa_id ON dlg_outliers (empresa_id)",
        "CREATE INDEX IF NOT EXISTS ix_dlg_outliers_cte_id ON dlg_outliers (cte_id)",
        "CREATE INDEX IF NOT EXISTS ix_dlg_outliers_periodo_ref ON dlg_outliers (periodo_ref)",
        # MBL — Benchmark Logístico (estatístico versionado)
        """CREATE TABLE IF NOT EXISTS mbl_benchmark (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            dimensao VARCHAR(20) NOT NULL,
            segmento VARCHAR(200) NOT NULL,
            metrica VARCHAR(20) NOT NULL,
            periodo_ref VARCHAR(7) NOT NULL,
            amostra INTEGER NOT NULL DEFAULT 0,
            p10 FLOAT NOT NULL DEFAULT 0,
            p25 FLOAT NOT NULL DEFAULT 0,
            p50 FLOAT NOT NULL DEFAULT 0,
            p75 FLOAT NOT NULL DEFAULT 0,
            p90 FLOAT NOT NULL DEFAULT 0,
            media FLOAT NOT NULL DEFAULT 0,
            desvio_padrao FLOAT NOT NULL DEFAULT 0,
            low_confidence BOOLEAN NOT NULL DEFAULT FALSE,
            outliers_excluidos INTEGER NOT NULL DEFAULT 0,
            versao INTEGER NOT NULL DEFAULT 1,
            gerado_em TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_mbl_benchmark UNIQUE (empresa_id, dimensao, segmento, metrica, periodo_ref)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_empresa_id ON mbl_benchmark (empresa_id)",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_dimensao ON mbl_benchmark (dimensao)",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_segmento ON mbl_benchmark (segmento)",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_metrica ON mbl_benchmark (metrica)",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_periodo_ref ON mbl_benchmark (periodo_ref)",
        "CREATE INDEX IF NOT EXISTS ix_mbl_benchmark_low_confidence ON mbl_benchmark (low_confidence)",
        # MCL — Concorrência Logística (decisão de BID versionada)
        """CREATE TABLE IF NOT EXISTS mcl_decisoes (
            id SERIAL PRIMARY KEY,
            bid_id INTEGER NOT NULL REFERENCES bids(id),
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            versao INTEGER NOT NULL DEFAULT 1,
            vencedora_bt_id INTEGER NOT NULL DEFAULT 0,
            vencedora_transp_id INTEGER NOT NULL DEFAULT 0,
            vencedora_nome VARCHAR(200) NOT NULL DEFAULT '',
            score_vencedora FLOAT NOT NULL DEFAULT 0,
            diferenca_segunda FLOAT NOT NULL DEFAULT 0,
            peso_custo FLOAT NOT NULL DEFAULT 0.40,
            peso_dlg FLOAT NOT NULL DEFAULT 0.25,
            peso_mbl FLOAT NOT NULL DEFAULT 0.20,
            peso_sla FLOAT NOT NULL DEFAULT 0.10,
            peso_estabilidade FLOAT NOT NULL DEFAULT 0.05,
            ranking JSON,
            justificativa VARCHAR(1000) NOT NULL DEFAULT '',
            propostas_rejeitadas JSON,
            gerado_em TIMESTAMP DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_mcl_decisoes_bid_id ON mcl_decisoes (bid_id)",
        "CREATE INDEX IF NOT EXISTS ix_mcl_decisoes_empresa_id ON mcl_decisoes (empresa_id)",
        """DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_cluster_empresa_uf_mun'
                  AND conrelid = 'clusters_cliente'::regclass
            ) THEN
                ALTER TABLE clusters_cliente
                ADD CONSTRAINT uq_cluster_empresa_uf_mun
                UNIQUE (empresa_id, uf, municipio);
            END IF;
        END $$""",
        """DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_corredor_origem_destino'
                  AND conrelid = 'benchmarks_corredor'::regclass
            ) THEN
                ALTER TABLE benchmarks_corredor
                ADD CONSTRAINT uq_corredor_origem_destino
                UNIQUE (hub_origem_codigo, hub_destino_codigo);
            END IF;
        END $$""",
        # ── V6.4.0 — MELHORIA 1: situação/cancelamento do CT-e ──
        "ALTER TABLE ctes ADD COLUMN IF NOT EXISTS status VARCHAR(10) NOT NULL DEFAULT 'ATIVO'",
        "ALTER TABLE ctes ADD COLUMN IF NOT EXISTS cancelado_em DATE",
        "ALTER TABLE ctes ADD COLUMN IF NOT EXISTS protocolo_cancelamento VARCHAR(30)",
        "ALTER TABLE ctes ADD COLUMN IF NOT EXISTS numero_evento_cancelamento VARCHAR(30)",
        "CREATE INDEX IF NOT EXISTS ix_ctes_status ON ctes (status)",
        """CREATE TABLE IF NOT EXISTS cte_cancelamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            cte_id INTEGER REFERENCES ctes(id),
            chave VARCHAR(50) NOT NULL,
            protocolo VARCHAR(30) NOT NULL DEFAULT '',
            numero_evento VARCHAR(30) NOT NULL DEFAULT '',
            tipo_evento VARCHAR(10) NOT NULL DEFAULT '',
            data_cancelamento DATE,
            resultado VARCHAR(20) NOT NULL DEFAULT '',
            mensagem VARCHAR(500) NOT NULL DEFAULT '',
            arquivo VARCHAR(255) NOT NULL DEFAULT '',
            xml_evento TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_cte_cancelamentos_empresa_id ON cte_cancelamentos (empresa_id)",
        "CREATE INDEX IF NOT EXISTS ix_cte_cancelamentos_cte_id ON cte_cancelamentos (cte_id)",
        "CREATE INDEX IF NOT EXISTS ix_cte_cancelamentos_chave ON cte_cancelamentos (chave)",
        "CREATE INDEX IF NOT EXISTS ix_cte_cancelamentos_resultado ON cte_cancelamentos (resultado)",
        "CREATE INDEX IF NOT EXISTS ix_cte_cancelamentos_created_at ON cte_cancelamentos (created_at)",
        """DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_cte_cancelamento_evento'
                  AND conrelid = 'cte_cancelamentos'::regclass
            ) THEN
                ALTER TABLE cte_cancelamentos
                ADD CONSTRAINT uq_cte_cancelamento_evento
                UNIQUE (empresa_id, chave, numero_evento);
            END IF;
        END $$""",
        # ── V6.4.0 — MELHORIA 8: recomendações consolidadas ──
        """CREATE TABLE IF NOT EXISTS recomendacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            titulo VARCHAR(300) NOT NULL,
            descricao VARCHAR(2000) NOT NULL DEFAULT '',
            indicador VARCHAR(40) NOT NULL DEFAULT '',
            chave_origem VARCHAR(200) NOT NULL DEFAULT '',
            valor_encontrado VARCHAR(120) NOT NULL DEFAULT '',
            valor_recomendado VARCHAR(120) NOT NULL DEFAULT '',
            impacto VARCHAR(200) NOT NULL DEFAULT '',
            economia_estimada FLOAT NOT NULL DEFAULT 0,
            prioridade VARCHAR(10) NOT NULL DEFAULT 'MEDIA',
            origem VARCHAR(10) NOT NULL DEFAULT 'REGRA',
            status VARCHAR(15) NOT NULL DEFAULT 'ABERTA',
            dados JSON,
            gerado_em TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_recomendacao_origem UNIQUE (empresa_id, indicador, chave_origem)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_recomendacoes_empresa_id ON recomendacoes (empresa_id)",
        "CREATE INDEX IF NOT EXISTS ix_recomendacoes_indicador ON recomendacoes (indicador)",
        "CREATE INDEX IF NOT EXISTS ix_recomendacoes_prioridade ON recomendacoes (prioridade)",
        # ── V6.4.0 — MELHORIA 9: dimensão CLIENTE → FILIAL (dados) ──
        "UPDATE dlg_analitico SET dimensao='FILIAL' WHERE dimensao='CLIENTE'",
        # ── V6.11.0 — Simulador de Hub: prazo de referência por corredor ──
        "ALTER TABLE benchmarks_corredor ADD COLUMN IF NOT EXISTS prazo_dias_medio FLOAT NOT NULL DEFAULT 0",
    ]

    is_sqlite = str(engine.url).startswith("sqlite")

    with engine.begin() as conn:
        for sql in alteracoes:
            if is_sqlite and "DO $$" in sql:
                continue
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.debug("Alteração incremental ignorada (%s): %s", type(e).__name__, str(e)[:120])

    logger.info("Alterações incrementais de schema aplicadas.")


def seed_inicial() -> None:
    """Popula dados iniciais obrigatórios (admin, metas, benchmarks, hubs).

    Usa a API select() do SQLAlchemy 2.x em vez de db.query() para evitar
    o erro 'Multiple classes found for FilialModel' que ocorre quando o
    registry de mapeadores tem duplicatas por conta de caminhos de import
    divergentes no ambiente Windows.
    """
    from sqlalchemy import select
    db = SessionLocal()
    try:
        def existe(model, *filtros):
            return db.execute(select(model).where(*filtros)).first() is not None

        if not existe(UserModel, UserModel.email == settings.FIRST_SUPERUSER_EMAIL):
            db.add(UserModel(
                nome=settings.FIRST_SUPERUSER_NAME,
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
                is_active=True, is_superuser=True,
            ))
            logger.info("Usuário administrador inicial criado: %s", settings.FIRST_SUPERUSER_EMAIL)

        # Metas (nacional/regional) não são mais globais — cada empresa
        # ganha seu próprio conjunto zerado ao ser criada (ver
        # seed_metas_padroes, chamado em empresas.py::criar()).

        for (regiao, kg_min, kg_med, kg_max, pct_min, pct_med, pct_max) in BENCHMARKS_SEED:
            if not existe(BenchmarkModel, BenchmarkModel.regiao == regiao):
                db.add(BenchmarkModel(
                    regiao=regiao, frete_kg_min=kg_min, frete_kg_medio=kg_med, frete_kg_max=kg_max,
                    frete_pct_min=pct_min, frete_pct_medio=pct_med, frete_pct_max=pct_max,
                ))

        # Hubs logísticos não são mais um catálogo global — cada empresa
        # cria e mantém o seu próprio, sem seed automático (v6.13).

        db.commit()
        logger.info("Seed concluído.")
    except Exception:
        db.rollback()
        logger.exception(
            "Falha durante o seed inicial — aplicação continua. "
            "Verifique o schema do banco (rode: alembic upgrade head)."
        )
    finally:
        db.close()


def _hub_para_regiao(codigo: str) -> str:
    """Converte o código de hub legado ('SUDESTE_HUB') na macrorregião ('SUDESTE')."""
    return (codigo or "").upper().replace("_HUB", "").replace("HUB", "").strip()


def migrar_benchmark_mercado_v2() -> None:
    """Benchmark V2 — popula benchmark_mercado (matriz OD por região) a partir dos
    corredores legados, UMA vez (idempotente: só age se a tabela estiver vazia).

    Os corredores guardam min/médio/máx; convertemos para percentis de forma
    aproximada (p10=min, p50=médio, p90=máx; p25/p75 interpolados). Origem marcada
    como 'MERCADO_LEGADO' para rastrear que veio de migração, não de coleta nova.
    As tabelas antigas (benchmarks, benchmarks_corredor) permanecem intactas.
    """
    from sqlalchemy import select
    from app.infrastructure.database.models import (
        BenchmarkMercadoModel, BenchmarkCorredorModel,
    )
    db = SessionLocal()
    try:
        ja_tem = db.execute(select(BenchmarkMercadoModel.id).limit(1)).first()
        if ja_tem:
            return  # já migrado / já há dados de mercado

        corredores = db.execute(select(BenchmarkCorredorModel)).scalars().all()
        criados = 0
        for c in corredores:
            origem = _hub_para_regiao(c.hub_origem_codigo)
            destino = _hub_para_regiao(c.hub_destino_codigo)
            if not origem or not destino:
                continue
            mn, md, mx = c.frete_kg_min, c.frete_kg_medio, c.frete_kg_max
            db.add(BenchmarkMercadoModel(
                origem_regiao=origem, destino_regiao=destino,
                modal="", tipo_operacao="TODOS", faixa_peso_min=0.0, faixa_peso_max=0.0,
                rs_kg_p10=mn,
                rs_kg_p25=round(mn + (md - mn) / 2, 4),
                rs_kg_p50=md,
                rs_kg_p75=round(md + (mx - md) / 2, 4),
                rs_kg_p90=mx,
                fonte="MERCADO_LEGADO",
            ))
            criados += 1
        db.commit()
        if criados:
            logger.info("Benchmark V2: %d corredores migrados para benchmark_mercado (OD).", criados)
    except Exception:
        db.rollback()
        logger.exception("Falha na migração do Benchmark V2 — aplicação continua.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando %s v%s", settings.PROJECT_NAME, settings.VERSION)
    # R-07: em produção, o schema é responsabilidade EXCLUSIVA do Alembic.
    # create_all + seed automáticos rodam apenas fora de produção (dev/local),
    # evitando divergência de schema e seed indevido no ambiente produtivo.
    if not settings.is_production:
        criar_tabelas()
        _aplicar_alteracoes_incrementais()
        seed_inicial()
        migrar_benchmark_mercado_v2()
    else:
        logger.info("Ambiente de produção: schema gerenciado por Alembic (migrations). "
                    "create_all/seed automáticos desativados.")
        if settings.secret_key_insegura:
            # Defesa adicional além do validator de config.
            raise RuntimeError("SECRET_KEY insegura em produção. Abortando inicialização.")
    yield
    logger.info("Encerrando aplicação.")


# ── Swagger: desabilitado em produção ─────────────────────────────────────────
_docs_url  = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else f"{settings.API_V1_PREFIX}/openapi.json"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API do GD Diagnóstico Logístico — diagnóstico de custos logísticos a partir "
        "da importação de CT-es, NF-es e planilhas, com indicadores nacionais, "
        "regionais, por transportadora e de prazo, além de relatórios em Excel e PDF."
    ),
    openapi_url=_openapi_url,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

# ── Rate Limiting (SlowAPI) ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Métodos e headers explícitos em vez de "*" para reduzir superfície de ataque.
# TRACE e CONNECT (vetores XST) ficam excluídos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["health"])
def health_check():
    """Verificação simples de disponibilidade da API."""
    return {"aplicacao": settings.PROJECT_NAME, "versao": settings.VERSION, "status": "online"}
