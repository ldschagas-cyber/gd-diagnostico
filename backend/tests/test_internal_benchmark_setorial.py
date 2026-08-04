"""Testes do endpoint interno /internal/benchmark-setorial — consumido pelo CRM
(Inteligência Comercial na Pesquisa de Leads). Autenticação por chave estática,
não por JWT de usuário — ver `verify_internal_api_key`.

Mesmo padrão de banco temporário isolado de `test_smoke.py`.
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ENDPOINT = "/api/v1/internal/benchmark-setorial"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_sem_header_e_401(client):
    resp = client.get(ENDPOINT)
    assert resp.status_code == 401


def test_header_errado_e_401(client):
    resp = client.get(ENDPOINT, headers={"X-Internal-Api-Key": "chave-errada"})
    assert resp.status_code == 401


def test_header_correto_retorna_segmentos_seedados(client):
    resp = client.get(ENDPOINT, headers={"X-Internal-Api-Key": "test-internal-key"})
    assert resp.status_code == 200
    dados = resp.json()
    segmentos = {linha["segmento"] for linha in dados}
    assert segmentos == {"INDUSTRIA", "DISTRIBUIDOR", "ATACADISTA", "VAREJO", "ECOMMERCE", "AGRONEGOCIO"}
    distribuidor = next(linha for linha in dados if linha["segmento"] == "DISTRIBUIDOR")
    assert distribuidor["segmento_rotulo"] == "Distribuidor"
    assert distribuidor["frete_kg_medio"] == 0.55
