"""Gerador de relatórios do módulo BID — PDF e Excel.

Tipos disponíveis:
  - executivo: visão geral do BID
  - comparativo: proposta vs. atual por grupo
  - ranking: score de transportadoras
  - economia: projeções de saving
  - resultado: BID encerrado com vencedoras

Pacote de Cotação (formato especial): sem valores pagos atualmente.
"""
from io import BytesIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.infrastructure.reports.excel_report import _autofit, _style_header, _title_font
from app.infrastructure.reports.pdf_report import _br, _estilos, _tabela


def _rotulo(tipo: str) -> str:
    return {
        "REGIAO": "Região", "UF": "UF", "FILIAL": "Filial",
        "TRANSPORTADORA": "Transportadora", "FAIXA_PESO": "Faixa de Peso",
    }.get(tipo, tipo)


# ═══════════════════════════════════════════ PDF ════════════════════════════

def gerar_bid_pdf(tipo: str, empresa_nome: str, bid, dados: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        title=f"BID {bid.nome} — {tipo.title()}",
    )
    s = _estilos()
    el = []

    el.append(Paragraph(f"BID de Frete — {tipo.replace('_', ' ').title()}", s["GDTitulo"]))
    el.append(Paragraph(f"{empresa_nome}  ·  {bid.nome}", s["GDInfo"]))
    el.append(Paragraph(f"Status: {bid.status.value}  ·  Período: {bid.periodo_analise_inicio} → {bid.periodo_analise_fim}", s["GDInfo"]))
    el.append(Spacer(1, 8))

    if tipo == "executivo":
        el += _secao_executivo(bid, dados, s)
    elif tipo == "comparativo":
        el += _secao_comparativo(dados, s)
    elif tipo == "ranking":
        el += _secao_ranking(dados, s)
    elif tipo == "economia":
        el += _secao_economia(dados, s)
    elif tipo == "resultado":
        el += _secao_resultado(dados, s)

    el.append(Spacer(1, 12))
    el.append(Paragraph("GD Conecta — Governança de Frete · Torre de Controle Logístico", s["GDInfo"]))
    doc.build(el)
    return buf.getvalue()


def _secao_executivo(bid, dados, s):
    el = []
    el.append(Paragraph("1. Escopo do BID", s["GDSub"]))
    escopos = dados.get("escopos", [])
    linhas = [["Agrupamento", "Grupo", "Embarques", "Peso (kg)", "Frete (R$)", "R$/kg"]]
    for e in escopos:
        linhas.append([
            _rotulo(e.tipo_agrupamento.value), e.valor_grupo,
            str(e.qtd_embarques), _br(e.peso_total, 0),
            _br(e.valor_frete_total), _br(e.frete_rs_kg, 4),
        ])
    el.append(_tabela(linhas))
    el.append(Spacer(1, 8))
    el.append(Paragraph("2. Transportadoras Convidadas", s["GDSub"]))
    bts = dados.get("bid_transportadoras", [])
    transp_nomes = dados.get("transp_nomes", {})
    linhas = [["Transportadora", "Status"]]
    for bt in bts:
        linhas.append([transp_nomes.get(bt.transportadora_id, str(bt.transportadora_id)), bt.status.value])
    el.append(_tabela(linhas))
    return el


def _secao_comparativo(dados, s):
    el = []
    el.append(Paragraph("Comparativo de Propostas", s["GDSub"]))
    comparativo = dados.get("comparativo", [])
    linhas = [["Grupo", "Atual R$/kg", "Transportadora", "Proposta R$/kg", "Economia R$", "Economia %"]]
    for linha in comparativo:
        for p in linha.propostas:
            linhas.append([
                linha.valor_grupo, _br(linha.frete_atual_rs_kg, 4),
                p["transportadora"], _br(p["rs_kg"], 4),
                _br(p["economia_rs"]), f"{_br(p['economia_pct'], 1)}%",
            ])
    el.append(_tabela(linhas))
    return el


