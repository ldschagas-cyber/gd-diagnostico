# 13 · Inventário Técnico — Linha de Base Oficial (Technical Baseline)

> **Finalidade**: este documento é a Linha de Base Oficial (Technical Baseline) da plataforma GD Frete Diagnóstico, preparada para sustentar a **Fase 1 — Auditoria Técnica**. É um levantamento factual — não contém julgamento de qualidade, severidade ou recomendação de correção; isso é objeto da Fase 1. Onde um item já tem um documento dedicado no conjunto oficial (`00`–`12`), este inventário resume e aponta para lá em vez de duplicar.
>
> **Versão da plataforma**: 6.5.1 · **Data do levantamento**: 2026-07-07 · **Baseado em**: leitura direta do código-fonte em `C:\gdconecta\frete` (backend, frontend, infraestrutura, testes).
>
> Este inventário é a referência factual que toda nova Especificação Técnica deve verificar antes de propor mudança — ver ordem obrigatória de leitura para agentes de IA em [`README_AI.md`](README_AI.md) e o documento mestre de governança em [`00_contexto_oficial.md`](00_contexto_oficial.md).

---

## 1. Visão geral da plataforma

GD Frete Diagnóstico é uma plataforma de inteligência logística (GD Conecta) que importa documentos fiscais de transporte (CT-e, NF-e, Excel), calcula indicadores de custo de frete, compara com benchmarks de mercado em três modelos coexistentes, conduz processos de cotação eletrônica entre transportadoras (BID) com um motor de decisão determinístico (MCL), e opera uma camada de Inteligência Artificial que narra e prioriza — nunca calcula — sobre números sempre produzidos por SQL. É multi-tenant (uma instância atende várias empresas-cliente, isoladas por `empresa_id`) e tem controle de acesso por papel (RBAC). Descrição completa em [`01_visao_geral.md`](01_visao_geral.md).

## 2. Módulos existentes

| Módulo | Maturidade |
|---|---|
| Autenticação e Usuários | Implementado |
| Cadastros (Empresas, Filiais, Transportadoras, Regiões, Cidades, Metas) | Implementado |
| Importação (CT-e XML, Excel, Cancelamento) | Implementado |
| Diagnóstico Logístico (Dashboard) | Implementado |
| DLG — Diagnóstico Logístico Analítico | Implementado |
| Recomendações | Implementado |
| Benchmark legado (regional) | Implementado |
| Benchmark OD / Corredor (hubs, clusters) | Implementado |
| Benchmark V2 (matriz de mercado) + MBL | Implementado |
| Concorrência Logística (BID de Frete) | Implementado |
| MCL — Motor de Decisão de BID | Implementado |
| Inteligência Logística com IA (insights, diagnóstico, score, oportunidades, assistente, RAG, relatório) | Implementado (modo simulado por padrão) |
| Relatórios (Excel/PDF/Word/PowerPoint) | Implementado |
| Benchmark Coletivo Anonimizado (V5) | **Não implementado** |
| Inteligência de Mercado Logístico (V6) | **Não implementado** |

