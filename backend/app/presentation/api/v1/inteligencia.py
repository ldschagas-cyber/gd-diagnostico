"""Router do módulo Inteligência Logística com IA (V4).

Endpoints:
  /inteligencia/insights              → insights automáticos
  /inteligencia/diagnostico           → diagnóstico IA
  /inteligencia/score                 → score logístico
  /inteligencia/oportunidades         → oportunidades automáticas
  /inteligencia/assistente            → chat com tool-calling
  /inteligencia/dashboard             → KPIs de inteligência
  /inteligencia/uso                   → consumo de IA (custo)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.application.use_cases.insights import InsightsUseCase
from app.application.use_cases.score_logistico import ScoreLogisticoUseCase
from app.application.use_cases.diagnostico_ia import DiagnosticoIAUseCase
from app.application.use_cases.oportunidades import OportunidadesUseCase
from app.application.use_cases.assistente import AssistenteUseCase
from app.application.use_cases.benchmark_setorial import BenchmarkSetorialUseCase
from app.application.use_cases.rag_service import RagService, TIPOS_INDEXAVEIS
from app.application.use_cases.relatorio_ia import RelatorioIAUseCase
from app.infrastructure.ai.usage_logger import custo_total_empresa
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_current_user,
    verificar_acesso_empresa,
)

router = APIRouter(prefix="/inteligencia", tags=["Inteligência IA"])


# ─────────── Schemas ───────────
class MensagemIn(BaseModel):
    mensagem: str


class SessaoIn(BaseModel):
    titulo: Optional[str] = "Nova conversa"


class DocumentoIn(BaseModel):
    tipo_documento: str
    titulo: str
    conteudo: str


class BuscaIn(BaseModel):
    consulta: str
    top_k: Optional[int] = 4


# ─────────── Status da IA ───────────
@router.get("/status")
def status_ia(_=Depends(get_current_user)):
    """Informa se a IA está em modo simulado ou real."""
    return {
        "modo_simulado": not settings.ai_ativa,
        "modelo_principal": settings.AI_MODEL_PRINCIPAL,
        "modelo_volume": settings.AI_MODEL_VOLUME,
        "rag_disponivel": settings.rag_disponivel,
        "mensagem": (
            "IA em modo simulado. Configure as chaves de API para análises reais."
            if not settings.ai_ativa else "IA ativa com modelos reais."
        ),
    }


# ─────────── Insights ───────────
@router.post("/insights/gerar")
def gerar_insights(empresa_id: int = Query(...), db: Session = Depends(get_db),
                   _=Depends(bloquear_visualizador), _ac=Depends(verificar_acesso_empresa)):
    uc = InsightsUseCase(db)
    total = uc.executar(empresa_id)
    return {"total_insights": total}


@router.get("/insights")
def listar_insights(empresa_id: int = Query(...), apenas_nao_lidos: bool = False,
                    db: Session = Depends(get_db), _=Depends(get_current_user),
                    _ac=Depends(verificar_acesso_empresa)):
    uc = InsightsUseCase(db)
    insights = uc.listar(empresa_id, apenas_nao_lidos)
    return [
        {
            "id": i.id, "categoria": i.categoria, "classificacao": i.classificacao,
            "titulo": i.titulo, "descricao": i.descricao,
            "impacto_financeiro": i.impacto_financeiro, "prioridade": i.prioridade,
            "lido": i.lido, "created_at": i.created_at,
        }
        for i in insights
    ]


@router.patch("/insights/{insight_id}/lido")
def marcar_insight_lido(insight_id: int, empresa_id: int = Query(...),
                        db: Session = Depends(get_db), _=Depends(bloquear_visualizador),
                        _ac=Depends(verificar_acesso_empresa)):
    uc = InsightsUseCase(db)
    if not uc.marcar_lido(insight_id, empresa_id):
        raise HTTPException(404, "Insight não encontrado")
    return {"ok": True}


# ─────────── Score Logístico ───────────
@router.post("/score/calcular")
def calcular_score(empresa_id: int = Query(...), db: Session = Depends(get_db),
                   _=Depends(bloquear_visualizador), _ac=Depends(verificar_acesso_empresa)):
    uc = ScoreLogisticoUseCase(db)
    score = uc.calcular(empresa_id, salvar=True)
    return _score_dict(score)


@router.get("/score")
def obter_score(empresa_id: int = Query(...), db: Session = Depends(get_db),
                _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = ScoreLogisticoUseCase(db)
    score = uc.ultimo(empresa_id) or uc.calcular(empresa_id, salvar=True)
    return _score_dict(score)


@router.get("/score/historico")
def historico_score(empresa_id: int = Query(...), db: Session = Depends(get_db),
                    _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = ScoreLogisticoUseCase(db)
    return [
        {"score_total": h.score_total, "classificacao": h.classificacao,
         "periodo": h.periodo_referencia, "created_at": h.created_at}
        for h in uc.historico(empresa_id)
    ]


def _score_dict(s):
    return {
        "score_total": s.score_total, "classificacao": s.classificacao,
        "componentes": {
            "benchmark_nacional": s.score_benchmark_nacional,
            "benchmark_regional": s.score_benchmark_regional,
            "transportadoras": s.score_transportadoras,
            "filiais": s.score_filiais, "economia": s.score_economia,
        },
        "created_at": s.created_at,
    }


# ─────────── Diagnóstico IA ───────────
@router.post("/diagnostico/gerar")
def gerar_diagnostico(empresa_id: int = Query(...), forcar: bool = False,
                      db: Session = Depends(get_db), user=Depends(bloquear_visualizador),
                      _ac=Depends(verificar_acesso_empresa)):
    uc = DiagnosticoIAUseCase(db)
    diag = uc.gerar(empresa_id, forcar=forcar, user_id=getattr(user, "id", None))
    return _diag_dict(diag)


@router.get("/diagnostico")
def obter_diagnostico(empresa_id: int = Query(...), db: Session = Depends(get_db),
                      _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = DiagnosticoIAUseCase(db)
    diag = uc.ultimo(empresa_id)
    if not diag:
        raise HTTPException(404, "Nenhum diagnóstico gerado ainda")
    return _diag_dict(diag)


@router.get("/diagnostico/historico")
def historico_diagnostico(empresa_id: int = Query(...), db: Session = Depends(get_db),
                          _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = DiagnosticoIAUseCase(db)
    return [
        {"score": h.score, "economia_potencial": h.economia_potencial,
         "resumo": h.resumo, "created_at": h.created_at}
        for h in uc.historico(empresa_id)
    ]


def _diag_dict(d):
    return {
        "id": d.id, "resumo_executivo": d.resumo_executivo,
        "pontos_fortes": d.pontos_fortes, "pontos_atencao": d.pontos_atencao,
        "principais_desvios": d.principais_desvios, "plano_acao": d.plano_acao,
        "economia_potencial": d.economia_potencial, "score_logistico": d.score_logistico,
        "modelo_usado": d.modelo_usado, "created_at": d.created_at,
    }


# ─────────── Oportunidades ───────────
@router.post("/oportunidades/detectar")
def detectar_oportunidades(empresa_id: int = Query(...), db: Session = Depends(get_db),
                           _=Depends(bloquear_visualizador), _ac=Depends(verificar_acesso_empresa)):
    uc = OportunidadesUseCase(db)
    total = uc.detectar(empresa_id)
    return {"total": total}


@router.get("/oportunidades")
def listar_oportunidades(empresa_id: int = Query(...), db: Session = Depends(get_db),
                         _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = OportunidadesUseCase(db)
    return [
        {
            "id": o.id, "tipo": o.tipo, "titulo": o.titulo, "descricao": o.descricao,
            "economia_estimada": o.economia_estimada, "impacto": o.impacto,
            "complexidade": o.complexidade, "prioridade": o.prioridade,
            "justificativa": o.justificativa, "status": o.status,
        }
        for o in uc.listar(empresa_id)
    ]


# ─────────── Assistente ───────────
@router.post("/assistente/sessoes")
def criar_sessao(dados: SessaoIn, empresa_id: int = Query(...),
                 db: Session = Depends(get_db), user=Depends(bloquear_visualizador),
                 _ac=Depends(verificar_acesso_empresa)):
    uc = AssistenteUseCase(db)
    sessao = uc.criar_sessao(empresa_id, getattr(user, "id", None), dados.titulo)
    return {"id": sessao.id, "titulo": sessao.titulo, "created_at": sessao.created_at}


@router.get("/assistente/sessoes")
def listar_sessoes(empresa_id: int = Query(...), db: Session = Depends(get_db),
                   _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = AssistenteUseCase(db)
    return [
        {"id": s.id, "titulo": s.titulo, "updated_at": s.updated_at}
        for s in uc.listar_sessoes(empresa_id)
    ]


@router.get("/assistente/sessoes/{sessao_id}/mensagens")
def listar_mensagens(sessao_id: int, empresa_id: int = Query(...),
                     db: Session = Depends(get_db), _=Depends(get_current_user),
                     _ac=Depends(verificar_acesso_empresa)):
    uc = AssistenteUseCase(db)
    return [
        {"id": m.id, "papel": m.papel, "conteudo": m.conteudo,
         "ferramentas_usadas": m.ferramentas_usadas, "created_at": m.created_at}
        for m in uc.listar_mensagens(sessao_id, empresa_id)
    ]


@router.post("/assistente/sessoes/{sessao_id}/mensagens")
def enviar_mensagem(sessao_id: int, dados: MensagemIn, empresa_id: int = Query(...),
                    db: Session = Depends(get_db), user=Depends(bloquear_visualizador),
                    _ac=Depends(verificar_acesso_empresa)):
    uc = AssistenteUseCase(db)
    resposta = uc.enviar_mensagem(sessao_id, empresa_id, dados.mensagem,
                                  getattr(user, "id", None))
    return {
        "id": resposta.id, "papel": resposta.papel, "conteudo": resposta.conteudo,
        "ferramentas_usadas": resposta.ferramentas_usadas, "created_at": resposta.created_at,
    }


# ─────────── Benchmark Setorial ───────────
@router.get("/benchmark-setorial")
def benchmark_setorial(empresa_id: int = Query(...), db: Session = Depends(get_db),
                       _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    uc = BenchmarkSetorialUseCase(db)
    return uc.comparar(empresa_id)


@router.get("/benchmark-setorial/segmentos")
def listar_segmentos(db: Session = Depends(get_db), _=Depends(get_current_user)):
    uc = BenchmarkSetorialUseCase(db)
    return uc.listar_segmentos()


# ─────────── RAG / Base de Conhecimento ───────────
@router.get("/rag/status")
def rag_status(empresa_id: int = Query(...), db: Session = Depends(get_db),
               _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    rag = RagService(db)
    return rag.estatisticas(empresa_id)


@router.get("/rag/documentos")
def rag_documentos(empresa_id: int = Query(...), db: Session = Depends(get_db),
                   _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    rag = RagService(db)
    return [
        {"id": d.id, "tipo": d.tipo_documento, "titulo": d.titulo,
         "indexado": d.indexado, "empresa_id": d.empresa_id,
         "created_at": d.created_at}
        for d in rag.listar(empresa_id)
    ]


@router.post("/rag/documentos")
def rag_indexar(dados: DocumentoIn, empresa_id: int = Query(...),
                db: Session = Depends(get_db), _=Depends(bloquear_visualizador),
                _ac=Depends(verificar_acesso_empresa)):
    rag = RagService(db)
    if dados.tipo_documento not in TIPOS_INDEXAVEIS:
        raise HTTPException(400, f"Tipo inválido. Permitidos: {sorted(TIPOS_INDEXAVEIS)}")
    doc = rag.indexar_documento(empresa_id, dados.tipo_documento, dados.titulo, dados.conteudo)
    return {"id": doc.id, "indexado": doc.indexado, "titulo": doc.titulo}


@router.post("/rag/buscar")
def rag_buscar(dados: BuscaIn, empresa_id: int = Query(...),
               db: Session = Depends(get_db), _=Depends(get_current_user),
               _ac=Depends(verificar_acesso_empresa)):
    rag = RagService(db)
    return rag.buscar(empresa_id, dados.consulta, top_k=dados.top_k)


@router.post("/rag/seed-legislacao")
def rag_seed_legislacao(db: Session = Depends(get_db), _=Depends(bloquear_visualizador)):
    """Indexa a legislação ANTT como conhecimento global."""
    rag = RagService(db)
    n = rag.indexar_legislacao_antt()
    return {"documentos_indexados": n}


# ─────────── Relatório Executivo IA ───────────
_MIME = {
    "pdf": ("application/pdf", "pdf"),
    "word": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "powerpoint": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
}


@router.get("/relatorio/{formato}")
def gerar_relatorio_executivo(formato: str, empresa_id: int = Query(...),
                              db: Session = Depends(get_db), _=Depends(get_current_user),
                              _ac=Depends(verificar_acesso_empresa)):
    """Gera o relatório executivo IA em pdf, word ou powerpoint."""
    if formato not in _MIME:
        raise HTTPException(400, "Formato inválido. Use: pdf, word ou powerpoint.")
    uc = RelatorioIAUseCase(db)
    try:
        conteudo = uc.gerar(empresa_id, formato)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Falha ao gerar relatório: {e}")
    mime, ext = _MIME[formato]
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo), media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=relatorio_executivo_{empresa_id}.{ext}"},
    )


# ─────────── Dashboard de Inteligência ───────────
@router.get("/dashboard")
def dashboard_inteligencia(empresa_id: int = Query(...), db: Session = Depends(get_db),
                           _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    from app.infrastructure.database.models import (
        InsightModel, OportunidadeModel,
    )
    from sqlalchemy import func as f

    score_uc = ScoreLogisticoUseCase(db)
    score = score_uc.ultimo(empresa_id)

    total_insights = db.query(f.count(InsightModel.id)).filter(
        InsightModel.empresa_id == empresa_id).scalar() or 0
    oportunidades_abertas = db.query(f.count(OportunidadeModel.id)).filter(
        OportunidadeModel.empresa_id == empresa_id,
        OportunidadeModel.status == "ABERTA").scalar() or 0
    economia_potencial = db.query(f.coalesce(f.sum(OportunidadeModel.economia_estimada), 0.0)).filter(
        OportunidadeModel.empresa_id == empresa_id,
        OportunidadeModel.status == "ABERTA").scalar() or 0

    return {
        "score_logistico": score.score_total if score else None,
        "classificacao": score.classificacao if score else None,
        "economia_potencial": round(economia_potencial, 2),
        "economia_capturada": 0.0,  # preenchido quando BIDs encerrarem
        "oportunidades_abertas": oportunidades_abertas,
        "insights_gerados": total_insights,
    }


# ─────────── Consumo de IA ───────────
@router.get("/uso")
def consumo_ia(empresa_id: int = Query(...), db: Session = Depends(get_db),
               _=Depends(get_current_user), _ac=Depends(verificar_acesso_empresa)):
    return custo_total_empresa(db, empresa_id)
