"""Tema visual compartilhado pelos relatórios em HTML (Diagnóstico, Benchmark,
Concorrência/BID) — paleta GD Conecta, formatação numérica e o wrapper de
página (cabeçalho/corpo/rodapé) usados por todos, para manter os três
relatórios com a mesma identidade visual sem duplicar CSS em cada um.

Documentos autocontidos (CSS inline, sem dependências externas) — abrem direto
no navegador. Todo texto de origem do usuário deve passar por ``html.escape``
antes de entrar no HTML montado aqui.
"""
from typing import List, Optional

INDIGO = "#2D3561"
AMBER = "#C9A84C"
AMBER_DARK = "#A98A33"
BLUE = "#0077A8"
IVORY = "#F5F1EB"
IVORY_DEEP = "#ECE6DA"
INK = "#1C2030"
SLATE = "#5A6072"
OK = "#2E7D5B"
OK_BG = "#E7F2EC"
WARN = "#C9772F"
WARN_BG = "#FBF0E4"
DANGER = "#B4453B"
DANGER_BG = "#FBEAE8"
RULE = "rgba(45,53,97,0.12)"


def moeda(v: Optional[float]) -> str:
    return f"R$ {(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def numero(v: Optional[float], casas: int = 2) -> str:
    return f"{(v or 0):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: Optional[float], casas: int = 2) -> str:
    return f"{numero(v, casas)}%"


def chip(rotulo: str, classe: str) -> str:
    from html import escape
    return f'<span class="chip {classe}">{escape(rotulo)}</span>'


CSS_BASE = f"""
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: {IVORY}; color: {INK};
    font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 14.5px; line-height: 1.55;
  }}
  .tabular {{ font-variant-numeric: tabular-nums; }}
  .pagina {{ display: flex; justify-content: center; padding: 40px 20px 80px; }}
  .documento {{
    width: 100%; max-width: 860px; background: #FFFFFF; border-radius: 14px;
    box-shadow: 0 1px 2px rgba(28,32,48,0.04), 0 8px 24px rgba(28,32,48,0.06);
    overflow: hidden;
  }}
  .cabecalho {{ background: {INDIGO}; color: #fff; padding: 32px 40px 28px; }}
  .marca {{ display: flex; align-items: center; gap: 12px; margin-bottom: 22px; }}
  .selo {{
    width: 36px; height: 36px; border-radius: 8px; background: {AMBER}; color: {INDIGO};
    display: grid; place-items: center; font-weight: 800; font-size: 15px;
  }}
  .marca span {{ font-weight: 700; font-size: 14px; opacity: 0.92; }}
  .cabecalho h1 {{ margin: 0 0 6px; font-size: 27px; font-weight: 800; letter-spacing: -0.01em; }}
  .linha-titulo {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .selo-saude {{ display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 800; }}
  .meta-cabecalho {{ display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: 13px; color: rgba(255,255,255,0.78); margin-top: 6px; }}
  .meta-cabecalho b {{ color: #fff; font-weight: 600; }}
  .resumo-executivo {{ margin: 14px 0 0; font-size: 14px; color: rgba(255,255,255,0.92); max-width: 70ch; }}
  .corpo {{ padding: 8px 40px 12px; }}
  section.bloco {{ padding: 28px 0; border-bottom: 1px solid {RULE}; }}
  section.bloco:last-of-type {{ border-bottom: none; }}
  .titulo-secao {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 0 0 4px; }}
  .titulo-secao h2 {{ margin: 0; font-size: 17px; font-weight: 800; color: {INDIGO}; letter-spacing: -0.01em; }}
  .titulo-secao .nota {{ font-size: 12.5px; color: {SLATE}; white-space: nowrap; }}
  .descricao-secao {{ margin: 2px 0 18px; color: {SLATE}; font-size: 13.5px; max-width: 66ch; }}
  .grade-kpi {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
  .kpi {{ border: 1px solid {RULE}; border-radius: 10px; padding: 14px 16px; background: {IVORY_DEEP}; }}
  .kpi .rotulo {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: {SLATE}; display: block; margin-bottom: 6px; }}
  .kpi .valor {{ font-size: 21px; font-weight: 800; color: {INDIGO}; }}
  .kpi .legenda {{ font-size: 12px; color: {SLATE}; margin-top: 2px; }}
  .kpi .legenda.desvio-neg {{ color: {OK}; font-weight: 700; }}
  .kpi .legenda.desvio-pos {{ color: {DANGER}; font-weight: 700; }}
  .tabela-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 9px 12px; text-align: right; white-space: nowrap; }}
  th:first-child, td:first-child {{ text-align: left; white-space: normal; }}
  thead th {{ color: {INDIGO}; font-weight: 700; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid {RULE}; }}
  tbody td {{ border-bottom: 1px solid {RULE}; color: {INK}; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  .chip {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }}
  .chip.critico {{ background: {DANGER_BG}; color: {DANGER}; }}
  .chip.atencao {{ background: {WARN_BG}; color: {WARN}; }}
  .chip.eficiente {{ background: {OK_BG}; color: {OK}; }}
  .chip.neutro {{ background: {IVORY_DEEP}; color: {SLATE}; }}
  .desvio-pos {{ color: {DANGER}; font-weight: 700; }}
  .desvio-neg {{ color: {OK}; font-weight: 700; }}
  .distribuicao {{ display: flex; gap: 18px; margin: 4px 0 12px; flex-wrap: wrap; }}
  .distribuicao .item {{ display: flex; align-items: center; gap: 7px; font-size: 13px; }}
  .distribuicao .ponto {{ width: 9px; height: 9px; border-radius: 50%; }}
  .distribuicao b {{ font-weight: 800; }}
  .subgrupo {{ margin-top: 22px; }}
  .subgrupo:first-child {{ margin-top: 0; }}
  .subgrupo > .rotulo-dim {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: {SLATE}; margin-bottom: 8px; display: block; }}
  .vazio {{ color: {SLATE}; font-size: 13px; font-style: italic; }}
  .recomendacao {{ border: 1px solid {RULE}; border-left: 4px solid {DANGER}; border-radius: 8px; padding: 16px 18px; margin-bottom: 14px; }}
  .recomendacao.atencao {{ border-left-color: {WARN}; }}
  .recomendacao.eficiente {{ border-left-color: {OK}; }}
  .recomendacao.neutro {{ border-left-color: {SLATE}; }}
  .recomendacao .linha-topo {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 6px; }}
  .recomendacao h3 {{ margin: 0; font-size: 14.5px; font-weight: 700; color: {INK}; }}
  .recomendacao p {{ margin: 0 0 8px; color: {SLATE}; font-size: 13px; max-width: 68ch; }}
  .recomendacao .acao {{ background: {IVORY_DEEP}; border-radius: 6px; padding: 9px 12px; font-size: 12.8px; color: {INK}; }}
  .recomendacao .acao b {{ color: {OK}; }}
  .recomendacao .valores {{ display: flex; gap: 22px; flex-wrap: wrap; margin-top: 10px; font-size: 12.5px; }}
  .recomendacao .valores .par {{ color: {SLATE}; }}
  .recomendacao .valores .par b {{ color: {INK}; font-weight: 700; }}
  .recomendacao .economia {{ color: {OK}; font-weight: 800; }}
  .rodape {{ padding: 22px 40px 32px; color: {SLATE}; font-size: 12px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
  @media (max-width: 640px) {{
    .cabecalho, .corpo, .rodape {{ padding-left: 22px; padding-right: 22px; }}
  }}
  @media print {{
    body {{ background: #fff; }}
    .pagina {{ padding: 0; }}
    .documento {{ box-shadow: none; border-radius: 0; max-width: none; }}
  }}
"""


