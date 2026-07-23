"""Testes da importação de Referências de Corredor via Excel — tela Hubs
Logísticos > Parâmetros de Hubs (`benchmark_od_config.py`).

Independente da suíte de smoke HTTP — chama as funções de endpoint
diretamente (bypass de FastAPI DI/HTTP/auth), com sessão SQLAlchemy isolada
em SQLite em memória, mesmo padrão de ``test_v670_dimensao_cliente.py``.
"""
import asyncio
from io import BytesIO

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.domain.entities import HubLogistico
from app.infrastructure.database.models import EmpresaModel
from app.infrastructure.database.repositories import (
    BenchmarkCorredorRepository,
    EmpresaRepository,
    HubLogisticoRepository,
)
from app.presentation.api.v1.benchmark_od_config import (
    baixar_modelo_corredores,
    importar_corredores_excel,
)


# ─────────────────────────── fixtures ───────────────────────────

@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def empresa_id(db):
    emp = EmpresaModel(razao_social="Empresa Teste", cnpj_matriz="11222333000181", setor="Outros")
    db.add(emp)
    db.commit()
    return emp.id


@pytest.fixture()
def hubs(db, empresa_id):
    repo = HubLogisticoRepository(db)
    h1 = repo.create(HubLogistico(empresa_id=empresa_id, codigo="SUDESTE_HUB", nome="Sudeste", descricao="", ativo=True))
    h2 = repo.create(HubLogistico(empresa_id=empresa_id, codigo="NORDESTE_HUB", nome="Nordeste", descricao="", ativo=True))
    return h1, h2


class _FakeUpload:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self):
        return self._content


def _xlsx_bytes(header, linhas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for linha in linhas:
        ws.append(linha)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─────────────────────────── modelo ───────────────────────────

def test_baixar_modelo_gera_xlsx_valido(db, empresa_id):
    # Chegar a construir o StreamingResponse já prova que o workbook foi
    # montado e salvo em BytesIO sem erro (openpyxl não levanta exceção).
    resp = baixar_modelo_corredores(empresa_id)
    assert resp.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert resp.headers["content-disposition"] == "attachment; filename=modelo_corredores.xlsx"


# ─────────────────────────── importação ───────────────────────────

def test_importar_corredores_cria_novos(db, empresa_id, hubs):
    h1, h2 = hubs
    conteudo = _xlsx_bytes(
        ["hub_origem_codigo", "hub_destino_codigo", "frete_kg_min", "frete_kg_medio", "frete_kg_max",
         "frete_pct_min", "frete_pct_medio", "frete_pct_max", "volume_referencia", "dispersao_kg", "observacoes"],
        [["SUDESTE_HUB", "NORDESTE_HUB", 0.8, 1.2, 1.8, 3.0, 6.0, 12.0, 5000, 0.15, "via planilha"]],
    )
    resultado = asyncio.run(importar_corredores_excel(
        empresa_id, arquivo=_FakeUpload(conteudo),
        repo=BenchmarkCorredorRepository(db), hub_repo=HubLogisticoRepository(db),
        empresa_repo=EmpresaRepository(db),
    ))
    assert resultado == {"importados": 1, "atualizados": 0, "ignorados": 0}

    linhas = BenchmarkCorredorRepository(db).list(empresa_id)
    assert len(linhas) == 1
    assert linhas[0].hub_origem_codigo == "SUDESTE_HUB"
    assert linhas[0].hub_destino_codigo == "NORDESTE_HUB"
    assert linhas[0].frete_kg_medio == 1.2
    assert linhas[0].observacoes == "via planilha"


def test_importar_corredores_atualiza_existente_sem_duplicar(db, empresa_id, hubs):
    h1, h2 = hubs
    repo = BenchmarkCorredorRepository(db)
    from app.domain.entities import BenchmarkCorredor
    repo.upsert(BenchmarkCorredor(
        empresa_id=empresa_id, hub_origem_codigo="SUDESTE_HUB", hub_destino_codigo="NORDESTE_HUB",
        frete_kg_min=0.5, frete_kg_medio=0.7, frete_kg_max=1.0,
        frete_pct_min=1.0, frete_pct_medio=2.0, frete_pct_max=3.0,
        volume_referencia=100, dispersao_kg=0.1, observacoes="original",
    ))

    conteudo = _xlsx_bytes(
        ["hub_origem_codigo", "hub_destino_codigo", "frete_kg_medio"],
        [["SUDESTE_HUB", "NORDESTE_HUB", 9.9]],
    )
    resultado = asyncio.run(importar_corredores_excel(
        empresa_id, arquivo=_FakeUpload(conteudo),
        repo=repo, hub_repo=HubLogisticoRepository(db), empresa_repo=EmpresaRepository(db),
    ))
    assert resultado == {"importados": 0, "atualizados": 1, "ignorados": 0}

    linhas = repo.list(empresa_id)
    assert len(linhas) == 1  # não duplicou
    assert linhas[0].frete_kg_medio == 9.9  # atualizou o valor
    assert linhas[0].observacoes == ""  # colunas ausentes na planilha viram default, não preservam o valor antigo


def test_importar_corredores_ignora_hub_inexistente(db, empresa_id, hubs):
    conteudo = _xlsx_bytes(
        ["hub_origem_codigo", "hub_destino_codigo"],
        [["SUDESTE_HUB", "HUB_INEXISTENTE"], ["", "NORDESTE_HUB"]],
    )
    resultado = asyncio.run(importar_corredores_excel(
        empresa_id, arquivo=_FakeUpload(conteudo),
        repo=BenchmarkCorredorRepository(db), hub_repo=HubLogisticoRepository(db),
        empresa_repo=EmpresaRepository(db),
    ))
    assert resultado == {"importados": 0, "atualizados": 0, "ignorados": 2}
    assert BenchmarkCorredorRepository(db).list(empresa_id) == []


def test_importar_corredores_colunas_obrigatorias_ausentes(db, empresa_id, hubs):
    from fastapi import HTTPException
    conteudo = _xlsx_bytes(["hub_origem_codigo"], [["SUDESTE_HUB"]])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(importar_corredores_excel(
            empresa_id, arquivo=_FakeUpload(conteudo),
            repo=BenchmarkCorredorRepository(db), hub_repo=HubLogisticoRepository(db),
            empresa_repo=EmpresaRepository(db),
        ))
    assert exc.value.status_code == 400


def test_importar_corredores_arquivo_invalido(db, empresa_id):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        asyncio.run(importar_corredores_excel(
            empresa_id, arquivo=_FakeUpload(b"nao e um xlsx"),
            repo=BenchmarkCorredorRepository(db), hub_repo=HubLogisticoRepository(db),
            empresa_repo=EmpresaRepository(db),
        ))
    assert exc.value.status_code == 400
