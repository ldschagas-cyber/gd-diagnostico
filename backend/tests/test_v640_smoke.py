"""Testes de fumaça das melhorias da versão 6.4.0.

Cobre: importação de evento de cancelamento (MELHORIA 1), base de CT-e por
competência com cancelados (MELHORIA 2), cards do dashboard (MELHORIAS 3-7),
recomendações consolidadas (MELHORIA 8) e a dimensão FILIAL do DLG (MELHORIA 9).

Roda em SQLite isolado, independente do banco de desenvolvimento.
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

EVENTO_CANCELAMENTO_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<procEventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <eventoCTe versao="3.00"><infEvento Id="ID110111{CHAVE}01">
   <cOrgao>35</cOrgao><tpAmb>1</tpAmb>
   <CNPJ>11222333000181</CNPJ>
   <chCTe>{CHAVE}</chCTe>
   <dhEvento>2025-03-15T10:00:00-03:00</dhEvento>
   <tpEvento>110111</tpEvento>
   <nSeqEvento>1</nSeqEvento>
   <detEvento versaoEvento="3.00"><evCancCTe>
     <descEvento>Cancelamento</descEvento>
     <nProt>135250000000099</nProt>
     <xJust>Erro de emissao do documento fiscal para teste.</xJust>
   </evCancCTe></detEvento>
 </infEvento></eventoCTe>
 <retEventoCTe versao="3.00"><infEvento>
   <tpAmb>1</tpAmb><cStat>135</cStat>
   <xMotivo>Evento registrado e vinculado a CT-e</xMotivo>
   <nProt>135250000000099</nProt>
   <dhRegEvento>2025-03-15T10:05:00-03:00</dhRegEvento>
 </infEvento></retEventoCTe>
</procEventoCTe>"""

EVENTO_INEXISTENTE_XML = EVENTO_CANCELAMENTO_XML.replace(CHAVE, "99999999999999999999999999999999999999999999")


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
        "/api/v1/empresas",
        headers=auth_headers,
        json={
            "razao_social": "Empresa Cliente Matriz",
            "nome_fantasia": "Cliente 640",
            "cnpj_matriz": "12.345.678/0001-95",
            "setor": "Indústria",
        },
    )
    assert emp.status_code == 201
    eid = emp.json()["id"]
    files = [("arquivos", ("cte1.xml", CTE_XML.encode("utf-8"), "text/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200 and imp.json()["importados"] == 1
    return eid


# ── MELHORIA 1 — cancelamento via XML ─────────────────────────────────────────

def test_cancelamento_cte_nao_encontrado(client, auth_headers, empresa_id):
    files = [("arquivos", ("ev0.xml", EVENTO_INEXISTENTE_XML.encode("utf-8"), "text/xml"))]
    resp = client.post(
        f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
        headers=auth_headers, files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nao_encontrados"] == 1
    assert body["cancelados"] == 0


def test_cancelamento_cte_sucesso_e_duplicidade(client, auth_headers, empresa_id):
    files = [("arquivos", ("ev1.xml", EVENTO_CANCELAMENTO_XML.encode("utf-8"), "text/xml"))]
    resp = client.post(
        f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
        headers=auth_headers, files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cancelados"] == 1

    # Reimportar o mesmo evento não pode cancelar de novo.
    resp2 = client.post(
        f"/api/v1/importacao/cte/cancelamento/{empresa_id}",
        headers=auth_headers, files=files,
    )
    assert resp2.json()["duplicados"] == 1
    assert resp2.json()["cancelados"] == 0


def test_log_cancelamentos_registrado(client, auth_headers, empresa_id):
    resp = client.get(
        f"/api/v1/importacao/dados/{empresa_id}/cancelamentos",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    log = resp.json()
    resultados = {r["resultado"] for r in log}
    assert "CANCELADO" in resultados
    assert "CTE_NAO_ENCONTRADO" in resultados
    assert "DUPLICADO" in resultados


# ── MELHORIA 2 — base por competência com cancelados ──────────────────────────

def test_competencia_com_cancelados(client, auth_headers, empresa_id):
    resp = client.get(
        f"/api/v1/importacao/dados/{empresa_id}/competencias",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    comp = resp.json()[0]
    assert comp["emitidos"] == 1
    assert comp["cancelados"] == 1
    assert comp["ativos"] == 0


# ── MELHORIAS 3-7 — cards do dashboard ────────────────────────────────────────

def test_dashboard_cards_cancelamento(client, auth_headers, empresa_id):
    resp = client.get(f"/api/v1/dashboard/{empresa_id}", headers=auth_headers)
    assert resp.status_code == 200
    nac = resp.json()["nacional"]
    # Após o cancelamento, os indicadores financeiros zeram (único CT-e cancelado).
    assert nac["qtd_ctes_emitidos"] == 1
    assert nac["qtd_ctes_cancelados"] == 1
    assert nac["qtd_ctes_ativos"] == 0
    assert round(nac["pct_cancelados"], 2) == 100.0
    assert nac["valor_total_frete"] == 0.0        # cancelado não conta no frete ativo
    assert "custo_medio_kg" in nac


# ── MELHORIA 8 — recomendações consolidadas ───────────────────────────────────

def test_recomendacoes_consolidar_e_listar(client, auth_headers, empresa_id):
    resp = client.post(
        f"/api/v1/recomendacoes/{empresa_id}/consolidar", headers=auth_headers
    )
    assert resp.status_code == 200
    resumo = resp.json()
    assert "por_prioridade" in resumo

    lst = client.get(f"/api/v1/recomendacoes/{empresa_id}", headers=auth_headers)
    assert lst.status_code == 200
    assert isinstance(lst.json(), list)


# ── MELHORIA 9 — dimensão FILIAL no DLG ───────────────────────────────────────

def test_dlg_dimensao_filial(client, auth_headers):
    # Empresa nova com CT-e ativo para o DLG processar.
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Filial Teste DLG", "nome_fantasia": "DLG",
              "cnpj_matriz": "12.345.678/0001-95", "setor": "Indústria"},
    )
    # CNPJ repetido é rejeitado; usa a empresa já existente nesse caso.
    if emp.status_code == 201:
        eid = emp.json()["id"]
    else:
        eid = client.get("/api/v1/empresas", headers=auth_headers).json()[0]["id"]

    proc = client.post(f"/api/v1/dlg/{eid}/processar", headers=auth_headers)
    assert proc.status_code == 200

    # A dimensão CLIENTE não deve mais existir; FILIAL sim (quando há dados).
    cliente = client.get(
        f"/api/v1/dlg/{eid}/analitico", headers=auth_headers,
        params={"dimensao": "CLIENTE"},
    )
    assert cliente.status_code == 200
    assert cliente.json() == []  # dimensão descontinuada