def _secao_ranking(dados, s):
    el = []
    el.append(Paragraph("Ranking de Transportadoras", s["GDSub"]))
    scores = dados.get("scores", [])
    linhas = [["#", "Transportadora", "Score", "Classificação", "R$/kg médio", "Prazo médio"]]
    for i, sc in enumerate(scores, 1):
        linhas.append([
            str(i), sc.nome, str(sc.score), sc.classificacao,
            _br(sc.proposta_media_rs_kg, 4), f"{_br(sc.prazo_medio, 0)} dias",
        ])
    el.append(_tabela(linhas))
    return el


def _secao_economia(dados, s):
    el = []
    eco = dados.get("economia")
    if eco:
        el.append(Paragraph("Potencial de Economia", s["GDSub"]))
        el.append(_tabela([
            ["Métrica", "Valor"],
            ["Frete atual total", f"R$ {_br(eco.frete_atual_total)}"],
            ["Economia no período", f"R$ {_br(eco.economia_total_periodo)}"],
            ["% de redução", f"{_br(eco.economia_pct, 1)}%"],
            ["Ritmo mensal", f"R$ {_br(eco.ritmo_mensal)}"],
            ["Projeção trimestral", f"R$ {_br(eco.proj_trimestral)}"],
            ["Projeção semestral", f"R$ {_br(eco.proj_semestral)}"],
            ["Projeção anual", f"R$ {_br(eco.proj_anual)}"],
        ], col_widths=[10 * cm, 7 * cm]))
        el.append(Spacer(1, 6))
        el.append(Paragraph("Por grupo", s["GDSub"]))
        linhas = [["Grupo", "R$/kg atual", "Melhor proposta", "Economia R$"]]
        for g in eco.por_grupo:
            linhas.append([
                g["valor_grupo"], _br(g["frete_atual_rs_kg"], 4),
                _br(g["melhor_proposta_rs_kg"], 4), _br(g["economia"]),
            ])
        el.append(_tabela(linhas))
    return el


def _secao_resultado(dados, s):
    el = _secao_comparativo(dados, s)
    el += _secao_ranking(dados, s)
    el += _secao_economia(dados, s)
    return el


# ══════════════════════════════════════════ Excel ═══════════════════════════

