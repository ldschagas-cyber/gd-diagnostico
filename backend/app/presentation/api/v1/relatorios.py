"""Router de relatórios (RF015).

Diagnóstico Logístico: HTML e Excel (sem PDF). Benchmark, Fechamento de
Custo de Frete e BID Executivo: HTML, PDF e Excel. Todos reaproveitam
sempre os mesmos dados das telas de origem, nunca recalculados em paralelo
aqui. Os demais subtipos do BID (comparativo, ranking, economia,
resultado), voltados ao trabalho interno, continuam em PDF e Excel.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.use_cases.benchmark import BenchmarkUseCase
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.application.use_cases.dlg import DlgUseCase
from app.application.use_cases.fechamento_mensal import FechamentoMensalUseCase
from app.core.database import get_db
from app.infrastructure.database.repositories import RecomendacaoRepository
from app.infrastructure.reports.benchmark_report import (
    gerar_benchmark_excel,
    gerar_benchmark_html,
    gerar_benchmark_pdf,
)
from app.infrastructure.reports.fechamento_report import (
    gerar_fechamento_excel,
    gerar_fechamento_html,
    gerar_fechamento_pdf,
)
from app.infrastructure.reports.html_report import gerar_relatorio_excel, gerar_relatorio_html
from app.presentation.api.dependencies import (
    get_benchmark_repo,
    get_cte_repo,
    get_current_user,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
    get_transportadora_repo,
)

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


def _gerar_diag(empresa_id, data_inicio, data_fim, cte_repo, empresa_repo,
                transp_repo, meta_nac, meta_reg):
    uc = DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)
    try:
        return uc.gerar(empresa_id, data_inicio, data_fim)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


def _gerar_dados_dlg_extra(empresa_id, data_inicio, data_fim, db: Session):
    """Indicadores por dimensão (DLG consolidado), outliers e recomendações
    já persistidas — reaproveitados como estão pelas telas Análise de
    Eficiência e Recomendações, nunca recalculados em paralelo aqui."""
    dlg_uc = DlgUseCase(db)
    dlg_por_dimensao = {
        dim: dlg_uc.listar(
            empresa_id, dimensao=dim, modo="consolidado",
            data_inicio=data_inicio, data_fim=data_fim,
        )
        for dim in ("CLIENTE_FINAL", "ROTA", "TRANSPORTADORA", "FILIAL")
    }
    outliers = dlg_uc.listar_outliers(
        empresa_id, data_inicio=data_inicio, data_fim=data_fim
    )
    recomendacoes = RecomendacaoRepository(db).listar(empresa_id)
    return dlg_por_dimensao, outliers, recomendacoes


@router.get("/diagnostico/{empresa_id}/html")
def relatorio_html(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    diag = _gerar_diag(empresa_id, data_inicio, data_fim, cte_repo, empresa_repo,
                       transp_repo, meta_nac, meta_reg)
    dlg_por_dimensao, outliers, recomendacoes = _gerar_dados_dlg_extra(
        empresa_id, data_inicio, data_fim, db
    )

    conteudo = gerar_relatorio_html(
        diag, dlg_por_dimensao, outliers, recomendacoes,
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=diagnostico_{empresa_id}.html"
        },
    )


@router.get("/diagnostico/{empresa_id}/excel")
def relatorio_diagnostico_excel(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    db: Session = Depends(get_db),
):
    diag = _gerar_diag(empresa_id, data_inicio, data_fim, cte_repo, empresa_repo,
                       transp_repo, meta_nac, meta_reg)
    dlg_por_dimensao, outliers, recomendacoes = _gerar_dados_dlg_extra(
        empresa_id, data_inicio, data_fim, db
    )

    conteudo = gerar_relatorio_excel(diag, dlg_por_dimensao, outliers, recomendacoes)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=diagnostico_{empresa_id}.xlsx"
        },
    )


# ==================== Relatórios de Benchmark (seção 14) ====================
def _benchmark_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db):
    diag = DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)
    return BenchmarkUseCase(diag, cte_repo, bench_repo, db=db)


def _dados_benchmark(uc, empresa_repo, empresa_id, data_inicio, data_fim):
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada.")
    nome = empresa.nome_fantasia or empresa.razao_social
    nacional = uc.nacional(empresa_id, data_inicio, data_fim, None)
    nacional.empresa_nome = nome
    regional = uc.regional(empresa_id, data_inicio, data_fim, None)
    transportadoras = uc.transportadoras(empresa_id, data_inicio, data_fim)
    economia = uc.potencial_economia(empresa_id, data_inicio, data_fim)
    return nome, nacional, regional, transportadoras, economia


@router.get("/benchmark/{empresa_id}/html")
def relatorio_benchmark_html(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    bench_repo=Depends(get_benchmark_repo),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    uc = _benchmark_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db)
    nome, nacional, regional, transps, economia = _dados_benchmark(
        uc, empresa_repo, empresa_id, data_inicio, data_fim
    )
    conteudo = gerar_benchmark_html(
        nome, nacional, regional, transps, economia,
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=benchmark_{empresa_id}.html"},
    )


@router.get("/benchmark/{empresa_id}/pdf")
def relatorio_benchmark_pdf(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    bench_repo=Depends(get_benchmark_repo),
    db: Session = Depends(get_db),
):
    uc = _benchmark_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db)
    nome, nacional, regional, transps, economia = _dados_benchmark(
        uc, empresa_repo, empresa_id, data_inicio, data_fim
    )
    conteudo = gerar_benchmark_pdf(nome, nacional, regional, transps, economia)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=benchmark_{empresa_id}.pdf"},
    )


@router.get("/benchmark/{empresa_id}/excel")
def relatorio_benchmark_excel(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    bench_repo=Depends(get_benchmark_repo),
    db: Session = Depends(get_db),
):
    uc = _benchmark_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db)
    nome, nacional, regional, transps, economia = _dados_benchmark(
        uc, empresa_repo, empresa_id, data_inicio, data_fim
    )
    conteudo = gerar_benchmark_excel(nome, nacional, regional, transps, economia)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=benchmark_{empresa_id}.xlsx"},
    )


# ==================== Relatório do Fechamento de Custo de Frete ====================
@router.get("/fechamento/{empresa_id}/{formato}")
def relatorio_fechamento(
    empresa_id: int,
    formato: str,
    competencia: Optional[str] = Query(None),
    _=Depends(verificar_acesso_empresa),
    empresa_repo=Depends(get_empresa_repo),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    if formato not in ("html", "pdf", "excel"):
        raise HTTPException(400, "Formato inválido. Use: html, pdf, excel.")

    hoje = date.today()
    competencia = competencia or f"{hoje.year}-{hoje.month:02d}"

    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada.")
    nome = empresa.nome_fantasia or empresa.razao_social

    uc = FechamentoMensalUseCase(db)
    atual = uc.obter(empresa_id, competencia)
    historico = uc.historico(empresa_id, 13)

    from io import BytesIO

    if formato == "html":
        conteudo = gerar_fechamento_html(
            nome, atual, historico, gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        return StreamingResponse(
            BytesIO(conteudo), media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=fechamento_{empresa_id}_{competencia}.html"},
        )
    if formato == "pdf":
        conteudo = gerar_fechamento_pdf(nome, atual, historico)
        return StreamingResponse(
            BytesIO(conteudo), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=fechamento_{empresa_id}_{competencia}.pdf"},
        )
    conteudo = gerar_fechamento_excel(nome, atual, historico)
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=fechamento_{empresa_id}_{competencia}.xlsx"},
    )


# ════════ Relatórios do Módulo BID (V3.1) ════════
from app.infrastructure.reports.bid_report import (
    gerar_bid_excel, gerar_bid_executivo_excel, gerar_bid_executivo_html,
    gerar_bid_pdf, gerar_pacote_cotacao_pdf,
)
from app.presentation.api.dependencies import (
    get_bid_repo, get_bid_escopo_repo, get_bid_proposta_repo,
    get_bid_simulacao_repo, get_bid_transportadora_repo,
)
from app.application.use_cases.bid_economia import EconomiaUseCase


@router.get("/bid/{bid_id}/{tipo}/{formato}")
def relatorio_bid(
    bid_id: int,
    tipo: str,
    formato: str,
    empresa_id: int = Query(...),
    _=Depends(verificar_acesso_empresa),
    bid_repo=Depends(get_bid_repo),
    escopo_repo=Depends(get_bid_escopo_repo),
    proposta_repo=Depends(get_bid_proposta_repo),
    bt_repo=Depends(get_bid_transportadora_repo),
    sim_repo=Depends(get_bid_simulacao_repo),
    transp_repo=Depends(get_transportadora_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    from io import BytesIO

    bid = bid_repo.get(bid_id)
    if not bid:
        raise HTTPException(404, "BID não encontrado.")
    empresa = empresa_repo.get(empresa_id)
    empresa_nome = empresa.nome_fantasia or empresa.razao_social if empresa else ""
    ts = transp_repo.list_by_empresa(empresa_id, limit=1000)
    nomes = {t.id: (t.nome_fantasia or t.razao_social) for t in ts}

    uc = EconomiaUseCase(escopo_repo, proposta_repo, bt_repo, sim_repo, nomes)
    dados = {
        "escopos": escopo_repo.list_by_bid(bid_id),
        "bid_transportadoras": bt_repo.list_by_bid(bid_id),
        "transp_nomes": nomes,
        "comparativo": uc.comparativo(bid_id),
        "scores": uc.scores(bid_id),
        "economia": uc.economia(bid_id, bid.periodo_analise_inicio, bid.periodo_analise_fim),
    }

    if tipo == "pacote_cotacao":
        conteudo = gerar_pacote_cotacao_pdf(empresa_nome, bid, dados["escopos"])
        return StreamingResponse(
            BytesIO(conteudo), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=pacote_cotacao_{bid_id}.pdf"},
        )

    if tipo not in ("executivo", "comparativo", "ranking", "economia", "resultado"):
        raise HTTPException(400, f"Tipo inválido: {tipo}. Use: executivo, comparativo, ranking, economia, resultado, pacote_cotacao")

    formatos_validos = ("pdf", "html", "excel") if tipo == "executivo" else ("pdf", "excel")
    if formato not in formatos_validos:
        raise HTTPException(400, f"Formato inválido para tipo '{tipo}'. Use: {', '.join(formatos_validos)}.")

    if formato == "html":
        from datetime import datetime
        conteudo = gerar_bid_executivo_html(
            empresa_nome, bid, dados, gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        return StreamingResponse(
            BytesIO(conteudo), media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_executivo.html"},
        )

    if formato == "pdf":
        conteudo = gerar_bid_pdf(tipo, empresa_nome, bid, dados)
        return StreamingResponse(
            BytesIO(conteudo), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_{tipo}.pdf"},
        )
    else:
        conteudo = (
            gerar_bid_executivo_excel(empresa_nome, bid, dados)
            if tipo == "executivo"
            else gerar_bid_excel(tipo, empresa_nome, bid, dados)
        )
        return StreamingResponse(
            BytesIO(conteudo),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_{tipo}.xlsx"},
        )
