"""RAG Seletivo (Fase 7 — V4).

Indexa apenas documentos de CONHECIMENTO (não CT-es brutos):
- Benchmarks
- Relatórios executivos
- Diagnósticos históricos
- BIDs encerrados
- Legislação ANTT

A busca é por similaridade de cosseno sobre embeddings. Em SQLite/modo
simulado, a similaridade é calculada em Python; em PostgreSQL com pgvector,
o mesmo armazenamento JSON funciona (a otimização nativa com coluna Vector +
índice ivfflat é o caminho para grandes volumes, documentado no guia).

FILTRO POR empresa_id É OBRIGATÓRIO em toda busca — um documento de uma
empresa nunca é recuperado para outra.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.ai.llm_client import get_llm_client
from app.infrastructure.database.models import (
    DocumentoVetorialModel, EmbeddingJobModel,
)

logger = logging.getLogger(__name__)


TIPOS_INDEXAVEIS = {
    "benchmark", "relatorio", "diagnostico", "bid", "legislacao",
}


def _cosseno(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores."""
    if not a or not b or len(a) != len(b):
        return 0.0
    produto = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return produto / (na * nb)


# Legislação ANTT (trechos de referência para o RAG) — conhecimento público
LEGISLACAO_ANTT_SEED = [
    {
        "titulo": "Piso Mínimo de Frete (Lei 13.703/2018)",
        "conteudo": "A Política Nacional de Pisos Mínimos do Transporte Rodoviário "
                    "de Cargas estabelece valores mínimos por eixo carregado e por "
                    "quilômetro rodado, conforme tabelas publicadas pela ANTT. O piso "
                    "varia por tipo de carga (geral, granel, frigorificada, perigosa, "
                    "neogranel, conteinerizada) e número de eixos. O contratante deve "
                    "observar o piso vigente na data da contratação do frete.",
    },
    {
        "titulo": "Resolução ANTT sobre componentes do frete",
        "conteudo": "O valor do frete pode ser composto por: frete-peso (proporcional "
                    "ao peso/distância), frete-valor (ad valorem, percentual sobre o "
                    "valor da mercadoria), GRIS (Gerenciamento de Risco), pedágio, taxas "
                    "de coleta e entrega, TDE (taxa de dificuldade de entrega) e TDA "
                    "(taxa de difícil acesso). A composição deve constar no CT-e.",
    },
    {
        "titulo": "Prazos e OTIF no transporte rodoviário",
        "conteudo": "O cumprimento de prazos de entrega (lead time) e a integridade da "
                    "carga são indicadores centrais de desempenho logístico. O OTIF "
                    "(On Time In Full) mede o percentual de entregas no prazo e completas. "
                    "Atrasos e avarias impactam custo total de propriedade e nível de "
                    "serviço ao cliente final.",
    },
]


