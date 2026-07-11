"""Router de relatórios de diagnóstico (RF015) — exportação Excel e PDF."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.use_cases.benchmark import BenchmarkUseCase
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.core.database import get_db
from app.infrastructure.reports.benchmark_report import (
    gerar_benchmark_excel,
    gerar_benchmark_pdf,
)
from app.infrastructure.reports.excel_report import gerar_relatorio_excel
from app.infrastructure.reports.pdf_report import gerar_relatorio_pdf
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


@router.get("/diagnostico/{empresa_id}/excel")
def relatorio_excel(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
):
    diag = _gerar_diag(empresa_id, data_inicio, data_fim, cte_repo, empresa_repo,
                       transp_repo, meta_nac, meta_reg)
    conteudo = gerar_relatorio_excel(diag)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=diagnostico_{empresa_id}.xlsx"
        },
    )


@router.get("/diagnostico/{empresa_id}/pdf")
def relatorio_pdf(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
):
    diag = _gerar_diag(empresa_id, data_inicio, data_fim, cte_repo, empresa_repo,
                       transp_repo, meta_nac, meta_reg)
    conteudo = gerar_relatorio_pdf(diag)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=diagnostico_{empresa_id}.pdf"
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


# ════════ Relatórios do Módulo BID (V3.1) ════════
from app.infrastructure.reports.bid_report import (
    gerar_bid_excel, gerar_bid_pdf, gerar_pacote_cotacao_pdf,
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
    if formato not in ("pdf", "excel"):
        raise HTTPException(400, "Formato inválido. Use 'pdf' ou 'excel'.")

    if formato == "pdf":
        conteudo = gerar_bid_pdf(tipo, empresa_nome, bid, dados)
        return StreamingResponse(
            BytesIO(conteudo), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_{tipo}.pdf"},
        )
    else:
        conteudo = gerar_bid_excel(tipo, empresa_nome, bid, dados)
        return StreamingResponse(
            BytesIO(conteudo),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_{tipo}.xlsx"},
        )
