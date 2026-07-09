"""Schemas de saída do módulo DLG (Diagnóstico Logístico).
Importados em app/presentation/schemas/__init__.py.
"""
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel


class DlgAnaliticoOut(BaseModel):
    id: int = 0  # 0 nas linhas consolidadas (não correspondem a um registro físico)
    empresa_id: int
    dimensao: str
    chave: str
    chave_label: str
    periodo_ref: str  # "YYYY-MM" no modo mensal; "CONSOLIDADO" no consolidado
    qtd_ctes: int
    peso_total: float
    frete_total: float
    mercadoria_total: float
    rs_kg: float
    pct_frete: float
    custo_medio_entrega: float
    rs_kg_ref: float
    desvio_pct: float
    classificacao: str
    # ── derivados (v6.7.0) — Optional e aplicável às 5 dimensões, ainda que só
    # façam sentido de negócio para CLIENTE_FINAL nesta versão (Especificação
    # Técnica §3.9 — evita `if dimensao == "CLIENTE_FINAL"` espalhado na API).
    peso_medio: Optional[float] = None
    ticket_medio: Optional[float] = None
    impacto_financeiro_potencial: Optional[float] = None
    composicao_frete: Optional[Dict[str, float]] = None
    frete_transporte_principal: Optional[float] = None
    pct_componentes_adicionais: Optional[float] = None  # None = sem dado de composição, não zero (RN-72)
    ranking_componentes: Optional[List[Tuple[str, float]]] = None
    sinal_fragmentacao: Optional[bool] = None
    causa_dominante: Optional[str] = None  # ADICIONAIS | FRAGMENTACAO | AMBAS | NENHUMA — só ATENCAO/CRITICO

    class Config:
        from_attributes = True


class DlgOutlierOut(BaseModel):
    id: int
    empresa_id: int
    cte_id: int
    periodo_ref: str
    tipo_outlier: str
    valor_real: float
    valor_limite: float
    desvio_pct: float

    class Config:
        from_attributes = True


class DlgProcessarOut(BaseModel):
    status: str
    ctes: int = 0
    periodos: List[str] = []
    analiticos: int = 0
    outliers: int = 0


class DlgTopItem(BaseModel):
    chave: str
    frete: float
    rs_kg: float
    classificacao: Optional[str] = None
    desvio_pct: Optional[float] = None


class DlgResumoOut(BaseModel):
    total_ctes: int = 0
    frete_total: float = 0.0
    rs_kg_medio: float = 0.0
    pct_frete_merc_medio: float = 0.0
    distribuicao_classificacao: Dict[str, int] = {}
    top_filiais: List[dict] = []
    top_clientes: List[dict] = []  # compatibilidade retroativa (aponta para FILIAL)
    top_clientes_finais: List[dict] = []  # v6.7.0 — dimensão CLIENTE_FINAL (destinatário)
    top_rotas_criticas: List[dict] = []
    por_dimensao: Dict[str, Dict[str, int]] = {}
