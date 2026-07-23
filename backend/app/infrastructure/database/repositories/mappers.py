"""Mapeamento entre modelos ORM e entidades de domínio (adapters)."""
from app.domain.entities import (
    CTe,
    Benchmark,
    Cidade,
    Empresa,
    FechamentoMensal,
    Filial,
    MacroRegiaoEnum,
    MetaNacional,
    MetaRegional,
    NFe,
    Regiao,
    SetorEnum,
    StatusEnum,
    StatusFechamentoEnum,
    Transportadora,
    User,
)
from app.infrastructure.database.models import (
    BenchmarkModel,
    CidadeModel,
    CTeModel,
    EmpresaModel,
    FechamentoMensalModel,
    FilialModel,
    MetaNacionalModel,
    MetaRegionalModel,
    NFeModel,
    RegiaoModel,
    TransportadoraModel,
    UserModel,
)


def user_to_domain(m: UserModel) -> User:
    from app.domain.entities import RoleEnum
    return User(
        id=m.id, nome=m.nome, email=m.email, hashed_password=m.hashed_password,
        is_active=m.is_active, is_superuser=m.is_superuser,
        role=RoleEnum(m.role) if m.role else (RoleEnum.ADMIN if m.is_superuser else RoleEnum.ANALISTA),
        empresa_id=m.empresa_id,
        empresas_ids=[e.id for e in (m.empresas or [])],
        created_at=m.created_at,
    )


def empresa_to_domain(m: EmpresaModel) -> Empresa:
    return Empresa(
        id=m.id, razao_social=m.razao_social, nome_fantasia=m.nome_fantasia,
        cnpj_matriz=m.cnpj_matriz, status=StatusEnum(m.status),
        setor=SetorEnum(m.setor), created_at=m.created_at,
    )


def filial_to_domain(m: FilialModel) -> Filial:
    return Filial(
        id=m.id, empresa_id=m.empresa_id, razao_social=m.razao_social,
        cnpj=m.cnpj, cidade=m.cidade, uf=m.uf,
    )


def transportadora_to_domain(m: TransportadoraModel) -> Transportadora:
    return Transportadora(
        id=m.id, empresa_id=m.empresa_id,
        razao_social=m.razao_social, nome_fantasia=m.nome_fantasia,
        cnpj=m.cnpj, endereco=m.endereco, cidade=m.cidade, uf=m.uf, cep=m.cep,
        contato=m.contato, telefone=m.telefone, email=m.email,
        status=StatusEnum(m.status),
    )


def regiao_to_domain(m: RegiaoModel) -> Regiao:
    return Regiao(id=m.id, nome=m.nome, descricao=m.descricao)


def cidade_to_domain(m: CidadeModel) -> Cidade:
    return Cidade(
        id=m.id, nome=m.nome, uf=m.uf, regiao_id=m.regiao_id,
        macro_regiao=MacroRegiaoEnum(m.macro_regiao) if m.macro_regiao else None,
    )


def meta_nacional_to_domain(m: MetaNacionalModel) -> MetaNacional:
    return MetaNacional(
        id=m.id, empresa_id=m.empresa_id,
        meta_rs_kg=m.meta_rs_kg, meta_pct_frete=m.meta_pct_frete,
    )


def meta_regional_to_domain(m: MetaRegionalModel) -> MetaRegional:
    return MetaRegional(
        id=m.id, empresa_id=m.empresa_id, macro_regiao=MacroRegiaoEnum(m.macro_regiao),
        meta_rs_kg=m.meta_rs_kg, meta_pct_frete=m.meta_pct_frete,
        prazo_medio_meta=m.prazo_medio_meta, orcamento_mensal=m.orcamento_mensal,
    )


