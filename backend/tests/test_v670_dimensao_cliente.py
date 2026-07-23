"""Testes da v6.7.0 — Dimensão Cliente no DLG.

Cobre RN-67 a RN-77: 5ª dimensão do motor genérico (CLIENTE_FINAL), dedup de
identidade (RN-68), composição de frete genérica (RN-72/RN-73/RN-74),
fragmentação operacional (RN-75) e diagnóstico causal (RN-76), além da
regressão das 4 dimensões existentes (OBJ-4/CA-11).

Independente da suíte de smoke HTTP (que depende de login/JWT) — usa uma
sessão SQLAlchemy isolada em SQLite em memória, exercitando o motor DLG real
(`DlgUseCase.processar`/`.listar`) sem subir a aplicação FastAPI.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.infrastructure.database.models import CTeModel, EmpresaModel, MetaNacionalModel
from app.application.use_cases.dlg import (
    DlgUseCase,
    _diagnosticar_causa,
    _ident_cliente_str,
    _tem_janela_curta,
    JANELA_DIAS_FRAGMENTACAO,
)
from app.infrastructure.parsers.cte_parser import _categoria_componente
from app.infrastructure.parsers.excel_parser import COMPONENTES


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
    db.flush()
    db.add(MetaNacionalModel(empresa_id=emp.id, meta_rs_kg=1.00, meta_pct_frete=5.0))
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


# ─────────────────────────── RN-73: granularização do parser ───────────────────────────

def test_categoria_componente_tde_tda_estadia():
    assert _categoria_componente("TDE") == "TDE"
    assert _categoria_componente("TDA") == "TDA"
    assert _categoria_componente("TDA/TDE") == "Outros"  # item combinado — inalterado
    assert _categoria_componente("ESTADIA ENTREGA") == "Estadia"  # substring


def test_categoria_componente_regressao_pedagio_inalterada():
    assert _categoria_componente("PEDAGIO") == "Pedágio"
    assert _categoria_componente("GRIS") == "GRIS"


def test_excel_componentes_match_exato_tde_tda_estadia():
    assert COMPONENTES["tde"] == "TDE"
    assert COMPONENTES["tda"] == "TDA"
    assert COMPONENTES["tda/tde"] == "Outros"
    assert COMPONENTES["estadia"] == "Estadia"


# ─────────────────────────── RN-68: dedup de identidade ───────────────────────────

def test_ident_cliente_por_raiz_cnpj():
    a = _ident_cliente_str("11222333000181", "Cliente A Matriz")
    b = _ident_cliente_str("11222333000262", "Cliente A Filial")  # mesma raiz, CNPJ completo diferente
    assert a == b == ("RAIZ", "11222333")


def test_ident_cliente_por_nome_normalizado_sem_sufixo():
    a = _ident_cliente_str("", "Comércio Beta Ltda")
    b = _ident_cliente_str("", "COMERCIO BETA")
    assert a == b


def test_ident_cliente_sem_cnpj_nem_nome():
    assert _ident_cliente_str("", "") == ("SEM_ID", None)


# ─────────────────────────── RN-75 Parte B: janela de despacho ───────────────────────────

def test_tem_janela_curta_limite_exato():
    datas_7_dias = [date(2026, 3, 1), date(2026, 3, 4), date(2026, 3, 8)]  # 0..7 dias
    assert _tem_janela_curta(datas_7_dias, min_ctes=3, dias=JANELA_DIAS_FRAGMENTACAO) is True

    datas_8_dias = [date(2026, 3, 1), date(2026, 3, 4), date(2026, 3, 9)]  # 0..8 dias
    assert _tem_janela_curta(datas_8_dias, min_ctes=3, dias=JANELA_DIAS_FRAGMENTACAO) is False


def test_tem_janela_curta_menos_que_minimo_nunca_sinaliza():
    assert _tem_janela_curta([date(2026, 3, 1)], min_ctes=3) is False
    assert _tem_janela_curta([], min_ctes=3) is False


# ─────────────────────────── RN-76: diagnóstico causal ───────────────────────────

def test_diagnosticar_causa_quatro_combinacoes():
    assert _diagnosticar_causa(50.0, 10.0, True, [("TDE", 100.0)])["causa"] == "AMBAS"
    assert _diagnosticar_causa(50.0, 10.0, False, [("TDE", 100.0)])["causa"] == "ADICIONAIS"
    assert _diagnosticar_causa(5.0, 10.0, True, [])["causa"] == "FRAGMENTACAO"
    assert _diagnosticar_causa(5.0, 10.0, False, [])["causa"] == "NENHUMA"


def test_diagnosticar_causa_nao_inventa_quando_pct_none():
    # OBJ-9: pct_adicionais=None (sem dado de composição) nunca deve virar "ADICIONAIS".
    assert _diagnosticar_causa(None, 10.0, False, None)["causa"] == "NENHUMA"


# ─────────────────────────── motor DLG — agregação + composição ───────────────────────────

def test_agregar_clientes_dedup_por_raiz_cnpj(db, empresa_id):
    db.add_all([
        _cte(empresa_id, chave="1" * 44, destinatario_cnpj="11222333000181",
             destinatario_nome="Distribuidora XPTO Matriz"),
        _cte(empresa_id, chave="2" * 44, destinatario_cnpj="11222333000262",
             destinatario_nome="Distribuidora XPTO Filial"),
    ])
    db.commit()

    uc = DlgUseCase(db)
    uc.processar(empresa_id)
    clientes = uc.listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")

    assert len(clientes) == 1
    assert clientes[0]["qtd_ctes"] == 2
    assert clientes[0]["frete_total"] == pytest.approx(1000.0)


def test_cliente_sem_destinatario_agrupado_como_nao_identificado(db, empresa_id):
    db.add(_cte(empresa_id, chave="3" * 44, destinatario_cnpj="", destinatario_nome=""))
    db.commit()

    uc = DlgUseCase(db)
    uc.processar(empresa_id)
    clientes = uc.listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")

    assert len(clientes) == 1
    assert clientes[0]["chave_label"] == "Cliente não identificado"
    assert clientes[0]["chave"] == "SEM_ID"


def test_pct_componentes_adicionais_none_quando_sem_composicao(db, empresa_id):
    db.add(_cte(empresa_id, chave="4" * 44, destinatario_cnpj="99888777000100",
                destinatario_nome="Cliente Sem Composicao", composicao_frete={}))
    db.commit()

    uc = DlgUseCase(db)
    uc.processar(empresa_id)
    clientes = uc.listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")

    assert clientes[0]["pct_componentes_adicionais"] is None  # nunca 0, nunca 100


def test_composicao_frete_e_ranking_componentes(db, empresa_id):
    db.add(_cte(
        empresa_id, chave="5" * 44, destinatario_cnpj="55666777000144",
        destinatario_nome="Cliente Com Adicionais",
        composicao_frete={"Frete Peso": 300.0, "TDE": 150.0, "TDA": 50.0},
    ))
    db.commit()

    uc = DlgUseCase(db)
    uc.processar(empresa_id)
    clientes = uc.listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")
    c = clientes[0]

    assert c["frete_transporte_principal"] == pytest.approx(300.0)
    assert c["pct_componentes_adicionais"] == pytest.approx(40.0)  # 200/500*100
    assert c["ranking_componentes"][0][0] == "TDE"  # maior componente adicional primeiro


def test_regressao_quatro_dimensoes_existentes_ganham_composicao_sem_quebrar(db, empresa_id):
    """OBJ-4/CA-11: FILIAL/ROTA/TRANSPORTADORA/REGIAO continuam funcionando e
    passam a ter `composicao_frete` (genérico, §4.2) sem alterar valores
    financeiros já existentes."""
    db.add(_cte(
        empresa_id, chave="6" * 44, tomador_cnpj="11222333000181",
        destinatario_cnpj="", destinatario_nome="",
        composicao_frete={"Frete Peso": 500.0},
    ))
    db.commit()

    uc = DlgUseCase(db)
    resultado = uc.processar(empresa_id)
    assert resultado["status"] == "ok"

    for dim in ("FILIAL", "ROTA", "TRANSPORTADORA", "REGIAO"):
        linhas = uc.listar(empresa_id, dimensao=dim, modo="consolidado")
        # TRANSPORTADORA pode ficar vazia (CT-e de teste sem transportadora_id)
        if dim == "TRANSPORTADORA":
            continue
        assert len(linhas) == 1
        assert linhas[0]["frete_total"] == pytest.approx(500.0)
        assert linhas[0]["composicao_frete"] == {"Frete Peso": 500.0}


def test_diagnostico_causal_so_roda_para_atencao_critico(db, empresa_id):
    """RN-76 passo 1: cliente EFICIENTE nunca recebe causa_dominante."""
    db.add(_cte(
        empresa_id, chave="7" * 44, destinatario_cnpj="33444555000122",
        destinatario_nome="Cliente Eficiente", valor_frete=50.0,  # bem abaixo da meta
        composicao_frete={"Frete Peso": 50.0},
    ))
    db.commit()

    uc = DlgUseCase(db)
    uc.processar(empresa_id)
    clientes = uc.listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")
    c = clientes[0]
    assert c["classificacao"] == "EFICIENTE"
    assert c["causa_dominante"] is None


# ─────────────────────────── RN-77: recomendações causais ───────────────────────────

def test_recomendacao_causal_cliente_critico_com_adicionais(db, empresa_id):
    from app.application.use_cases.recomendacoes import RecomendacoesUseCase

    # Cliente bem acima da meta (rs_kg alto), maioria do frete em TDE (adicionais).
    # Um segundo cliente sem adicionais estabelece a mediana de referência da
    # RN-76 (com 1 único cliente, a mediana seria o próprio valor — degenerado).
    db.add_all([
        _cte(
            empresa_id, chave="8" * 44, destinatario_cnpj="22333444000155",
            destinatario_nome="Cliente Critico Adicionais",
            peso=100.0, valor_frete=1000.0,  # rs_kg = 10, bem acima da meta (1.0)
            composicao_frete={"Frete Peso": 300.0, "TDE": 700.0},
        ),
        _cte(
            empresa_id, chave="a" * 44, destinatario_cnpj="66777888000199",
            destinatario_nome="Cliente Referencia Sem Adicionais",
            peso=100.0, valor_frete=100.0,  # rs_kg = 1.0 (na meta) — EFICIENTE
            composicao_frete={"Frete Peso": 100.0},
        ),
    ])
    db.commit()

    DlgUseCase(db).processar(empresa_id)

    capturadas = []

    def registrar(indicador, chave_origem, **campos):
        capturadas.append((indicador, chave_origem, campos))

    uc = RecomendacoesUseCase(db)
    uc._recomendacoes_dlg_clientes(empresa_id, registrar)

    criticos = [c for c in capturadas if c[0] == "DLG_CLIENTE_CRITICO"]
    assert len(criticos) == 1
    _, _, campos = criticos[0]
    assert "TDE" in campos["descricao"]
    assert campos["prioridade"] == "CRITICA"


# ─────────────────────────── IA — get_ofensor_cliente ───────────────────────────

def test_get_ofensor_cliente_retorna_causa_ja_calculada(db, empresa_id):
    from app.application.use_cases.assistente_tools import FerramentasLogisticas

    # Segundo cliente sem adicionais estabelece a mediana de referência (RN-76).
    db.add_all([
        _cte(
            empresa_id, chave="9" * 44, destinatario_cnpj="77888999000166",
            destinatario_nome="Cliente Ofensor Teste",
            peso=100.0, valor_frete=1000.0,
            composicao_frete={"Frete Peso": 300.0, "TDE": 700.0},
        ),
        _cte(
            empresa_id, chave="b" * 44, destinatario_cnpj="12312312000100",
            destinatario_nome="Cliente Referencia Baixo",
            peso=100.0, valor_frete=100.0,
            composicao_frete={"Frete Peso": 100.0},
        ),
    ])
    db.commit()
    DlgUseCase(db).processar(empresa_id)

    ferramentas = FerramentasLogisticas(db, empresa_id)
    resultado = ferramentas.get_ofensor_cliente()

    assert resultado["cliente"] == "Cliente Ofensor Teste"
    assert resultado["causa_dominante"] == "ADICIONAIS"
    assert resultado["pct_componentes_adicionais"] == pytest.approx(70.0)


# ─────────────────────────── parser XML — extração do destinatário ───────────────────────────

def test_parse_cte_xml_extrai_destinatario():
    from app.infrastructure.parsers.cte_parser import parse_cte_xml

    chave = "35200714200166000187570010000000031000000031"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe{chave}" versao="3.00">
  <ide>
   <cUF>35</cUF><nCT>3</nCT><serie>1</serie>
   <dhEmi>2025-03-10T09:00:00-03:00</dhEmi>
   <cMunIni>3550308</cMunIni><xMunIni>SAO PAULO</xMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><xMunFim>RIO DE JANEIRO</xMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3>
  </ide>
  <emit><CNPJ>11222333000181</CNPJ><xNome>TRANSPORTADORA TESTE LTDA</xNome></emit>
  <dest><CNPJ>12345678000195</CNPJ><xNome>EMPRESA CLIENTE MATRIZ</xNome></dest>
  <vPrest><vTPrest>1500.00</vTPrest><vRec>1500.00</vRec>
   <Comp><xNome>TDE</xNome><vComp>50.00</vComp></Comp>
  </vPrest>
  <infCTeNorm>
   <infCarga><vCarga>50000.00</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>1200.0000</qCarga></infQ>
   </infCarga>
  </infCTeNorm>
 </infCte></CTe>
</cteProc>"""
    resultado = parse_cte_xml(xml.encode("utf-8"))
    assert resultado.destinatario_cnpj == "12345678000195"
    assert resultado.destinatario_nome == "EMPRESA CLIENTE MATRIZ"
    assert resultado.composicao.get("TDE") == 50.0


