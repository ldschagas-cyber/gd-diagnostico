# 07 · Módulos do Sistema

> Visão por módulo funcional, cruzando telas (frontend), endpoints (backend) e entidades de dados. Para regras de negócio detalhadas, ver [`06_regras_de_negocio.md`](06_regras_de_negocio.md); para o catálogo completo de endpoints, ver [`05_apis.md`](05_apis.md).

## Administração e Segurança

| | |
|---|---|
| **Telas** | `Usuarios.jsx` (`/usuarios`, restrita a admin) |
| **Endpoints** | `usuarios.py` (4), `auth.py` (4) |
| **Entidades** | `User` |
| **Regras** | RN-58, RN-61, RN-63 a RN-66 |

## Cadastros

| | |
|---|---|
| **Telas** | `Empresas.jsx`, `Filiais.jsx`, `Transportadoras.jsx`, `Regioes.jsx`, `Cidades.jsx`, `Metas.jsx` |
| **Endpoints** | `empresas.py` (9), `transportadoras.py` (5), `regioes.py` (11), `metas.py` (4) |
| **Entidades** | `Empresa`, `Filial`, `Transportadora`, `Regiao`, `Cidade`, `MetaNacional`, `MetaRegional` |
| **Regras** | RN-13, RN-60, RN-63 |
| **Observação** | `Empresas.jsx` integra busca automática de dados por CNPJ via BrasilAPI (serviço externo, não é backend próprio da plataforma). |

## Importação

| | |
|---|---|
| **Telas** | `ImportacaoCte.jsx` (+ `ImportacaoCancelamento`, `IndicadorBaseCte`, `GerenciarDadosImportados`), `ImportacaoExcel.jsx` |
| **Endpoints** | `importacao.py` (8) |
| **Entidades** | `CTe`, `NFe`, `CteCancelamento` (tabela `cte_cancelamentos`) |
| **Regras** | RN-01 a RN-08 |

## Diagnóstico Logístico

| | |
|---|---|
| **Telas** | `Dashboard.jsx`, `Relatorios.jsx` |
| **Endpoints** | `dashboard.py` (1), `relatorios.py` (parte) |
| **Entidades** | Deriva de `CTe`/`NFe`, sem tabela própria |
| **Regras** | RN-09 a RN-12 |

## DLG — Diagnóstico Logístico Analítico

| | |
|---|---|
| **Telas** | `DiagnosticoDLG.jsx` — 5 dimensões: Filial, Rota, Transportadora, Região, **Cliente** (v6.7.0) |
| **Endpoints** | `dlg.py` (4) — `GET /analitico` com paginação opcional (`page`/`page_size`, CA-16) |
| **Entidades** | `dlg_analitico` (+ `composicao_frete`, v6.7.0), `dlg_outliers` |
| **Regras** | RN-25 a RN-29, RN-67 a RN-77 |

## Recomendações

| | |
|---|---|
| **Telas** | `Recomendacoes.jsx` |
| **Endpoints** | `recomendacoes.py` (4) |
| **Entidades** | `recomendacoes` |
| **Regras** | RN-56, RN-57, RN-71, RN-77 (causais de Cliente, v6.7.0) |

## Benchmark Logístico

### Benchmark legado (regional)

| | |
|---|---|
| **Telas** | `BenchmarkNacional.jsx`, `BenchmarkRegional.jsx`, `BenchmarkTransportadoras.jsx`, `PotencialEconomia.jsx`, `DashboardExecutivo.jsx` |
| **Endpoints** | `benchmark_analise.py` (6), `benchmarks.py` (2) |
| **Entidades** | `Benchmark`, `MetaNacional`, `MetaRegional` |
| **Regras** | RN-13 a RN-16 |

### Benchmark OD / Corredor (V2.1)

| | |
|---|---|
| **Telas** | `BenchmarkCorredores.jsx`, `Clusters.jsx`, `BenchmarksCorredor.jsx` (config. de referências, admin) |
| **Endpoints** | `benchmark_od_config.py` (13, hubs+clusters+corredores), `benchmark_analise.py` (`/benchmark/corredores/{id}`) |
| **Entidades** | `HubLogistico`, `ClusterCliente`, `BenchmarkCorredor` |
| **Regras** | RN-17 a RN-21 |

### Benchmark V2 (Matriz de Mercado) e MBL

| | |
|---|---|
| **Telas** | `MatrizOD.jsx` (matriz de mercado, admin), `BenchmarkMBL.jsx` |
| **Endpoints** | `benchmark_v2_api.py` (8), `mbl.py` (3) |
| **Entidades** | `benchmark_mercado`, `benchmark_observado`, `benchmark_cliente`, `mbl_benchmark` |
| **Regras** | RN-22 a RN-24 (V2), RN-30 a RN-33 (MBL) |

## Concorrência Logística — BID de Frete

| | |
|---|---|
| **Telas** | `BidDashboard.jsx`, `BidLista.jsx`, `BidFormulario.jsx`, `BidDetalhe.jsx` (+abas: `BidVisaoGeral`, `BidEscopo`, `BidTransportadoras`, `BidPropostas`, `BidComparativo`, `BidSimulacao`, `BidRelatorios`), `BidComparativoSelecao.jsx`, `ConcorrenciaMCL.jsx` |
| **Endpoints** | `bid.py` (27), `mcl.py` (4), `relatorios.py` (`/relatorios/bid/...`) |
| **Entidades** | `Bid`, `BidEscopo`, `BidTransportadora`, `BidProposta`, `BidSimulacao`, `BidAuditoria`, `mcl_decisoes` |
| **Regras** | RN-34 a RN-42 (MCL + BID) |

## Inteligência Logística com IA

| | |
|---|---|
| **Telas** | `InteligenciaDashboard.jsx`, `DiagnosticoIA.jsx`, `Insights.jsx`, `ScoreLogistico.jsx`, `Oportunidades.jsx`, `AssistenteLogistico.jsx`, `BaseConhecimento.jsx` |
| **Endpoints** | `inteligencia.py` (26) |
| **Entidades** | `RegraInsight`, `Insight`, `InsightExecucao`, `DiagnosticoIA`, `DiagnosticoHistorico`, `ScoreLogistico`, `ScoreHistorico`, `BenchmarkSetorial`, `Oportunidade`, `PlanoAcao`, `ChatSessao`, `ChatMensagem`, `UsageLog`, `DocumentoVetorial`, `EmbeddingJob` |
| **Regras** | RN-43 a RN-55 |
| **Ferramentas do Assistente (tool-calling)** | 10 — inclui `get_pior_cliente`/`get_ofensor_cliente` (v6.7.0, RN-76) |
| **Observação** | Toda a camada de IA opera em modo simulado por padrão (`AI_SIMULATION_MODE=True`) — os números exibidos são sempre reais (vêm de SQL), só o texto narrativo é mockado até que chaves de API reais sejam configuradas. |

## Relatórios (transversal)

| | |
|---|---|
| **Telas** | `Relatorios.jsx`, `BidRelatorios.jsx`, telas de download embutidas em `DiagnosticoIA.jsx` |
| **Endpoints** | `relatorios.py` (5), `inteligencia.py` (`/inteligencia/relatorio/{formato}`) |
| **Formatos** | Excel (`openpyxl`), PDF (`reportlab`), Word (`python-docx`), PowerPoint (`python-pptx`) |
