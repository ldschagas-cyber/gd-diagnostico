"""Schemas Pydantic (validação/serialização da API)."""
import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.entities import (
    MacroRegiaoEnum,
    RegiaoBenchmarkEnum,
    SetorEnum,
    StatusEnum,
)


# ── Validadores reutilizáveis ─────────────────────────────────────────────────
def _validar_cnpj(cnpj: str) -> str:
    """Valida o dígito verificador do CNPJ (algoritmo módulo 11).

    Aceita formatos com ou sem máscara (XX.XXX.XXX/XXXX-XX).
    Recusa CNPJs com todos os dígitos iguais (ex: 00.000.000/0000-00).
    """
    if not cnpj:
        return cnpj
    digits = "".join(c for c in cnpj if c.isdigit())
    if len(digits) != 14:
        raise ValueError(f"CNPJ deve ter 14 dígitos (recebido: {len(digits)})")
    if len(set(digits)) == 1:
        raise ValueError("CNPJ inválido — todos os dígitos são iguais")

    def _calc(d, pesos):
        s = sum(int(d[i]) * pesos[i] for i in range(len(pesos)))
        r = s % 11
        return "0" if r < 2 else str(11 - r)

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if digits[12] != _calc(digits, pesos1) or digits[13] != _calc(digits, pesos2):
        raise ValueError("CNPJ inválido — dígito verificador incorreto")
    return digits  # devolve apenas dígitos (normalizado)


# ---------------- Auth / User ----------------
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class UserBase(BaseModel):
    nome: str
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    empresa_id: Optional[int] = None      # empresa padrão/preferida (pré-seleção no login)
    empresas_ids: List[int] = []          # vínculo real (M:N, v6.14) — fonte da autorização
    role: Optional[str] = None            # papel (R-04)


