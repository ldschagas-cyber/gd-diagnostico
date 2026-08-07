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

> **Reorganizado na v6.9.0** — a Matriz Benchmark (OD) passou a ser a fonte única de referência R$/kg (SSoT), consumida por `BenchmarkUseCase`, DLG, Score Logístico, Insights, Oportunidades e Assistente IA. O benchmark regional legado (V1, tabela `benchmarks`) e o Benchmark de Corredor (Hub-a-Hub) deixaram de ser referências de mercado independentes — ver `docs/11_changelog.md` [6.9.0] para o detalhamento da migração.

### Benchmark legado (regional, V1) — residual

| | |
|---|---|
| **Telas** | `Benchmarks.jsx` (rotulada "Benchmark % Frete (legado)", `/configuracoes/benchmark-pct`, grupo "Configuração", `soAdmin`) — reativada na v6.9.2 como cadastro remanescente, não removida |
| **Endpoints** | `benchmarks.py` (2) |
| **Entidades** | `Benchmark` — coluna R$/kg sem nenhum consumidor (vestigial); coluna `% Frete/Mercadoria` lida por `DiagnosticoUseCase._referencia_mercado_pct` (Dashboard, Recomendações) — a Matriz Benchmark (OD) ainda não modela esse campo |
| **Regras** | RN-13 a RN-16 |

### Benchmark Logístico — telas correntes (v6.9.0)

| | |
|---|---|
| **Telas** | `DashboardExecutivo.jsx` (visão executiva), `BenchmarkDiagnostico.jsx` (Nacional/Regional/Corredor/Transportadoras, seletor único), `BenchmarkComparativoMercado.jsx` (cliente × mercado por percentil, com `IndicadoresTransversais.jsx` — confiabilidade/cobertura), `PotencialEconomia.jsx` (com simulador de cenário P50/P25/P10) |
| **Endpoints** | `benchmark_analise.py` (6 + 3 novos: `comparativo-mercado`, `simulador-economia`, `indicadores-mercado`), `benchmark_v2_api.py` (8) |
| **Entidades** | `benchmark_mercado`, `benchmark_observado`, `benchmark_cliente` |
| **Use case novo** | `benchmark_dashboard.py` — não calcula, compõe `BenchmarkV2UseCase`/`BenchmarkObservadoUseCase` para as telas acima |
| **Regras** | RN-22 a RN-24 |

### Benchmark de Corredor (Hub-a-Hub) — detalhamento informativo

| | |
|---|---|
| **Telas** | `HubsLogisticos.jsx` (catálogo de hubs + mapeamento cliente→hub, ex-`Clusters.jsx`), `BenchmarksCorredor.jsx` (config. de referências, admin) |
| **Endpoints** | `benchmark_od_config.py` (13, hubs+clusters+corredores) |
| **Entidades** | `HubLogistico`, `ClusterCliente`, `BenchmarkCorredor` |
| **Regras** | RN-17 a RN-21 — resultado exibido como detalhamento (`por_corredor`) dentro de `PotencialEconomia.jsx`, não mais como referência de mercado própria |

### MBL — Benchmark Estatístico

| | |
|---|---|
| **Telas** | `BenchmarkMBL.jsx` |
| **Endpoints** | `mbl.py` (3) |
| **Entidades** | `mbl_benchmark` |
| **Regras** | RN-30 a RN-33 — isolado dos demais modelos de benchmark: serve DLG (classificação de eficiência) e MCL (score/limite de rejeição de proposta de BID), não é referência de mercado externa |

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

## Portal do Cliente (v6.18.0)

> Primeiro recorte do Portal do Cliente — usuário primário é o executivo da empresa cliente, não o analista (única exceção à regra geral da plataforma, ver `00_contexto_oficial.md` §9 e `docs/specs/v6.18.0/v6.18.0_validacao_estrategica.md`). App separado (`frontend-portal/`), autenticação própria, somente-leitura + uma ação de sinalização de baixo risco. Reutiliza 100% o motor analítico já usado pelo analista — nenhum cálculo novo.

| | |
|---|---|
| **App** | `frontend-portal/` (React + Vite, projeto próprio, não é uma rota de `frontend/`) |
| **Telas** | `LoginPage.jsx`, `DashboardExecutivoPage.jsx`, `OportunidadesPage.jsx` — os demais itens de menu (Diagnóstico/Benchmark/Inteligência/Governança/Relatórios/Minha Conta) mostram aviso "ainda não disponível", sem tela própria nesta versão |
| **Endpoints** | `portal_cliente.py` (7) |
| **Entidades** | `ClientePortalUser`, `PortalOportunidadeFlag` — nenhuma tabela do motor analítico alterada |
| **Reuso** | `ScoreLogisticoUseCase` (Performance Logística), `BenchmarkUseCase` (Benchmark/Custo por Macrorregião/Potencial de Economia/Evolução), `RecomendacoesUseCase` (Plano de Ação/Oportunidades) |
| **Observação** | Dois ajustes de escopo em relação ao protótipo original, por ausência de dado real: "Custo por Região" virou "Custo por Macrorregião" (não existe agregação por UF no motor) e "impacto anual" por oportunidade virou "impacto no período analisado" (não existe anualização por item, só agregada). Ver Especificação Técnica §3.8. |
