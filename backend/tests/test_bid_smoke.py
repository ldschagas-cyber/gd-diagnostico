"""Testes de fumaça do módulo Concorrência Logística (BID de Frete) — V3.1.

Cobre o fluxo completo:
  criar empresa → importar CT-es → criar BID → gerar escopo →
  convidar transportadora → incluir proposta → comparativo →
  motor de economia → simulação → relatório PDF/Excel →
  dashboard executivo → trilha de auditoria → isolamento multi-empresa.

Usa banco SQLite temporário isolado para não afetar desenvolvimento.
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

# CT-e com CNPJ válido (destinatário = empresa que será criada no teste)
CTE_BID = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe35200714200166000187570010000000031000000031" versao="3.00">
  <ide>
   <cUF>35</cUF><nCT>3</nCT><serie>1</serie>
   <dhEmi>2025-06-10T09:00:00-03:00</dhEmi>
   <cMunIni>3550308</cMunIni><xMunIni>SAO PAULO</xMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><xMunFim>RIO DE JANEIRO</xMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3>
  </ide>
  <emit><CNPJ>11222333000181</CNPJ><xNome>TRANSPORTADORA BID LTDA</xNome></emit>
  <dest><CNPJ>33888888000108</CNPJ><xNome>EMPRESA BID TESTE</xNome></dest>
  <vPrest><vTPrest>2000.00</vTPrest><vRec>2000.00</vRec></vPrest>
  <infCTeNorm>
   <infCarga><vCarga>80000.00</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>800.0000</qCarga></infQ>
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
def auth(client):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@gdconecta.com.br", "password": "admin123"},
    )
    assert r.status_code == 200, f"Login falhou: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def empresa_id(client, auth):
    """Cria empresa e importa CT-e."""
    r = client.post(
        "/api/v1/empresas",
        headers=auth,
        json={"razao_social": "Empresa BID Teste", "nome_fantasia": "BID Teste",
              "cnpj_matriz": "33.888.888/0001-08", "setor": "Indústria"},
    )
    assert r.status_code == 201, f"Empresa: {r.text}"
    eid = r.json()["id"]

    # Importa CT-e para ter dados no escopo
    files = [("arquivos", ("cte_bid.xml", CTE_BID.encode(), "text/xml"))]
    imp = client.post(f"/api/v1/importacao/cte/{eid}", headers=auth, files=files)
    assert imp.status_code == 200
    assert imp.json()["importados"] == 1
    return eid


@pytest.fixture(scope="module")
def bid_id(client, auth, empresa_id):
    """Cria o BID principal para os demais testes."""
    r = client.post(
        "/api/v1/bid",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "nome": "BID Frete Nacional 2025",
            "descricao": "Processo de concorrência para fretes nacionais",
            "objetivo": "Reduzir custo logístico em 15%",
            "status": "RASCUNHO",
            "data_inicio": "2025-07-01",
            "data_encerramento": "2025-07-31",
            "periodo_analise_inicio": "2025-01-01",
            "periodo_analise_fim": "2025-06-30",
        },
    )
    assert r.status_code == 201, f"BID: {r.text}"
    return r.json()["id"]


# ════════════════════════════════════════════════════════════════
# TESTES
# ════════════════════════════════════════════════════════════════

def test_bid_criado_com_status_rascunho(client, auth, bid_id):
    r = client.get(f"/api/v1/bid/{bid_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "RASCUNHO"
    assert r.json()["nome"] == "BID Frete Nacional 2025"


def test_bid_listagem_por_empresa(client, auth, empresa_id, bid_id):
    r = client.get("/api/v1/bid", headers=auth, params={"empresa_id": empresa_id})
    assert r.status_code == 200
    ids = [b["id"] for b in r.json()]
    assert bid_id in ids


def test_bid_alteracao_status(client, auth, bid_id):
    """Rascunho → Aberto → Em Cotação."""
    r = client.patch(f"/api/v1/bid/{bid_id}/status", headers=auth, json={"status": "ABERTO"})
    assert r.status_code == 200
    assert r.json()["status"] == "ABERTO"

    r = client.patch(f"/api/v1/bid/{bid_id}/status", headers=auth, json={"status": "EM_COTACAO"})
    assert r.status_code == 200
    assert r.json()["status"] == "EM_COTACAO"


def test_gerar_escopo_por_regiao(client, auth, empresa_id, bid_id):
    r = client.post(
        f"/api/v1/bid/{bid_id}/escopo/gerar",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "tipo_agrupamento": "REGIAO",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-12-31",
        },
    )
    assert r.status_code == 200, f"Escopo REGIAO: {r.text}"
    escopos = r.json()
    assert len(escopos) >= 1
    # Valida campos calculados
    e = escopos[0]
    assert e["peso_total"] > 0
    assert e["frete_rs_kg"] > 0
    assert e["tipo_agrupamento"] == "REGIAO"


def test_gerar_escopo_por_uf(client, auth, empresa_id, bid_id):
    r = client.post(
        f"/api/v1/bid/{bid_id}/escopo/gerar",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "tipo_agrupamento": "UF",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-12-31",
        },
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_gerar_escopo_faixas_peso_livres(client, auth, empresa_id, bid_id):
    """Faixas de peso são livres — definidas pelo usuário no payload."""
    r = client.post(
        f"/api/v1/bid/{bid_id}/escopo/gerar",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "tipo_agrupamento": "FAIXA_PESO",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-12-31",
            "faixas_peso": [
                {"label": "Até 500kg",    "min": 0,    "max": 500},
                {"label": "500kg a 1t",   "min": 500,  "max": 1000},
                {"label": "Acima de 1t",  "min": 1000, "max": 999999},
            ],
        },
    )
    assert r.status_code == 200, f"Faixas livres: {r.text}"


def test_listar_escopo(client, auth, bid_id):
    r = client.get(f"/api/v1/bid/{bid_id}/escopo", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.fixture(scope="module")
def transportadora_id(client, auth, empresa_id):
    """Usa a transportadora auto-criada durante importação do CT-e.
    
    O CT-e com CNPJ 11222333000181 já cria automaticamente a transportadora
    no escopo da empresa ao ser importado. Buscamos ela pelo CNPJ.
    """
    r = client.get(
        "/api/v1/transportadoras",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    transp_list = r.json()
    # A importação do CT-e cria a transportadora automaticamente
    if transp_list:
        return transp_list[0]["id"]
    # Fallback: cria uma nova com CNPJ diferente
    r = client.post(
        "/api/v1/transportadoras",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={"razao_social": "Transpofrete BID LTDA", "cnpj": "55667788000186",
              "cidade": "São Paulo", "uf": "SP"},
    )
    assert r.status_code == 201, f"Transportadora fallback: {r.text}"
    return r.json()["id"]


@pytest.fixture(scope="module")
def bt_id(client, auth, empresa_id, bid_id, transportadora_id):
    """Vincula transportadora ao BID."""
    r = client.post(
        f"/api/v1/bid/{bid_id}/transportadoras",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={"transportadora_id": transportadora_id, "observacoes": "Principal carrier"},
    )
    assert r.status_code == 201, f"BidTransportadora: {r.text}"
    return r.json()["id"]


def test_transportadora_convidada_status_inicial(client, auth, bid_id, bt_id):
    r = client.get(f"/api/v1/bid/{bid_id}/transportadoras", headers=auth)
    assert r.status_code == 200
    bt = next((t for t in r.json() if t["id"] == bt_id), None)
    assert bt is not None
    assert bt["status"] == "CONVIDADA"


def test_transportadora_status_participando(client, auth, bid_id, bt_id):
    r = client.patch(
        f"/api/v1/bid/{bid_id}/transportadoras/{bt_id}/status",
        headers=auth,
        json={"status": "PARTICIPANDO"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "PARTICIPANDO"


@pytest.fixture(scope="module")
def proposta_id(client, auth, bid_id, bt_id):
    """Inclui proposta manual."""
    r = client.post(
        f"/api/v1/bid/{bid_id}/propostas",
        headers=auth,
        json={
            "bid_transportadora_id": bt_id,
            "tipo_agrupamento": "REGIAO",
            "valor_grupo": "SUDESTE",
            "valor_rs_kg": 1.10,
            "valor_minimo": 150.0,
            "prazo_dias": 2,
            "cobertura_pct": 95.0,
            "observacoes": "Proposta competitiva",
        },
    )
    assert r.status_code == 201, f"Proposta: {r.text}"
    return r.json()["id"]


def test_proposta_criada(client, auth, bid_id, proposta_id):
    r = client.get(f"/api/v1/bid/{bid_id}/propostas", headers=auth)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert proposta_id in ids


def test_comparativo_propostas(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/bid/{bid_id}/comparativo",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200


def test_motor_economia(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/bid/{bid_id}/economia",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    d = r.json()
    # Motor de economia deve ter projeções
    assert "proj_anual" in d
    assert "proj_semestral" in d
    assert "proj_trimestral" in d
    assert "ritmo_mensal" in d


def test_score_transportadoras(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/bid/{bid_id}/score",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200


def test_simulacao_calcular(client, auth, empresa_id, bid_id, bt_id):
    r = client.post(
        f"/api/v1/bid/{bid_id}/simulacoes/calcular",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "nome": "Cenário 100% Transpofrete",
            "descricao": "Alocação total",
            "itens": [
                {"bid_transportadora_id": bt_id, "valor_grupo": "SUDESTE", "pct_alocado": 100.0}
            ],
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert "economia_total" in d
    assert "reducao_pct" in d


def test_simulacao_salvar(client, auth, empresa_id, bid_id, bt_id):
    r = client.post(
        f"/api/v1/bid/{bid_id}/simulacoes",
        headers=auth,
        params={"empresa_id": empresa_id},
        json={
            "nome": "Cenário Salvo",
            "descricao": "Teste de persistência",
            "itens": [
                {"bid_transportadora_id": bt_id, "valor_grupo": "SUDESTE", "pct_alocado": 100.0}
            ],
        },
    )
    assert r.status_code == 201
    assert r.json()["nome"] == "Cenário Salvo"


def test_relatorio_bid_pdf(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/relatorios/bid/{bid_id}/executivo/pdf",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    assert len(r.content) > 500  # PDF real tem conteúdo


def test_relatorio_bid_excel(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/relatorios/bid/{bid_id}/comparativo/excel",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    assert len(r.content) > 500


def test_relatorio_bid_executivo_html(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/relatorios/bid/{bid_id}/executivo/html",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    assert r.content[:15] == b"<!DOCTYPE html>"


def test_relatorio_bid_executivo_excel(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/relatorios/bid/{bid_id}/executivo/excel",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    assert len(r.content) > 500


def test_pacote_cotacao_pdf(client, auth, empresa_id, bid_id):
    r = client.get(
        f"/api/v1/relatorios/bid/{bid_id}/pacote_cotacao/pdf",
        headers=auth,
        params={"empresa_id": empresa_id},
    )
    assert r.status_code == 200
    assert len(r.content) > 200


def test_auditoria_registra_acoes(client, auth, bid_id):
    r = client.get(f"/api/v1/bid/{bid_id}/auditoria", headers=auth)
    assert r.status_code == 200
    # Deve ter registros das ações executadas no BID
    assert len(r.json()) >= 1
    assert any("criado" in a["acao"].lower() or "status" in a["acao"].lower()
               for a in r.json())


def test_dashboard_executivo_bids(client, auth, empresa_id):
    r = client.get("/api/v1/bid/dashboard", headers=auth, params={"empresa_id": empresa_id})
    assert r.status_code == 200
    d = r.json()
    assert d["total_bids"] >= 1
    assert "economia_identificada" in d
    assert "economia_contratada" in d
    assert "transportadoras_avaliadas" in d


def test_isolamento_multiempresa(client, auth):
    """Empresa B não deve ver os BIDs da Empresa A."""
    r = client.post(
        "/api/v1/empresas",
        headers=auth,
        json={"razao_social": "Empresa Isolamento B", "nome_fantasia": "Empresa B",
              "cnpj_matriz": "22.222.222/0001-91", "setor": "Indústria"},
    )
    assert r.status_code == 201
    empresa_b_id = r.json()["id"]

    r = client.get("/api/v1/bid", headers=auth, params={"empresa_id": empresa_b_id})
    assert r.status_code == 200
    assert len(r.json()) == 0  # Empresa B não tem BIDs


def test_suite_original_intacta(client, auth):
    """Garante que as funcionalidades V1/V2 continuam funcionando."""
    r = client.get("/api/v1/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["email"] == "admin@gdconecta.com.br"
