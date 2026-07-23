"""DTOs da camada de aplicação (resultados de casos de uso)."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IndicadorNacional:
    valor_total_frete: float = 0.0
    valor_total_mercadoria: float = 0.0
    peso_total: float = 0.0
    frete_rs_kg: float = 0.0
    frete_pct: float = 0.0
    meta_rs_kg: Optional[float] = None
    meta_pct: Optional[float] = None
    desvio_rs_kg: Optional[float] = None
    desvio_pct: Optional[float] = None
    qtd_ctes: int = 0            # ativos (mantido por compatibilidade)
    # ── Situação dos CT-es (MELHORIAS 3, 4 e 7) ──
    qtd_ctes_emitidos: int = 0
    qtd_ctes_ativos: int = 0
    qtd_ctes_cancelados: int = 0
    pct_cancelados: float = 0.0
    custo_medio_kg: float = 0.0
    # ── Referência de mercado para % Frete/Mercadoria (MELHORIA 6) ──
    ref_pct_ideal_max: Optional[float] = None
    ref_pct_mercado_min: Optional[float] = None
    ref_pct_mercado_max: Optional[float] = None
    # ── Meta mensal de orçamento nacional (v6.12) — indicador "Evolução mensal de frete" ──
    orcamento_mensal: Optional[float] = None


@dataclass
class IndicadorRegional:
    macro_regiao: str = ""
    frete_total: float = 0.0
    mercadoria_total: float = 0.0
    peso_total: float = 0.0
    frete_rs_kg: float = 0.0
    frete_pct: float = 0.0
    meta_rs_kg: Optional[float] = None
    meta_pct: Optional[float] = None
    qtd_ctes: int = 0
    orcamento_mensal: Optional[float] = None
    orcamento_periodo: Optional[float] = None


@dataclass
class IndicadorTransportadora:
    transportadora_id: Optional[int]
    nome: str = ""
    frete_total: float = 0.0
    mercadoria_total: float = 0.0
    participacao_pct: float = 0.0
    frete_rs_kg: float = 0.0
    frete_pct: float = 0.0
    custo_medio_entrega: float = 0.0
    qtd_ctes: int = 0
    peso_transportado: float = 0.0


@dataclass
class IndicadorPrazo:
    macro_regiao: str = ""
    prazo_medio: float = 0.0
    entregas_no_prazo: int = 0
    entregas_atraso: int = 0
    sla_pct: float = 0.0
    prazo_meta: Optional[int] = None


@dataclass
class Diagnostico:
    empresa_id: int
    empresa_nome: str = ""
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    nacional: IndicadorNacional = field(default_factory=IndicadorNacional)
    regionais: List[IndicadorRegional] = field(default_factory=list)
    transportadoras: List[IndicadorTransportadora] = field(default_factory=list)
    prazos: List[IndicadorPrazo] = field(default_factory=list)
    composicao_frete: dict = field(default_factory=dict)
    oportunidades: List[str] = field(default_factory=list)
    # Série mensal do Frete Total (sparkline do card — últimos meses, apenas
    # CT-es ativos). Alimenta a tendência de gasto no Dashboard. (mock 07/2026)
    evolucao_frete: List["EvolucaoMensalItem"] = field(default_factory=list)


@dataclass
class ResultadoImportacao:
    importados: int = 0
    ignorados_sem_vinculo: int = 0
    duplicados: int = 0
    atualizados: int = 0
    sem_identificador: int = 0
    erros: List[str] = field(default_factory=list)
    total_processados: int = 0


@dataclass
class OcorrenciaCancelamento:
    """Uma linha do log de importação de evento de cancelamento (MELHORIA 1)."""
    arquivo: str = ""
    chave: str = ""
    resultado: str = ""            # CANCELADO | DUPLICADO | CTE_NAO_ENCONTRADO | ERRO
    mensagem: str = ""


@dataclass
class ResultadoCancelamento:
    """Resumo da importação de eventos de cancelamento de CT-e (MELHORIA 1)."""
    total_processados: int = 0
    cancelados: int = 0
    duplicados: int = 0
    nao_encontrados: int = 0
    erros: int = 0
    ocorrencias: List[OcorrenciaCancelamento] = field(default_factory=list)


@dataclass
class OcorrenciaCCe:
    """Uma linha do log de registro de Carta de Correção (CCe, v6.11)."""
    arquivo: str = ""
    chave: str = ""
    resultado: str = ""            # REGISTRADA | DUPLICADO | NAO_ENCONTRADO | ERRO
    mensagem: str = ""


@dataclass
class ResultadoCCe:
    """Resumo do registro de Cartas de Correção de CT-e (v6.11).

    A CCe nunca é aplicada automaticamente ao CT-e — apenas registrada no log
    de auditoria para revisão manual do analista (ver `CartaCorrecaoCteUseCase`).
    """
    total_processados: int = 0
    registradas: int = 0
    duplicados: int = 0
    nao_encontrados: int = 0
    erros: int = 0
    ocorrencias: List[OcorrenciaCCe] = field(default_factory=list)


# ===================== Módulo Benchmark Logístico =====================
@dataclass
class ComparacaoBenchmark:
    """Comparação de um indicador da empresa contra a referência de mercado."""
    valor: float = 0.0
    benchmark_min: float = 0.0
    benchmark_medio: float = 0.0
    benchmark_max: float = 0.0
    desvio_pct: float = 0.0          # desvio vs. benchmark médio (%)
    classificacao: str = "Sem referência"
    dentro_faixa: bool = False       # valor <= benchmark_max


@dataclass
class BenchmarkNacional:
    empresa_nome: str = ""
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    valor_total_frete: float = 0.0
    peso_total: float = 0.0
    valor_total_mercadoria: float = 0.0
    qtd_ctes: int = 0
    frete_kg: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)
    frete_pct: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)


@dataclass
class BenchmarkRegionalItem:
    macro_regiao: str = ""
    frete_total: float = 0.0
    peso_total: float = 0.0
    qtd_ctes: int = 0
    frete_kg: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)
    frete_pct: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)


@dataclass
class BenchmarkTransportadoraItem:
    transportadora_id: Optional[int] = None
    nome: str = ""
    frete_total: float = 0.0
    peso_transportado: float = 0.0
    participacao_pct: float = 0.0
    qtd_ctes: int = 0
    nivel_custo: str = ""            # "Melhor custo" / "Custo médio" / "Pior custo"
    frete_kg: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)
    frete_pct: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)


# ----------- Potencial de Economia (seção 11) -----------
@dataclass
class EconomiaRegiaoItem:
    macro_regiao: str = ""
    frete_total: float = 0.0
    peso_total: float = 0.0
    frete_rs_kg: float = 0.0
    benchmark_medio: float = 0.0
    economia: float = 0.0


@dataclass
class PotencialEconomia:
    economia_total: float = 0.0          # economia do período (R$)
    economia_pct: float = 0.0            # economia / frete total (%)
    frete_total: float = 0.0
    peso_total: float = 0.0
    meses_periodo: float = 1.0
    economia_mensal: float = 0.0         # ritmo mensal (projeção base)
    proj_mensal: float = 0.0
    proj_trimestral: float = 0.0
    proj_semestral: float = 0.0
    proj_anual: float = 0.0
    por_regiao: List[EconomiaRegiaoItem] = field(default_factory=list)
    # V2.1 — economia detalhada por corredor OD (base de cálculo)
    por_corredor: List["EconomiaCorredorItem"] = field(default_factory=list)


# ----------- Evolução mensal + Dashboard Executivo (seção 13) -----------
@dataclass
class EvolucaoMensalItem:
    mes: str = ""                        # AAAA-MM
    frete_total: float = 0.0
    frete_rs_kg: float = 0.0
    frete_pct: float = 0.0


@dataclass
class DashboardExecutivo:
    empresa_nome: str = ""
    frete_kg_atual: float = 0.0
    benchmark_nacional_kg: float = 0.0
    benchmark_regional_kg: float = 0.0   # média regional ponderada por peso
    economia_mensal: float = 0.0
    economia_total: float = 0.0
    melhor_transportadora: str = ""
    melhor_transportadora_kg: float = 0.0
    pior_transportadora: str = ""
    pior_transportadora_kg: float = 0.0
    evolucao: List[EvolucaoMensalItem] = field(default_factory=list)
    regionais: List["BenchmarkRegionalItem"] = field(default_factory=list)
    transportadoras: List["BenchmarkTransportadoraItem"] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# BENCHMARK LOGÍSTICO V2.1 — MODELO ORIGEM → DESTINO (OD)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkCorredorItem:
    """Resultado de um corredor (Hub origem → Hub destino) vs. referência."""
    hub_origem: str = ""              # código do hub de origem
    hub_origem_nome: str = ""
    hub_destino: str = ""             # código do hub de destino
    hub_destino_nome: str = ""
    corredor: str = ""                # rótulo "Origem → Destino"
    # volume da empresa neste corredor
    frete_total: float = 0.0
    peso_total: float = 0.0
    mercadoria_total: float = 0.0
    qtd_ctes: int = 0
    frete_rs_kg: float = 0.0
    frete_pct: float = 0.0
    # comparação com a referência global do corredor
    tem_referencia: bool = False      # se False → tela mostra CTA "cadastrar referência"
    frete_kg: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)
    frete_pct_comp: ComparacaoBenchmark = field(default_factory=ComparacaoBenchmark)
    # itens que compõem o corredor (pares UF→UF agregados), p/ transparência
    ufs_origem: List[str] = field(default_factory=list)
    ufs_destino: List[str] = field(default_factory=list)
    # score do corredor (0-100)
    score: float = 0.0
    classificacao: str = "Sem referência"


@dataclass
class BenchmarkODResultado:
    """Visão completa do benchmark OD (lista de corredores + score global)."""
    empresa_nome: str = ""
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    score_global: float = 0.0
    classificacao_global: str = "Sem referência"
    qtd_corredores: int = 0
    corredores_sem_referencia: int = 0
    frete_total: float = 0.0
    peso_total: float = 0.0
    corredores: List[BenchmarkCorredorItem] = field(default_factory=list)


@dataclass
class EconomiaCorredorItem:
    corredor: str = ""
    hub_origem: str = ""
    hub_destino: str = ""
    frete_total: float = 0.0
    peso_total: float = 0.0
    frete_rs_kg: float = 0.0
    benchmark_medio: float = 0.0
    tem_referencia: bool = False
    economia: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# SIMULADOR DE HUB DE ORIGEM
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SimulacaoHubRotaItem:
    """Uma rota (hub atual → hub destino) real da empresa, comparada contra a
    referência de mercado do MESMO destino partindo do hub alternativo."""
    hub_destino: str = ""
    hub_destino_nome: str = ""
    # operação real da empresa hoje, no hub atual, para este destino
    qtd_ctes: int = 0
    peso_total: float = 0.0
    frete_atual_total: float = 0.0
    frete_atual_rs_kg: float = 0.0
    # simulação: referência de mercado do hub alternativo aplicada ao MESMO
    # peso real da empresa (não é dado observado — é estimativa de mercado)
    tem_referencia_alt: bool = False   # False → sem referência cadastrada p/ este par; tela mostra CTA
    frete_simulado_rs_kg: float = 0.0
    frete_simulado_total: float = 0.0
    delta_custo_pct: float = 0.0
    # prazo: atual é observado (CT-e), simulado é referência de mercado (pode faltar)
    prazo_atual_dias: Optional[float] = None
    amostra_prazo_atual: int = 0
    prazo_simulado_dias: Optional[float] = None
    delta_prazo_dias: Optional[float] = None
    # confiança: amostra real abaixo do threshold do MBL não deve embasar decisão
    baixa_confianca: bool = False
    # "manter_atual" | "avaliar_alternativo" | "dados_insuficientes"
    recomendacao: str = "dados_insuficientes"


@dataclass
class SimulacaoHubResultado:
    hub_atual: str = ""
    hub_atual_nome: str = ""
    hub_alt: str = ""
    hub_alt_nome: str = ""
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    opera_no_hub_atual: bool = False   # False → empresa não tem CT-e real partindo deste hub no período
    rotas: List[SimulacaoHubRotaItem] = field(default_factory=list)
    qtd_rotas: int = 0
    rotas_com_referencia: int = 0
    rotas_sem_referencia: int = 0
    rotas_com_ganho: int = 0           # dentre as com referência: custo simulado < atual
    rotas_com_perda: int = 0
    frete_atual_total: float = 0.0             # soma de TODAS as rotas reais do hub atual
    frete_comparavel_total: float = 0.0        # soma só das rotas COM referência (base do delta)
    frete_simulado_total: float = 0.0          # soma simulada das rotas com referência
    delta_custo_total_pct: float = 0.0         # sobre frete_comparavel_total, não frete_atual_total
    prazo_atual_medio_dias: Optional[float] = None
    prazo_simulado_medio_dias: Optional[float] = None
    nota: str = ""

