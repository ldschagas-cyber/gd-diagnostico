"""Testes de fumaça (smoke tests) dos fluxos principais da API.

Executa em banco SQLite isolado (arquivo temporário) para não afetar o
banco de desenvolvimento. Cobre: boot da aplicação, autenticação, seed de
metas, CRUD de empresa, importação de CT-e, dashboard e relatórios.
"""
import os
import tempfile

import pytest

# Banco temporário ANTES de importar a aplicação.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CTE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe35200714200166000187570010000000031000000031" versao="3.00">
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


def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


def test_login_invalido(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@gdconecta.com.br", "password": "errada"},
    )
    assert resp.status_code == 401


def test_seed_metas_regionais(client, auth_headers):
    resp = client.get("/api/v1/metas/regionais", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 5  # 5 macro-regiões


def test_fluxo_completo_importacao_e_relatorios(client, auth_headers):
    # cria empresa cujo CNPJ matriz é o destinatário do CT-e
    emp = client.post(
        "/api/v1/empresas",
        headers=auth_headers,
        json={
            "razao_social": "Empresa Cliente Matriz",
            "nome_fantasia": "Cliente",
            "cnpj_matriz": "12.345.678/0001-95", "setor": "Indústria",
        },
    )
    assert emp.status_code == 201
    eid = emp.json()["id"]

    # importa CT-e
    files = [("arquivos", ("cte1.xml", CTE_XML.encode("utf-8"), "text/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200
    assert imp.json()["importados"] == 1

    # duplicidade: reimportar o mesmo CT-e não deve duplicar
    imp2 = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp2.json()["duplicados"] == 1

    # dashboard
    dash = client.get(f"/api/v1/dashboard/{eid}", headers=auth_headers)
    assert dash.status_code == 200
    d = dash.json()
    assert d["nacional"]["valor_total_frete"] == 1500.0
    assert round(d["nacional"]["frete_rs_kg"], 2) == 1.25
    # Regressão: valor da mercadoria (infCarga aninhado em infCTeNorm) deve fluir.
    assert d["nacional"]["valor_total_mercadoria"] == 50000.0
    assert round(d["nacional"]["frete_pct"], 2) == 3.0
    assert len(d["transportadoras"]) == 1

    # relatórios
    xlsx = client.get(f"/api/v1/relatorios/diagnostico/{eid}/excel", headers=auth_headers)
    assert xlsx.status_code == 200 and len(xlsx.content) > 0
    pdf = client.get(f"/api/v1/relatorios/diagnostico/{eid}/pdf", headers=auth_headers)
    assert pdf.status_code == 200 and len(pdf.content) > 0


def test_cte_sem_vinculo_e_ignorado(client, auth_headers):
    # empresa com CNPJ diferente do destinatário do CT-e
    emp = client.post(
        "/api/v1/empresas",
        headers=auth_headers,
        json={
            "razao_social": "Outra Empresa",
            "nome_fantasia": "Outra",
            "cnpj_matriz": "98.765.432/0001-98", "setor": "Indústria",
        },
    )
    eid = emp.json()["id"]
    files = [("arquivos", ("cte1.xml", CTE_XML.encode("utf-8"), "text/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200
    # destinatário não bate com a matriz -> ignorado por falta de vínculo
    assert imp.json()["ignorados_sem_vinculo"] == 1
    assert imp.json()["importados"] == 0


def test_peso_taxado_usa_o_maior_peso():
    """O peso considerado deve ser o maior entre bruto e cubado (peso taxado)."""
    from app.infrastructure.parsers.cte_parser import parse_cte_xml

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe35200714200166000187570010000000041000000041" versao="3.00">
  <ide><cUF>35</cUF><nCT>4</nCT><serie>1</serie>
   <dhEmi>2025-03-10T09:00:00-03:00</dhEmi>
   <cMunIni>3550308</cMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3></ide>
  <emit><CNPJ>11222333000181</CNPJ><xNome>TRANSP</xNome></emit>
  <dest><CNPJ>12345678000195</CNPJ><xNome>CLIENTE</xNome></dest>
  <vPrest><vTPrest>1000.00</vTPrest></vPrest>
  <infCTeNorm><infCarga><vCarga>5000.00</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>2.0000</qCarga></infQ>
    <infQ><cUnid>01</cUnid><tpMed>PESO CUBADO</tpMed><qCarga>11.7833</qCarga></infQ>
    <infQ><cUnid>03</cUnid><tpMed>VOLUMES</tpMed><qCarga>2.0000</qCarga></infQ>
    <infQ><cUnid>00</cUnid><tpMed>CUBAGEM</tpMed><qCarga>0.0707</qCarga></infQ>
  </infCarga></infCTeNorm>
 </infCte></CTe></cteProc>"""
    r = parse_cte_xml(xml.encode("utf-8"))
    assert r.peso == 11.7833  # maior peso (cubado), não o bruto (2.0)
    assert r.valor_mercadoria == 5000.0


def test_benchmark_seed_e_edicao(client, auth_headers):
    """Fase A: 6 benchmarks semeados (5 regiões + nacional) e edição por admin."""
    r = client.get("/api/v1/benchmarks", headers=auth_headers)
    assert r.status_code == 200
    linhas = r.json()
    assert len(linhas) == 6
    nacional = next(b for b in linhas if b["regiao"] == "NACIONAL")
    assert nacional["frete_kg_medio"] == 1.65
    assert nacional["frete_pct_medio"] == 10.0
    # edição (upsert) por admin
    up = client.put(
        "/api/v1/benchmarks/SUDESTE",
        headers=auth_headers,
        json={
            "regiao": "SUDESTE",
            "frete_kg_min": 0.75, "frete_kg_medio": 1.00, "frete_kg_max": 1.25,
            "frete_pct_min": 4.5, "frete_pct_medio": 6.5, "frete_pct_max": 8.5,
        },
    )
    assert up.status_code == 200
    assert up.json()["frete_kg_medio"] == 1.00


def test_benchmark_analise_classificacao(client, auth_headers):
    """Fase B/C: nacional, regional e transportadoras com classificação."""
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Bench Co", "nome_fantasia": "Bench", "cnpj_matriz": "11.111.111/0001-91", "setor": "Indústria"},
    ).json()
    eid = emp["id"]
    # CT-e: frete 1500 / peso 1000 = 1.50 R$/kg ; merc 50000 -> 3% frete ; destino RJ (Sudeste)
    xml = CTE_XML.replace("12345678000195", "11111111000191").replace(
        "35200714200166000187570010000000031000000031",
        "35200714200166000187570010000000099000000099",
    )
    client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers,
                files=[("arquivos", ("c.xml", xml.encode(), "text/xml"))])

    nac = client.get(f"/api/v1/benchmark/nacional/{eid}", headers=auth_headers).json()
    # 1.50 <= benchmark nacional medio 1.65 -> Excelente
    assert nac["frete_kg"]["classificacao"] == "Excelente"
    assert nac["frete_kg"]["benchmark_medio"] == 1.65

    reg = client.get(f"/api/v1/benchmark/regional/{eid}", headers=auth_headers).json()
    sudeste = next(r for r in reg if r["macro_regiao"] == "SUDESTE")
    # 1.50 / 0.95 (sudeste) = 1.58 -> acima de +20% -> Crítico
    assert sudeste["frete_kg"]["classificacao"] == "Crítico"

    tr = client.get(f"/api/v1/benchmark/transportadoras/{eid}", headers=auth_headers).json()
    assert len(tr) == 1
    assert tr[0]["nivel_custo"] == "Melhor custo"


def test_relatorios_benchmark_pdf_e_excel(client, auth_headers):
    """Fase E/F: relatórios consolidados de benchmark em PDF e Excel."""
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Rep Co", "nome_fantasia": "Rep", "cnpj_matriz": "44.444.444/0001-91", "setor": "Indústria"},
    ).json()
    eid = emp["id"]
    xml = CTE_XML.replace("12345678000195", "44444444000191").replace(
        "35200714200166000187570010000000031000000031",
        "35200714200166000187570010000000044000000044",
    )
    client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers,
                files=[("arquivos", ("c.xml", xml.encode(), "text/xml"))])

    pdf = client.get(f"/api/v1/relatorios/benchmark/{eid}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"

    xls = client.get(f"/api/v1/relatorios/benchmark/{eid}/excel", headers=auth_headers)
    assert xls.status_code == 200
    assert xls.content[:2] == b"PK"


# ── MELHORIA 2 — Setor obrigatório no cadastro de empresa ───────────────────
def test_setor_obrigatorio_e_edicao(client, auth_headers):
    # Sem setor → 422 (campo obrigatório).
    sem = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Sem Setor LTDA", "cnpj_matriz": "19.876.543/0001-03"},
    )
    assert sem.status_code == 422

    # Setor inválido (fora do vocabulário controlado) → 422.
    invalido = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Setor Errado LTDA", "cnpj_matriz": "19.876.543/0001-03",
              "setor": "Mineração"},
    )
    assert invalido.status_code == 422

    # Com setor válido → 201 e setor retornado.
    ok = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Com Setor LTDA", "nome_fantasia": "ComSetor",
              "cnpj_matriz": "19.876.543/0001-03", "setor": "Varejo"},
    )
    assert ok.status_code == 201
    body = ok.json()
    assert body["setor"] == "Varejo"
    eid = body["id"]

    # Edição posterior do setor (PUT) deve persistir.
    upd = client.put(
        f"/api/v1/empresas/{eid}", headers=auth_headers,
        json={"setor": "E-commerce"},
    )
    assert upd.status_code == 200
    assert upd.json()["setor"] == "E-commerce"


# ── MELHORIA 1 — Indicador de base de CT-e por competência ──────────────────
def test_indicador_competencias_cte(client, auth_headers):
    emp = client.post(
        "/api/v1/empresas", headers=auth_headers,
        json={"razao_social": "Indicador Competencia LTDA", "nome_fantasia": "Indicador",
              "cnpj_matriz": "28.765.432/0001-02", "setor": "Indústria"},
    )
    assert emp.status_code == 201
    eid = emp.json()["id"]

    # Sem importação ainda → lista vazia (períodos sem registro não aparecem).
    vazio = client.get(f"/api/v1/importacao/dados/{eid}/competencias", headers=auth_headers)
    assert vazio.status_code == 200
    assert vazio.json() == []

    # Importa um CT-e (emitido em 2025-03-10) vinculado à matriz desta empresa.
    xml = CTE_XML.replace("12345678000195", "28765432000102").replace(
        "35200714200166000187570010000000031000000031",
        "35200714200166000187570010000000028000000028",
    )
    files = [("arquivos", ("cte_comp.xml", xml.encode("utf-8"), "application/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth_headers, files=files)
    assert imp.status_code == 200
    assert imp.json()["importados"] == 1

    # Atualização automática: a competência 03/2025 passa a aparecer.
    comp = client.get(f"/api/v1/importacao/dados/{eid}/competencias", headers=auth_headers)
    assert comp.status_code == 200
    dados = comp.json()
    assert len(dados) >= 1
    primeiro = dados[0]
    assert primeiro["ano"] == 2025 and primeiro["mes"] == 3
    assert primeiro["rotulo"] == "03/2025"
    assert primeiro["competencia"] == "2025-03"
    assert primeiro["quantidade"] >= 1
    # Ordenação do mais recente para o mais antigo.
    chaves = [(d["ano"], d["mes"]) for d in dados]
    assert chaves == sorted(chaves, reverse=True)