def gerar_bid_excel(tipo: str, empresa_nome: str, bid, dados: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = tipo.title()

    ws.cell(row=1, column=1, value=f"BID: {bid.nome} — {empresa_nome}").font = _title_font
    ws.cell(row=2, column=1, value=f"Status: {bid.status.value} | Período: {bid.periodo_analise_inicio} → {bid.periodo_analise_fim}")
    ws.append([])

    if tipo == "executivo":
        _aba_executivo(ws, dados)
    elif tipo == "comparativo":
        _aba_comparativo(ws, dados)
    elif tipo == "ranking":
        _aba_ranking(ws, dados)
    elif tipo == "economia":
        _aba_economia(ws, dados, wb)
    elif tipo == "resultado":
        _aba_comparativo(ws, dados)
        ws2 = wb.create_sheet("Score")
        _aba_ranking(ws2, dados)
        ws3 = wb.create_sheet("Economia")
        _aba_economia(ws3, dados, wb)

    _autofit(ws)
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def _aba_executivo(ws, dados):
    ws.append(["Agrupamento", "Grupo", "Embarques", "Peso (kg)", "Frete (R$)", "R$/kg"])
    _style_header(ws, ws.max_row, 6)
    for e in dados.get("escopos", []):
        ws.append([_rotulo(e.tipo_agrupamento.value), e.valor_grupo, e.qtd_embarques,
                   round(e.peso_total, 0), round(e.valor_frete_total, 2), round(e.frete_rs_kg, 4)])
    ws.append([])
    ws.append(["Transportadora", "Status"])
    _style_header(ws, ws.max_row, 2)
    transp_nomes = dados.get("transp_nomes", {})
    for bt in dados.get("bid_transportadoras", []):
        ws.append([transp_nomes.get(bt.transportadora_id, str(bt.transportadora_id)), bt.status.value])


def _aba_comparativo(ws, dados):
    ws.append(["Grupo", "Atual R$/kg", "Transportadora", "Proposta R$/kg", "Economia R$", "Economia %"])
    _style_header(ws, ws.max_row, 6)
    for linha in dados.get("comparativo", []):
        for p in linha.propostas:
            ws.append([linha.valor_grupo, round(linha.frete_atual_rs_kg, 4),
                       p["transportadora"], round(p["rs_kg"], 4),
                       round(p["economia_rs"], 2), round(p["economia_pct"], 1)])


def _aba_ranking(ws, dados):
    ws.append(["#", "Transportadora", "Score", "Classificação", "R$/kg médio", "Prazo médio", "Cobertura %"])
    _style_header(ws, ws.max_row, 7)
    for i, sc in enumerate(dados.get("scores", []), 1):
        ws.append([i, sc.nome, sc.score, sc.classificacao,
                   round(sc.proposta_media_rs_kg, 4), round(sc.prazo_medio, 0), round(sc.cobertura_media, 1)])


def _aba_economia(ws, dados, wb=None):
    eco = dados.get("economia")
    if not eco:
        return
    ws.append(["Métrica", "Valor (R$)"])
    _style_header(ws, ws.max_row, 2)
    ws.append(["Frete atual total", round(eco.frete_atual_total, 2)])
    ws.append(["Economia no período", round(eco.economia_total_periodo, 2)])
    ws.append(["% redução", round(eco.economia_pct, 1)])
    ws.append(["Ritmo mensal", round(eco.ritmo_mensal, 2)])
    ws.append(["Projeção trimestral", round(eco.proj_trimestral, 2)])
    ws.append(["Projeção semestral", round(eco.proj_semestral, 2)])
    ws.append(["Projeção anual", round(eco.proj_anual, 2)])
    ws.append([])
    ws.append(["Grupo", "R$/kg atual", "Melhor proposta", "Economia R$"])
    _style_header(ws, ws.max_row, 4)
    for g in eco.por_grupo:
        ws.append([g["valor_grupo"], round(g["frete_atual_rs_kg"], 4),
                   round(g["melhor_proposta_rs_kg"], 4), round(g["economia"], 2)])


# ══════════════════════════════════════ Pacote de Cotação ════════════════════

def gerar_pacote_cotacao_pdf(empresa_nome: str, bid, escopos: list) -> bytes:
    """Documento enviado às transportadoras. SEM valores de frete atuais."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm,
                             leftMargin=1.5*cm, rightMargin=1.5*cm)
    s = _estilos()
    el = []
    el.append(Paragraph("Pacote de Cotação — BID de Frete", s["GDTitulo"]))
    el.append(Paragraph(f"{empresa_nome}  ·  {bid.nome}", s["GDInfo"]))
    if bid.data_encerramento:
        el.append(Paragraph(f"Prazo para propostas: {bid.data_encerramento}", s["GDInfo"]))
    el.append(Spacer(1, 8))
    if bid.objetivo:
        el.append(Paragraph("Objetivo", s["GDSub"]))
        el.append(Paragraph(bid.objetivo, s["GDInfo"]))
        el.append(Spacer(1, 6))
    el.append(Paragraph("Perfil Operacional (volume histórico)", s["GDSub"]))
    linhas = [["Grupo", "Tipo", "Embarques", "Peso total (kg)"]]
    for e in escopos:
        linhas.append([e.valor_grupo, _rotulo(e.tipo_agrupamento.value),
                       str(e.qtd_embarques), _br(e.peso_total, 0)])
    el.append(_tabela(linhas))
    el.append(Spacer(1, 10))
    el.append(Paragraph(
        "Por favor, envie sua proposta preenchendo: R$/kg, frete mínimo, prazo e cobertura por grupo.",
        s["GDInfo"],
    ))
    doc.build(el)
    return buf.getvalue()
