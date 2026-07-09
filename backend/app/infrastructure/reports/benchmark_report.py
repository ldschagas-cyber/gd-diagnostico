"""Relatórios consolidados do Módulo Benchmark Logístico (seção 14).

Gera, em PDF e Excel, um relatório único cobrindo Benchmark Nacional,
Regional, Transportadoras e Potencial de Economia — reaproveitando os
estilos e a paleta GD Conecta já definidos nos relatórios de diagnóstico.
"""
from io import BytesIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.application.dtos import (
    BenchmarkNacional,
    PotencialEconomia,
)
from app.infrastructure.reports.excel_report import (
    _autofit,
    _style_header,
    _sub_font,
    _title_font,
)
from app.infrastructure.reports.pdf_report import _br, _estilos, _tabela


def _rotulo_macro(m: str) -> str:
    return {
        "NORTE": "Norte", "NORDESTE": "Nordeste", "CENTRO_OESTE": "Centro-Oeste",
        "SUDESTE": "Sudeste", "SUL": "Sul",
    }.get(m, m)


# ============================ PDF ============================
def gerar_benchmark_pdf(
    empresa_nome: str,
    nacional: BenchmarkNacional,
    regional: list,
    transportadoras: list,
    economia: PotencialEconomia,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        title=f"Benchmark Logístico — {empresa_nome}",
    )
    s = _estilos()
    el = []
    el.append(Paragraph("Relatório de Benchmark Logístico", s["GDTitulo"]))
    el.append(Paragraph(f"{empresa_nome} — comparativo com o mercado", s["GDInfo"]))
    el.append(Spacer(1, 6))

    # --- Benchmark Nacional ---
    el.append(Paragraph("1. Benchmark Nacional", s["GDSub"]))
    el.append(_tabela([
        ["Indicador", "Empresa", "Bench. médio", "Desvio", "Classificação"],
        ["Custo por kg", _br(nacional.frete_kg.valor, 4), _br(nacional.frete_kg.benchmark_medio, 4),
         f"{_br(nacional.frete_kg.desvio_pct, 1)}%", nacional.frete_kg.classificacao],
        ["% Frete s/ mercadoria", f"{_br(nacional.frete_pct.valor, 2)}%",
         f"{_br(nacional.frete_pct.benchmark_medio, 2)}%",
         f"{_br(nacional.frete_pct.desvio_pct, 1)}%", nacional.frete_pct.classificacao],
    ]))

    # --- Benchmark Regional ---
    el.append(Paragraph("2. Benchmark Regional", s["GDSub"]))
    linhas = [["Região", "R$/kg", "Bench.", "Desvio", "Classif.", "% Frete"]]
    for r in regional:
        linhas.append([
            _rotulo_macro(r.macro_regiao), _br(r.frete_kg.valor, 4),
            _br(r.frete_kg.benchmark_medio, 4), f"{_br(r.frete_kg.desvio_pct, 1)}%",
            r.frete_kg.classificacao, f"{_br(r.frete_pct.valor, 2)}%",
        ])
    el.append(_tabela(linhas))

    # --- Transportadoras ---
    el.append(Paragraph("3. Benchmark por Transportadora", s["GDSub"]))
    linhas = [["Transportadora", "Frete total", "R$/kg", "Desvio", "Nível", "Classif."]]
    for t in transportadoras[:20]:
        linhas.append([
            t.nome[:28], _br(t.frete_total), _br(t.frete_kg.valor, 4),
            f"{_br(t.frete_kg.desvio_pct, 1)}%", t.nivel_custo, t.frete_kg.classificacao,
        ])
    el.append(_tabela(linhas))

    # --- Potencial de Economia ---
    el.append(Paragraph("4. Potencial de Economia", s["GDSub"]))
    el.append(_tabela([
        ["Métrica", "Valor"],
        ["Economia no período", f"R$ {_br(economia.economia_total)}"],
        ["% sobre o frete", f"{_br(economia.economia_pct, 1)}%"],
        ["Projeção mensal", f"R$ {_br(economia.proj_mensal)}"],
        ["Projeção trimestral", f"R$ {_br(economia.proj_trimestral)}"],
        ["Projeção semestral", f"R$ {_br(economia.proj_semestral)}"],
        ["Projeção anual", f"R$ {_br(economia.proj_anual)}"],
    ], col_widths=[9 * cm, 7 * cm]))

    el.append(Spacer(1, 10))
    el.append(Paragraph(
        "GD Conecta — Governança de Frete · Análise de Dados · Torre de Controle",
        s["GDInfo"],
    ))
    doc.build(el)
    return buf.getvalue()


