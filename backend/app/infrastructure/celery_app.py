"""Configuração do Celery para processamento assíncrono (V4 — DT-09).

O Celery executa tarefas pesadas de IA em background, sem bloquear o
servidor HTTP: geração de diagnósticos, relatórios executivos, cálculo
de insights diários e embeddings.

Broker e backend usam Redis. Em desenvolvimento sem Redis, as tarefas
podem ser executadas de forma síncrona via CELERY_TASK_ALWAYS_EAGER.
"""
from __future__ import annotations

import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "gd_frete",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.infrastructure.tasks.ai_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,          # 5 min hard limit
    task_soft_time_limit=240,     # 4 min soft limit
    task_acks_late=True,          # confirma só após concluir (retry seguro)
    worker_prefetch_multiplier=1,
    task_default_retry_delay=10,
    task_max_retries=3,
)

# Agendamento periódico (Celery Beat) — insights diários
celery_app.conf.beat_schedule = {
    "gerar-insights-diarios": {
        "task": "app.infrastructure.tasks.ai_tasks.gerar_insights_todas_empresas",
        "schedule": 60 * 60 * 24,  # a cada 24h
    },
}


def celery_disponivel() -> bool:
    """Verifica se o broker Redis está acessível."""
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1, timeout=2)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Celery/Redis indisponível: %s", e)
        return False