Detalhamento em [`01_visao_geral.md`](01_visao_geral.md#módulos-implementados-hoje-v651) e [`07_modulos_do_sistema.md`](07_modulos_do_sistema.md).

## 3. Funcionalidades implementadas por módulo

Ver [`07_modulos_do_sistema.md`](07_modulos_do_sistema.md) para o cruzamento tela↔endpoint↔entidade↔regra de cada módulo, e [`02_especificacao_funcional.md`](02_especificacao_funcional.md) para a descrição funcional de cada fluxo. Resumo por módulo:

- **Cadastros**: CRUD completo de empresa/filial/transportadora/região/cidade/meta; busca de CNPJ via serviço externo (BrasilAPI) no cadastro de empresa.
- **Importação**: upload de XML (individual e em lote), upload de Excel, importação de eventos de cancelamento, download de planilhas-modelo, log de ocorrências, exclusão administrada de dados importados.
- **Diagnóstico/DLG**: cálculo de indicadores nacional/regional/transportadora/prazo; motor analítico por 4 dimensões com classificação e detecção de outliers.
- **Benchmark (3 gerações)**: cadastro manual regional; corredor Hub-OD com hierarquia de resolução por cluster; matriz de mercado global + benchmark observado do cliente + MBL estatístico.
- **BID**: CRUD, máquina de estados, geração de escopo via SQL, convite/gestão de transportadoras, coleta de propostas (manual/Excel), comparativo, simulação de cenários, decisão via MCL, relatórios, trilha de auditoria.
- **IA**: geração de insights por regras configuráveis, diagnóstico executivo narrativo com cache, score logístico ponderado, detecção de oportunidades, chat com tool-calling, RAG com busca semântica, relatório executivo em 3 formatos.
- **Recomendações**: consolidação idempotente de ações priorizadas a partir do diagnóstico/DLG.

## 4. Tecnologias utilizadas

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.12+, FastAPI ≥0.115, Uvicorn ≥0.34, SQLAlchemy ≥2.0 (síncrono), Alembic ≥1.14, Pydantic ≥2.10 |
| Autenticação/Segurança | python-jose (JWT), bcrypt (sem passlib), slowapi (rate limit), defusedxml |
| Banco de dados | PostgreSQL 16 (produção, com `pgvector`) / SQLite (dev local) |
| Processamento assíncrono | Celery ≥5.3, Redis ≥5.0 |
| IA | openai ≥1.50, anthropic ≥0.40 (abstração própria, modo simulado por padrão) |
| Relatórios | openpyxl, reportlab, python-docx, python-pptx |
| Frontend | React 18.3, Vite 6, React Router 6.28, MUI 6.2 (+ `@mui/x-data-grid` 7.23), TanStack React Query 5.62, Axios 1.7, Recharts 2.13 |
| Infraestrutura | Docker, Docker Compose (3 variantes), Nginx |

Lista de versões completa em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#2-stack-tecnológica-versões-mínimas-reais-de-requirementstxtpackagejson).

## 5. Arquitetura identificada

**Clean Architecture** no backend, com 4 camadas e regra de dependência unidirecional (apresentação → aplicação → domínio; infraestrutura implementa interfaces do domínio):

```
presentation (routers FastAPI, schemas Pydantic)
   → application (use cases — regra de negócio pura)
   → domain (entidades dataclass + interfaces de repositório, sem framework)
   ↑ implementado por infrastructure (SQLAlchemy, parsers, IA, relatórios, Celery)
```

No frontend: SPA React com roteamento client-side, contextos globais (`AuthContext`, `EmpresaContext`), camada de API centralizada (`client.js`/`endpoints.js`) e adoção parcial de React Query (`queries.js`) para cache de dados — parte das telas mais antigas ainda usa `useState`/`useEffect` com chamada direta à API. Detalhes em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md).

## 6. Estrutura de diretórios

```
gd_frete_diagnostico/
├── backend/
│   ├── app/{domain,application,infrastructure,presentation,core}/
│   ├── alembic/versions/        (11 migrations)
│   └── tests/                    (8 arquivos, 97 casos)
├── frontend/
│   └── src/{api,contexts,layouts,components,pages,theme}/
├── docs/                          (documentação oficial — este conjunto)
├── docker-compose.yml / .dev.yml / .prod.yml
└── iniciar.bat / parar.bat
```

Árvore completa em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#3-estrutura-de-pastas).

## 7. Organização do frontend

- **~50 páginas** em `src/pages/`, cada uma correspondendo a uma rota de `App.jsx`.
- **Menu lateral** (`AppLayout.jsx`) com 8 grupos: Acesso e Segurança (admin), Cadastros, Configuração, Importação, Diagnóstico Logístico, Benchmark Logístico, Concorrência Logística (BID), Inteligência Logística - IA.
- **Contextos**: `AuthContext` (sessão via cookie httpOnly, nunca lê/escreve token em JS) e `EmpresaContext` (empresa ativa, seleção persistida em `localStorage` só como preferência de UI).
- **Camada de API**: `client.js` (Axios, `withCredentials: true`, fila de retry em 401), `endpoints.js` (~30 grupos de função por domínio), `queries.js` (hooks React Query, adoção parcial), `queryKeys.js`.
- **Componentes reutilizáveis**: 15 componentes em `src/components/` (tabela padrão, cartão de indicador, error boundary, diálogo de confirmação, seletor de empresa, banners, etc.).
- **Tema**: paleta institucional GD Conecta (Indigo/Amber/Blue/Ivory), tipografia Sora (títulos) + Inter (corpo).

Inventário completo de páginas e chamadas de API em [`07_modulos_do_sistema.md`](07_modulos_do_sistema.md).

## 8. Organização do backend

