"""Verificação ad hoc dos achados da auditoria de segurança (v6.5.0 -> v6.5.1).

Prova que um usuário comum da Empresa A NÃO consegue mais acessar/alterar
dados de BID, MCL, Transportadoras e Inteligência IA da Empresa B trocando
o empresa_id/ID na URL, e que um ADMIN de empresa não escala privilégio
via /usuarios. Roda com banco SQLite temporário isolado.
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, senha):
    r = client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _admin_headers(client):
    return _login(client, "admin@gdconecta.com.br", "admin123")


def _criar_empresa(client, nome, cnpj, admin_headers):
    r = client.post("/api/v1/empresas", json={
        "razao_social": nome, "nome_fantasia": nome, "cnpj_matriz": cnpj,
        "status": "ATIVO", "setor": "Outros",
    }, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _criar_usuario(client, email, senha, empresa_id, role, admin_headers):
    r = client.post("/api/v1/usuarios", json={
        "nome": email, "email": email, "senha": senha,
        "is_active": True, "is_superuser": False,
        "empresa_id": empresa_id, "role": role,
    }, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_isolamento_bid_mcl_transportadora_inteligencia_e_usuarios(client):
    admin = _admin_headers(client)
    empresa_a = _criar_empresa(client, "Empresa A Teste", "11444777000161", admin)
    empresa_b = _criar_empresa(client, "Empresa B Teste", "45723174000110", admin)

    _criar_usuario(client, "analista.a@teste.com", "Senha123", empresa_a, "ANALISTA", admin)
    user_a = _login(client, "analista.a@teste.com", "Senha123")

    admin_b = _criar_usuario(client, "admin.b@teste.com", "Senha123", empresa_b, "ADMIN", admin)
    headers_admin_b = _login(client, "admin.b@teste.com", "Senha123")

    # BID criado sob a Empresa B
    r = client.post("/api/v1/bid", params={"empresa_id": empresa_b}, json={
        "nome": "BID Empresa B", "descricao": "", "periodo_analise_inicio": None,
        "periodo_analise_fim": None,
    }, headers=headers_admin_b)
    assert r.status_code == 201, r.text
    bid_b_id = r.json()["id"]

    # Transportadora cadastrada sob a Empresa B
    r = client.post("/api/v1/transportadoras", params={"empresa_id": empresa_b}, json={
        "razao_social": "Transportadora B", "cnpj": "07526557000100",
    }, headers=headers_admin_b)
    assert r.status_code == 201, r.text
    transp_b_id = r.json()["id"]

    # ── Usuário da Empresa A tentando acessar recursos da Empresa B ──
    assert client.get(f"/api/v1/bid/{bid_b_id}", headers=user_a).status_code == 403
    assert client.get("/api/v1/bid", params={"empresa_id": empresa_b}, headers=user_a).status_code == 403
    assert client.delete(f"/api/v1/bid/{bid_b_id}", headers=user_a).status_code == 403
    assert client.get(f"/api/v1/bid/{bid_b_id}/propostas", headers=user_a).status_code == 403
    assert client.get(f"/api/v1/bid/{bid_b_id}/auditoria", headers=user_a).status_code == 403

    assert client.get(f"/api/v1/mcl/{bid_b_id}/decidir", headers=user_a).status_code == 403
    assert client.post(f"/api/v1/mcl/{bid_b_id}/decidir", headers=user_a).status_code == 403

    assert client.get(f"/api/v1/transportadoras/{transp_b_id}", headers=user_a).status_code == 403
    assert client.delete(f"/api/v1/transportadoras/{transp_b_id}", headers=user_a).status_code == 403

    assert client.get(
        "/api/v1/inteligencia/score", params={"empresa_id": empresa_b}, headers=user_a
    ).status_code == 403
    assert client.get(
        "/api/v1/inteligencia/insights", params={"empresa_id": empresa_b}, headers=user_a
    ).status_code == 403

    assert client.get(
        "/api/v1/benchmark-v2/observado", params={"empresa_id": empresa_b}, headers=user_a
    ).status_code == 403
    assert client.get(
        "/api/v1/benchmark-v2/indicadores-regionais", params={"empresa_id": empresa_b}, headers=user_a
    ).status_code == 403

    # ── Metas e matriz de mercado são globais (sem empresa_id) — leitura livre,
    #    mas escrita restrita a admin. Um ANALISTA não pode alterá-las. ──
    assert client.put(
        "/api/v1/metas/nacional", json={"meta_rs_kg": 1.0, "meta_pct_frete": 5.0}, headers=user_a
    ).status_code == 403
    assert client.put(
        "/api/v1/benchmark-v2/mercado",
        json={"origem_regiao": "SUDESTE", "destino_regiao": "SUL",
              "rs_kg_p50": 1.5},
        headers=user_a,
    ).status_code == 403

    # ── O dono legítimo (Empresa B) continua acessando normalmente ──
    assert client.get(f"/api/v1/bid/{bid_b_id}", headers=headers_admin_b).status_code == 200
    assert client.get(f"/api/v1/transportadoras/{transp_b_id}", headers=headers_admin_b).status_code == 200
    assert client.get(
        "/api/v1/inteligencia/score", params={"empresa_id": empresa_b}, headers=headers_admin_b
    ).status_code == 200

    # ── ADMIN da Empresa B não pode listar/editar usuários da Empresa A nem se autopromover ──
    lista = client.get("/api/v1/usuarios", headers=headers_admin_b).json()
    assert all(u["empresa_id"] == empresa_b for u in lista), "ADMIN de empresa viu usuário de outra empresa"

    user_a_id = [u for u in client.get("/api/v1/usuarios", headers=admin).json()
                 if u["email"] == "analista.a@teste.com"][0]["id"]
    r = client.put(f"/api/v1/usuarios/{user_a_id}", json={"nome": "Hackeado"}, headers=headers_admin_b)
    assert r.status_code == 403, "ADMIN de empresa conseguiu editar usuário de outra empresa"

    r = client.put(f"/api/v1/usuarios/{admin_b['id']}", json={"is_superuser": True}, headers=headers_admin_b)
    assert r.status_code == 403, "ADMIN de empresa conseguiu se autopromover a superusuário global"


def test_visualizador_e_somente_leitura(client):
    """VISUALIZADOR lê tudo normalmente, mas qualquer escrita retorna 403.
    ANALISTA, com a mesma empresa, continua podendo escrever."""
    admin = _admin_headers(client)
    empresa = _criar_empresa(client, "Empresa Visualizador Teste", "11222333001153", admin)

    _criar_usuario(client, "visualizador@teste.com", "Senha123", empresa, "VISUALIZADOR", admin)
    viewer = _login(client, "visualizador@teste.com", "Senha123")

    _criar_usuario(client, "analista.viz@teste.com", "Senha123", empresa, "ANALISTA", admin)
    analista = _login(client, "analista.viz@teste.com", "Senha123")

    # Leitura: liberada para o VISUALIZADOR
    assert client.get("/api/v1/bid", params={"empresa_id": empresa}, headers=viewer).status_code == 200
    assert client.get(
        "/api/v1/transportadoras", params={"empresa_id": empresa}, headers=viewer
    ).status_code == 200
    assert client.get(
        "/api/v1/inteligencia/insights", params={"empresa_id": empresa}, headers=viewer
    ).status_code == 200

    # Escrita: bloqueada (403) para o VISUALIZADOR em módulos variados
    assert client.post("/api/v1/bid", params={"empresa_id": empresa}, json={
        "nome": "BID Bloqueado", "descricao": "",
        "periodo_analise_inicio": None, "periodo_analise_fim": None,
    }, headers=viewer).status_code == 403

    assert client.post("/api/v1/transportadoras", params={"empresa_id": empresa}, json={
        "razao_social": "Transportadora Bloqueada", "cnpj": "11444777000161",
    }, headers=viewer).status_code == 403

    assert client.post(
        "/api/v1/inteligencia/insights/gerar", params={"empresa_id": empresa}, headers=viewer
    ).status_code == 403

    assert client.post(
        f"/api/v1/dlg/{empresa}/processar", headers=viewer
    ).status_code == 403

    assert client.post(
        f"/api/v1/mbl/{empresa}/processar", headers=viewer
    ).status_code == 403

    assert client.post(
        f"/api/v1/recomendacoes/{empresa}/consolidar", headers=viewer
    ).status_code == 403

    # A mesma escrita funciona normalmente para ANALISTA (não deve ficar mais restrito que antes)
    r = client.post("/api/v1/transportadoras", params={"empresa_id": empresa}, json={
        "razao_social": "Transportadora Permitida", "cnpj": "11444777000161",
    }, headers=analista)
    assert r.status_code == 201, r.text


def test_visualizador_pode_usar_acoes_que_nao_persistem(client):
    """calcular_simulacao, mcl/simular e rag/buscar não gravam dado algum —
    ficam abertos mesmo para VISUALIZADOR (não são 'escrita')."""
    admin = _admin_headers(client)
    empresa = _criar_empresa(client, "Empresa Simulacao Viz", "07526557000100", admin)
    _criar_usuario(client, "visualizador2@teste.com", "Senha123", empresa, "VISUALIZADOR", admin)
    viewer = _login(client, "visualizador2@teste.com", "Senha123")

    r = client.post("/api/v1/bid", params={"empresa_id": empresa}, json={
        "nome": "BID Simulacao", "descricao": "",
        "periodo_analise_inicio": None, "periodo_analise_fim": None,
    }, headers=admin)
    assert r.status_code == 201, r.text
    bid_id = r.json()["id"]

    r = client.post(
        f"/api/v1/bid/{bid_id}/simulacoes/calcular",
        json={"nome": "prevista", "descricao": "", "itens": []},
        headers=viewer,
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/api/v1/mcl/{bid_id}/simular", json={"variacao_preco_pct": 0.0}, headers=viewer)
    assert r.status_code in (200, 400), r.text  # 400 = sem dados suficientes, não é bloqueio de permissão

    r = client.post(
        "/api/v1/inteligencia/rag/buscar",
        params={"empresa_id": empresa}, json={"consulta": "frete", "top_k": 2},
        headers=viewer,
    )
    assert r.status_code == 200, r.text


def test_atualizar_usuario_sem_senha_nao_zera_hash(client):
    """Regressão: PUT /usuarios/{id} sem `senha` não pode invalidar o login."""
    admin = _admin_headers(client)
    empresa = _criar_empresa(client, "Empresa Senha Teste", "12345678000195", admin)
    novo = _criar_usuario(client, "usuario.senha@teste.com", "Senha123", empresa, "ANALISTA", admin)

    r = client.put(f"/api/v1/usuarios/{novo['id']}", json={"nome": "Nome Atualizado"}, headers=admin)
    assert r.status_code == 200, r.text

    # login com a senha original ainda precisa funcionar
    r = client.post("/api/v1/auth/login", data={
        "username": "usuario.senha@teste.com", "password": "Senha123",
    })
    assert r.status_code == 200, f"Login quebrou após update sem senha: {r.text}"
