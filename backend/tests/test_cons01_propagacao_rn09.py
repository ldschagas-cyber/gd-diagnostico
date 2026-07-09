"""Testes de regressão CONS-01 — propagação da RN-09 (exclusão de CT-e
cancelado dos totais analíticos) aos módulos afetados: MBL, Benchmark
(legado, OD, Observado), Indicadores Regionais V2, Score Logístico,
Insights, Oportunidades, Diagnóstico IA e Benchmark Setorial.

Cenário: 2 CT-es no mesmo corredor (SP→RJ), com transportadoras
DIFERENTES — CT-e A (ativo, Transportadora Alfa, frete R$1000/peso
1000kg) e CT-e B (cancelado, Transportadora Beta, frete R$1500/peso
500kg). Depois de cancelar B, todo total analítico deve refletir
SOMENTE A. Usar transportadoras diferentes torna os asserts de
concentração (Score/Insights/Oportunidades) sensíveis à correção: se o
cancelado ainda contaminasse o total, a concentração da Alfa cairia de
100% para ~67%.

Rodar isolado (conflito de DATABASE_URL em nível de módulo, como os
demais arquivos de teste de integração deste projeto):
  pytest backend/tests/test_cons01_propagacao_rn09.py -v
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
# Fixa a senha do superusuário semeado, independente de um .env local que a
# sobrescreva (variável de ambiente do processo tem prioridade sobre .env no
# pydantic-settings) — evita acoplar o teste ao segredo real do ambiente.
os.environ["FIRST_SUPERUSER_PASSWORD"] = "admin123"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CHAVE_ATIVO = "35200714200166000187570010000000041000000041"
CHAVE_CANCELADO = "35200714200166000187570010000000042000000042"

CNPJ_TRANSP_A = "11222333000181"
CNPJ_TRANSP_B = "22333444000155"
CNPJ_DEST = "12345678000195"


def _cte_xml(chave: str, n_ct: str, cnpj_transp: str, nome_transp: str,
             dh_emi: str, v_frete: str, v_carga: str, q_carga: str,
             nfe_chave: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe{chave}" versao="3.00">
  <ide>
   <cUF>35</cUF><nCT>{n_ct}</nCT><serie>1</serie>
   <dhEmi>{dh_emi}</dhEmi>
   <cMunIni>3550308</cMunIni><xMunIni>SAO PAULO</xMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><xMunFim>RIO DE JANEIRO</xMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3>
  </ide>
  <emit><CNPJ>{cnpj_transp}</CNPJ><xNome>{nome_transp}</xNome></emit>
  <dest><CNPJ>{CNPJ_DEST}</CNPJ><xNome>EMPRESA CLIENTE MATRIZ</xNome></dest>
  <vPrest><vTPrest>{v_frete}</vTPrest><vRec>{v_frete}</vRec></vPrest>
  <infCTeNorm>
   <infCarga><vCarga>{v_carga}</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>{q_carga}</qCarga></infQ>
   </infCarga>
   <infDoc><infNFe><chave>{nfe_chave}</chave></infNFe></infDoc>
  </infCTeNorm>
 </infCte></CTe>
</cteProc>"""


CTE_XML_ATIVO = _cte_xml(
    CHAVE_ATIVO, "41", CNPJ_TRANSP_A, "TRANSPORTADORA ALFA LTDA",
    "2025-03-10T09:00:00-03:00", "1000.00", "40000.00", "1000.0000",
    "26260603822909000113550040000492621906001",
)
CTE_XML_CANCELADO = _cte_xml(
    CHAVE_CANCELADO, "42", CNPJ_TRANSP_B, "TRANSPORTADORA BETA LTDA",
    "2025-03-12T09:00:00-03:00", "1500.00", "30000.00", "500.0000",
    "26260603822909000113550040000492621906002",
)

