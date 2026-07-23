"""Helpers de estilo PDF compartilhados (ReportLab) — usados pelo relatório de
Benchmark (o relatório de Diagnóstico Logístico em PDF foi substituído pelo
HTML, ver app/infrastructure/reports/html_report.py).

Paleta GD Conecta: Indigo #2D3561, Amber #C9A84C, Blue #0077A8, Ivory #F5F1EB.
"""
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Table, TableStyle

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
