"""Geração de relatório de diagnóstico em PDF (RF015) — ReportLab.

Paleta GD Conecta: Indigo #2D3561, Amber #C9A84C, Blue #0077A8, Ivory #F5F1EB.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.application.dtos import Diagnostico

INDIGO = colors.HexColor("#2D3561")
AMBER = colors.HexColor("#C9A84C")
BLUE = colors.HexColor("#0077A8")
IVORY = colors.HexColor("#F5F1EB")


def _br(valor: float, casas: int = 2) -> str:
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _estilos():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("GDTitulo", parent=base["Title"], textColor=INDIGO,
                            fontSize=20, spaceAfter=4))
    base.add(ParagraphStyle("GDSub", parent=base["Normal"], textColor=BLUE,
                            fontSize=13, spaceBefore=14, spaceAfter=6, leading=16,
                            fontName="Helvetica-Bold"))
    base.add(ParagraphStyle("GDInfo", parent=base["Normal"], fontSize=10,
                            textColor=colors.HexColor("#555555")))
    base.add(ParagraphStyle("GDOp", parent=base["Normal"], fontSize=10,
                            leftIndent=8, spaceAfter=4, leading=14))
    return base


def _tabela(dados, col_widths=None):
    t = Table(dados, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, IVORY]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def gerar_relatorio_pdf(diag: Diagnostico) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title=f"Diagnóstico - {diag.empresa_nome}",
    )
    s = _estilos()
    el = []

    el.append(Paragraph("GD Frete Diagnóstico", s["GDTitulo"]))
    el.append(Paragraph("Relatório de Diagnóstico Logístico", s["GDInfo"]))
    el.append(Spacer(1, 8))
    el.append(Paragraph(f"<b>Empresa:</b> {diag.empresa_nome}", s["GDInfo"]))
    periodo = "Todo o período"
    if diag.periodo_inicio or diag.periodo_fim:
        periodo = f"{diag.periodo_inicio or '...'} a {diag.periodo_fim or '...'}"
    el.append(Paragraph(f"<b>Período:</b> {periodo}", s["GDInfo"]))

    # Nacional
    n = diag.nacional
    el.append(Paragraph("Indicadores Nacionais (RF011)", s["GDSub"]))
    dados = [
        ["Indicador", "Valor", "Meta", "Desvio"],
        ["Total Frete (R$)", _br(n.valor_total_frete), "-", "-"],
        ["Total Mercadoria (R$)", _br(n.valor_total_mercadoria), "-", "-"],
        ["Peso Total (kg)", _br(n.peso_total), "-", "-"],
        ["Frete R$/kg", _br(n.frete_rs_kg, 4),
         _br(n.meta_rs_kg, 4) if n.meta_rs_kg is not None else "-",
         _br(n.desvio_rs_kg, 4) if n.desvio_rs_kg is not None else "-"],
        ["Frete % s/ Mercadoria", _br(n.frete_pct) + "%",
         (_br(n.meta_pct) + "%") if n.meta_pct is not None else "-",
         (_br(n.desvio_pct) + " p.p.") if n.desvio_pct is not None else "-"],
        ["Quantidade de CT-es", str(n.qtd_ctes), "-", "-"],
    ]
    el.append(_tabela(dados, [7 * cm, 3.5 * cm, 3 * cm, 3 * cm]))

    # Regionais
    el.append(Paragraph("Indicadores por Macro Região (RF012)", s["GDSub"]))
    dados = [["Região", "Frete", "Merc.", "Peso", "R$/kg", "Frete%", "CT-es"]]
    for r in diag.regionais:
        dados.append([
            r.macro_regiao, _br(r.frete_total), _br(r.mercadoria_total),
            _br(r.peso_total), _br(r.frete_rs_kg, 3), _br(r.frete_pct) + "%",
            str(r.qtd_ctes),
        ])
    if len(dados) == 1:
        dados.append(["Sem dados", "-", "-", "-", "-", "-", "-"])
    el.append(_tabela(dados))

    # Transportadoras
    el.append(Paragraph("Ranking de Transportadoras (RF013)", s["GDSub"]))
    dados = [["Transportadora", "Frete Total", "Part.%", "R$/kg", "CT-es", "Peso"]]
    for t in diag.transportadoras[:15]:
        dados.append([
            t.nome[:32], _br(t.frete_total), _br(t.participacao_pct) + "%",
            _br(t.frete_rs_kg, 3), str(t.qtd_ctes), _br(t.peso_transportado),
        ])
    if len(dados) == 1:
        dados.append(["Sem dados", "-", "-", "-", "-", "-"])
    el.append(_tabela(dados))

    # Prazos
    el.append(Paragraph("Indicadores de Prazo (RF014)", s["GDSub"]))
    dados = [["Região", "Prazo Médio", "No Prazo", "Atraso", "SLA%", "Meta"]]
    for p in diag.prazos:
        dados.append([
            p.macro_regiao, f"{p.prazo_medio} d", str(p.entregas_no_prazo),
            str(p.entregas_atraso), _br(p.sla_pct, 1) + "%",
            f"{p.prazo_meta} d" if p.prazo_meta is not None else "-",
        ])
    if len(dados) == 1:
        dados.append(["Sem dados de prazo", "-", "-", "-", "-", "-"])
    el.append(_tabela(dados))

    # Oportunidades
    el.append(Paragraph("Oportunidades de Melhoria (RF015)", s["GDSub"]))
    for op in diag.oportunidades:
        el.append(Paragraph(f"• {op}", s["GDOp"]))

    doc.build(el)
    return buffer.getvalue()
