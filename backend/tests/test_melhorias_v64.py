"""Testes das melhorias v6.4 — cancelamento de CT-e, cards do dashboard,
base por competência e recomendações.

Executa em banco SQLite isolado. Rode SEPARADAMENTE dos demais arquivos de
teste (conflito de DATABASE_URL em nível de módulo — igual aos smoke tests).
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CHAVE = "35200714200166000187570010000000031000000031"

CTE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe{CHAVE}" versao="3.00">
  <ide>
   <cUF>35</cUF><nCT>3</nCT><serie>1</serie>
   <dhEmi>2025-03-10T09:00:00-03:00</dhEmi>
   <cMunIni>3550308</cMunIni><xMunIni>SAO PAULO</xMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><xMunFim>RIO DE JANEIRO</xMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3>
  </ide>
  <emit><CNPJ>11222333000181</CNPJ><xNome>TRANSPORTADORA TESTE LTDA</xNome></emit>
  <dest><CNPJ>12345678000195</CNPJ><xNome>EMPRESA CLIENTE MATRIZ</xNome></dest>
  <vPrest><vTPrest>1500.00</vTPrest><vRec>1500.00</vRec></vPrest>
  <infCTeNorm>
   <infCarga><vCarga>50000.00</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>1200.0000</qCarga></infQ>
   </infCarga>
   <infDoc><infNFe><chave>26260603822909000113550040000492621906782994</chave></infNFe></infDoc>
  </infCTeNorm>
 </infCte></CTe>
</cteProc>"""

CANCEL_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<procEventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <eventoCTe versao="3.00">
  <infEvento Id="ID110111{CHAVE}01">
   <cOrgao>35</cOrgao><tpAmb>1</tpAmb><CNPJ>11222333000181</CNPJ>
   <chCTe>{CHAVE}</chCTe>
   <dhEvento>2025-03-15T10:00:00-03:00</dhEvento>
   <tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento>
   <detEvento versaoEvento="3.00">
    <evCancCTe><descEvento>Cancelamento</descEvento>
     <nProt>135250000000123</nProt><xJust>Erro de emissao para teste</xJust>
    </evCancCTe>
   </detEvento>
  </infEvento>
 </eventoCTe>
 <retEventoCTe versao="3.00">
  <infEvento><tpAmb>1</tpAmb><cOrgao>35</cOrgao><cStat>135</cStat>
   <xMotivo>Evento registrado e vinculado ao CT-e</xMotivo>
   <chCTe>{CHAVE}</chCTe><tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento>
   <dhRegEvento>2025-03-15T10:05:00-03:00</dhRegEvento><nProt>135250000000123</nProt>
  </infEvento>
 </retEventoCTe>
</procEventoCTe>"""

CANCEL_XML_INEXISTENTE = CANCEL_XML.replace(CHAVE, "35200714200166000187570010000000099000000099")


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
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Empresa Cliente Matriz", "nome_fantasia": "Cliente",
              "cnpj_matriz": "12.345.678/0001-95", "setor": "Indústria"},
    )
    assert emp.status_code == 201
    eid = emp.json()["id"]
    # define metas nacionais (habilita desvios/recomendações)
    client.put("/api/v1/metas/nacional", headers=auth_headers,
               json={"meta_rs_kg": 1.00, "meta_pct_frete": 2.5})
    # importa o CT-e
    files = [("arquivos", ("cte1.xml", CTE_XML.encode("utf-8"), "text/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200 and imp.json()["importados"] == 1
    return eid


# ── MELHORIA 1 — cancelamento via XML ─────────────────────────────────────────

def test_cancelamento_cte_nao_encontrado(client, auth_headers, empresa_id):
    files = [("arquivos", ("cancel_x.xml", CANCEL_XML_INEXISTENTE.encode("utf-8"), "text/xml"))]
    r = client.post(f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
                    headers=auth_headers, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["nao_encontrados"] == 1
    assert body["cancelados"] == 0
    assert body["ocorrencias"][0]["resultado"] == "CTE_NAO_ENCONTRADO"


def test_cancelamento_cte_sucesso(client, auth_headers, empresa_id):
    files = [("arquivos", ("cancel1.xml", CANCEL_XML.encode("utf-8"), "text/xml"))]
    r = client.post(f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
                    headers=auth_headers, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["cancelados"] == 1
    # dashboard: CT-e agora está cancelado → ativos = 0
    dash = client.get(f"/api/v1/dashboard/{empresa_id}", headers=auth_headers).json()
    nac = dash["nacional"]
    assert nac["qtd_ctes_emitidos"] == 1
    assert nac["qtd_ctes_cancelados"] == 1
    assert nac["qtd_ctes_ativos"] == 0
    assert nac["valor_total_frete"] == 0.0  # frete só considera ativos
    assert round(nac["pct_cancelados"], 2) == 100.0


def test_cancelamento_duplicado(client, auth_headers, empresa_id):
    files = [("arquivos", ("cancel1.xml", CANCEL_XML.encode("utf-8"), "text/xml"))]
    r = client.post(f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
                    headers=auth_headers, files=files)
    assert r.status_code == 200
    assert r.json()["duplicados"] == 1


def test_log_cancelamentos(client, auth_headers, empresa_id):
    r = client.get(f"/api/v1/importacao/dados/{empresa_id}/cancelamentos",
                   headers=auth_headers)
    assert r.status_code == 200
    log = r.json()
    resultados = {item["resultado"] for item in log}
    assert "CANCELADO" in resultados
    assert "CTE_NAO_ENCONTRADO" in resultados


# ── MELHORIA 2 — base por competência com cancelados ──────────────────────────

def test_competencia_com_cancelados(client, auth_headers, empresa_id):
    r = client.get(f"/api/v1/importacao/dados/{empresa_id}/competencias",
                   headers=auth_headers)
    assert r.status_code == 200
    comp = r.json()
    assert len(comp) == 1
    c = comp[0]
    assert c["emitidos"] == 1
    assert c["cancelados"] == 1
    assert c["ativos"] == 0
    assert c["quantidade"] == 1  # compatibilidade


# ── MELHORIA 8 — recomendações ────────────────────────────────────────────────

def test_recomendacoes_consolidar_e_listar(client, auth_headers, empresa_id):
    # Reativa um cenário com dados ativos: nova empresa + CT-e sem cancelamento.
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Empresa B", "nome_fantasia": "B",
              "cnpj_matriz": "12.345.678/0001-95", "setor": "Indústria"},
    )
    # CNPJ duplicado é rejeitado; usa a empresa original (que tem meta e desvio).
    r = client.post(f"/api/v1/recomendacoes/{empresa_id}/consolidar", headers=auth_headers)
    assert r.status_code == 200
    resumo = r.json()
    assert "por_prioridade" in resumo
    lst = client.get(f"/api/v1/recomendacoes/{empresa_id}", headers=auth_headers)
    assert lst.status_code == 200
    # A estrutura de cada recomendação deve conter os campos exigidos.
    for rec in lst.json():
        assert set(["titulo", "descricao", "indicador", "valor_encontrado",
                    "valor_recomendado", "impacto", "prioridade", "status"]).issubset(rec)
