"""Verifica a migração do JWT para cookies httpOnly (mitigação de S-04).

Cobre:
  - login grava cookies httpOnly de access e refresh
  - uma chamada autenticada funciona SÓ com o cookie, sem header Authorization
  - /auth/refresh funciona lendo o refresh token do cookie (sem corpo)
  - /auth/logout limpa os cookies (a chamada seguinte volta a exigir login)
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.security import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_login_grava_cookies_httponly(client):
    r = client.post("/api/v1/auth/login", data={
        "username": "admin@gdconecta.com.br", "password": "admin123",
    })
    assert r.status_code == 200

    access_cookie = next((c for c in client.cookies.jar if c.name == ACCESS_COOKIE_NAME), None)
    refresh_cookie = next((c for c in client.cookies.jar if c.name == REFRESH_COOKIE_NAME), None)
    assert access_cookie is not None, "cookie de access não foi definido no login"
    assert refresh_cookie is not None, "cookie de refresh não foi definido no login"
    # httpOnly precisa estar marcado — é o que impede leitura via JS (mitigação de XSS)
    assert access_cookie.has_nonstandard_attr("HttpOnly") or access_cookie._rest.get("HttpOnly") is not None
    assert refresh_cookie.path.startswith("/api/v1/auth"), "cookie de refresh deveria ter path restrito a /auth"


def test_chamada_autenticada_funciona_so_com_cookie_sem_header(client):
    client.post("/api/v1/auth/login", data={
        "username": "admin@gdconecta.com.br", "password": "admin123",
    })
    # nenhum header Authorization — só o cookie que o TestClient já guarda
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "admin@gdconecta.com.br"


def test_refresh_le_cookie_sem_precisar_de_corpo(client):
    client.post("/api/v1/auth/login", data={
        "username": "admin@gdconecta.com.br", "password": "admin123",
    })
    r = client.post("/api/v1/auth/refresh")  # sem body — refresh vem do cookie
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_logout_limpa_cookies_e_revoga_acesso(client):
    client.post("/api/v1/auth/login", data={
        "username": "admin@gdconecta.com.br", "password": "admin123",
    })
    assert client.get("/api/v1/auth/me").status_code == 200

    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 204

    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401, "logout deveria invalidar o acesso via cookie"
