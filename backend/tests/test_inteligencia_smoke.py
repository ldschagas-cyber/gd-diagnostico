"""Testes de fumaça do módulo Inteligência Logística (V4).

Valida o fluxo completo em modo simulado:
- Status da IA
- Score logístico
- Insights automáticos
- Diagnóstico IA
- Oportunidades
- Benchmark setorial
- Assistente com tool-calling
- Dashboard e consumo
- Isolamento multi-empresa

Rodar isolado:  pytest tests/test_inteligencia_smoke.py -v
(Conflito conhecido de DATABASE_URL em nível de módulo: rodar separado das
outras suites, como já documentado para test_smoke.py e test_bid_smoke.py.)
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/v1/auth/login",
                    data={"username": "admin@gdconecta.com.br", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def empresa_id(client, auth):
    r = client.post("/api/v1/empresas", headers=auth,
                    json={"razao_social": "Empresa Teste IA", "nome_fantasia": "IA",
                          "cnpj_matriz": "33.888.888/0001-08", "setor": "Indústria"})
    assert r.status_code in (200, 201)
    return r.json()["id"]


def test_status_ia(client, auth):
    r = client.get("/api/v1/inteligencia/status", headers=auth)
    assert r.status_code == 200
    assert "modo_simulado" in r.json()


def test_score(client, auth, empresa_id):
    r = client.post(f"/api/v1/inteligencia/score/calcular?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["score_total"] <= 100
    assert "componentes" in body


def test_insights(client, auth, empresa_id):
    r = client.post(f"/api/v1/inteligencia/insights/gerar?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    r = client.get(f"/api/v1/inteligencia/insights?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_diagnostico(client, auth, empresa_id):
    r = client.post(f"/api/v1/inteligencia/diagnostico/gerar?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert "resumo_executivo" in r.json()
    assert "(simulado)" in r.json()["modelo_usado"]


def test_oportunidades(client, auth, empresa_id):
    r = client.post(f"/api/v1/inteligencia/oportunidades/detectar?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    r = client.get(f"/api/v1/inteligencia/oportunidades?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200


def test_benchmark_setorial(client, auth, empresa_id):
    r = client.get(f"/api/v1/inteligencia/benchmark-setorial?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert len(r.json()["comparativo"]) == 6  # 6 segmentos


def test_assistente_tool_calling(client, auth, empresa_id):
    r = client.post(f"/api/v1/inteligencia/assistente/sessoes?empresa_id={empresa_id}",
                    headers=auth, json={"titulo": "Teste"})
    sid = r.json()["id"]
    r = client.post(f"/api/v1/inteligencia/assistente/sessoes/{sid}/mensagens?empresa_id={empresa_id}",
                    headers=auth, json={"mensagem": "Qual minha transportadora mais cara?"})
    assert r.status_code == 200
    # No modo simulado, a ferramenta é escolhida pela heurística
    assert "calls" in r.json()["ferramentas_usadas"]


def test_dashboard(client, auth, empresa_id):
    r = client.get(f"/api/v1/inteligencia/dashboard?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert "score_logistico" in r.json()


def test_uso_custo(client, auth, empresa_id):
    r = client.get(f"/api/v1/inteligencia/uso?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert "custo_brl_total" in r.json()


def test_isolamento_multiempresa(client, auth, empresa_id):
    """Cria 2a empresa e garante que insights não vazam entre empresas."""
    r = client.post("/api/v1/empresas", headers=auth,
                    json={"razao_social": "Empresa 2", "nome_fantasia": "E2",
                          "cnpj_matriz": "11.222.333/0001-81", "setor": "Indústria"})
    eid2 = r.json()["id"]
    # Gera insights só para a empresa 2
    client.post(f"/api/v1/inteligencia/insights/gerar?empresa_id={eid2}", headers=auth)
    # Lista da empresa 1 não deve conter insights da empresa 2
    r1 = client.get(f"/api/v1/inteligencia/insights?empresa_id={empresa_id}", headers=auth)
    r2 = client.get(f"/api/v1/inteligencia/insights?empresa_id={eid2}", headers=auth)
    assert r1.status_code == 200 and r2.status_code == 200
    # IDs não se sobrepõem (isolamento)
    ids1 = {i["id"] for i in r1.json()}
    ids2 = {i["id"] for i in r2.json()}
    assert ids1.isdisjoint(ids2)


def test_rag_seed_e_busca(client, auth, empresa_id):
    """Indexa legislação ANTT e valida a busca semântica."""
    r = client.post("/api/v1/inteligencia/rag/seed-legislacao", headers=auth)
    assert r.status_code == 200
    r = client.post(f"/api/v1/inteligencia/rag/buscar?empresa_id={empresa_id}",
                    headers=auth, json={"consulta": "piso minimo de frete ANTT", "top_k": 2})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rag_isolamento(client, auth, empresa_id):
    """Documento de uma empresa não aparece para outra."""
    # Indexa benchmark na empresa 1
    client.post(f"/api/v1/inteligencia/rag/documentos?empresa_id={empresa_id}", headers=auth,
                json={"tipo_documento": "benchmark", "titulo": "Benchmark Confidencial E1",
                      "conteudo": "Dado sensível da empresa 1 sobre frete."})
    # Cria empresa 3 e busca
    r = client.post("/api/v1/empresas", headers=auth,
                    json={"razao_social": "Empresa 3", "nome_fantasia": "E3",
                          "cnpj_matriz": "55.666.777/0001-81", "setor": "Indústria"})
    eid3 = r.json()["id"]
    r = client.post(f"/api/v1/inteligencia/rag/buscar?empresa_id={eid3}", headers=auth,
                    json={"consulta": "benchmark confidencial", "top_k": 5})
    assert r.status_code == 200
    # Nenhum resultado deve pertencer à empresa 1
    vazamento = [d for d in r.json() if d.get("empresa_id") == empresa_id]
    assert len(vazamento) == 0


def test_relatorio_executivo_pdf(client, auth, empresa_id):
    """Gera relatório executivo em PDF e valida a assinatura do arquivo."""
    client.post(f"/api/v1/inteligencia/diagnostico/gerar?empresa_id={empresa_id}", headers=auth)
    r = client.get(f"/api/v1/inteligencia/relatorio/pdf?empresa_id={empresa_id}", headers=auth)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_relatorio_executivo_word_pptx(client, auth, empresa_id):
    """Gera Word e PowerPoint (assinatura ZIP/PK do OOXML)."""
    for fmt in ("word", "powerpoint"):
        r = client.get(f"/api/v1/inteligencia/relatorio/{fmt}?empresa_id={empresa_id}", headers=auth)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"
