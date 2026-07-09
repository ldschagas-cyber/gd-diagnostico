"""Assistente Logístico IA (Fase 6 — V4).

Chat conversacional que usa Tool-Calling para responder perguntas sobre
os dados do cliente. A IA escolhe ferramentas; o backend executa SQL real;
a IA narra. Isolamento por empresa_id em toda a conversa.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.infrastructure.ai.llm_client import get_llm_client, ModeloTipo
from app.infrastructure.ai.usage_logger import registrar_uso
from app.infrastructure.database.models import ChatSessaoModel, ChatMensagemModel
from app.application.use_cases.assistente_tools import (
    FerramentasLogisticas, DEFINICOES_FERRAMENTAS,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Assistente Logístico da GD Conecta, especializado em análise \
de frete. Responda perguntas sobre a operação logística do cliente usando as ferramentas \
disponíveis.

REGRAS:
- SEMPRE use as ferramentas para obter números. Nunca invente valores.
- Os números retornados pelas ferramentas são a verdade absoluta.
- Responda em português brasileiro, de forma clara e objetiva.
- Após obter os dados, interprete-os e sugira ações quando fizer sentido."""


class AssistenteUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()

    def criar_sessao(self, empresa_id: int, user_id: int = None, titulo: str = "Nova conversa") -> ChatSessaoModel:
        sessao = ChatSessaoModel(empresa_id=empresa_id, user_id=user_id, titulo=titulo)
        self.db.add(sessao)
        self.db.commit()
        self.db.refresh(sessao)
        return sessao

    def listar_sessoes(self, empresa_id: int) -> list[ChatSessaoModel]:
        return (
            self.db.query(ChatSessaoModel)
            .filter(ChatSessaoModel.empresa_id == empresa_id)
            .order_by(ChatSessaoModel.updated_at.desc())
            .all()
        )

    def listar_mensagens(self, sessao_id: int, empresa_id: int) -> list[ChatMensagemModel]:
        return (
            self.db.query(ChatMensagemModel)
            .filter(
                ChatMensagemModel.sessao_id == sessao_id,
                ChatMensagemModel.empresa_id == empresa_id,
            )
            .order_by(ChatMensagemModel.created_at)
            .all()
        )

    def enviar_mensagem(self, sessao_id: int, empresa_id: int, mensagem: str,
                        user_id: int = None) -> ChatMensagemModel:
        """Processa uma mensagem do usuário e gera a resposta do assistente."""
        # Salva a mensagem do usuário
        msg_user = ChatMensagemModel(
            sessao_id=sessao_id, empresa_id=empresa_id,
            papel="user", conteudo=mensagem,
        )
        self.db.add(msg_user)
        self.db.commit()

        # Monta histórico recente (últimas 6 mensagens)
        historico = self._montar_historico(sessao_id, empresa_id)

        # RAG: recupera contexto de conhecimento relevante (legislação, diagnósticos, etc.)
        system_prompt = SYSTEM_PROMPT
        try:
            from app.application.use_cases.rag_service import RagService
            rag = RagService(self.db)
            if rag.disponivel:
                contexto_rag = rag.montar_contexto(empresa_id, mensagem, top_k=3)
                if contexto_rag:
                    system_prompt = f"{SYSTEM_PROMPT}\n\n{contexto_rag}"
        except Exception:  # noqa: BLE001
            pass  # RAG é complementar; falha não bloqueia o chat

        # Executor de ferramentas com isolamento por empresa
        ferramentas = FerramentasLogisticas(self.db, empresa_id)

        resposta = self.llm.conversar_com_ferramentas(
            mensagem,
            ferramentas=DEFINICOES_FERRAMENTAS,
            executor=ferramentas.executar,
            system=system_prompt,
            historico=historico,
            tipo=ModeloTipo.PRINCIPAL,
        )
        registrar_uso(self.db, resposta, feature="chat",
                      empresa_id=empresa_id, user_id=user_id)

        # Salva a resposta do assistente
        msg_assistente = ChatMensagemModel(
            sessao_id=sessao_id, empresa_id=empresa_id,
            papel="assistant", conteudo=resposta.texto,
            ferramentas_usadas={"calls": resposta.tool_calls},
            tokens=resposta.tokens_input + resposta.tokens_output,
        )
        self.db.add(msg_assistente)

        # Atualiza título da sessão na primeira interação
        sessao = self.db.query(ChatSessaoModel).filter(ChatSessaoModel.id == sessao_id).first()
        if sessao and sessao.titulo == "Nova conversa":
            sessao.titulo = mensagem[:60]

        self.db.commit()
        self.db.refresh(msg_assistente)
        return msg_assistente

    def _montar_historico(self, sessao_id: int, empresa_id: int) -> list[dict]:
        msgs = (
            self.db.query(ChatMensagemModel)
            .filter(
                ChatMensagemModel.sessao_id == sessao_id,
                ChatMensagemModel.empresa_id == empresa_id,
            )
            .order_by(ChatMensagemModel.created_at.desc())
            .limit(6)
            .all()
        )
        msgs = list(reversed(msgs))
        return [{"role": m.papel, "content": m.conteudo} for m in msgs[:-1]]  # exclui a recém-criada
