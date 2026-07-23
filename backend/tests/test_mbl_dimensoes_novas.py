"""Testes das novas dimensões do Benchmark Interno (MBL) — Transportadora,
Filial e Cliente — incluindo corte de cardinalidade (top-N) e busca por
segmento (``segmento_contains``).

Independente da suíte de smoke HTTP — usa sessão SQLAlchemy isolada em SQLite
em memória, mesmo padrão de ``test_v670_dimensao_cliente.py``.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.infrastructure.database.models import (
    CTeModel,
    EmpresaModel,
    FilialModel,
    MblBenchmarkModel,
    TransportadoraModel,
)
from app.application.use_cases.mbl import MblUseCase


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


def _cte(empresa_id, **kw):
    base = dict(
        empresa_id=empresa_id, chave=kw.pop("chave"),
        data_emissao=kw.pop("data_emissao", date(2026, 3, 10)),
        peso=100.0, valor_frete=500.0, valor_mercadoria=5000.0,
        uf_origem="SP", uf_destino="RJ", macro_regiao_destino="SUDESTE",
        status="ATIVO",
    )
    base.update(kw)
    return CTeModel(**base)


# ─────────────────── Transportadora / Filial: resolução por mapa ───────────────────

def test_dimensoes_transportadora_e_filial_geradas(db, empresa_id):
    transp = TransportadoraModel(empresa_id=empresa_id, razao_social="Transportes X",
                                  nome_fantasia="TransX", cnpj="10000000000100")
    filial = FilialModel(empresa_id=empresa_id, razao_social="Filial SP",
                          cnpj="20000000000100", cidade="São Paulo", uf="SP")
    db.add_all([transp, filial])
    db.flush()

    for i in range(6):
        db.add(_cte(
            empresa_id, chave=f"C{i}",
            transportadora_id=transp.id, tomador_cnpj="20000000000100",
            destinatario_cnpj="99999999000100", destinatario_nome="Cliente Único",
        ))
    db.commit()

    resultado = MblUseCase(db).processar(empresa_id)
    assert resultado["status"] == "ok"

    linhas = db.scalars(
        select(MblBenchmarkModel).where(MblBenchmarkModel.empresa_id == empresa_id)
    ).all()
    dims = {(l.dimensao, l.segmento) for l in linhas}
    assert ("TRANSPORTADORA", "TransX") in dims
    assert ("FILIAL", "Filial SP") in dims
    assert ("CLIENTE", "Cliente Único") in dims

    linha_cliente_rs_kg = next(
        l for l in linhas if l.dimensao == "CLIENTE" and l.metrica == "RS_KG"
    )
    assert linha_cliente_rs_kg.amostra == 6
    assert linha_cliente_rs_kg.low_confidence is False


def test_cte_sem_filial_correspondente_nao_gera_linha_filial(db, empresa_id):
    """CT-e cujo tomador_cnpj não bate com nenhuma FilialModel cadastrada não
    deve gerar linha FILIAL (dimensão esparsa) nem quebrar o processamento."""
    for i in range(3):
        db.add(_cte(
            empresa_id, chave=f"S{i}",
            tomador_cnpj="99999999000199",  # sem FilialModel correspondente
            destinatario_cnpj="88888888000100", destinatario_nome="Cliente Sem Filial",
        ))
    db.commit()

    resultado = MblUseCase(db).processar(empresa_id)
    assert resultado["status"] == "ok"

    linhas = db.scalars(
        select(MblBenchmarkModel).where(MblBenchmarkModel.empresa_id == empresa_id)
    ).all()
    assert not any(l.dimensao == "FILIAL" for l in linhas)
    # as demais dimensões continuam sendo geradas normalmente
    assert any(l.dimensao == "CLIENTE" for l in linhas)
    assert any(l.dimensao == "REGIAO" for l in linhas)


# ─────────────────── corte de cardinalidade (top-N) ───────────────────

def test_top_n_dimensao_limita_linhas_de_cliente(db, empresa_id):
    # 5 clientes distintos, com amostras de tamanho decrescente (5,4,3,2,1)
    # para tornar o ranking por volume determinístico.
    for cliente_idx, qtd in enumerate([5, 4, 3, 2, 1]):
        for i in range(qtd):
            db.add(_cte(
                empresa_id, chave=f"cli{cliente_idx}-{i}",
                destinatario_cnpj=f"{cliente_idx}0000000000{cliente_idx}",
                destinatario_nome=f"Cliente {cliente_idx}",
            ))
    db.commit()

    resultado = MblUseCase(db).processar(empresa_id, top_n_dimensao=2)
    assert resultado["status"] == "ok"

    segmentos_cliente = db.scalars(
        select(MblBenchmarkModel.segmento).where(
            MblBenchmarkModel.empresa_id == empresa_id,
            MblBenchmarkModel.dimensao == "CLIENTE",
            MblBenchmarkModel.metrica == "RS_KG",
        )
    ).all()
    # só os 2 clientes com mais volume (Cliente 0 = 5 CT-es, Cliente 1 = 4) sobrevivem ao corte.
    assert set(segmentos_cliente) == {"Cliente 0", "Cliente 1"}


def test_sem_top_n_todas_as_linhas_sao_persistidas(db, empresa_id):
    for cliente_idx in range(3):
        db.add(_cte(
            empresa_id, chave=f"cli{cliente_idx}",
            destinatario_cnpj=f"{cliente_idx}1111111000100",
            destinatario_nome=f"Cliente {cliente_idx}",
        ))
    db.commit()

    resultado = MblUseCase(db).processar(empresa_id, top_n_dimensao=100)
    assert resultado["status"] == "ok"

    segmentos_cliente = db.scalars(
        select(MblBenchmarkModel.segmento).where(
            MblBenchmarkModel.empresa_id == empresa_id,
            MblBenchmarkModel.dimensao == "CLIENTE",
            MblBenchmarkModel.metrica == "RS_KG",
        )
    ).all()
    assert len(segmentos_cliente) == 3


# ─────────────────── listar() com segmento_contains ───────────────────

def test_listar_com_segmento_contains_filtra_por_substring(db, empresa_id):
    for nome in ["Distribuidora Horizonte", "Distribuidora Aurora", "Comércio Beta"]:
        db.add(_cte(
            empresa_id, chave=nome,
            destinatario_cnpj=f"{abs(hash(nome)) % 10**11}0000000",
            destinatario_nome=nome,
        ))
    db.commit()

    uc = MblUseCase(db)
    uc.processar(empresa_id)

    resultado = uc.listar(
        empresa_id, dimensao="CLIENTE", metrica="RS_KG", segmento_contains="Distribuidora"
    )
    nomes = {r.segmento for r in resultado}
    assert nomes == {"Distribuidora Horizonte", "Distribuidora Aurora"}