- **`domain/`**: 35 dataclasses + 12 enums, sem dependência de ORM/framework.
- **`application/use_cases/`**: 25 arquivos, um por área de regra de negócio (ver seção 10).
- **`infrastructure/`**: modelos ORM (53 classes → 44 tabelas), repositórios concretos, parsers (CT-e XML, cancelamento, Excel), camada de IA (`llm_client`, cache, usage_logger), relatórios (Excel/PDF/Word/PPTX), Celery.
- **`presentation/`**: 19 routers (148 endpoints), schemas Pydantic, `dependencies.py` (DI de repositórios + autenticação/autorização).
- **`core/`**: configuração (`config.py`), conexão de banco (`database.py`), segurança (`security.py` — hash, JWT, cookies), logging.

Detalhado em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#3-estrutura-de-pastas).

## 9. Organização das APIs

**19 routers, 148 endpoints**, todos sob o prefixo `/api/v1`. Catálogo completo com método, path, descrição e autorização exigida em [`05_apis.md`](05_apis.md). Distribuição:

| Router | Endpoints | Router | Endpoints |
|---|---|---|---|
| `auth` | 4 | `benchmark_v2_api` | 8 |
| `usuarios` | 4 | `bid` | 27 |
| `empresas` | 9 | `mcl` | 4 |
| `transportadoras` | 5 | `dlg` | 4 |
| `regioes`/`cidades` | 11 | `mbl` | 3 |
| `metas` | 4 | `recomendacoes` | 4 |
| `benchmarks` | 2 | `inteligencia` | 26 |
| `benchmark_analise` | 6 | `importacao` | 8 |
| `benchmark_od_config` | 13 | `dashboard` | 1 |
| | | `relatorios` | 5 |

## 10. Organização dos serviços

Não há microsserviços — "serviços" aqui correspondem aos **use cases** (regra de negócio, camada `application`) e aos **serviços de infraestrutura** (camada `infrastructure`):

| Categoria | Serviços |
|---|---|
| Use cases de domínio (25) | `auth`, `diagnostico`, `dlg`, `mbl`, `mcl`, `recomendacoes`, `importacao`, `indicadores_regionais`, `benchmark` (legado), `benchmark_od`, `benchmark_v2`, `benchmark_observado`, `benchmark_setorial`, `bid`, `bid_escopo`, `bid_economia`, `cancelamento`, `insights`, `oportunidades`, `score_logistico`, `diagnostico_ia`, `assistente` + `assistente_tools`, `rag_service`, `relatorio_ia` |
| Serviços de infraestrutura | `llm_client` (abstração OpenAI/Anthropic + modo simulado), `cache_service` (Redis + memória), `usage_logger`, `celery_app` + `tasks/ai_tasks` (processamento assíncrono, beat diário), parsers (`cte_parser`, `evento_cancelamento_parser`, `excel_parser`, `macro_regiao`), geradores de relatório (`excel_report`, `pdf_report`, `benchmark_report`, `bid_report`) |

## 11. Organização do banco de dados

44 tabelas agrupadas em 8 domínios: Cadastro base, CT-e/NF-e, Benchmark Corredor OD, Benchmark V2/Matriz de Mercado, DLG/MBL/MCL, BID, Recomendações, Inteligência IA. Nenhuma tabela nova na v6.7.0 (Dimensão Cliente) — apenas colunas novas em `ctes` (`destinatario_cnpj`/`destinatario_nome`) e `dlg_analitico` (`composicao_frete`, genérica às 5 dimensões). Ver o detalhamento completo (campos, relacionamentos, unicidades) em [`04_modelo_de_dados.md`](04_modelo_de_dados.md).

## 12. Principais entidades do domínio