def render_documento(
    titulo_pagina: str,
    titulo_relatorio: str,
    meta_items: List[str],
    corpo_html: str,
    selo_saude: Optional[tuple] = None,
    resumo_executivo: Optional[str] = None,
    rodape_nota: str = "",
) -> bytes:
    """Monta o HTML completo (doctype/head/body) a partir das seções já
    renderizadas por cada gerador (``corpo_html``). ``selo_saude`` é uma tupla
    ``(rotulo, cor_texto, cor_fundo)`` opcional exibida ao lado do título."""
    selo_html = ""
    if selo_saude:
        rotulo, cor, fundo = selo_saude
        selo_html = (
            f'<span class="selo-saude" style="color:{cor};background:{fundo}">{rotulo}</span>'
        )
    resumo_html = f'<p class="resumo-executivo">{resumo_executivo}</p>' if resumo_executivo else ""

    pagina_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{titulo_pagina}</title>
<style>{CSS_BASE}</style>
</head>
<body>
<div class="pagina">
  <div class="documento">

    <div class="cabecalho">
      <div class="marca"><div class="selo">GD</div><span>GD Diagnóstico Logístico</span></div>
      <div class="linha-titulo"><h1>{titulo_relatorio}</h1>{selo_html}</div>
      <div class="meta-cabecalho">{"".join(meta_items)}</div>
      {resumo_html}
    </div>

    <div class="corpo">
{corpo_html}
    </div>

    <div class="rodape">
      <span>{rodape_nota or "GD Diagnóstico Logístico — relatório gerado automaticamente."}</span>
      <span>gdconecta.com.br</span>
    </div>

  </div>
</div>
</body>
</html>"""
    return pagina_html.encode("utf-8")