def fechamento_mensal_to_domain(m: FechamentoMensalModel) -> FechamentoMensal:
    return FechamentoMensal(
        id=m.id, empresa_id=m.empresa_id, competencia=m.competencia,
        fat_norte=m.fat_norte, fat_nordeste=m.fat_nordeste, fat_centro_oeste=m.fat_centro_oeste,
        fat_sudeste=m.fat_sudeste, fat_sul=m.fat_sul,
        devolucao=m.devolucao, frete_complementar=m.frete_complementar,
        status=StatusFechamentoEnum(m.status), fechado_em=m.fechado_em,
    )


def benchmark_to_domain(m: BenchmarkModel) -> Benchmark:
    from app.domain.entities import RegiaoBenchmarkEnum

    return Benchmark(
        id=m.id,
        regiao=RegiaoBenchmarkEnum(m.regiao),
        frete_kg_min=m.frete_kg_min,
        frete_kg_medio=m.frete_kg_medio,
        frete_kg_max=m.frete_kg_max,
        frete_pct_min=m.frete_pct_min,
        frete_pct_medio=m.frete_pct_medio,
        frete_pct_max=m.frete_pct_max,
    )


def nfe_to_domain(m: NFeModel) -> NFe:
    return NFe(
        id=m.id, cte_id=m.cte_id, chave=m.chave, numero=m.numero,
        data_emissao=m.data_emissao, valor_mercadoria=m.valor_mercadoria,
        peso=m.peso, municipio_destino=m.municipio_destino,
    )


# ══════════ Mappers Benchmark OD (V2.1) ══════════
def hub_to_domain(m):
    from app.domain.entities import HubLogistico
    return HubLogistico(
        id=m.id, empresa_id=m.empresa_id, codigo=m.codigo, nome=m.nome,
        descricao=m.descricao, ativo=m.ativo,
    )


def cluster_to_domain(m, hub=None):
    from app.domain.entities import ClusterCliente
    return ClusterCliente(
        id=m.id, empresa_id=m.empresa_id, uf=m.uf, municipio=m.municipio,
        hub_id=m.hub_id,
        hub_codigo=hub.codigo if hub else "",
        hub_nome=hub.nome if hub else "",
    )


def benchmark_corredor_to_domain(m):
    from app.domain.entities import BenchmarkCorredor
    return BenchmarkCorredor(
        id=m.id,
        empresa_id=m.empresa_id,
        hub_origem_codigo=m.hub_origem_codigo,
        hub_destino_codigo=m.hub_destino_codigo,
        frete_kg_min=m.frete_kg_min, frete_kg_medio=m.frete_kg_medio, frete_kg_max=m.frete_kg_max,
        frete_pct_min=m.frete_pct_min, frete_pct_medio=m.frete_pct_medio, frete_pct_max=m.frete_pct_max,
        volume_referencia=m.volume_referencia, dispersao_kg=m.dispersao_kg,
        prazo_dias_medio=m.prazo_dias_medio,
        observacoes=m.observacoes,
    )


def cte_to_domain(m: CTeModel) -> CTe:
    return CTe(
        id=m.id, empresa_id=m.empresa_id, transportadora_id=m.transportadora_id,
        chave=m.chave, numero=m.numero, serie=m.serie, data_emissao=m.data_emissao,
        tomador_cnpj=m.tomador_cnpj,
        destinatario_cnpj=getattr(m, "destinatario_cnpj", None) or "",
        destinatario_nome=getattr(m, "destinatario_nome", None) or "",
        peso=m.peso, valor_frete=m.valor_frete,
        valor_mercadoria=m.valor_mercadoria, municipio_origem=m.municipio_origem,
        uf_origem=m.uf_origem, municipio_destino=m.municipio_destino,
        uf_destino=m.uf_destino,
        macro_regiao_destino=MacroRegiaoEnum(m.macro_regiao_destino)
        if m.macro_regiao_destino else None,
        data_saida=m.data_saida, data_entrega=m.data_entrega,
        origem_importacao=m.origem_importacao,
        composicao_frete=m.composicao_frete or {},
        status=getattr(m, "status", "ATIVO") or "ATIVO",
        cancelado_em=getattr(m, "cancelado_em", None),
        protocolo_cancelamento=getattr(m, "protocolo_cancelamento", None),
        numero_evento_cancelamento=getattr(m, "numero_evento_cancelamento", None),
        nfes=[nfe_to_domain(n) for n in m.nfes],
    )


