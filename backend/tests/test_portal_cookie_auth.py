"""Autenticação do Portal do Cliente (v6.18.0) — cookies próprios, isolados
da sessão interna.

Cobre:
  - login do Portal grava cookies httpOnly com nomes DISTINTOS dos internos
  - uma chamada autenticada do Portal funciona só com o cookie do Portal
  - /portal/auth/refresh lê o refresh do cookie do Portal
  - /portal/auth/logout limpa só os cookies do Portal
  - um token de cliente NUNCA autentica uma rota interna (GET /auth/me), e
    o token interno do admin NUNCA autentica uma rota do Portal
    (Especificação Técnica v6.18.0 §3.3)
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import (  # noqa: E402
    ACCESS_COOKIE_NAME,
    CLIENTE_ACCESS_COOKIE_NAME,
    CLIENTE_REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    hash_password,
)
from app.infrastructure.database.models import ClientePortalUserModel  # noqa: E402
from app.main import app  # noqa: E402

CLIENTE_EMAIL = "diretoria@clientepiloto.com.br"
CLIENTE_SENHA = "Cliente@123"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _admin_headers(client):
    r = client.post("/api/v1/auth/login", data={"username": "admin@gdconecta.com.br", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def empresa_id(client):
    admin = _admin_headers(client)
    r = client.post("/api/v1/empresas", json={
        "razao_social": "Cliente Piloto Portal Teste", "nome_fantasia": "Cliente Piloto",
        "cnpj_matriz": "11444777000161", "status": "ATIVO", "setor": "Outros",
    }, headers=admin)
    assert r.status_code == 201, r.text
    empresa_id = r.json()["id"]

    # Provisionamento do usuário-cliente é manual (script), sem endpoint de
    # API — insere direto, mesmo caminho de scripts/seed_portal_cliente_piloto.py.
    db = SessionLocal()
    try:
        db.add(ClientePortalUserModel(
            empresa_id=empresa_id, nome="Diretoria Cliente Piloto", email=CLIENTE_EMAIL,
            hashed_password=hash_password(CLIENTE_SENHA), ativo=True,
        ))
        db.commit()
    finally:
        db.close()
    return empresa_id


def test_login_grava_cookies_com_nomes_distintos_dos_internos(client, empresa_id):
    r = client.post("/api/v1/portal/auth/login", data={"username": CLIENTE_EMAIL, "password": CLIENTE_SENHA})
    assert r.status_code == 200, r.text

    # Só os cookies que ESTA resposta gravou — não o jar inteiro do client, que
    # já carrega o cookie interno do admin usado pela fixture `empresa_id`
    # para cadastrar a empresa via API antes deste teste rodar.
    gravados = {c.name for c in r.cookies.jar}
    assert CLIENTE_ACCESS_COOKIE_NAME in gravados
    assert CLIENTE_REFRESH_COOKIE_NAME in gravados
    assert ACCESS_COOKIE_NAME not in gravados, "login do Portal não deve gravar o cookie interno"
    assert REFRESH_COOKIE_NAME not in gravados


def test_chamada_autenticada_funciona_so_com_cookie_do_portal(client, empresa_id):
    client.post("/api/v1/portal/auth/login", data={"username": CLIENTE_EMAIL, "password": CLIENTE_SENHA})
    r = client.get("/api/v1/portal/auth/me")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == CLIENTE_EMAIL
    assert r.json()["empresa_id"] == empresa_id


def test_refresh_do_portal_le_cookie_proprio(client, empresa_id):
    client.post("/api/v1/portal/auth/login", data={"username": CLIENTE_EMAIL, "password": CLIENTE_SENHA})
    r = client.post("/api/v1/portal/auth/refresh")
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_logout_do_portal_revoga_so_a_sessao_do_portal(client, empresa_id):
    client.post("/api/v1/portal/auth/login", data={"username": CLIENTE_EMAIL, "password": CLIENTE_SENHA})
    assert client.get("/api/v1/portal/auth/me").status_code == 200
    r = client.post("/api/v1/portal/auth/logout")
    assert r.status_code == 204
    assert client.get("/api/v1/portal/auth/me").status_code == 401


def test_token_de_cliente_nunca_autentica_rota_interna(client, empresa_id):
    r = client.post("/api/v1/portal/auth/login", data={"username": CLIENTE_EMAIL, "password": CLIENTE_SENHA})
    token_cliente = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_cliente}"})
    assert r.status_code == 401, "token do Portal não pode autenticar uma rota interna"


def test_token_interno_nunca_autentica_rota_do_portal(client, empresa_id):
    admin = _admin_headers(client)
    token_interno = admin["Authorization"].split(" ", 1)[1]

    r = client.get("/api/v1/portal/auth/me", headers={"Authorization": f"Bearer {token_interno}"})
    assert r.status_code == 401, "token interno não pode autenticar uma rota do Portal"
