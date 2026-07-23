"""Entidades de domínio puras (sem dependência de framework ou ORM).

Representam as regras e os dados do negócio. A camada de infraestrutura
mapeia estas entidades para/desde os modelos ORM.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional


class StatusEnum(str, Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"


class RoleEnum(str, Enum):
    """Perfil de acesso do usuário na plataforma."""
    ADMIN = "ADMIN"
    ANALISTA = "ANALISTA"
    VISUALIZADOR = "VISUALIZADOR"


class MacroRegiaoEnum(str, Enum):
    NORTE = "NORTE"
    NORDESTE = "NORDESTE"
    CENTRO_OESTE = "CENTRO_OESTE"
    SUDESTE = "SUDESTE"
    SUL = "SUL"


class SetorEnum(str, Enum):
    """Setor (segmento econômico) do embarcador.

    Vocabulário controlado para classificação das empresas-cliente. É a base
    para filtros, consultas SQL, dashboards e benchmarking por segmento. Os
    valores são armazenados exatamente como abaixo (rótulo humano); a inclusão
    de novos setores no futuro exige apenas acrescentar membros a este enum.
    """

    INDUSTRIA = "Indústria"
    DISTRIBUIDOR = "Distribuidor"
    ATACADO = "Atacado"
    VAREJO = "Varejo"
    ECOMMERCE = "E-commerce"
    TRANSPORTADORA = "Transportadora"
    OPERADOR_LOGISTICO = "Operador Logístico"
    AGRONEGOCIO = "Agronegócio"
    SAUDE = "Saúde"
    FARMACEUTICO = "Farmacêutico"
    ALIMENTICIO = "Alimentício"
    AUTOMOTIVO = "Automotivo"
    CONSTRUCAO_CIVIL = "Construção Civil"
    QUIMICO = "Químico"
    TEXTIL = "Têxtil"
    PAPEL_CELULOSE = "Papel e Celulose"
    METALURGIA = "Metalurgia"
    TECNOLOGIA = "Tecnologia"
    OUTROS = "Outros"


class RegiaoBenchmarkEnum(str, Enum):
    """Regiões de referência do benchmark de mercado.

    Inclui as cinco macro-regiões e a referência NACIONAL.
    """

    NORTE = "NORTE"
    NORDESTE = "NORDESTE"
    CENTRO_OESTE = "CENTRO_OESTE"
    SUDESTE = "SUDESTE"
    SUL = "SUL"
    NACIONAL = "NACIONAL"


@dataclass
class User:
    id: Optional[int] = None
    nome: str = ""
    email: str = ""
    hashed_password: str = ""
    is_active: bool = True
    is_superuser: bool = False
    role: RoleEnum = RoleEnum.ANALISTA
    empresa_id: Optional[int] = None   # empresa padrão/preferida (pré-seleção na tela de login)
    empresas_ids: List[int] = field(default_factory=list)  # vínculo real (M:N) — fonte de verdade da autorização
    created_at: Optional[datetime] = None


@dataclass
class Empresa:
    id: Optional[int] = None
    razao_social: str = ""
    nome_fantasia: str = ""
    cnpj_matriz: str = ""
    status: StatusEnum = StatusEnum.ATIVO
    setor: SetorEnum = SetorEnum.OUTROS
    created_at: Optional[datetime] = None


@dataclass
class Filial:
    id: Optional[int] = None
    empresa_id: int = 0
    razao_social: str = ""
    cnpj: str = ""
    cidade: str = ""
    uf: str = ""


@dataclass
class Transportadora:
    id: Optional[int] = None
    empresa_id: Optional[int] = None   # None = registro legado/global (migração)
    razao_social: str = ""
    nome_fantasia: str = ""
    cnpj: str = ""
    endereco: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""
    contato: str = ""
    telefone: str = ""
    email: str = ""
    status: StatusEnum = StatusEnum.ATIVO


@dataclass
class Regiao:
    id: Optional[int] = None
    nome: str = ""
    descricao: str = ""


@dataclass
class Cidade:
    id: Optional[int] = None
    nome: str = ""
    uf: str = ""
    regiao_id: Optional[int] = None
    macro_regiao: Optional[MacroRegiaoEnum] = None


@dataclass
class MetaNacional:
    id: Optional[int] = None
    empresa_id: int = 0
    meta_rs_kg: float = 0.0
    meta_pct_frete: float = 0.0


@dataclass
class MetaRegional:
    id: Optional[int] = None
    empresa_id: int = 0
    macro_regiao: MacroRegiaoEnum = MacroRegiaoEnum.SUDESTE
    meta_rs_kg: float = 0.0
    meta_pct_frete: float = 0.0
    prazo_medio_meta: int = 0
    orcamento_mensal: float = 0.0


class StatusFechamentoEnum(str, Enum):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"


@dataclass
class FechamentoMensal:
    """Fechamento de Custo de Frete — um registro por empresa e competência.

    Faturamento é informado por região; devolução e frete complementar são
    totais nacionais. Frete realizado e budget não moram aqui — são sempre
    calculados a partir do CT-e e de MetaRegional (RN: nunca duplicar dado
    que já existe automático)."""

    id: Optional[int] = None
    empresa_id: int = 0
    competencia: str = ""  # "AAAA-MM"
    fat_norte: float = 0.0
    fat_nordeste: float = 0.0
    fat_centro_oeste: float = 0.0
    fat_sudeste: float = 0.0
    fat_sul: float = 0.0
    devolucao: float = 0.0
    frete_complementar: float = 0.0
    status: StatusFechamentoEnum = StatusFechamentoEnum.ABERTO
    fechado_em: Optional[datetime] = None


@dataclass
class Benchmark:
    """Referência de mercado por região (módulo Benchmark Logístico).

    Valores mínimo, médio e máximo de frete por kg e de frete sobre
    mercadoria. Dado global (não pertence a uma empresa), editável pelo
    administrador.
    """

    id: Optional[int] = None
    regiao: RegiaoBenchmarkEnum = RegiaoBenchmarkEnum.NACIONAL
    frete_kg_min: float = 0.0
    frete_kg_medio: float = 0.0
    frete_kg_max: float = 0.0
    frete_pct_min: float = 0.0
    frete_pct_medio: float = 0.0
    frete_pct_max: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO BENCHMARK LOGÍSTICO V2.1 — MODELO ORIGEM → DESTINO (OD)
# ═══════════════════════════════════════════════════════════════════════════
# O custo logístico mora no PAR origem→destino, não na região de chegada.
# Por isso o benchmark passa a ser por CORREDOR (Hub origem → Hub destino).
#
#   • HubLogistico      → catálogo GLOBAL de hubs (vocabulário controlado).
#   • ClusterCliente    → mapeia UF/município → Hub, POR EMPRESA-cliente.
#   • BenchmarkCorredor → referência de mercado GLOBAL por par de hubs.
#
# A tabela Benchmark (por região) permanece como legado/fallback nacional.
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class HubLogistico:
    """Hub logístico — catálogo próprio de cada empresa-cliente.

    Cada empresa cria e mantém seu próprio catálogo de hubs, sem afetar
    outras empresas. O código é único apenas dentro da empresa.
    """

    id: Optional[int] = None
    empresa_id: int = 0
    codigo: str = ""           # ex.: "SUDESTE_HUB" (estável, usado em chaves)
    nome: str = ""             # ex.: "Sudeste Hub" (exibição)
    descricao: str = ""
    ativo: bool = True


@dataclass
class ClusterCliente:
    """Regra de mapeamento UF/município → Hub, por empresa-cliente.

    Quando `municipio` é vazio, a regra vale para toda a UF. Uma regra
    com município preenchido tem precedência sobre a regra só-UF.
    """

    id: Optional[int] = None
    empresa_id: int = 0
    uf: str = ""
    municipio: str = ""        # opcional; vazio = regra para a UF inteira
    hub_id: int = 0
    hub_codigo: str = ""       # desnormalizado p/ leitura rápida
    hub_nome: str = ""


@dataclass
class BenchmarkCorredor:
    """Referência de mercado por corredor (Hub origem → Hub destino), por empresa.

    Substitui a lógica regional como base de cálculo. Inclui volume de
    referência e dispersão (desvio-padrão relativo) do fluxo, usados na
    ponderação e na suavização do score.
    """

    id: Optional[int] = None
    empresa_id: int = 0
    hub_origem_codigo: str = ""
    hub_destino_codigo: str = ""
    frete_kg_min: float = 0.0
    frete_kg_medio: float = 0.0
    frete_kg_max: float = 0.0
    frete_pct_min: float = 0.0
    frete_pct_medio: float = 0.0
    frete_pct_max: float = 0.0
    volume_referencia: float = 0.0   # volume de mercado do fluxo (peso/qtd) — ponderação
    dispersao_kg: float = 0.0        # desvio-padrão relativo do R$/kg (0-1) — suavização
    prazo_dias_medio: float = 0.0    # prazo de entrega de referência do corredor (0 = não cadastrado)
    observacoes: str = ""

    @property
    def chave(self) -> str:
        return f"{self.hub_origem_codigo}->{self.hub_destino_codigo}"


@dataclass
class NFe:
    id: Optional[int] = None
    cte_id: Optional[int] = None
    chave: str = ""
    numero: str = ""
    data_emissao: Optional[date] = None
    valor_mercadoria: float = 0.0
    peso: float = 0.0
    municipio_destino: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# Composição de frete — funções puras (RN-72/RN-74, v6.7.0)
# Vivem no domínio (sem dependência de ORM/framework) para serem reaproveitadas
# tanto pelos `@property` de DlgAnaliticoModel (infraestrutura) quanto pela
# consolidação em memória do DlgUseCase (aplicação) — uma única fonte de
# verdade para o cálculo, nunca duplicado entre as duas camadas.
# ═══════════════════════════════════════════════════════════════════════════

def calc_frete_transporte_principal(composicao: Optional[dict]) -> Optional[float]:
    """RN-72: soma de Frete Peso + Frete Valor. None quando não há composição."""
    if not composicao:
        return None
    return round((composicao.get("Frete Peso", 0.0) or 0.0)
                 + (composicao.get("Frete Valor", 0.0) or 0.0), 2)


def calc_pct_componentes_adicionais(composicao: Optional[dict], frete_total: float) -> Optional[float]:
    """RN-72: % de componentes adicionais sobre o frete total.

    None (não 0, não 100) quando não há dado de composição — ausência de
    dado é um estado próprio, nunca um zero (mesma filosofia de SEM_REF).
    """
    if not composicao or not frete_total:
        return None
    principal = calc_frete_transporte_principal(composicao) or 0.0
    adicionais = max(0.0, frete_total - principal)
    return round(adicionais / frete_total * 100, 2)


def calc_ranking_componentes(composicao: Optional[dict]) -> Optional[list]:
    """RN-74: ranking decrescente dos componentes adicionais (exclui Frete Peso/Valor)."""
    if not composicao:
        return None
    itens = [(cat, val) for cat, val in composicao.items() if cat not in ("Frete Peso", "Frete Valor")]
    return sorted(itens, key=lambda x: x[1], reverse=True)


# Situação do CT-e (MELHORIA 1). Usar sempre estas constantes em vez do
# literal — todo módulo analítico que lê CTeModel para totais/indicadores
# deve filtrar por CTE_STATUS_ATIVO (RN-09; ver docs/06_regras_de_negocio.md).
CTE_STATUS_ATIVO = "ATIVO"
CTE_STATUS_CANCELADO = "CANCELADO"


@dataclass
class CTe:
    id: Optional[int] = None
    empresa_id: int = 0
    transportadora_id: Optional[int] = None
    chave: str = ""
    numero: str = ""
    serie: str = ""
    data_emissao: Optional[date] = None
    tomador_cnpj: str = ""
    destinatario_cnpj: str = ""
    destinatario_nome: str = ""
    peso: float = 0.0
    valor_frete: float = 0.0
    valor_mercadoria: float = 0.0
    municipio_origem: str = ""
    uf_origem: str = ""
    municipio_destino: str = ""
    uf_destino: str = ""
    macro_regiao_destino: Optional[MacroRegiaoEnum] = None
    data_saida: Optional[date] = None
    data_entrega: Optional[date] = None
    origem_importacao: str = "XML"  # XML | EXCEL
    composicao_frete: dict = field(default_factory=dict)
    # Situação do CT-e: ATIVO | CANCELADO
    status: str = CTE_STATUS_ATIVO
    cancelado_em: Optional[date] = None
    protocolo_cancelamento: Optional[str] = None
    numero_evento_cancelamento: Optional[str] = None
    nfes: List[NFe] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO CONCORRÊNCIA LOGÍSTICA — BID DE FRETE (V3.1)
# ═══════════════════════════════════════════════════════════════════════════

class BidStatusEnum(str, Enum):
    RASCUNHO = "RASCUNHO"
    ABERTO = "ABERTO"
    EM_COTACAO = "EM_COTACAO"
    ENCERRADO = "ENCERRADO"
    CANCELADO = "CANCELADO"


class BidTransportadoraStatusEnum(str, Enum):
    CONVIDADA = "CONVIDADA"
    PARTICIPANDO = "PARTICIPANDO"
    PROPOSTA_RECEBIDA = "PROPOSTA_RECEBIDA"
    DESISTIU = "DESISTIU"
    DESCLASSIFICADA = "DESCLASSIFICADA"
    VENCEDORA = "VENCEDORA"


class TipoAgrupamentoEnum(str, Enum):
    REGIAO = "REGIAO"
    UF = "UF"
    FILIAL = "FILIAL"
    TRANSPORTADORA = "TRANSPORTADORA"
    FAIXA_PESO = "FAIXA_PESO"


class PropostaOrigemEnum(str, Enum):
    MANUAL = "MANUAL"
    EXCEL = "EXCEL"


@dataclass
class Bid:
    """Processo de concorrência logística (BID de frete)."""
    id: Optional[int] = None
    empresa_id: int = 0
    nome: str = ""
    descricao: str = ""
    objetivo: str = ""
    observacoes: str = ""
    status: BidStatusEnum = BidStatusEnum.RASCUNHO
    segmentacao_tipo: str = "GERAL"
    segmentacao_valor: str = ""
    data_inicio: Optional[date] = None
    data_encerramento: Optional[date] = None
    periodo_analise_inicio: Optional[date] = None
    periodo_analise_fim: Optional[date] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BidEscopo:
    """Linha do escopo do BID — consolidação SQL dos CT-es por grupo."""
    id: Optional[int] = None
    bid_id: int = 0
    tipo_agrupamento: TipoAgrupamentoEnum = TipoAgrupamentoEnum.REGIAO
    valor_grupo: str = ""           # ex: "SUDESTE", "SP", "0-100kg"
    peso_total: float = 0.0         # kg
    valor_frete_total: float = 0.0  # R$
    valor_mercadoria_total: float = 0.0
    qtd_embarques: int = 0
    frete_rs_kg: float = 0.0        # calculado
    frete_pct: float = 0.0          # calculado


@dataclass
class BidTransportadora:
    """Relacionamento entre um BID e uma Transportadora cadastrada."""
    id: Optional[int] = None
    bid_id: int = 0
    transportadora_id: int = 0      # FK → transportadoras (cadastro existente)
    status: BidTransportadoraStatusEnum = BidTransportadoraStatusEnum.CONVIDADA
    observacoes: str = ""
    avaliacao_usuario: Optional[float] = None  # 0-10 (compõe score)


@dataclass
class BidProposta:
    """Proposta de preço de uma transportadora convidada."""
    id: Optional[int] = None
    bid_id: int = 0
    bid_transportadora_id: int = 0
    tipo_agrupamento: TipoAgrupamentoEnum = TipoAgrupamentoEnum.REGIAO
    valor_grupo: str = ""
    valor_rs_kg: float = 0.0
    valor_minimo: float = 0.0
    prazo_dias: int = 0
    cobertura_pct: float = 100.0
    observacoes: str = ""
    origem: PropostaOrigemEnum = PropostaOrigemEnum.MANUAL
    created_at: Optional[datetime] = None


@dataclass
class BidSimulacao:
    """Cenário de distribuição de carga entre transportadoras."""
    id: Optional[int] = None
    bid_id: int = 0
    nome: str = ""
    descricao: str = ""
    itens: List[dict] = field(default_factory=list)  # [{bid_transportadora_id, valor_grupo, pct_alocado}]
    custo_atual: float = 0.0
    custo_proposto: float = 0.0
    economia_total: float = 0.0
    reducao_pct: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class BidAuditoria:
    """Trilha de auditoria de todas as ações do BID."""
    id: Optional[int] = None
    bid_id: int = 0
    user_id: Optional[int] = None
    acao: str = ""
    detalhe: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════
# V4 — INTELIGÊNCIA LOGÍSTICA COM IA
# ════════════════════════════════════════════════════════════════════

class InsightCategoriaEnum(str, Enum):
    CUSTO = "CUSTO"
    PERFORMANCE = "PERFORMANCE"
    BENCHMARK = "BENCHMARK"
    TRANSPORTADORAS = "TRANSPORTADORAS"
    FILIAIS = "FILIAIS"
    REGIOES = "REGIOES"


class InsightClassificacaoEnum(str, Enum):
    INFORMATIVO = "INFORMATIVO"
    ATENCAO = "ATENCAO"
    CRITICO = "CRITICO"
    OPORTUNIDADE = "OPORTUNIDADE"


class OportunidadeTipoEnum(str, Enum):
    BID = "BID"
    CONSOLIDACAO = "CONSOLIDACAO"
    REDISTRIBUICAO = "REDISTRIBUICAO"
    RENEGOCIACAO = "RENEGOCIACAO"
    CONCENTRACAO = "CONCENTRACAO"


class SegmentoEnum(str, Enum):
    INDUSTRIA = "INDUSTRIA"
    DISTRIBUIDOR = "DISTRIBUIDOR"
    ATACADISTA = "ATACADISTA"
    VAREJO = "VAREJO"
    ECOMMERCE = "ECOMMERCE"
    AGRONEGOCIO = "AGRONEGOCIO"


@dataclass
class RegraInsight:
    """Regra configurável do motor de insights (armazenada no banco)."""
    id: Optional[int] = None
    empresa_id: Optional[int] = None       # None = regra global
    nome: str = ""
    categoria: str = InsightCategoriaEnum.CUSTO.value
    classificacao: str = InsightClassificacaoEnum.ATENCAO.value
    # Expressão avaliada: ex. "frete_regiao > benchmark * 1.15"
    expressao: str = ""
    titulo_template: str = ""
    descricao_template: str = ""
    ativa: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Insight:
    """Insight gerado automaticamente pelo motor de regras."""
    id: Optional[int] = None
    empresa_id: int = 0
    regra_id: Optional[int] = None
    categoria: str = InsightCategoriaEnum.CUSTO.value
    classificacao: str = InsightClassificacaoEnum.INFORMATIVO.value
    titulo: str = ""
    descricao: str = ""
    impacto_financeiro: float = 0.0
    prioridade: int = 3                    # 1 (alta) a 5 (baixa)
    dados: dict = field(default_factory=dict)
    lido: bool = False
    created_at: Optional[datetime] = None


@dataclass
class InsightExecucao:
    """Registro de cada execução do motor de insights."""
    id: Optional[int] = None
    empresa_id: int = 0
    total_insights: int = 0
    duracao_ms: int = 0
    status: str = "OK"
    erro: str = ""
    created_at: Optional[datetime] = None


@dataclass
class DiagnosticoIA:
    """Diagnóstico executivo gerado por IA."""
    id: Optional[int] = None
    empresa_id: int = 0
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    resumo_executivo: str = ""
    pontos_fortes: str = ""
    pontos_atencao: str = ""
    principais_desvios: str = ""
    economia_potencial: float = 0.0
    plano_acao: str = ""
    score_logistico: float = 0.0
    modelo_usado: str = ""
    cache_hash: str = ""
    created_at: Optional[datetime] = None


@dataclass
class DiagnosticoHistorico:
    """Snapshot histórico de diagnósticos para comparação temporal."""
    id: Optional[int] = None
    empresa_id: int = 0
    diagnostico_id: int = 0
    score: float = 0.0
    economia_potencial: float = 0.0
    resumo: str = ""
    created_at: Optional[datetime] = None


@dataclass
class ScoreLogistico:
    """Score logístico 0-100 da operação."""
    id: Optional[int] = None
    empresa_id: int = 0
    score_total: float = 0.0
    score_benchmark_nacional: float = 0.0     # peso 30%
    score_benchmark_regional: float = 0.0     # peso 20%
    score_transportadoras: float = 0.0        # peso 20%
    score_filiais: float = 0.0                # peso 15%
    score_economia: float = 0.0               # peso 15%
    classificacao: str = ""                   # Excelente/Muito Bom/Regular/Crítico/Muito Crítico
    periodo_referencia: Optional[date] = None
    created_at: Optional[datetime] = None


@dataclass
class ScoreHistorico:
    """Histórico de scores para evolução temporal."""
    id: Optional[int] = None
    empresa_id: int = 0
    score_total: float = 0.0
    classificacao: str = ""
    periodo_referencia: Optional[date] = None
    created_at: Optional[datetime] = None


@dataclass
class BenchmarkSetorial:
    """Benchmark de referência por segmento de mercado."""
    id: Optional[int] = None
    segmento: str = SegmentoEnum.INDUSTRIA.value
    frete_kg_medio: float = 0.0
    frete_pct_medio: float = 0.0
    custo_medio: float = 0.0
    regiao: str = ""
    created_at: Optional[datetime] = None


@dataclass
class Oportunidade:
    """Oportunidade de economia identificada automaticamente."""
    id: Optional[int] = None
    empresa_id: int = 0
    tipo: str = OportunidadeTipoEnum.BID.value
    titulo: str = ""
    descricao: str = ""
    economia_estimada: float = 0.0
    impacto: str = "MEDIO"            # ALTO / MEDIO / BAIXO
    complexidade: str = "MEDIA"       # ALTA / MEDIA / BAIXA
    prioridade: int = 3
    justificativa: str = ""
    status: str = "ABERTA"            # ABERTA / EM_ANDAMENTO / CONCLUIDA / DESCARTADA
    dados: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class PlanoAcao:
    """Ação concreta sugerida para uma oportunidade."""
    id: Optional[int] = None
    empresa_id: int = 0
    oportunidade_id: Optional[int] = None
    acao: str = ""
    impacto: str = "MEDIO"
    economia_estimada: float = 0.0
    prioridade: str = "MEDIA"
    prazo_dias: int = 30
    status: str = "PENDENTE"
    created_at: Optional[datetime] = None


@dataclass
class ChatSessao:
    """Sessão de conversa com o assistente logístico."""
    id: Optional[int] = None
    empresa_id: int = 0
    user_id: Optional[int] = None
    titulo: str = "Nova conversa"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ChatMensagem:
    """Mensagem dentro de uma sessão de chat."""
    id: Optional[int] = None
    sessao_id: int = 0
    empresa_id: int = 0
    papel: str = "user"              # user / assistant
    conteudo: str = ""
    ferramentas_usadas: dict = field(default_factory=dict)
    tokens: int = 0
    created_at: Optional[datetime] = None


@dataclass
class UsageLog:
    """Registro de uso de IA para auditoria e controle de custo."""
    id: Optional[int] = None
    empresa_id: Optional[int] = None
    user_id: Optional[int] = None
    feature: str = ""                # diagnostico / relatorio / chat / insight / score
    modelo: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    custo_usd: float = 0.0
    custo_brl: float = 0.0
    simulado: bool = True
    created_at: Optional[datetime] = None


@dataclass
class DocumentoVetorial:
    """Documento indexado para RAG (pgvector)."""
    id: Optional[int] = None
    empresa_id: int = 0
    tipo_documento: str = ""         # benchmark / relatorio / diagnostico / bid / legislacao
    titulo: str = ""
    conteudo: str = ""
    data_referencia: Optional[date] = None
    metadata: dict = field(default_factory=dict)
    indexado: bool = False
    created_at: Optional[datetime] = None


@dataclass
class EmbeddingJob:
    """Job de geração de embeddings para documentos."""
    id: Optional[int] = None
    empresa_id: int = 0
    documento_id: int = 0
    status: str = "PENDENTE"         # PENDENTE / PROCESSANDO / CONCLUIDO / ERRO
    erro: str = ""
    created_at: Optional[datetime] = None
