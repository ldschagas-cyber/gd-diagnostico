"""Schemas de saída do Portal do Cliente (v6.18.0).

Importados diretamente em app/presentation/api/v1/portal_cliente.py (mesmo
padrão de dlg_schemas.py — não são re-exportados por
app/presentation/schemas/__init__.py).

Ver Especificação Técnica v6.18.0 §3.6/§3.8 para a origem de cada campo e os
dois ajustes de escopo (custo por macrorregião em vez de UF; impacto no
período analisado em vez de "anual" por item).
"""
from typing import List

from pydantic import BaseModel, ConfigDict


class PortalClienteUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    nome: str
    email: str
    empresa_nome: str = ""


class PortalResumoItemOut(BaseModel):
    chave: str      # "performance" | "benchmark" | "economia" | "plano_acao"
    status: str     # "verde" | "amarelo" | "vermelho"
    titulo: str
    valor: str


class PortalKpisOut(BaseModel):
    economia_potencial_anual: float
    aderencia_mercado_pct: float
    performance_logistica: float
    rotas_acima_benchmark: int
    transportadoras_monitoradas: int


class PortalEvolucaoItemOut(BaseModel):
    mes: str            # "AAAA-MM"
    custo_real_kg: float


class PortalBenchmarkRegiaoOut(BaseModel):
    """Comparação empresa vs. mercado por macrorregião — ver §3.8.1: o
    protótipo mostrava categorias de serviço (Frete rodoviário/Armazenagem/
    Última milha/Devolução), que não existem como dimensão real hoje; a
    dimensão real disponível é macrorregião (mesma usada em "Custo por
    Região")."""
    regiao: str
    valor_empresa_kg: float
    valor_mercado_kg: float


class PortalCustoRegiaoOut(BaseModel):
    regiao: str
    custo_kg: float


class PortalEconomiaRegiaoOut(BaseModel):
    """Potencial de economia por macrorregião — mesma ressalva de §3.8.1: o
    protótipo mostrava categorias de iniciativa (renegociação, tabela de
    frete, HUB); a quebra real disponível é por macrorregião."""
    regiao: str
    valor: float


class PortalPotencialEconomiaOut(BaseModel):
    total_anual: float
    por_regiao: List[PortalEconomiaRegiaoOut]


class PortalPlanoAcaoItemOut(BaseModel):
    id: int
    titulo: str
    categoria: str
    status: str    # "pendente" | "andamento" | "concluido"


class PortalDashboardOut(BaseModel):
    empresa_nome: str
    resumo: List[PortalResumoItemOut]
    kpis: PortalKpisOut
    evolucao_frete: List[PortalEvolucaoItemOut]
    referencia_mercado_kg: float
    benchmark_mercado: List[PortalBenchmarkRegiaoOut]
    custo_por_regiao: List[PortalCustoRegiaoOut]
    potencial_economia: PortalPotencialEconomiaOut
    plano_acao: List[PortalPlanoAcaoItemOut]
    plano_acao_concluidas: int
    plano_acao_total: int


class PortalOportunidadeOut(BaseModel):
    id: int
    titulo: str
    descricao: str
    categoria: str
    prioridade: str    # "alta" | "media" | "baixa"
    status: str        # "pendente" | "andamento" | "concluido"
    impacto_estimado: float   # valor no período analisado — NÃO anualizado, ver §3.8.2
    priorizada_pelo_cliente: bool
