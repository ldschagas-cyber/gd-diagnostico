"""Verificação manual do novo gerador HTML de Concorrência (BID) — não há BID
real no banco de dev ainda, então simulamos os objetos com SimpleNamespace,
nos dois cenários: BID vazio (recém-criado) e BID com dados completos."""
from types import SimpleNamespace
from app.infrastructure.reports.bid_report import gerar_bid_executivo_html

bid_vazio = SimpleNamespace(
    nome="BID Frete Sudeste 2026",
    status=SimpleNamespace(value="ABERTO"),
    periodo_analise_inicio="2026-01-01",
    periodo_analise_fim="2026-06-30",
)
dados_vazio = {"escopos": [], "bid_transportadoras": [], "transp_nomes": {}, "comparativo": [], "scores": [], "economia": None}

html_vazio = gerar_bid_executivo_html("Connectoway", bid_vazio, dados_vazio, gerado_em="16/07/2026 21:30")
with open("/tmp/bid_vazio.html", "wb") as f:
    f.write(html_vazio)
print("BID vazio OK ->", len(html_vazio), "bytes")

bid_cheio = SimpleNamespace(
    nome="BID Frete Sudeste 2026",
    status=SimpleNamespace(value="EM_COTACAO"),
    periodo_analise_inicio="2026-01-01",
    periodo_analise_fim="2026-06-30",
)
escopo1 = SimpleNamespace(tipo_agrupamento=SimpleNamespace(value="REGIAO"), valor_grupo="Sudeste", qtd_embarques=1200, peso_total=45000, valor_frete_total=180000.0, frete_rs_kg=4.0)
bt1 = SimpleNamespace(transportadora_id=1, status=SimpleNamespace(value="PROPOSTA_RECEBIDA"))
bt2 = SimpleNamespace(transportadora_id=2, status=SimpleNamespace(value="DESISTIU"))
sc1 = SimpleNamespace(nome="Transportes Rápido Ltda", score=87, classificacao="Excelente", proposta_media_rs_kg=3.2, prazo_medio=2)
sc2 = SimpleNamespace(nome="LogExpress", score=61, classificacao="Bom", proposta_media_rs_kg=3.6, prazo_medio=3)
eco = SimpleNamespace(
    frete_atual_total=180000.0, economia_total_periodo=28000.0, economia_pct=15.5,
    ritmo_mensal=4600.0, proj_trimestral=13800.0, proj_semestral=27600.0, proj_anual=55200.0,
    por_grupo=[{"valor_grupo": "Sudeste", "frete_atual_rs_kg": 4.0, "melhor_proposta_rs_kg": 3.2, "economia": 28000.0}],
)
dados_cheio = {
    "escopos": [escopo1],
    "bid_transportadoras": [bt1, bt2],
    "transp_nomes": {1: "Transportes Rápido Ltda", 2: "LogExpress"},
    "comparativo": [],
    "scores": [sc2, sc1],  # fora de ordem de propósito, para testar o sort
    "economia": eco,
}
html_cheio = gerar_bid_executivo_html("Connectoway", bid_cheio, dados_cheio, gerado_em="16/07/2026 21:30")
with open("/tmp/bid_cheio.html", "wb") as f:
    f.write(html_cheio)
print("BID cheio OK ->", len(html_cheio), "bytes")
