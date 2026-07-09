"""Serviço de registro de uso de IA (UsageLog).

Toda chamada ao LLM passa por aqui para auditoria e controle de custo,
conforme exigência de segurança da V4. Registra: empresa, usuário,
feature, modelo, tokens, custo (USD e BRL) e se foi simulado.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.ai.llm_client import RespostaLLM
from app.infrastructure.database.models import UsageLogModel

logger = logging.getLogger(__name__)


def registrar_uso(
    db: Session,
    resposta: RespostaLLM,
    *,
    feature: str,
    empresa_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> UsageLogModel:
    """Registra uma chamada de IA no banco para auditoria de custo."""
    log = UsageLogModel(
        empresa_id=empresa_id,
        user_id=user_id,
        feature=feature,
        modelo=resposta.modelo,
        tokens_input=resposta.tokens_input,
        tokens_output=resposta.tokens_output,
        custo_usd=resposta.custo_usd,
        custo_brl=resposta.custo_brl,
        simulado=resposta.simulado,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def custo_total_empresa(db: Session, empresa_id: int) -> dict:
    """Retorna o custo acumulado de IA de uma empresa."""
    from sqlalchemy import func as f

    row = (
        db.query(
            f.coalesce(f.sum(UsageLogModel.custo_brl), 0.0),
            f.coalesce(f.sum(UsageLogModel.tokens_input + UsageLogModel.tokens_output), 0),
            f.count(UsageLogModel.id),
        )
        .filter(UsageLogModel.empresa_id == empresa_id)
        .first()
    )
    return {
        "custo_brl_total": round(row[0], 2),
        "tokens_total": int(row[1]),
        "chamadas_total": int(row[2]),
    }