class UserCreate(UserBase):
    senha: str = Field(
        min_length=8,
        description="Mínimo 8 caracteres com pelo menos uma letra e um número",
    )

    @field_validator("senha")
    @classmethod
    def senha_complexidade(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra")
        if not any(c.isdigit() for c in v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = Field(default=None, min_length=6)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    empresas_ids: Optional[List[int]] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


# ---------------- Empresa ----------------
class EmpresaBase(BaseModel):
    razao_social: str
    nome_fantasia: str = ""
    cnpj_matriz: str
    status: StatusEnum = StatusEnum.ATIVO
    setor: SetorEnum  # obrigatório (RF002): segmento econômico do embarcador

    @field_validator("cnpj_matriz")
    @classmethod
    def validar_cnpj_matriz(cls, v: str) -> str:
        return _validar_cnpj(v)


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj_matriz: Optional[str] = None
    status: Optional[StatusEnum] = None
    setor: Optional[SetorEnum] = None


class EmpresaOut(EmpresaBase):
    id: int


# ---------------- Filial ----------------
class FilialBase(BaseModel):
    empresa_id: int
    razao_social: str
    cnpj: str
    cidade: str = ""
    uf: str = ""

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj_filial(cls, v: str) -> str:
        return _validar_cnpj(v)


class FilialCreate(FilialBase):
    pass


class FilialOut(FilialBase):
    id: int


# ---------------- Transportadora ----------------
class TransportadoraBase(BaseModel):
    razao_social: str
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


class TransportadoraCreate(TransportadoraBase):
    pass


class TransportadoraOut(TransportadoraBase):
    id: int


# ---------------- Região ----------------
class RegiaoBase(BaseModel):
    nome: str
    descricao: str = ""


class RegiaoCreate(RegiaoBase):
    pass


class RegiaoOut(RegiaoBase):
    id: int


# ---------------- Cidade ----------------
class CidadeBase(BaseModel):
    nome: str
    uf: str
    regiao_id: Optional[int] = None
    macro_regiao: Optional[MacroRegiaoEnum] = None


class CidadeCreate(CidadeBase):
    pass


class CidadeOut(CidadeBase):
    id: int


# ---------------- Metas ----------------
class MetaNacionalIn(BaseModel):
    meta_rs_kg: float
    meta_pct_frete: float


class MetaNacionalOut(MetaNacionalIn):
    id: Optional[int] = None
    empresa_id: Optional[int] = None


class MetaRegionalIn(BaseModel):
    macro_regiao: MacroRegiaoEnum
    meta_rs_kg: float
    meta_pct_frete: float
    prazo_medio_meta: int = 0
    orcamento_mensal: float = 0.0


class MetaRegionalOut(MetaRegionalIn):
    id: Optional[int] = None
    empresa_id: Optional[int] = None


# ---------------- Fechamento Mensal (Fechamento de Custo de Frete) ---------
_RE_COMPETENCIA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class FechamentoMensalIn(BaseModel):
    competencia: str  # "AAAA-MM"
    fat_norte: float = 0.0
    fat_nordeste: float = 0.0
    fat_centro_oeste: float = 0.0
    fat_sudeste: float = 0.0
    fat_sul: float = 0.0
    devolucao: float = 0.0
    frete_complementar: float = 0.0

    @field_validator("competencia")
    @classmethod
    def _validar_competencia(cls, v: str) -> str:
        if not _RE_COMPETENCIA.match(v):
            raise ValueError("competencia deve estar no formato AAAA-MM")
        return v


class FechamentoAcaoIn(BaseModel):
    """Body de /fechar e /reabrir — só a competência-alvo."""
    competencia: str

    @field_validator("competencia")
    @classmethod
    def _validar_competencia(cls, v: str) -> str:
        if not _RE_COMPETENCIA.match(v):
            raise ValueError("competencia deve estar no formato AAAA-MM")
        return v


class FechamentoRegionalOut(BaseModel):
    macro_regiao: MacroRegiaoEnum
    fat_real: float
    frete_real: float
    pct_frete_fat_real: float
    fat_budget: float
    frete_budget: float
    pct_frete_fat_budget: float
    representatividade_real: float
    representatividade_budget: float


class FechamentoRegionalTotalOut(BaseModel):
    fat_real: float
    frete_real: float
    pct_frete_fat_real: float
    fat_budget: float
    frete_budget: float
    pct_frete_fat_budget: float


class FechamentoMensalOut(BaseModel):
    competencia: str
    status: str
    fechado_em: Optional[datetime] = None
    fat_norte: float
    fat_nordeste: float
    fat_centro_oeste: float
    fat_sudeste: float
    fat_sul: float
    devolucao: float
    frete_complementar: float
    faturamento_total: float
    frete_contratado: float
    regional: List[FechamentoRegionalOut]
    regional_total: FechamentoRegionalTotalOut


class FechamentoHistoricoItemOut(BaseModel):
    competencia: str
    status: str
    faturamento_total: float
    devolucao: float
    frete_complementar: float
    frete_contratado: float


# ---------------- Importação ----------------
class ResultadoImportacaoOut(BaseModel):
    importados: int
    ignorados_sem_vinculo: int
    duplicados: int
    atualizados: int = 0
    sem_identificador: int = 0
    total_processados: int
    erros: List[str]


class ContagemImportacaoOut(BaseModel):
    """Contagem de registros importados por origem (para gestão/exclusão)."""
    total: int
    xml: int
    excel: int


class CompetenciaCteOut(BaseModel):
    """Quantidade de CT-es armazenados em uma competência (mês/ano da emissão).

    Alimenta o indicador de base de CT-e da tela de importação. A lista é
    ordenada do período mais recente para o mais antigo; competências sem
    registros simplesmente não aparecem.
    """
    ano: int
    mes: int
    competencia: str  # "AAAA-MM"
    rotulo: str        # "MM/AAAA"
    quantidade: int    # compatibilidade: = emitidos
    emitidos: int = 0
    ativos: int = 0
    cancelados: int = 0


class ResultadoExclusaoOut(BaseModel):
    excluidos: int


# ---------------- Cancelamento de CT-e (MELHORIA 1) ----------------
class OcorrenciaCancelamentoOut(BaseModel):
    arquivo: str
    chave: str
    resultado: str      # CANCELADO | DUPLICADO | CTE_NAO_ENCONTRADO | ERRO
    mensagem: str


class ResultadoCancelamentoOut(BaseModel):
    total_processados: int
    cancelados: int
    duplicados: int
    nao_encontrados: int
    erros: int
    ocorrencias: List[OcorrenciaCancelamentoOut]


class CancelamentoLogOut(BaseModel):
    id: int
    chave: str
    protocolo: str
    numero_evento: str
    data_cancelamento: Optional[date]
    resultado: str
    mensagem: str
    arquivo: str
    created_at: Optional[datetime]


# ---------------- Carta de Correção de CT-e — CCe (v6.11) ----------------
class OcorrenciaCCeOut(BaseModel):
    arquivo: str
    chave: str
    resultado: str      # REGISTRADA | DUPLICADO | NAO_ENCONTRADO | ERRO
    mensagem: str


class ResultadoCCeOut(BaseModel):
    total_processados: int
    registradas: int
    duplicados: int
    nao_encontrados: int
    erros: int
    ocorrencias: List[OcorrenciaCCeOut]


# ---------------- Importação unificada de CT-e + cancelamento (v6.11) ----------------
class ResultadoImportacaoCteOut(BaseModel):
    """Resultado combinado do upload de um lote de XMLs de CT-e.

    O lote pode conter, ao mesmo tempo, XMLs de CT-e, XMLs de evento de
    cancelamento e XMLs de Carta de Correção (CCe) — cada arquivo é
    classificado automaticamente pelo conteúdo e roteado para o caso de uso
    correspondente. CCe nunca é aplicada automaticamente ao CT-e, apenas
    registrada para revisão manual (ver `carta_correcao`).
    """
    importacao: ResultadoImportacaoOut
    cancelamento: ResultadoCancelamentoOut
    carta_correcao: ResultadoCCeOut


# ---------------- Grid de CT-e individuais (v6.11) ----------------
class CteListaItemOut(BaseModel):
    id: int
    chave: str
    numero: str
    serie: str
    data_emissao: Optional[date]
    transportadora_nome: Optional[str] = None
    municipio_origem: str
    uf_origem: str
    municipio_destino: str
    uf_destino: str
    peso: float
    valor_frete: float
    status: str
    origem_importacao: str
    cancelado_em: Optional[date]


class CteListaPaginadaOut(BaseModel):
    items: List[CteListaItemOut]
    total: int


class ExcluirCtesIn(BaseModel):
    ids: List[int]

    class Config:
        from_attributes = True


# ---------------- Recomendações (MELHORIA 8) ----------------
class RecomendacaoOut(BaseModel):
    id: int
    titulo: str
    descricao: str
    indicador: str
    valor_encontrado: str
    valor_recomendado: str
    impacto: str
    economia_estimada: float
    prioridade: str      # CRITICA | ALTA | MEDIA | BAIXA
    origem: str          # REGRA | IA
    status: str          # ABERTA | EM_ANDAMENTO | CONCLUIDA | DESCARTADA
    dados: Optional[dict] = None  # extra por tipo de recomendação — ex.: {"acao_recomendada": "..."}

    class Config:
        from_attributes = True


class RecomendacaoStatusUpdate(BaseModel):
    status: str = Field(..., description="ABERTA | EM_ANDAMENTO | CONCLUIDA | DESCARTADA")


class RecomendacoesResumoOut(BaseModel):
    total: int
    por_prioridade: dict
    economia_estimada_total: float


# ---------------- Dashboard / Diagnóstico ----------------
class IndicadorNacionalOut(BaseModel):
    valor_total_frete: float
    valor_total_mercadoria: float
    peso_total: float
    frete_rs_kg: float
    frete_pct: float
    meta_rs_kg: Optional[float]
    meta_pct: Optional[float]
    desvio_rs_kg: Optional[float]
    desvio_pct: Optional[float]
    qtd_ctes: int
    # Situação dos CT-es (MELHORIAS 3, 4, 7)
    qtd_ctes_emitidos: int = 0
    qtd_ctes_ativos: int = 0
    qtd_ctes_cancelados: int = 0
    pct_cancelados: float = 0.0
    custo_medio_kg: float = 0.0
    # Referência de mercado para % Frete/Mercadoria (MELHORIA 6)
    ref_pct_ideal_max: Optional[float] = None
    ref_pct_mercado_min: Optional[float] = None
    ref_pct_mercado_max: Optional[float] = None
    # Meta mensal de orçamento nacional (v6.12) — indicador "Evolução mensal de frete"
    orcamento_mensal: Optional[float] = None


class IndicadorRegionalOut(BaseModel):
    macro_regiao: str
    frete_total: float
    mercadoria_total: float
    peso_total: float
    frete_rs_kg: float
    frete_pct: float
    meta_rs_kg: Optional[float]
    meta_pct: Optional[float]
    qtd_ctes: int
    # Orçamento mensal (R$) da Meta Regional e seu equivalente multiplicado
    # pelos meses do período filtrado (None quando não há filtro de período
    # ou a região não tem orçamento mensal configurado).
    orcamento_mensal: Optional[float] = None
    orcamento_periodo: Optional[float] = None


class IndicadorTransportadoraOut(BaseModel):
    transportadora_id: Optional[int]
    nome: str
    frete_total: float
    mercadoria_total: float = 0.0
    participacao_pct: float
    frete_rs_kg: float
    frete_pct: float = 0.0
    custo_medio_entrega: float = 0.0
    qtd_ctes: int
    peso_transportado: float


class IndicadorPrazoOut(BaseModel):
    macro_regiao: str
    prazo_medio: float
    entregas_no_prazo: int
    entregas_atraso: int
    sla_pct: float
    prazo_meta: Optional[int]


class EvolucaoFreteOut(BaseModel):
    """Ponto mensal de evolução (sparkline do card + gráficos de Frete Total,
    % Frete/Mercadoria e Frete por Kg do dashboard)."""
    model_config = ConfigDict(from_attributes=True)
    mes: str
    frete_total: float
    frete_pct: float = 0.0
    frete_rs_kg: float = 0.0


class DiagnosticoOut(BaseModel):
    empresa_id: int
    empresa_nome: str
    periodo_inicio: Optional[str]
    periodo_fim: Optional[str]
    nacional: IndicadorNacionalOut
    regionais: List[IndicadorRegionalOut]
    transportadoras: List[IndicadorTransportadoraOut]
    prazos: List[IndicadorPrazoOut]
    composicao_frete: dict = {}
    oportunidades: List[str]
    # Série mensal do Frete Total (sparkline). Vazia quando não há histórico.
    evolucao_frete: List[EvolucaoFreteOut] = []


# ============== Módulo Benchmark Logístico — análise ==============
class ComparacaoBenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    valor: float
    benchmark_min: float
    benchmark_medio: float
    benchmark_max: float
    desvio_pct: float
    classificacao: str
    dentro_faixa: bool


class BenchmarkNacionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    empresa_nome: str
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    valor_total_frete: float
    peso_total: float
    valor_total_mercadoria: float
    qtd_ctes: int
    frete_kg: ComparacaoBenchmarkOut
    frete_pct: ComparacaoBenchmarkOut


class BenchmarkRegionalItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    macro_regiao: str
    frete_total: float
    peso_total: float
    qtd_ctes: int
    frete_kg: ComparacaoBenchmarkOut
    frete_pct: ComparacaoBenchmarkOut


class BenchmarkTransportadoraItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transportadora_id: Optional[int] = None
    nome: str
    frete_total: float
    peso_transportado: float
    participacao_pct: float
    qtd_ctes: int
    nivel_custo: str
    frete_kg: ComparacaoBenchmarkOut
    frete_pct: ComparacaoBenchmarkOut


# ============== Benchmark — Economia e Executivo ==============
class EconomiaRegiaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    macro_regiao: str
    frete_total: float
    peso_total: float
    frete_rs_kg: float
    benchmark_medio: float
    economia: float


class PotencialEconomiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    economia_total: float
    economia_pct: float
    frete_total: float
    peso_total: float
    meses_periodo: float
    economia_mensal: float
    proj_mensal: float
    proj_trimestral: float
    proj_semestral: float
    proj_anual: float
    por_regiao: List[EconomiaRegiaoOut]
    por_corredor: List["EconomiaCorredorOut"] = []


class EvolucaoMensalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mes: str
    frete_total: float
    frete_rs_kg: float
    frete_pct: float


class DashboardExecutivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    empresa_nome: str
    frete_kg_atual: float
    benchmark_nacional_kg: float
    benchmark_regional_kg: float
    economia_mensal: float
    economia_total: float
    melhor_transportadora: str
    melhor_transportadora_kg: float
    pior_transportadora: str
    pior_transportadora_kg: float
    evolucao: List[EvolucaoMensalOut]
    regionais: List[BenchmarkRegionalItemOut]
    transportadoras: List[BenchmarkTransportadoraItemOut]


# ══════════ Benchmark Logístico V2.1 — Modelo OD ══════════
class HubLogisticoIn(BaseModel):
    codigo: str
    nome: str
    descricao: str = ""
    ativo: bool = True


class HubLogisticoOut(HubLogisticoIn):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    empresa_id: Optional[int] = None


class ClusterClienteIn(BaseModel):
    uf: str
    municipio: str = ""
    hub_id: int


class ClusterClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    empresa_id: int
    uf: str
    municipio: str = ""
    hub_id: int
    hub_codigo: str = ""
    hub_nome: str = ""


class BenchmarkCorredorIn(BaseModel):
    hub_origem_codigo: str
    hub_destino_codigo: str
    frete_kg_min: float = 0.0
    frete_kg_medio: float = 0.0
    frete_kg_max: float = 0.0
    frete_pct_min: float = 0.0
    frete_pct_medio: float = 0.0
    frete_pct_max: float = 0.0
    volume_referencia: float = 0.0
    dispersao_kg: float = 0.0
    prazo_dias_medio: float = 0.0
    observacoes: str = ""


class BenchmarkCorredorOut(BenchmarkCorredorIn):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    empresa_id: Optional[int] = None


class BenchmarkCorredorItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hub_origem: str
    hub_origem_nome: str
    hub_destino: str
    hub_destino_nome: str
    corredor: str
    frete_total: float
    peso_total: float
    mercadoria_total: float
    qtd_ctes: int
    frete_rs_kg: float
    frete_pct: float
    tem_referencia: bool
    frete_kg: ComparacaoBenchmarkOut
    frete_pct_comp: ComparacaoBenchmarkOut
    ufs_origem: List[str]
    ufs_destino: List[str]
    score: float
    classificacao: str


class BenchmarkODResultadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    empresa_nome: str
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    score_global: float
    classificacao_global: str
    qtd_corredores: int
    corredores_sem_referencia: int
    frete_total: float
    peso_total: float
    corredores: List[BenchmarkCorredorItemOut]


class EconomiaCorredorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    corredor: str
    hub_origem: str
    hub_destino: str
    frete_total: float
    peso_total: float
    frete_rs_kg: float
    benchmark_medio: float
    tem_referencia: bool
    economia: float


# ══════════ Simulador de Hub de Origem ══════════
class SimulacaoHubRotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hub_destino: str
    hub_destino_nome: str
    qtd_ctes: int
    peso_total: float
    frete_atual_total: float
    frete_atual_rs_kg: float
    tem_referencia_alt: bool
    frete_simulado_rs_kg: float
    frete_simulado_total: float
    delta_custo_pct: float
    prazo_atual_dias: Optional[float] = None
    amostra_prazo_atual: int
    prazo_simulado_dias: Optional[float] = None
    delta_prazo_dias: Optional[float] = None
    baixa_confianca: bool
    recomendacao: str


class SimulacaoHubResultadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hub_atual: str
    hub_atual_nome: str
    hub_alt: str
    hub_alt_nome: str
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    opera_no_hub_atual: bool
    rotas: List[SimulacaoHubRotaOut]
    qtd_rotas: int
    rotas_com_referencia: int
    rotas_sem_referencia: int
    rotas_com_ganho: int
    rotas_com_perda: int
    frete_atual_total: float
    frete_comparavel_total: float
    frete_simulado_total: float
    delta_custo_total_pct: float
    prazo_atual_medio_dias: Optional[float] = None
    prazo_simulado_medio_dias: Optional[float] = None
    nota: str


# ═══════════════════════════════════════════════════════════════
# MÓDULO BID — Concorrência Logística (V3.1)
# ═══════════════════════════════════════════════════════════════
from app.domain.entities import (
    BidStatusEnum, BidTransportadoraStatusEnum,
    TipoAgrupamentoEnum, PropostaOrigemEnum, RoleEnum,
)


class BidCreate(BaseModel):
    nome: str = Field(min_length=3, max_length=200)
    descricao: str = ""
    objetivo: str = ""
    observacoes: str = ""
    segmentacao_tipo: str = "GERAL"   # GERAL | REGIAO | CIDADE | REGIAO_LOGISTICA
    segmentacao_valor: str = ""
    data_inicio: Optional[date] = None
    data_encerramento: Optional[date] = None
    periodo_analise_inicio: Optional[date] = None
    periodo_analise_fim: Optional[date] = None


class BidOut(BidCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    status: BidStatusEnum
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BidStatusUpdate(BaseModel):
    status: BidStatusEnum


class FaixaPesoIn(BaseModel):
    label: str
    min: float = 0.0
    max: Optional[float] = None


class GerarEscopoIn(BaseModel):
    tipo_agrupamento: TipoAgrupamentoEnum
    faixas_peso: Optional[List[FaixaPesoIn]] = None


class BidEscopoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bid_id: int
    tipo_agrupamento: TipoAgrupamentoEnum
    valor_grupo: str
    peso_total: float
    valor_frete_total: float
    valor_mercadoria_total: float
    qtd_embarques: int
    frete_rs_kg: float
    frete_pct: float


class BidTransportadoraCreate(BaseModel):
    transportadora_id: int
    observacoes: str = ""
    avaliacao_usuario: Optional[float] = Field(None, ge=0, le=10)


class BidTransportadoraOut(BidTransportadoraCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bid_id: int
    status: BidTransportadoraStatusEnum
    transportadora_nome: Optional[str] = None


class BidTransportadoraStatusUpdate(BaseModel):
    status: BidTransportadoraStatusEnum


class BidPropostaCreate(BaseModel):
    bid_transportadora_id: int
    tipo_agrupamento: TipoAgrupamentoEnum
    valor_grupo: str
    valor_rs_kg: float = Field(ge=0)
    valor_minimo: float = 0.0
    prazo_dias: int = 0
    cobertura_pct: float = Field(default=100.0, ge=0, le=100)
    observacoes: str = ""


class BidPropostaOut(BidPropostaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bid_id: int
    origem: PropostaOrigemEnum
    created_at: Optional[datetime] = None


class SimulacaoItemIn(BaseModel):
    bid_transportadora_id: int
    valor_grupo: str
    pct_alocado: float = Field(ge=0, le=100)


class BidSimulacaoCreate(BaseModel):
    nome: str
    descricao: str = ""
    itens: List[SimulacaoItemIn]


class BidSimulacaoOut(BidSimulacaoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bid_id: int
    custo_atual: float
    custo_proposto: float
    economia_total: float
    reducao_pct: float
    created_at: Optional[datetime] = None


class BidAuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bid_id: int
    user_id: Optional[int]
    acao: str
    detalhe: dict
    created_at: Optional[datetime] = None


class PropostaComparativaOut(BaseModel):
    bid_transportadora_id: int
    transportadora: str
    rs_kg: float
    valor_minimo: float
    prazo_dias: int
    cobertura_pct: float
    economia_rs: float
    economia_pct: float
    faixa_mercado: Optional[str] = None          # ABAIXO_P50 | ENTRE_P50_P75 | ACIMA_P75
    delta_mercado_p50_pct: Optional[float] = None


class LinhaComparativaOut(BaseModel):
    valor_grupo: str
    peso_total: float
    frete_atual_rs_kg: float
    custo_atual_total: float
    propostas: List[PropostaComparativaOut]
    melhor_proposta_rs_kg: Optional[float]
    melhor_economia: float
    mercado_p50: Optional[float] = None
    mercado_p75: Optional[float] = None
    mercado_fonte: Optional[str] = None


class EconomiaGrupoOut(BaseModel):
    valor_grupo: str
    frete_atual_rs_kg: float
    melhor_proposta_rs_kg: float
    peso_total: float
    economia: float


class ResultadoEconomiaOut(BaseModel):
    economia_total_periodo: float
    frete_atual_total: float
    economia_pct: float
    meses_periodo: float
    ritmo_mensal: float
    proj_trimestral: float
    proj_semestral: float
    proj_anual: float
    por_grupo: List[EconomiaGrupoOut]


class ScoreTransportadoraOut(BaseModel):
    bid_transportadora_id: int
    transportadora_id: int
    nome: str
    score: float
    classificacao: str
    score_preco: float
    score_prazo: float
    score_cobertura: float
    score_avaliacao: float
    proposta_media_rs_kg: float
    prazo_medio: float
    cobertura_media: float


class ItemSimulacaoOut(BaseModel):
    valor_grupo: str
    bid_transportadora_id: int
    transportadora: str = ""
    pct_alocado: float
    rs_kg: float
    custo: float


class ResultadoSimulacaoOut(BaseModel):
    custo_atual: float
    custo_proposto: float
    economia_total: float
    reducao_pct: float
    itens: List[ItemSimulacaoOut]


class BidDashboardKPIOut(BaseModel):
    total_bids: int
    bids_abertos: int
    bids_encerrados: int
    economia_identificada: float
    economia_contratada: float
    melhor_economia: float
    transportadoras_avaliadas: int
