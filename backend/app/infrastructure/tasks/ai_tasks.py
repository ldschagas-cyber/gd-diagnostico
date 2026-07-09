"""Tarefas assíncronas de IA executadas via Celery (V4).

Estas tarefas rodam em background para não bloquear o servidor HTTP:
- Geração de diagnóstico IA
- Cálculo de insights diários (todas as empresas)
- Geração de relatório executivo

Em modo simulado ou sem Redis, podem ser chamadas diretamente (síncrono)
através das funções `_executar_*` que cada task encapsula.
"""
from __future__ import annotations

import logging

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def gerar_diagnostico_async(self, empresa_id: int, periodo_inicio: str = None, periodo_fim: str = None):
    """Gera um diagnóstico IA em background."""
    try:
        from app.core.database import SessionLocal
        from app.application.use_cases.diagnostico_ia import DiagnosticoIAUseCase

        db = SessionLocal()
        try:
            uc = DiagnosticoIAUseCase(db)
            resultado = uc.gerar(empresa_id, periodo_inicio, periodo_fim)
            return {"status": "ok", "diagnostico_id": resultado.id}
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro ao gerar diagnóstico para empresa %s", empresa_id)
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=3)
def gerar_insights_empresa(self, empresa_id: int):
    """Executa o motor de insights para uma empresa."""
    try:
        from app.core.database import SessionLocal
        from app.application.use_cases.insights import InsightsUseCase

        db = SessionLocal()
        try:
            uc = InsightsUseCase(db)
            total = uc.executar(empresa_id)
            return {"status": "ok", "empresa_id": empresa_id, "insights": total}
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro ao gerar insights para empresa %s", empresa_id)
        raise self.retry(exc=exc, countdown=10)


@celery_app.task
def gerar_insights_todas_empresas():
    """Tarefa periódica (Celery Beat): gera insights para todas as empresas."""
    from app.core.database import SessionLocal
    from app.infrastructure.database.models import EmpresaModel

    db = SessionLocal()
    try:
        empresas = db.query(EmpresaModel.id).all()
        total = 0
        for (empresa_id,) in empresas:
            gerar_insights_empresa.delay(empresa_id)
            total += 1
        return {"status": "ok", "empresas_agendadas": total}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def gerar_relatorio_executivo_async(self, empresa_id: int, formato: str = "pdf"):
    """Gera relatório executivo IA em background."""
    try:
        from app.core.database import SessionLocal
        from app.application.use_cases.relatorio_ia import RelatorioIAUseCase

        db = SessionLocal()
        try:
            uc = RelatorioIAUseCase(db)
            caminho = uc.gerar(empresa_id, formato)
            return {"status": "ok", "arquivo": caminho}
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro ao gerar relatório para empresa %s", empresa_id)
        raise self.retry(exc=exc, countdown=15)


@celery_app.task
def ping():
    """Tarefa de teste para validar que o worker está operacional (DT-09)."""
    return {"status": "pong", "worker": "ok"}