# ─────────────────────────── DT-27: backfill de destinatário/composição ───────────────────────────

_XML_BACKFILL = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
 <CTe><infCte Id="CTe{chave}" versao="3.00">
  <ide>
   <cUF>35</cUF><nCT>3</nCT><serie>1</serie>
   <dhEmi>2025-03-10T09:00:00-03:00</dhEmi>
   <cMunIni>3550308</cMunIni><xMunIni>SAO PAULO</xMunIni><UFIni>SP</UFIni>
   <cMunFim>3304557</cMunFim><xMunFim>RIO DE JANEIRO</xMunFim><UFFim>RJ</UFFim>
   <toma3><toma>3</toma></toma3>
  </ide>
  <emit><CNPJ>11222333000181</CNPJ><xNome>TRANSPORTADORA TESTE LTDA</xNome></emit>
  <dest><CNPJ>44555666000177</CNPJ><xNome>Cliente Retroativo Ltda</xNome></dest>
  <vPrest><vTPrest>500.00</vTPrest><vRec>500.00</vRec>
   <Comp><xNome>TDE</xNome><vComp>50.00</vComp></Comp>
  </vPrest>
  <infCTeNorm>
   <infCarga><vCarga>5000.00</vCarga>
    <infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>100.0000</qCarga></infQ>
   </infCarga>
  </infCTeNorm>
 </infCte></CTe>