# ============================ Excel ============================
def _aba_titulo(ws, titulo):
    ws.cell(row=1, column=1, value=titulo).font = _title_font


def gerar_benchmark_excel(
    empresa_nome: str,
    nacional: BenchmarkNacional,
    regional: list,
    transportadoras: list,
    economia: PotencialEconomia,
) -> bytes:
    wb = Workbook()

    # Aba 1 — Nacional
    ws = wb.active
    ws.title = "Nacional"
    _aba_titulo(ws, f"Benchmark Nacional — {empresa_nome}")
    ws.append([])
    ws.append(["Indicador", "Empresa", "Bench. médio", "Desvio %", "Classificação"])
    _style_header(ws, ws.max_row, 5)
    ws.append(["Custo por kg", round(nacional.frete_kg.valor, 4),
               round(nacional.frete_kg.benchmark_medio, 4),
               round(nacional.frete_kg.desvio_pct, 1), nacional.frete_kg.classificacao])
    ws.append(["% Frete s/ mercadoria", round(nacional.frete_pct.valor, 2),
               round(nacional.frete_pct.benchmark_medio, 2),
               round(nacional.frete_pct.desvio_pct, 1), nacional.frete_pct.classificacao])
    _autofit(ws)

    # Aba 2 — Regional
    ws = wb.create_sheet("Regional")
    ws.append(["Região", "Frete total", "R$/kg", "Bench. médio", "Desvio %", "Classif.", "% Frete", "Classif. %"])
    _style_header(ws, 1, 8)
    for r in regional:
        ws.append([_rotulo_macro(r.macro_regiao), round(r.frete_total, 2),
                   round(r.frete_kg.valor, 4), round(r.frete_kg.benchmark_medio, 4),
                   round(r.frete_kg.desvio_pct, 1), r.frete_kg.classificacao,
                   round(r.frete_pct.valor, 2), r.frete_pct.classificacao])
    _autofit(ws)

    # Aba 3 — Transportadoras
    ws = wb.create_sheet("Transportadoras")
    ws.append(["Transportadora", "Frete total", "Peso (kg)", "Part. %", "R$/kg", "Desvio %", "Nível custo", "Classif."])
    _style_header(ws, 1, 8)
    for t in transportadoras:
        ws.append([t.nome, round(t.frete_total, 2), round(t.peso_transportado, 0),
                   round(t.participacao_pct, 1), round(t.frete_kg.valor, 4),
                   round(t.frete_kg.desvio_pct, 1), t.nivel_custo, t.frete_kg.classificacao])
    _autofit(ws)

    # Aba 4 — Economia
    ws = wb.create_sheet("Economia")
    _aba_titulo(ws, "Potencial de Economia")
    ws.append([])
    ws.append(["Métrica", "Valor (R$)"])
    _style_header(ws, ws.max_row, 2)
    ws.append(["Economia no período", round(economia.economia_total, 2)])
    ws.append(["% sobre o frete", round(economia.economia_pct, 1)])
    ws.append(["Projeção mensal", round(economia.proj_mensal, 2)])
    ws.append(["Projeção trimestral", round(economia.proj_trimestral, 2)])
    ws.append(["Projeção semestral", round(economia.proj_semestral, 2)])
    ws.append(["Projeção anual", round(economia.proj_anual, 2)])
    ws.append([])
    ws.append(["Economia por região", "", ""])
    ws.append(["Região", "R$/kg atual", "Economia (R$)"])
    _style_header(ws, ws.max_row, 3)
    for r in economia.por_regiao:
        ws.append([_rotulo_macro(r.macro_regiao), round(r.frete_rs_kg, 4), round(r.economia, 2)])
    _autofit(ws)

    out = BytesIO()
    wb.save(out)
    return out.getvalue()