# ══════════ Mappers BID (V3.1) ══════════
from app.domain.entities import (
    Bid, BidAuditoria, BidEscopo, BidProposta, BidSimulacao, BidTransportadora,
    BidStatusEnum, BidTransportadoraStatusEnum, TipoAgrupamentoEnum, PropostaOrigemEnum, RoleEnum,
)
from app.infrastructure.database.models import (
    BidAuditoriaModel, BidEscopoModel, BidModel,
    BidPropostaModel, BidSimulacaoModel, BidTransportadoraModel,
)


def bid_to_domain(m: BidModel) -> Bid:
    return Bid(
        id=m.id, empresa_id=m.empresa_id, nome=m.nome,
        descricao=m.descricao or "", objetivo=m.objetivo or "",
        observacoes=m.observacoes or "",
        status=BidStatusEnum(m.status),
        segmentacao_tipo=getattr(m, "segmentacao_tipo", None) or "GERAL",
        segmentacao_valor=getattr(m, "segmentacao_valor", None) or "",
        data_inicio=m.data_inicio, data_encerramento=m.data_encerramento,
        periodo_analise_inicio=m.periodo_analise_inicio,
        periodo_analise_fim=m.periodo_analise_fim,
        created_by=m.created_by, created_at=m.created_at, updated_at=m.updated_at,
    )


def bid_escopo_to_domain(m: BidEscopoModel) -> BidEscopo:
    return BidEscopo(
        id=m.id, bid_id=m.bid_id,
        tipo_agrupamento=TipoAgrupamentoEnum(m.tipo_agrupamento),
        valor_grupo=m.valor_grupo,
        peso_total=m.peso_total, valor_frete_total=m.valor_frete_total,
        valor_mercadoria_total=m.valor_mercadoria_total,
        qtd_embarques=m.qtd_embarques, frete_rs_kg=m.frete_rs_kg, frete_pct=m.frete_pct,
    )


def bid_transportadora_to_domain(m: BidTransportadoraModel) -> BidTransportadora:
    return BidTransportadora(
        id=m.id, bid_id=m.bid_id, transportadora_id=m.transportadora_id,
        status=BidTransportadoraStatusEnum(m.status),
        observacoes=m.observacoes or "",
        avaliacao_usuario=m.avaliacao_usuario,
    )


def bid_proposta_to_domain(m: BidPropostaModel) -> BidProposta:
    return BidProposta(
        id=m.id, bid_id=m.bid_id, bid_transportadora_id=m.bid_transportadora_id,
        tipo_agrupamento=TipoAgrupamentoEnum(m.tipo_agrupamento),
        valor_grupo=m.valor_grupo, valor_rs_kg=m.valor_rs_kg,
        valor_minimo=m.valor_minimo, prazo_dias=m.prazo_dias,
        cobertura_pct=m.cobertura_pct, observacoes=m.observacoes or "",
        origem=PropostaOrigemEnum(m.origem), created_at=m.created_at,
    )


def bid_simulacao_to_domain(m: BidSimulacaoModel) -> BidSimulacao:
    return BidSimulacao(
        id=m.id, bid_id=m.bid_id, nome=m.nome, descricao=m.descricao or "",
        itens=m.itens or [], custo_atual=m.custo_atual,
        custo_proposto=m.custo_proposto, economia_total=m.economia_total,
        reducao_pct=m.reducao_pct, created_at=m.created_at,
    )


def bid_auditoria_to_domain(m: BidAuditoriaModel) -> BidAuditoria:
    return BidAuditoria(
        id=m.id, bid_id=m.bid_id, user_id=m.user_id,
        acao=m.acao, detalhe=m.detalhe or {}, created_at=m.created_at,
    )