class RagService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()

    @property
    def disponivel(self) -> bool:
        """RAG está habilitado? (em SQLite funciona com cosseno em Python)."""
        return settings.RAG_ENABLED

    # ─────────── Indexação ───────────
    def indexar_documento(
        self, empresa_id: int, tipo_documento: str, titulo: str,
        conteudo: str, data_referencia: Optional[date] = None,
        metadata: Optional[dict] = None,
    ) -> DocumentoVetorialModel:
        """Cria e indexa um documento (gera embedding na hora)."""
        if tipo_documento not in TIPOS_INDEXAVEIS:
            raise ValueError(
                f"Tipo '{tipo_documento}' não é indexável. "
                f"Permitidos: {sorted(TIPOS_INDEXAVEIS)}"
            )

        doc = DocumentoVetorialModel(
            empresa_id=empresa_id, tipo_documento=tipo_documento,
            titulo=titulo[:300], conteudo=conteudo,
            data_referencia=data_referencia, doc_metadata=metadata or {},
            indexado=False,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        # Gera embedding do título + conteúdo
        texto = f"{titulo}\n{conteudo}"
        doc.embedding = self.llm.gerar_embedding(texto)
        doc.indexado = True
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def reindexar_pendentes(self, empresa_id: int = None) -> int:
        """Gera embeddings para documentos ainda não indexados."""
        q = self.db.query(DocumentoVetorialModel).filter(
            DocumentoVetorialModel.indexado == False  # noqa: E712
        )
        if empresa_id is not None:
            q = q.filter(DocumentoVetorialModel.empresa_id == empresa_id)
        docs = q.all()
        for doc in docs:
            texto = f"{doc.titulo}\n{doc.conteudo}"
            doc.embedding = self.llm.gerar_embedding(texto)
            doc.indexado = True
        self.db.commit()
        return len(docs)

    # ─────────── Busca semântica ───────────
    def buscar(
        self, empresa_id: int, consulta: str, *,
        top_k: int = 4, tipos: Optional[list[str]] = None,
        incluir_globais: bool = True,
    ) -> list[dict]:
        """Busca os documentos mais relevantes para a consulta.

        SEMPRE filtra por empresa_id. Documentos de legislação (empresa_id=0)
        podem ser compartilhados como conhecimento global se incluir_globais.
        """
        emb_consulta = self.llm.gerar_embedding(consulta)

        q = self.db.query(DocumentoVetorialModel).filter(
            DocumentoVetorialModel.indexado == True  # noqa: E712
        )
        # Isolamento: documentos da empresa + (opcional) globais (empresa_id=0)
        if incluir_globais:
            q = q.filter(
                (DocumentoVetorialModel.empresa_id == empresa_id) |
                (DocumentoVetorialModel.empresa_id == 0)
            )
        else:
            q = q.filter(DocumentoVetorialModel.empresa_id == empresa_id)

        if tipos:
            q = q.filter(DocumentoVetorialModel.tipo_documento.in_(tipos))

        candidatos = q.all()

        # Calcula similaridade
        resultados = []
        for doc in candidatos:
            if not doc.embedding:
                continue
            sim = _cosseno(emb_consulta, doc.embedding)
            resultados.append({
                "id": doc.id, "tipo": doc.tipo_documento, "titulo": doc.titulo,
                "conteudo": doc.conteudo, "similaridade": round(sim, 4),
                "empresa_id": doc.empresa_id,
            })

        resultados.sort(key=lambda r: r["similaridade"], reverse=True)
        return resultados[:top_k]

    def montar_contexto(self, empresa_id: int, consulta: str, top_k: int = 3) -> str:
        """Monta um bloco de contexto textual com os documentos relevantes."""
        docs = self.buscar(empresa_id, consulta, top_k=top_k)
        if not docs:
            return ""
        partes = ["Contexto recuperado da base de conhecimento:"]
        for d in docs:
            partes.append(f"\n[{d['tipo'].upper()}] {d['titulo']}\n{d['conteudo']}")
        return "\n".join(partes)

    # ─────────── Seed e auto-indexação ───────────
    def indexar_legislacao_antt(self) -> int:
        """Indexa a legislação ANTT como conhecimento global (empresa_id=0)."""
        count = 0
        for item in LEGISLACAO_ANTT_SEED:
            existe = self.db.query(DocumentoVetorialModel).filter(
                DocumentoVetorialModel.empresa_id == 0,
                DocumentoVetorialModel.tipo_documento == "legislacao",
                DocumentoVetorialModel.titulo == item["titulo"],
            ).first()
            if existe:
                continue
            doc = DocumentoVetorialModel(
                empresa_id=0, tipo_documento="legislacao",
                titulo=item["titulo"], conteudo=item["conteudo"],
                doc_metadata={"fonte": "ANTT"}, indexado=False,
            )
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)
            doc.embedding = self.llm.gerar_embedding(f"{item['titulo']}\n{item['conteudo']}")
            doc.indexado = True
            self.db.commit()
            count += 1
        return count

    def indexar_diagnostico(self, empresa_id: int, diagnostico) -> None:
        """Indexa um diagnóstico recém-gerado para consulta futura."""
        conteudo = (
            f"{diagnostico.resumo_executivo}\n\n"
            f"Pontos fortes: {diagnostico.pontos_fortes}\n"
            f"Pontos de atenção: {diagnostico.pontos_atencao}\n"
            f"Plano de ação: {diagnostico.plano_acao}"
        )
        try:
            self.indexar_documento(
                empresa_id, "diagnostico",
                f"Diagnóstico de {diagnostico.created_at:%d/%m/%Y}" if diagnostico.created_at else "Diagnóstico",
                conteudo,
                metadata={"score": diagnostico.score_logistico,
                          "economia": diagnostico.economia_potencial},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao indexar diagnóstico: %s", e)

    def listar(self, empresa_id: int) -> list[DocumentoVetorialModel]:
        return (
            self.db.query(DocumentoVetorialModel)
            .filter(
                (DocumentoVetorialModel.empresa_id == empresa_id) |
                (DocumentoVetorialModel.empresa_id == 0)
            )
            .order_by(DocumentoVetorialModel.created_at.desc())
            .all()
        )

    def estatisticas(self, empresa_id: int) -> dict:
        docs = self.listar(empresa_id)
        por_tipo = {}
        for d in docs:
            por_tipo[d.tipo_documento] = por_tipo.get(d.tipo_documento, 0) + 1
        return {
            "total_documentos": len(docs),
            "indexados": sum(1 for d in docs if d.indexado),
            "por_tipo": por_tipo,
            "rag_disponivel": self.disponivel,
        }
