"""Testes das melhorias de UX do Benchmark de Mercado — escopo CLIENTE no
Comparativo de Mercado (``BenchmarkDashboardUseCase._comparativo_por_cliente``)
e filtro de Filial em Nacional/Regional (``BenchmarkUseCase._ctes``).

Independente da suíte de smoke HTTP — usa sessão SQLAlchemy isolada em SQLite
em memória, mesmo padrão de ``test_v670_dimensao_cliente.py``.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.infrastructure.database.models import (
    BenchmarkMercadoModel,
    CTeModel,
    EmpresaModel,
)
from app.infrastructure.database.repositories import CTeRepository
from app.application.use_cases.benchmark import BenchmarkUseCase
from app.application.use_cases.benchmark_dashboard import BenchmarkDashboardUseCase


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
        uf_origem="SP", uf_destino="SP", status="ATIVO",
    )
    base.update(kw)
    return CTeModel(**base)


def _seed_referencia_nacional(db):
    """Uma linha de Matriz Benchmark (OD) basta para `_referencia_nacional()`
    (mapa_percentis_mercado) ficar `disponivel=True`."""
    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="SUDESTE",
        rs_kg_p10=3.0, rs_kg_p25=3.5, rs_kg_p50=4.0, rs_kg_p75=4.5, rs_kg_p90=5.0,
    ))
    db.commit()


# ─────────────────── escopo CLIENTE no Comparativo de Mercado ───────────────────

def test_comparativo_por_cliente_agrupa_por_raiz_cnpj(db, empresa_id):
    _seed_referencia_nacional(db)
    # Cliente A: mesma raiz de CNPJ (8 dígitos), CNPJs completos diferentes
    # (matriz/filial) — devem cair no mesmo grupo (RN-68, mesma regra do DLG).
    for i in range(6):
        db.add(_cte(
            empresa_id, chave=f"A{i}",
            destinatario_cnpj="11222333000181" if i % 2 == 0 else "11222333000262",
            destinatario_nome="Cliente A Matriz",
            valor_frete=400.0 + i, peso=100.0,
        ))
    # Cliente B: amostra pequena (< 5) → low_confidence
    for i in range(2):
        db.add(_cte(
            empresa_id, chave=f"B{i}",
            destinatario_cnpj="99888777000100",
            destinatario_nome="Cliente B Pequeno",
            valor_frete=600.0, peso=100.0,
        ))
    db.commit()

    uc = BenchmarkDashboardUseCase(db, CTeRepository(db))
    itens = uc.comparativo_mercado(empresa_id, escopo="CLIENTE")

    por_nome = {i["cliente_nome"]: i for i in itens}
    assert por_nome["Cliente A Matriz"]["qtd_ctes"] == 6
    assert por_nome["Cliente A Matriz"]["low_confidence"] is False
    assert por_nome["Cliente B Pequeno"]["qtd_ctes"] == 2
    assert por_nome["Cliente B Pequeno"]["low_confidence"] is True
    # comparação sempre contra a referência NACIONAL (cliente não tem
    # segmentação geográfica na Matriz Benchmark).
    assert por_nome["Cliente A Matriz"]["mercado_p50"] == 4.0


def test_comparativo_por_cliente_sem_id_nao_e_descartado(db, empresa_id):
    _seed_referencia_nacional(db)
    db.add(_cte(empresa_id, chave="X1", destinatario_cnpj="", destinatario_nome=""))
    db.commit()

    uc = BenchmarkDashboardUseCase(db, CTeRepository(db))
    itens = uc.comparativo_mercado(empresa_id, escopo="CLIENTE")

    assert any(i["cliente_nome"] == "Cliente não identificado" for i in itens)


def test_comparativo_por_cliente_busca_encontra_fora_do_top_n(db, empresa_id):
    _seed_referencia_nacional(db)
    # Cliente grande (alto volume) — ficaria dentro de qualquer top-N razoável.
    for i in range(10):
        db.add(_cte(empresa_id, chave=f"G{i}", destinatario_cnpj="11111111000100",
                     destinatario_nome="Cliente Grande"))
    # Cliente pequeno, específico — só encontrável via busca se `limite` cortar antes.
    db.add(_cte(empresa_id, chave="P1", destinatario_cnpj="22222222000100",
                 destinatario_nome="Cliente Pequeno Especifico"))
    db.commit()

    uc = BenchmarkDashboardUseCase(db, CTeRepository(db))

    # limite=1 sem busca: só o cliente grande aparece.
    itens_sem_busca = uc.comparativo_mercado(empresa_id, escopo="CLIENTE", limite=1)
    assert len(itens_sem_busca) == 1
    assert itens_sem_busca[0]["cliente_nome"] == "Cliente Grande"

    # com busca, o cliente pequeno é encontrado mesmo com limite=1 (busca
    # filtra ANTES do corte top-N).
    itens_busca = uc.comparativo_mercado(
        empresa_id, escopo="CLIENTE", busca="Pequeno Especifico", limite=1
    )
    assert len(itens_busca) == 1
    assert itens_busca[0]["cliente_nome"] == "Cliente Pequeno Especifico"


def test_comparativo_mercado_dispatch_escopo_cliente(db, empresa_id):
    """`comparativo_mercado(escopo="CLIENTE")` desvia para `_comparativo_por_cliente`
    sem passar pelo fluxo geográfico (Benchmark Observado / Matriz Benchmark OD)."""
    _seed_referencia_nacional(db)
    db.add(_cte(empresa_id, chave="D1", destinatario_cnpj="33333333000100",
                 destinatario_nome="Cliente Dispatch"))
    db.commit()

    uc = BenchmarkDashboardUseCase(db, CTeRepository(db))
    itens = uc.comparativo_mercado(empresa_id, escopo="CLIENTE")
    assert itens and "cliente_nome" in itens[0]
    assert "origem_regiao" not in itens[0]  # não é o formato geográfico


# ─────────────────── filtro de Filial em Nacional/Regional ───────────────────

class _FakeCteRepo:
    def __init__(self, ctes):
        self._ctes = ctes

    def list_by_empresa(self, empresa_id, data_inicio, data_fim, apenas_ativos=True):
        return self._ctes


class _CteFake:
    def __init__(self, transportadora_id=None, tomador_cnpj=""):
        self.transportadora_id = transportadora_id
        self.tomador_cnpj = tomador_cnpj


def test_ctes_filtra_por_filial_cnpj():
    ctes = [
        _CteFake(tomador_cnpj="11111111000100"),
        _CteFake(tomador_cnpj="22222222000100"),
        _CteFake(tomador_cnpj="11111111000100"),
    ]
    uc = BenchmarkUseCase(diagnostico_uc=None, cte_repo=_FakeCteRepo(ctes), benchmark_repo=None)

    todos = uc._ctes(1, None, None, None)
    assert len(todos) == 3

    filtrados = uc._ctes(1, None, None, None, filial_cnpj="11111111000100")
    assert len(filtrados) == 2
    assert all(c.tomador_cnpj == "11111111000100" for c in filtrados)


def test_ctes_combina_filtro_transportadora_e_filial():
    ctes = [
        _CteFake(transportadora_id=1, tomador_cnpj="11111111000100"),
        _CteFake(transportadora_id=2, tomador_cnpj="11111111000100"),
        _CteFake(transportadora_id=1, tomador_cnpj="22222222000100"),
    ]
    uc = BenchmarkUseCase(diagnostico_uc=None, cte_repo=_FakeCteRepo(ctes), benchmark_repo=None)

    filtrados = uc._ctes(1, None, None, transportadora_id=1, filial_cnpj="11111111000100")
    assert len(filtrados) == 1


# ─────────────── resolver() com dimensão de setor (Matriz Benchmark) ───────────────

def test_resolver_usa_linha_do_setor_da_empresa_quando_existe(db):
    """Empresa de setor 'Farmacêutico': se existir linha pesquisada para esse
    setor no corredor, ela deve vencer sobre a linha genérica 'TODOS'."""
    from app.application.use_cases.benchmark_v2 import BenchmarkV2UseCase

    emp = EmpresaModel(razao_social="Farma SA", cnpj_matriz="22333444000199", setor="Farmacêutico")
    db.add(emp)
    db.commit()

    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="NORDESTE", setor="TODOS",
        rs_kg_p50=5.0,
    ))
    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="NORDESTE", setor="Farmacêutico",
        rs_kg_p50=12.4, amostra_tamanho=14,
    ))
    db.commit()

    ref = BenchmarkV2UseCase(db).resolver(emp.id, "SUDESTE", "NORDESTE")
    assert ref.disponivel
    assert ref.setor == "Farmacêutico"
    assert ref.rs_kg_p50 == 12.4


def test_resolver_cai_para_todos_quando_setor_da_empresa_nao_tem_linha(db):
    """Sem pesquisa para o setor da empresa, cai para a linha genérica
    'TODOS' — comportamento preservado (não regride para indisponível)."""
    from app.application.use_cases.benchmark_v2 import BenchmarkV2UseCase

    emp = EmpresaModel(razao_social="Agro SA", cnpj_matriz="33444555000188", setor="Agronegócio")
    db.add(emp)
    db.commit()

    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="NORDESTE", setor="TODOS",
        rs_kg_p50=5.0,
    ))
    db.commit()

    ref = BenchmarkV2UseCase(db).resolver(emp.id, "SUDESTE", "NORDESTE")
    assert ref.disponivel
    assert ref.setor == "TODOS"
    assert ref.rs_kg_p50 == 5.0


def test_mapa_percentis_mercado_ignora_linhas_de_setor_especifico(db):
    """A referência nacional/regional genérica (usada por Score, Insights,
    Oportunidades, Assistente) não pode ser inflada por linhas pesquisadas
    para um setor específico."""
    from app.application.use_cases.benchmark_v2 import mapa_percentis_mercado

    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="NORDESTE", setor="TODOS",
        rs_kg_p50=5.0,
    ))
    db.add(BenchmarkMercadoModel(
        origem_regiao="SUDESTE", destino_regiao="NORDESTE", setor="Farmacêutico",
        rs_kg_p50=12.4,
    ))
    db.commit()

    mapa = mapa_percentis_mercado(db)
    assert mapa["NORDESTE"]["p50"] == 5.0
    assert mapa["NACIONAL"]["p50"] == 5.0
