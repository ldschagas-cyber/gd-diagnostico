"""Isolamento por empresa no Portal do Cliente (v6.18.0).

Diferente do padrão interno (empresa_id vem do path, checado contra
`usuario.empresas_ids`), o Portal nunca recebe empresa_id de path/query —
todo endpoint usa `current_user.empresa_id`, resolvido só do token
(Especificação Técnica v6.18.0 §3.4). Este teste prova que dois usuários-
cliente de empresas diferentes nunca veem, nem conseguem manipular, dado um
do outro — inclusive tentando "priorizar" uma oportunidade que não é da
própria empresa.
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.infrastructure.database.models import ClientePortalUserModel, RecomendacaoModel  # noqa: E402
from app.main import app  # noqa: E402

SENHA = "Cliente@123"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _admin_headers(client):
    r = client.post("/api/v1/auth/login", data={"username": "admin@gdconecta.com.br", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _criar_empresa(client, nome, cnpj, admin):
    r = client.post("/api/v1/empresas", json={
        "razao_social": nome, "nome_fantasia": nome, "cnpj_matriz": cnpj,
        "status": "ATIVO", "setor": "Outros",
    }, headers=admin)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _criar_cliente_portal(empresa_id, email, nome="Diretoria"):
    db = SessionLocal()
    try:
        db.add(ClientePortalUserModel(
            empresa_id=empresa_id, nome=nome, email=email,
            hashed_password=hash_password(SENHA), ativo=True,
        ))
        db.commit()
    finally:
        db.close()


def _criar_recomendacao(empresa_id, titulo, economia=1000.0):
    db = SessionLocal()
    try:
        rec = RecomendacaoModel(
            empresa_id=empresa_id, titulo=titulo, descricao="", indicador="TESTE",
            chave_origem=f"teste-{empresa_id}-{titulo}", economia_estimada=economia,
            prioridade="ALTA", status="ABERTA",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id
    finally:
        db.close()


def _login_portal(client, email):
    r = client.post("/api/v1/portal/auth/login", data={"username": email, "password": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def cenario(client):
    admin = _admin_headers(client)
    empresa_a = _criar_empresa(client, "Empresa Portal A", "11444777000161", admin)
    empresa_b = _criar_empresa(client, "Empresa Portal B", "45723174000110", admin)

    _criar_cliente_portal(empresa_a, "cliente.a@teste.com")
    _criar_cliente_portal(empresa_b, "cliente.b@teste.com")

    rec_a_id = _criar_recomendacao(empresa_a, "Renegociar Transportadora — Empresa A")
    rec_b_id = _criar_recomendacao(empresa_b, "Renegociar Transportadora — Empresa B")

    return {
        "empresa_a": empresa_a, "empresa_b": empresa_b,
        "rec_a_id": rec_a_id, "rec_b_id": rec_b_id,
    }


def test_dashboard_reflete_a_propria_empresa(client, cenario):
    headers_a = _login_portal(client, "cliente.a@teste.com")
    r = client.get("/api/v1/portal/dashboard", headers=headers_a)
    assert r.status_code == 200, r.text
    assert r.json()["empresa_nome"] == "Empresa Portal A"


def test_oportunidades_de_a_nunca_incluem_recomendacao_de_b(client, cenario):
    headers_a = _login_portal(client, "cliente.a@teste.com")
    r = client.get("/api/v1/portal/oportunidades", headers=headers_a)
    assert r.status_code == 200, r.text
    ids = {item["id"] for item in r.json()}
    assert cenario["rec_a_id"] in ids
    assert cenario["rec_b_id"] not in ids


def test_priorizar_oportunidade_de_outra_empresa_e_404(client, cenario):
    headers_a = _login_portal(client, "cliente.a@teste.com")
    r = client.patch(f"/api/v1/portal/oportunidades/{cenario['rec_b_id']}/priorizar", headers=headers_a)
    assert r.status_code == 404, "usuário da Empresa A não pode priorizar recomendação da Empresa B"


def test_priorizar_a_propria_oportunidade_funciona_e_e_idempotente_no_toggle(client, cenario):
    headers_a = _login_portal(client, "cliente.a@teste.com")
    r1 = client.patch(f"/api/v1/portal/oportunidades/{cenario['rec_a_id']}/priorizar", headers=headers_a)
    assert r1.status_code == 200, r1.text
    assert r1.json()["priorizada_pelo_cliente"] is True

    r2 = client.patch(f"/api/v1/portal/oportunidades/{cenario['rec_a_id']}/priorizar", headers=headers_a)
    assert r2.status_code == 200, r2.text
    assert r2.json()["priorizada_pelo_cliente"] is False, "segundo clique deve desfazer (toggle)"