CANCEL_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<procEventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <eventoCTe versao="3.00">
  <infEvento Id="ID110111{CHAVE_CANCELADO}01">
   <cOrgao>35</cOrgao><tpAmb>1</tpAmb><CNPJ>{CNPJ_TRANSP_B}</CNPJ>
   <chCTe>{CHAVE_CANCELADO}</chCTe>
   <dhEvento>2025-03-15T10:00:00-03:00</dhEvento>
   <tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento>
   <detEvento versaoEvento="3.00">
    <evCancCTe><descEvento>Cancelamento</descEvento>
     <nProt>135250000000456</nProt><xJust>Erro de emissao para teste</xJust>
    </evCancCTe>
   </detEvento>
  </infEvento>
 </eventoCTe>
 <retEventoCTe versao="3.00">
  <infEvento><tpAmb>1</tpAmb><cOrgao>35</cOrgao><cStat>135</cStat>
   <xMotivo>Evento registrado e vinculado ao CT-e</xMotivo>
   <chCTe>{CHAVE_CANCELADO}</chCTe><tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento>
   <dhRegEvento>2025-03-15T10:05:00-03:00</dhRegEvento><nProt>135250000000456</nProt>
  </infEvento>
 </retEventoCTe>
</procEventoCTe>"""


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@gdconecta.com.br", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def empresa_id(client, auth_headers):
    """Empresa com 2 CT-es no mesmo corredor SP→RJ: 1 ativo (Alfa,
    R$1000/1000kg) + 1 cancelado (Beta, R$1500/500kg). Todo total
    analítico deve refletir SOMENTE o ativo."""
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Empresa CONS-01", "nome_fantasia": "CONS01",
              "cnpj_matriz": "12.345.678/0001-95", "setor": "Indústria"},
    )
    assert emp.status_code == 201
    eid = emp.json()["id"]

    files = [
        ("arquivos", ("cte_ativo.xml", CTE_XML_ATIVO.encode("utf-8"), "text/xml")),
        ("arquivos", ("cte_cancelado.xml", CTE_XML_CANCELADO.encode("utf-8"), "text/xml")),
    ]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200 and imp.json()["importados"] == 2

    cancel_files = [("arquivos", ("cancel.xml", CANCEL_XML.encode("utf-8"), "text/xml"))]
    canc = client.post(f"/api/v1/importacao/cte/cancelamento/{eid}",
                        headers=auth_headers, files=cancel_files)
    assert canc.status_code == 200 and canc.json()["cancelados"] == 1

    return eid


# ── Teste de consistência cruzada (o mais importante — reproduz e corrige
# o sintoma literal do achado: "duas telas mostram números diferentes") ────

def test_consistencia_dashboard_vs_benchmark_nacional(client, auth_headers, empresa_id):
    dash = client.get(f"/api/v1/dashboard/{empresa_id}", headers=auth_headers).json()
    nac = dash["nacional"]
    assert nac["qtd_ctes_ativos"] == 1
    assert nac["valor_total_frete"] == 1000.00
    assert nac["peso_total"] == 1000.00

    bench = client.get(f"/api/v1/benchmark/nacional/{empresa_id}", headers=auth_headers).json()
    assert bench["qtd_ctes"] == 1
    assert bench["valor_total_frete"] == 1000.00
    assert bench["peso_total"] == 1000.00

    # O sintoma do achado CONS-01: as duas telas devem bater exatamente.
    assert nac["valor_total_frete"] == bench["valor_total_frete"]
    assert nac["peso_total"] == bench["peso_total"]


# ── MBL ──────────────────────────────────────────────────────────────────

def test_mbl_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.post(f"/api/v1/mbl/{empresa_id}/processar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ctes"] == 1  # só o ativo


# ── Benchmark OD (corredores) ───────────────────────────────────────────

def test_benchmark_od_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.get(f"/api/v1/benchmark/corredores/{empresa_id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["peso_total"] == 1000.00
    assert body["frete_total"] == 1000.00
    assert len(body["corredores"]) == 1
    assert body["corredores"][0]["qtd_ctes"] == 1
    assert body["corredores"][0]["frete_total"] == 1000.00


# ── Benchmark Observado ─────────────────────────────────────────────────

def test_benchmark_observado_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.post(
        f"/api/v1/benchmark-v2/observado/gerar?empresa_id={empresa_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["embarques_considerados"] == 1

    r = client.get(f"/api/v1/benchmark-v2/observado?empresa_id={empresa_id}", headers=auth_headers)
    assert r.status_code == 200
    linhas = r.json()
    assert len(linhas) == 1
    assert linhas[0]["qtd_embarques"] == 1
    assert linhas[0]["rs_kg_p50"] == 1.0  # só o CT-e ativo (1000/1000)


# ── Indicadores Regionais V2 ────────────────────────────────────────────

def test_indicadores_regionais_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.get(
        f"/api/v1/benchmark-v2/indicadores-regionais?empresa_id={empresa_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    ind = r.json()
    assert len(ind) == 1
    assert ind[0]["qtd_embarques"] == 1
    assert ind[0]["frete_medio_rs_kg"] == 1.0


# ── Score Logístico ─────────────────────────────────────────────────────

def test_score_logistico_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.post(
        f"/api/v1/inteligencia/score/calcular?empresa_id={empresa_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    componentes = r.json()["componentes"]
    # Só a Transportadora Alfa está ativa → concentração 100% → score no
    # piso da faixa (30.0). Se o cancelado (Transportadora Beta) ainda
    # contaminasse o total, a concentração cairia para ~67% e o score
    # subiria para ~53 — a asserção abaixo falharia sem a correção.
    assert componentes["transportadoras"] == 30.0


# ── Insights ─────────────────────────────────────────────────────────────

def test_insights_exclui_cancelado(client, auth_headers, empresa_id):
    client.post(f"/api/v1/inteligencia/insights/gerar?empresa_id={empresa_id}", headers=auth_headers)
    r = client.get(f"/api/v1/inteligencia/insights?empresa_id={empresa_id}", headers=auth_headers)
    assert r.status_code == 200
    insights = r.json()
    transp_insights = [i for i in insights if i["categoria"] == "TRANSPORTADORAS"]
    assert len(transp_insights) == 1
    assert "ALFA" in transp_insights[0]["titulo"].upper()
    assert "100" in transp_insights[0]["descricao"]
    assert "BETA" not in transp_insights[0]["descricao"].upper()


# ── Oportunidades ────────────────────────────────────────────────────────

def test_oportunidades_exclui_cancelado(client, auth_headers, empresa_id):
    client.post(f"/api/v1/inteligencia/oportunidades/detectar?empresa_id={empresa_id}", headers=auth_headers)
    r = client.get(f"/api/v1/inteligencia/oportunidades?empresa_id={empresa_id}", headers=auth_headers)
    assert r.status_code == 200
    oportunidades = r.json()
    concentracao = [o for o in oportunidades if o["tipo"] == "CONCENTRACAO"]
    assert len(concentracao) == 1
    assert "100%" in concentracao[0]["descricao"]
    assert "ALFA" in concentracao[0]["titulo"].upper()


# ── Diagnóstico IA ───────────────────────────────────────────────────────

def test_diagnostico_ia_consistente_com_score(client, auth_headers, empresa_id):
    score = client.get(f"/api/v1/inteligencia/score?empresa_id={empresa_id}", headers=auth_headers).json()
    r = client.post(
        f"/api/v1/inteligencia/diagnostico/gerar?empresa_id={empresa_id}&forcar=true",
        headers=auth_headers,
    )
    assert r.status_code == 200
    diag = r.json()
    # Diagnóstico IA recalcula o Score internamente a partir dos mesmos
    # CT-es — se ambos excluem o cancelado da mesma forma, os totais batem.
    assert diag["score_logistico"] == score["score_total"]


# ── Benchmark Setorial (achado adicional, mesmo padrão de bug, fora da
# lista original de módulos da Fase 7 — corrigido junto por ser a mesma
# causa raiz) ────────────────────────────────────────────────────────────

def test_benchmark_setorial_exclui_cancelado(client, auth_headers, empresa_id):
    r = client.get(f"/api/v1/inteligencia/benchmark-setorial?empresa_id={empresa_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["frete_kg_empresa"] == 1.0
