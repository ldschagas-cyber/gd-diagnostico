"""Geração de relatório de diagnóstico em Excel (RF015) — OpenPyXL.

Paleta GD Conecta: Indigo #2D3561, Amber #C9A84C, Blue #0077A8, Ivory #F5F1EB.
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from app.application.dtos import Diagnostico

INDIGO = "2D3561"
AMBER = "C9A84C"
BLUE = "0077A8"
IVORY = "F5F1EB"

_header_fill = PatternFill("solid", fgColor=INDIGO)
_header_font = Font(color="FFFFFF", bold=True, size=11, name="Arial")
_title_font = Font(color=INDIGO, bold=True, size=16, name="Arial")
_sub_font = Font(color=BLUE, bold=True, size=12, name="Arial")
_thin = Side(style="thin", color="DDDDDD")
_border = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


def _style_header(ws, row: int, ncols: int):
    for col in range(1, ncols + 1):
        c = ws.cell(row=row, column=col)
        c.fill = _header_fill
        c.font = _header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = _border


def _autofit(ws):
    for col in ws.columns:
        length = max((len(str(c.value)) if c.value is not None else 0) for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(length + 4, 45)


def gerar_relatorio_excel(diag: Diagnostico) -> bytes:
    wb = Workbook()

    # ---------- Aba Resumo ----------
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = "GD Frete Diagnóstico"
    ws["A1"].font = _title_font
    ws["A2"] = f"Empresa: {diag.empresa_nome}"
    ws["A2"].font = _sub_font
    periodo = "Todo o período"
    if diag.periodo_inicio or diag.periodo_fim:
        periodo = f"{diag.periodo_inicio or '...'} a {diag.periodo_fim or '...'}"
    ws["A3"] = f"Período: {periodo}"

    n = diag.nacional
    ws["A5"] = "Indicadores Nacionais (RF011)"
    ws["A5"].font = _sub_font
    linhas = [
        ("Indicador", "Valor", "Meta", "Desvio"),
        ("Valor Total Frete (R$)", round(n.valor_total_frete, 2), "", ""),
        ("Valor Total Mercadoria (R$)", round(n.valor_total_mercadoria, 2), "", ""),
        ("Peso Total (kg)", round(n.peso_total, 2), "", ""),
        ("Frete R$/kg", round(n.frete_rs_kg, 4),
         round(n.meta_rs_kg, 4) if n.meta_rs_kg is not None else "",
         round(n.desvio_rs_kg, 4) if n.desvio_rs_kg is not None else ""),
        ("Frete % s/ Mercadoria", round(n.frete_pct, 2),
         round(n.meta_pct, 2) if n.meta_pct is not None else "",
         round(n.desvio_pct, 2) if n.desvio_pct is not None else ""),
        ("Quantidade de CT-es", n.qtd_ctes, "", ""),
    ]
    start = 6
    for i, row in enumerate(linhas):
        for j, val in enumerate(row):
            ws.cell(row=start + i, column=1 + j, value=val).border = _border
    _style_header(ws, start, 4)
    _autofit(ws)

    # ---------- Aba Regiões ----------
    wr = wb.create_sheet("Regiões")
    wr["A1"] = "Indicadores por Macro Região (RF012)"
    wr["A1"].font = _sub_font
    cab = ["Macro Região", "Frete Total", "Mercadoria Total", "Peso (kg)",
           "R$/kg", "Frete %", "Meta R$/kg", "Meta %", "CT-es"]
    wr.append([])
    wr.append(cab)
    for r in diag.regionais:
        wr.append([
            r.macro_regiao, round(r.frete_total, 2), round(r.mercadoria_total, 2),
            round(r.peso_total, 2), round(r.frete_rs_kg, 4), round(r.frete_pct, 2),
            r.meta_rs_kg if r.meta_rs_kg is not None else "",
            r.meta_pct if r.meta_pct is not None else "", r.qtd_ctes,
        ])
    _style_header(wr, 3, len(cab))
    for row in wr.iter_rows(min_row=4, max_row=wr.max_row, max_col=len(cab)):
        for c in row:
            c.border = _border
    _autofit(wr)

    # ---------- Aba Transportadoras ----------
    wt = wb.create_sheet("Transportadoras")
    wt["A1"] = "Ranking de Transportadoras (RF013)"
    wt["A1"].font = _sub_font
    cab = ["Transportadora", "Frete Total", "Participação %", "R$/kg",
           "Qtd CT-es", "Peso Transportado (kg)"]
    wt.append([])
    wt.append(cab)
    for t in diag.transportadoras:
        wt.append([
            t.nome, round(t.frete_total, 2), round(t.participacao_pct, 2),
            round(t.frete_rs_kg, 4), t.qtd_ctes, round(t.peso_transportado, 2),
        ])
    _style_header(wt, 3, len(cab))
    for row in wt.iter_rows(min_row=4, max_row=wt.max_row, max_col=len(cab)):
        for c in row:
            c.border = _border
    _autofit(wt)

    # ---------- Aba Prazos ----------
    wp = wb.create_sheet("Prazos")
    wp["A1"] = "Indicadores de Prazo (RF014)"
    wp["A1"].font = _sub_font
    cab = ["Macro Região", "Prazo Médio (dias)", "No Prazo", "Em Atraso",
           "SLA %", "Meta (dias)"]
    wp.append([])
    wp.append(cab)
    for p in diag.prazos:
        wp.append([
            p.macro_regiao, p.prazo_medio, p.entregas_no_prazo, p.entregas_atraso,
            round(p.sla_pct, 1), p.prazo_meta if p.prazo_meta is not None else "",
        ])
    _style_header(wp, 3, len(cab))
    for row in wp.iter_rows(min_row=4, max_row=wp.max_row, max_col=len(cab)):
        for c in row:
            c.border = _border
    _autofit(wp)

    # ---------- Aba Oportunidades ----------
    wo = wb.create_sheet("Oportunidades")
    wo["A1"] = "Oportunidades de Melhoria (RF015)"
    wo["A1"].font = _sub_font
    for i, op in enumerate(diag.oportunidades, start=3):
        wo.cell(row=i, column=1, value=f"• {op}")
    wo.column_dimensions["A"].width = 100

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