35 dataclasses (`app/domain/entities/__init__.py`), com destaque para: `User`, `Empresa`, `Filial`, `Transportadora`, `CTe`/`NFe`, `Bid` (+ `BidEscopo`/`BidTransportadora`/`BidProposta`/`BidSimulacao`/`BidAuditoria`), `HubLogistico`/`ClusterCliente`/`BenchmarkCorredor`, `DiagnosticoIA`/`ScoreLogistico`/`Insight`/`Oportunidade`/`ChatSessao`/`DocumentoVetorial`. 12 enums, incluindo `RoleEnum` (ADMIN/ANALISTA/VISUALIZADOR) e `BidStatusEnum` (máquina de estados). Lista completa em [`04_modelo_de_dados.md`](04_modelo_de_dados.md#1-cadastro-base) (por tabela) e no inventário de entidades já levantado nesta auditoria.

## 13. Fluxos de negócio

Os quatro fluxos centrais do sistema:

1. **Diagnóstico**: importar CT-e/Excel → calcular indicadores (nacional/regional/transportadora/prazo) → comparar com benchmark → gerar relatório.
2. **DLG → MBL → MCL**: processar DLG (classificação/outliers) → MBL calcula percentis próprios excluindo outliers → MCL usa DLG+MBL para pontuar propostas de BID.
3. **BID de Frete**: criar BID → gerar escopo (SQL) → convidar transportadoras → coletar propostas → comparar/simular → decidir (MCL) → relatórios.
4. **Inteligência IA**: coletar contexto (score + indicadores) → gerar insights/diagnóstico/oportunidades via LLM (ou modo simulado) → indexar no RAG → disponibilizar ao assistente conversacional.

Descrição detalhada em [`02_especificacao_funcional.md`](02_especificacao_funcional.md#2-módulos-e-fluxos-principais).

## 14. Principais regras de negócio

66 regras catalogadas (`RN-01` a `RN-66`) em [`06_regras_de_negocio.md`](06_regras_de_negocio.md), cobrindo: importação e deduplicação, indicadores de diagnóstico, metas/benchmark legado, benchmark OD (score logarítmico, pesos 60/40), benchmark V2 (hierarquia cliente>mercado), DLG (classificação/outliers/deduplicação de transportadora), MBL (percentis, `low_confidence`), MCL (pesos 40/25/20/10/5, rejeição >20% acima do MBL), BID (máquina de estados, score de transportadora), score logístico (pesos 30/20/20/15/15), insights e oportunidades automáticas, recomendações, RBAC/multi-tenant, e segurança (CNPJ, senha, cookies).

## 15. Integrações internas

| Origem | Destino | Natureza |
|---|---|---|
| Importação (CT-e/Excel) | Diagnóstico, DLG, Benchmark Observado | Dados de entrada compartilhados |
| DLG | MBL | MBL exclui os outliers que o DLG detectou |
| DLG + MBL | MCL | Score de decisão de BID usa classificação DLG e desvio MBL como componentes |
| Diagnóstico + DLG | Recomendações, Insights, Oportunidades | Gatilhos determinísticos e regras de IA leem os mesmos indicadores |
| Diagnóstico, Relatórios, BID encerrado | RAG (Base de Conhecimento) | Auto-indexação de conteúdo para busca semântica |
| Score Logístico | Assistente IA (tool-calling) | Ferramenta `get_score_logistico` consulta o mesmo cálculo exposto em `/inteligencia/score` |
| Celery Beat | Insights | Execução diária agendada do motor de regras |

## 16. Integrações externas

| Serviço | Onde é usado | Natureza |
|---|---|---|
| BrasilAPI | `Empresas.jsx` (frontend) | Consulta de dados de CNPJ na criação/edição de empresa — chamada direta do navegador, não passa pelo backend |
| OpenAI (GPT-4.1) | `llm_client.py` | Modelo principal de IA quando `AI_SIMULATION_MODE=False` e `OPENAI_API_KEY` configurada |
| Anthropic (Claude Haiku) | `llm_client.py` | Modelo de volume/sumarização quando ativado |
| SEFAZ (indireta) | Parser de CT-e e de eventos de cancelamento | O sistema consome o **schema XML** de CT-e e de eventos oficiais da SEFAZ, mas não há chamada de API ativa à SEFAZ — os arquivos são fornecidos pelo usuário via upload |

Não há integração ativa com ANTT/IBGE/câmbio (previstas apenas no roadmap V6 — ver [`10_roadmap.md`](10_roadmap.md)).

## 17. Dependências do sistema

22 pacotes Python (`backend/requirements.txt`) e 9 dependências diretas de produção no frontend (`package.json`), listadas por completo em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#2-stack-tecnológica-versões-mínimas-reais-de-requirementstxtpackagejson).

## 18. Modelo de autenticação

JWT (HS256) com **access token** (30 min) e **refresh token** (7 dias), emitidos em `POST /auth/login` e entregues como **cookies `httpOnly`** (`SameSite=Lax`, `Secure` em produção; cookie de refresh com `path` restrito a `/api/v1/auth`). O corpo da resposta também traz os tokens em JSON, mantido por compatibilidade com clientes de API/scripts — o frontend web ignora esse campo. `get_current_user` aceita cookie ou header `Authorization: Bearer` (header tem prioridade quando ambos presentes). `POST /auth/logout` limpa os cookies no servidor. Detalhes em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#51-autenticação--jwt-via-cookie-httponly-desde-v651) e histórico da migração em [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md).

## 19. Modelo de autorização

RBAC com 3 papéis (`ADMIN`, `ANALISTA`, `VISUALIZADOR`) combinado com isolamento multi-tenant por `empresa_id`. Dependencies reutilizáveis do FastAPI: `get_current_user`, `get_current_superuser`/`require_admin`, `verificar_acesso_empresa`, `bloquear_visualizador`, `get_bid_com_acesso`, `get_transportadora_com_acesso`. Um superusuário global (`is_superuser=True`, sem `empresa_id`) acessa qualquer empresa; um ADMIN de empresa só administra a própria. VISUALIZADOR é bloqueado em toda escrita, exceto operações que só calculam sem persistir. Detalhes em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#52-autorização--dependencies-reutilizáveis).

## 20. Principais endpoints

Os de maior criticidade de negócio/segurança, por volume de uso ou sensibilidade dos dados:

| Endpoint | Por quê é crítico |
|---|---|
| `POST /auth/login`, `POST /auth/refresh` | Ponto de entrada de toda sessão; rate-limited |
| `GET /dashboard/{empresa_id}` | Endpoint mais consultado do sistema — agrega todos os indicadores |
| `POST /importacao/cte/{empresa_id}` | Ponto de entrada de dados fiscais; parsing de XML não confiável |
| `POST /bid` … `PATCH /bid/{bid_id}/status` | Dados comercialmente sensíveis (cotações entre transportadoras concorrentes) |
| `POST /mcl/{bid_id}/decidir` | Decisão de negócio com efeito financeiro direto, persistida e versionada |
| `POST /inteligencia/assistente/sessoes/{id}/mensagens` | Único ponto onde um LLM externo processa dados da empresa (quando não simulado) |
| `GET/POST/PUT/DELETE /usuarios` | Superfície de escalonamento de privilégio (alvo da correção de 2026-07-07) |

Catálogo completo em [`05_apis.md`](05_apis.md).

## 21. Estrutura de alto nível do banco de dados

```
Cadastro base (users, empresas, filiais, transportadoras, regioes, cidades, meta_nacional, meta_regional, benchmarks)
   ├─→ CT-e/NF-e (ctes, nfes, cte_cancelamentos)
   │      ├─→ Benchmark Corredor OD (hubs_logisticos, clusters_cliente, benchmarks_corredor)
   │      ├─→ Benchmark V2 (benchmark_mercado, benchmark_observado, benchmark_cliente)
   │      └─→ DLG/MBL/MCL (dlg_analitico, dlg_outliers, mbl_benchmark, mcl_decisoes)
   ├─→ BID (bids, bid_escopos, bid_transportadoras, bid_propostas, bid_simulacoes, bid_auditorias)
   ├─→ Recomendações (recomendacoes)
   └─→ Inteligência IA (regras_insight, insights, insight_execucoes, diagnosticos_ia, diagnostico_historicos,
          scores_logisticos, score_historicos, benchmarks_setoriais, oportunidades, planos_acao,
          chat_sessoes, chat_mensagens, usage_logs, documentos_vetoriais, embedding_jobs)
```

Toda ramificação abaixo de `empresas` é isolada por `empresa_id`, exceto os catálogos explicitamente marcados como globais (regiões, cidades, metas, benchmark legado, hubs, matriz de mercado, benchmark setorial) — ver [`02_especificacao_funcional.md`](02_especificacao_funcional.md#5-o-que-é-global-vs-o-que-é-isolado-por-empresa-multi-tenant).

## 22. Componentes críticos da aplicação

| Componente | Por quê é crítico |
|---|---|
| `app/core/security.py` | Hash de senha, criação/validação de JWT, cookies httpOnly — toda a segurança de sessão passa por aqui |
| `app/presentation/api/dependencies.py` | Ponto único de autorização (RBAC + multi-tenant) para os 148 endpoints |
| `app/infrastructure/parsers/cte_parser.py` | Parser de XML não confiável (entrada de terceiros); usa `defusedxml` |
| `app/application/use_cases/diagnostico.py` | Núcleo de cálculo dos indicadores centrais do produto |
| `app/application/use_cases/mcl.py` | Motor de decisão de BID — efeito financeiro direto e auditável |
| `app/infrastructure/ai/llm_client.py` | Único ponto de saída de dados a um provedor de IA externo |
| `app/main.py` | Bootstrap da aplicação, CORS, rate limiter, seed, lifespan — inclui a validação que bloqueia boot inseguro em produção |
| `app/core/config.py` | Fonte única de configuração/segredos; contém a validação de segurança de produção |

## 23. Principais pontos de entrada do sistema

| Ponto de entrada | Descrição |
|---|---|
| `uvicorn app.main:app` (HTTP) | API REST, 148 endpoints, único backend consumido pelo frontend |
| Celery worker (`app.infrastructure.celery_app`) | Processa tarefas assíncronas de IA (`tasks/ai_tasks.py`) |
| Celery beat | Agendador — dispara geração diária de insights |
| `frontend` SPA (`src/main.jsx`) | Único ponto de entrada do usuário final (navegador) |
| `docker-compose.{dev,prod}.yml` | Pontos de entrada de orquestração/deploy |
| `iniciar.bat` / `parar.bat` | Pontos de entrada de operação local (Windows) |

---

## Resumo Executivo da Arquitetura Atual

O GD Frete Diagnóstico é um sistema de porte médio-grande (148 endpoints, 44 tabelas, 35 entidades de domínio, 25 use cases) construído sobre uma Clean Architecture consistente, que sustentou 5 gerações de expansão de módulo (MVP → Benchmark → BID → IA → DLG/MBL/MCL/Recomendações) sem necessidade de reescrita estrutural. A separação domain/application/infrastructure/presentation é respeitada de forma real, não apenas nominal — troca de banco (SQLite↔PostgreSQL) e adição de módulos inteiros não exigiram alterar a camada de domínio.

O sistema é multi-tenant por design desde o início para as entidades operacionais centrais (CT-e, mais tarde estendido a transportadoras, BID e toda a camada de IA), com um conjunto de dependencies de autorização reutilizáveis (`verificar_acesso_empresa`, `bloquear_visualizador`, `get_bid_com_acesso`) que hoje cobrem consistentemente os 19 routers — depois de uma correção pontual em 2026-07-07 que fechou lacunas de aplicação inconsistente desse padrão em módulos adicionados mais recentemente (ver seção de riscos abaixo).

A camada de IA é arquitetada com uma disciplina específica ("a IA narra, nunca calcula") que a mantém auditável e desacoplada do provedor de LLM — o modo simulado por padrão permite operar o produto inteiro sem custo de API e sem dependência de disponibilidade externa.

## Principais Riscos Técnicos Já Identificados (sem auditar — apenas registro)

Estes riscos já constam em [`10_roadmap.md`](10_roadmap.md) e [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md); listados aqui só para ficarem visíveis no ponto de partida da Fase 1, **sem qualquer novo julgamento nesta etapa**:

1. Migrations Alembic ausentes para as tabelas de IA e para as mudanças de segurança v6.5.x (schema real não é 100% reproduzível só com `alembic upgrade head`).
2. `docker-compose.prod.yml` não inclui Redis/Celery — módulo de IA em produção exige adição manual.
3. Arquivos monolíticos em algumas camadas do backend (`repositories/__init__.py`, `schemas/__init__.py`, `dtos/__init__.py`) — um arquivo por camada, não por módulo.
4. Ausência de testes automatizados de frontend.
5. Frontend não esconde ações de escrita para o papel VISUALIZADOR (o backend já bloqueia com 403, mas a UI permanece "clicável").
6. Sem token CSRF complementar ao `SameSite=Lax`.
7. Débitos não revalidados desde a auditoria v2.0.0 (precisam confirmação na Fase 1): composição de frete agregada em Python em vez de SQL; `BenchmarkUseCase` acessando métodos privados de `DiagnosticoUseCase`; ausência de cache Redis no dashboard; relatórios gerados de forma síncrona; sem observabilidade (Sentry/OpenTelemetry); sem ADRs.
8. Migração de React Query no frontend é parcial — páginas mais antigas ainda chamam a API diretamente via `useState`/`useEffect`.

## Confirmação

Este Inventário Técnico está aprovado para uso como **Linha de Base Oficial (Technical Baseline)** da **Fase 1 — Auditoria Técnica da Arquitetura**. Qualquer achado da Fase 1 deve referenciar os itens numerados (1–23) ou os riscos já registrados acima, e atualizar este documento e/ou os documentos `01`–`12` correspondentes ao final da auditoria, preservando a regra de "documentação viva" estabelecida na Baseline Oficial (ver [`00_README.md`](00_README.md)).