</cteProc>"""


def _xml_backfill(chave: str) -> bytes:
    return _XML_BACKFILL.format(chave=chave).encode("utf-8")


def test_backfill_atualiza_cte_pre_v670(db, empresa_id):
    from app.application.use_cases.backfill_destinatario import BackfillDestinatarioUseCase
    from app.infrastructure.database.repositories import CTeRepository

    chave = "3" * 44
    # Simula um CT-e importado ANTES da v6.7.0: destinatário vazio,
    # composição ainda com TDE agrupado em "Outros" (categorização antiga).
    db.add(_cte(
        empresa_id, chave=chave, destinatario_cnpj="", destinatario_nome="",
        peso=100.0, valor_frete=500.0, valor_mercadoria=5000.0,
        composicao_frete={"Outros": 50.0},
    ))
    db.commit()

    uc = BackfillDestinatarioUseCase(CTeRepository(db))
    resultado = uc.executar(empresa_id, [("cte1.xml", _xml_backfill(chave))])

    assert resultado.atualizados == 1
    assert resultado.nao_encontrados == 0

    cte_atualizado = db.query(CTeModel).filter_by(chave=chave).one()
    assert cte_atualizado.destinatario_cnpj == "44555666000177"
    assert cte_atualizado.destinatario_nome == "Cliente Retroativo Ltda"
    assert cte_atualizado.composicao_frete.get("TDE") == 50.0
    # Nunca altera dado financeiro.
    assert cte_atualizado.valor_frete == 500.0
    assert cte_atualizado.peso == 100.0


def test_backfill_e_reprocessar_identifica_cliente(db, empresa_id):
    """Fim a fim: depois do backfill + processar(), o cliente deixa de
    aparecer como 'Cliente não identificado'."""
    from app.application.use_cases.backfill_destinatario import BackfillDestinatarioUseCase
    from app.infrastructure.database.repositories import CTeRepository

    chave = "4" * 44
    db.add(_cte(
        empresa_id, chave=chave, destinatario_cnpj="", destinatario_nome="",
        peso=100.0, valor_frete=500.0, valor_mercadoria=5000.0,
        composicao_frete={"Outros": 50.0},
    ))
    db.commit()

    BackfillDestinatarioUseCase(CTeRepository(db)).executar(
        empresa_id, [("cte1.xml", _xml_backfill(chave))])

    DlgUseCase(db).processar(empresa_id)
    clientes = DlgUseCase(db).listar(empresa_id, dimensao="CLIENTE_FINAL", modo="consolidado")

    assert len(clientes) == 1
    assert clientes[0]["chave_label"] == "Cliente Retroativo Ltda"
    assert clientes[0]["chave"] != "SEM_ID"


def test_backfill_nao_encontrado_para_empresa_errada(db, empresa_id):
    """Isolamento multi-tenant: chave existe, mas não nessa empresa."""
    from app.application.use_cases.backfill_destinatario import BackfillDestinatarioUseCase
    from app.infrastructure.database.repositories import CTeRepository

    outra_empresa = EmpresaModel(razao_social="Outra Empresa", cnpj_matriz="99999999000199", setor="Outros")
    db.add(outra_empresa)
    db.commit()

    chave = "5" * 44
    db.add(_cte(empresa_id, chave=chave, destinatario_cnpj="", destinatario_nome=""))
    db.commit()

    uc = BackfillDestinatarioUseCase(CTeRepository(db))
    resultado = uc.executar(outra_empresa.id, [("cte1.xml", _xml_backfill(chave))])

    assert resultado.nao_encontrados == 1
    assert resultado.atualizados == 0

    # Confirma que o CT-e da empresa original não foi alterado por engano.
    original = db.query(CTeModel).filter_by(chave=chave).one()
    assert original.destinatario_cnpj == ""


def test_backfill_idempotente(db, empresa_id):
    from app.application.use_cases.backfill_destinatario import BackfillDestinatarioUseCase
    from app.infrastructure.database.repositories import CTeRepository

    chave = "6" * 44
    db.add(_cte(empresa_id, chave=chave, destinatario_cnpj="", destinatario_nome=""))
    db.commit()

    uc = BackfillDestinatarioUseCase(CTeRepository(db))
    primeira = uc.executar(empresa_id, [("cte1.xml", _xml_backfill(chave))])
    segunda = uc.executar(empresa_id, [("cte1.xml", _xml_backfill(chave))])

    assert primeira.atualizados == 1
    assert segunda.atualizados == 0
    assert segunda.sem_mudanca == 1
