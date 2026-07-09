# Changelog — GD Frete Diagnóstico
**GD Conecta · Histórico de Versões**

---

## [5.0.0] — Junho 2026 — Inteligência Logística com IA (V4)

### Visão geral
Adição da camada de Inteligência Artificial ao GD Frete Diagnóstico. A IA
interpreta e narra; todos os números vêm de cálculo SQL no backend (a IA nunca
calcula). Implementado em modo simulado (mock sem custo) — as chaves de API
podem ser plugadas depois sem alteração de código.

### Infraestrutura de IA (Fase 0 — DT-09)
- Camada de abstração de LLM (`infrastructure/ai/llm_client.py`): modo simulado +
  GPT-4.1 (OpenAI) + Claude Haiku (Anthropic), com Tool-Calling.
- Celery + Redis (`infrastructure/celery_app.py`, `tasks/ai_tasks.py`):
  processamento assíncrono, beat schedule de insights diários, retry.
- Serviço de cache híbrido (Redis com fallback em memória).
- Registro de uso (`usage_logger.py`): tokens, custo USD/BRL, por empresa/feature.
- `config.py` estendido: AI_SIMULATION_MODE, chaves, modelos, Redis, RAG.

### Novas entidades (15)
RegraInsight, Insight, InsightExecucao, DiagnosticoIA, DiagnosticoHistorico,
ScoreLogistico, ScoreHistorico, BenchmarkSetorial, Oportunidade, PlanoAcao,
ChatSessao, ChatMensagem, UsageLog, DocumentoVetorial, EmbeddingJob.
Todas com `empresa_id` (isolamento multi-empresa).

### Módulos implementados
- **Insights Automáticos** (Fase 1): motor de regras configurável no banco
  (não hardcoded), 4 categorias de classificação, execução diária via Celery.
- **Diagnóstico IA** (Fase 2): análise executiva em 6 seções, cache por hash,
  persistência e reprocessamento.
- **Score Logístico** (Fase 3): nota 0-100 (Nacional 30% + Regional 20% +
  Transportadoras 20% + Filiais 15% + Economia 15%), histórico temporal.
- **Benchmark Setorial** (Fase 4): comparação com 6 segmentos de mercado.
- **Oportunidades Automáticas** (Fase 5): detecção de BID, Consolidação,
  Renegociação, Concentração, com economia estimada e plano de ação.
- **Assistente Logístico** (Fase 6): chat com Tool-Calling (8 ferramentas SQL),
  histórico de conversa, isolamento por empresa.
- **Dashboard de Inteligência** (Fase 9): KPIs consolidados de IA.

### Frontend (Fase 11)
- 6 telas React: Visão Geral, Diagnóstico IA, Insights, Score Logístico
  (com Benchmark Setorial), Oportunidades, Assistente Logístico.
- Novo grupo de menu "Inteligência Logística - IA".
- Banner de modo simulado em todas as telas.

### RAG Seletivo (Fase 7)
- Serviço de RAG (`rag_service.py`): indexação e busca semântica por
  similaridade de cosseno, com isolamento obrigatório por empresa_id.
- Tipos indexáveis: benchmark, relatório, diagnóstico, BID encerrado, legislação.
- Embeddings via `llm_client.gerar_embedding()` (simulado determinístico ou
  OpenAI real). Armazenamento JSON portável (SQLite e PostgreSQL).
- Legislação ANTT pré-carregada como conhecimento global (empresa_id=0).
- Diagnósticos auto-indexados; assistente recupera contexto relevante.
- Tela "Base de Conhecimento": busca semântica, indexação e estatísticas.

### Relatório Executivo IA (Fase 8)
- Geração em PDF (ReportLab), Word (python-docx) e PowerPoint (python-pptx).
- Conteúdo: capa, KPIs, resumo executivo, seções narrativas, oportunidades,
  plano de ação e conclusões, na paleta GD Conecta.
- Download direto da tela de Diagnóstico IA (menu PDF/Word/PowerPoint).

### Frontend (Fase 11)

### API
- Novo router `/api/v1/inteligencia` com 25+ endpoints (insights, score,
  diagnóstico, oportunidades, benchmark setorial, assistente, RAG, relatórios).
- Total: 106 rotas no sistema.

### Testes (Fase 12)
- `tests/test_inteligencia_smoke.py`: 14 testes, incluindo isolamento
  multi-empresa (insights e RAG) e geração dos 3 formatos de relatório.
- Suítes anteriores intactas: 9 (smoke) + 22 (BID) + 14 (IA) = 45 testes.

### Decisões de arquitetura
- Opção B: PostgreSQL local com pgvector (Docker), ambiente idêntico à produção.
- Modo simulado ativado por padrão (sem chaves de API ainda).
- RAG: busca por cosseno em Python sobre embeddings JSON (portável SQLite/PG);
  coluna pgvector nativa + índice ivfflat é a otimização para grandes volumes.

### Dependências adicionadas
celery, redis, openai, anthropic, pgvector, python-docx, python-pptx.

---

## [2.0.0] — Junho 2026

### Infraestrutura e Arquitetura
- Migração do banco de dados de **SQLite para PostgreSQL** (suporte completo, pool configurado).
- Adição de `psycopg2-binary` ao `requirements.txt`.
- `database.py` atualizado: pool_size, max_overflow, pool_timeout, pool_recycle para PG.
- `alembic/env.py` atualizado: `render_as_batch` condicional (só SQLite).
- Script `migrate_sqlite_to_pg.py` para migração de dados existentes.
- `config.py` atualizado: propriedades `is_production` e `is_postgres`, variável `ENVIRONMENT`.

### Docker
- `backend/Dockerfile` atualizado: libpq-dev (psycopg2), usuário não-root.
- `frontend/Dockerfile` atualizado: build-arg `VITE_API_URL`, healthcheck.
- `docker-compose.dev.yml` criado: PostgreSQL + backend hot-reload + frontend Vite.
- `docker-compose.prod.yml` criado: PostgreSQL (sem porta exposta), backend 2 workers, rede interna.
- `frontend/nginx.conf` atualizado: proxy reverso `/api/ → backend:8000`, SPA routing, gzip.
- `.gitignore` criado com padrões completos.

### Segurança
- `.env.example` reescrito: seções claras, comentários, variáveis PostgreSQL separadas.
- `.env.dev` criado para desenvolvimento local sem Docker.
- Variável `ENVIRONMENT` (development/production) adicionada.
- CORS expandido para incluir `localhost:8080` (porta padrão Docker frontend).

### Documentação (nova)
- `docs/01_especificacao_funcional.md` — Objetivo, módulos, fluxos, regras de negócio, indicadores, benchmarks.
- `docs/02_arquitetura_tecnica.md` — Stack, Clean Architecture, estrutura de pastas, segurança, relatórios.
- `docs/03_dicionario_dados.md` — Todas as tabelas com campos, tipos, constraints e relacionamentos.
- `docs/04_catalogo_apis.md` — Todos os endpoints (método, request, response, regras).
- `docs/05_guia_deploy_ubuntu.md` — Deploy completo em Ubuntu 24.04 com Docker, Nginx, HTTPS, backup.
- `docs/06_guia_manutencao.md` — Ambiente local, testes, migrations, publicação, novos módulos/endpoints.
- `docs/07_changelog.md` — Este arquivo.
- `docs/especificacao_funcional.docx` — Especificação funcional em formato Word.

---

## [1.5.0] — Junho 2026

### Módulo Benchmark Logístico — Fase E e F
- Relatórios PDF e Excel consolidados de benchmark (`benchmark_report.py`).
- Endpoints `GET /relatorios/benchmark/{empresa_id}/excel` e `/pdf`.
- Botões de download na página Relatórios (seção Benchmark Logístico).
- Testes de regressão para geração de PDF e Excel.

---

## [1.4.0] — Junho 2026

### Módulo Benchmark Logístico — Fase D
- `BenchmarkUseCase.potencial_economia()`: cálculo de economia por região e projeção.
- `BenchmarkUseCase.evolucao_mensal()`: evolução do custo/kg por mês.
- `BenchmarkUseCase.dashboard_executivo()`: consolidado estratégico.
- Endpoints `GET /benchmark/economia/{id}` e `GET /benchmark/executivo/{id}`.
- Página **Potencial de Economia**: destaque de economia total, projeções (mensal/trim/sem/anual), tabela por região.
- Página **Dashboard Executivo**: cards estratégicos, gráficos de evolução mensal e comparativo regional, ranking de transportadoras.
- Menu BENCHMARK expandido (Dashboard Executivo, Potencial de Economia).

---

## [1.3.0] — Junho 2026

### Módulo Benchmark Logístico — Fases B e C
- `BenchmarkUseCase` com métodos `nacional()`, `regional()`, `transportadoras()`.
- Funções de classificação automática: `classificar_frete_kg()`, `classificar_frete_pct()`.
- DTOs: `BenchmarkNacional`, `BenchmarkRegionalItem`, `BenchmarkTransportadoraItem`, `ComparacaoBenchmark`.
- Schemas Pydantic correspondentes.
- Endpoints `GET /benchmark/nacional/{id}`, `/regional/{id}`, `/transportadoras/{id}`.
- Componente `BenchmarkComparacao.jsx`: barra de posição na faixa + desvio + classificação.
- Utilitário `utils/benchmark.js`: mapeamento de cores por classificação.
- Páginas **Benchmark Nacional**, **Benchmark Regional** (gráfico combo + tabela), **Benchmark Transportadoras** (ranking com troféu).
- Menu BENCHMARK no sidebar.

---

## [1.2.0] — Junho 2026

### Módulo Benchmark Logístico — Fase A (Fundação)
- Entidade `Benchmark` + enum `RegiaoBenchmarkEnum` (NACIONAL + 5 macro-regiões).
- Tabela `benchmarks` + `IBenchmarkRepository`.
- Seed automático com valores de referência por região (seção 6 da especificação).
- API CRUD: `GET /benchmarks` e `PUT /benchmarks/{regiao}` (admin).
- Página **Configurações › Benchmarks**: tabela editável.
- Item no menu Administração (visível apenas para administrador).

---

## [1.1.0] — Junho 2026

### Correções Parser CT-e (dados reais)
- **Bug fix:** `infCarga` aninhado em `infCTeNorm` não era encontrado. Corrigido com busca recursiva `.//<namespace>:infCarga`.
- **Bug fix:** Peso calculado retornava o primeiro valor encontrado (peso bruto). Corrigido para retornar o **máximo** entre os pesos em KG (excluindo volumes e cubagem em m³) — refletindo o "peso taxado".
- Testes de regressão para `valor_mercadoria` e `peso_taxado`.

### Melhorias nos Gráficos do Dashboard
- Componente `GraficosDiagnostico.jsx` criado (extração dos gráficos inline).
- 6 gráficos implementados: custo/kg×meta por região (combo), frete por transportadora, custo/kg por transportadora, % frete por transportadora, % frete×meta por região (combo), composição do frete (pizza).

---

## [1.0.0] — Junho 2026

### MVP — Versão Inicial

#### Backend
- **Arquitetura:** Clean Architecture (domain → application → infrastructure → presentation).
- **Módulos:** Autenticação JWT, Empresas, Filiais, Transportadoras, Regiões, Cidades, Usuários.
- **Importação:** CT-e XML v3.00 (parser completo com extração de composição), Excel (mapeamento flexível de colunas).
- **Dashboard:** Indicadores nacionais (RF011), regionais (RF012), por transportadora (RF013), prazos/OTIF (RF014), oportunidades.
- **Metas:** Nacionais e regionais, comparativo automático.
- **Relatórios:** Excel (multi-aba) e PDF (identidade visual GD Conecta).
- **Banco:** SQLite (dev) preparado para PostgreSQL.
- **Testes:** Smoke tests com httpx (pytest).

#### Frontend
- **Stack:** React 18 + Vite + MUI v6 + Recharts.
- **Autenticação:** JWT com AuthContext + ProtectedRoute.
- **EmpresaContext:** seletor de empresa ativa persistido no localStorage.
- **Paleta:** Indigo #2D3561, Amber #C9A84C, Blue #0077A8, Ivory #F5F1EB.
- **Fontes:** Sora (títulos), Inter (corpo).
- **Páginas:** Login, Dashboard, Importação (XML/Excel), Metas, Relatórios, Empresas, Filiais, Transportadoras, Regiões, Cidades, Usuários.

#### Infraestrutura
- Dockerfile backend (Python 3.12-slim + ReportLab + OpenPyXL).
- Dockerfile frontend (Node 20 build + nginx:alpine serve).
- docker-compose.yml inicial (SQLite via volume).
- Alembic migrations.
- `.env.example` com todas as variáveis.

---

*Changelog mantido seguindo [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).*


---

## [3.0.0] — Junho 2026

### FASE 1 — Correções Críticas (P0)

- **XML Bomb protection:** `defusedxml.ElementTree` já estava ativo em `cte_parser.py`; confirmado e documentado.
- **Rate Limiting:** `slowapi` adicionado ao endpoint `POST /auth/login` — máximo 10 tentativas/minuto por IP. Proteção global de 200 req/min em todos os endpoints.
- **Upload de arquivos — limite de tamanho e tipo:**
  - XML: máx 10 MB por arquivo, máx 500 por lote
  - Excel: máx 20 MB por arquivo
  - Validação de assinatura (magic bytes) antes de processar
  - Nginx configurado com `client_max_body_size 25M`
- **Swagger/Redoc desabilitados em `ENVIRONMENT=production`.**
- **CORS restritivo:** métodos explícitos `["GET","POST","PUT","DELETE","OPTIONS","PATCH"]` e headers explícitos em vez de `["*"]`.

### FASE 2 — Isolamento Multi-empresa

- **`empresa_id` adicionado à tabela `transportadoras`** (FK → empresas, índice).
- **Constraint CNPJ global removida;** nova constraint composta `(empresa_id, cnpj)`.
- **`TransportadoraRepository` atualizado:** métodos `get_by_cnpj_empresa()` e `list_by_empresa()` para isolamento total.
- **Auto-cadastro de transportadoras escopado por empresa:** CT-es importados criam transportadoras vinculadas à empresa importadora — não mais compartilhadas globalmente.
- **Chave sintética Excel corrigida:** inclui linha para evitar colisão entre notas de mesmo número de empresas diferentes.
- **Router `/transportadoras` atualizado:** `empresa_id` obrigatório como query parameter para listagem e criação.
- **N+1 na listagem de transportadoras eliminado:** `list_by_empresa()` em vez de `list(limit=1000)` global.

### FASE 3 — Performance

- **Migração Alembic `a2f8c1e4b9d3`:** índice composto `(empresa_id, data_emissao)` na tabela `ctes` para filtros de período — maior ganho de performance no dashboard.
- **Índice `(empresa_id, transportadora_id)` na tabela `ctes`** para resolution de transportadoras.
- **`DiagnosticoUseCase.gerar()` refatorado:** cálculos de nacional, regional e transportadoras agora usam SQL (`GROUP BY`, `SUM`, `COUNT`) via novos métodos `agregar_*` no repositório — elimina materialização de todos os CT-es em memória Python.
- **`listar_prazos()`:** carrega apenas CT-es com datas preenchidas para cálculo de OTIF (subconjunto menor).
- **Método `agregar_nacional()`, `agregar_por_regiao()`, `agregar_por_transportadora()`** adicionados ao `CTeRepository` e interface `ICTeRepository`.

### FASE 4 — Segurança

- **Validação de CNPJ com dígito verificador** (algoritmo módulo 11) em `EmpresaBase` e `FilialBase`.
- **Política de senha aprimorada:** mínimo 8 caracteres + pelo menos 1 letra + 1 número (antes: mínimo 6).
- **`ErrorBoundary` adicionado ao frontend:** crashs de componentes React exibem tela amigável em vez de página em branco.
- **Helper `_get_empresa_or_404`** adicionado a `dependencies.py` — base para autorização por empresa em V3.

### Testes

- **CNPJs nos smoke tests atualizados** para CNPJs válidos com dígito verificador correto.
- **9/9 testes passando** após todas as correções.

### Frontend

- `transportadorasApi.listar()` agora requer `empresaId` — isolamento multi-tenant.
- `BenchmarkNacional.jsx` e `Transportadoras.jsx` atualizados para passar `empresaAtivaId`.
- `ErrorBoundary.jsx` criado como componente de classe reutilizável.


---

## [4.0.0] — Junho 2026 — Concorrência Logística (BID de Frete) V3.1

### Módulo novo: Concorrência Logística

Implementação completa do módulo de BID de Frete conforme especificação funcional V3.1.

**Entidades novas (domínio, ORM, repositório):**
- `Bid` — processo de concorrência com máquina de estados
- `BidEscopo` — consolidação SQL dos CT-es por agrupamento lógico
- `BidTransportadora` — relacionamento entre BID e transportadoras existentes
- `BidProposta` — propostas de preço por grupo logístico
- `BidSimulacao` — cenários de distribuição entre transportadoras
- `BidAuditoria` — trilha completa de ações

**Backend (28 endpoints):**
- CRUD de BID, máquina de estados (Rascunho→Aberto→Em Cotação→Encerrado/Cancelado)
- Geração automática de escopo via SQL GROUP BY (sem carregar CT-es em memória)
- Agrupamentos: Região, UF, Filial, Transportadora, Faixa de Peso **livre** por BID
- Motor de economia: projeções mensal/trimestral/semestral/anual
- Score de transportadora: Preço 40% + Prazo 30% + Cobertura 20% + Avaliação 10%
- Simulação de distribuição (cenários com % por transportadora)
- Pacote de Cotação PDF (sem dados sensíveis / sem valores atuais)
- Relatórios PDF e Excel: executivo, comparativo, ranking, economia, resultado final
- Dashboard executivo com KPIs consolidados

**Segurança:**
- Status DESCLASSIFICADA e VENCEDORA adicionados às transportadoras no BID
- Campo `role` (ADMIN/ANALISTA/VISUALIZADOR) adicionado ao `UserModel`
- Isolamento multi-empresa: todos os artefatos do BID têm `empresa_id`

**Frontend (10 páginas novas):**
- `BidDashboard.jsx` — dashboard executivo com KPIs e gráficos
- `BidLista.jsx` — lista de BIDs com indicadores rápidos
- `BidFormulario.jsx` — criar e editar BID
- `BidDetalhe.jsx` — hub com abas (Escopo/Transportadoras/Propostas/Comparativo/Simulação/Relatórios)
- `BidEscopo.jsx` — geração de escopo + faixas livres + Pacote de Cotação
- `BidTransportadoras.jsx` — vincular do cadastro existente + controle de status
- `BidPropostas.jsx` — inclusão manual e importação Excel
- `BidComparativo.jsx` — comparativo atual vs. propostas + ranking/score
- `BidSimulacao.jsx` — cenários de distribuição com cálculo de economia
- `BidRelatorios.jsx` — download PDF/Excel de todos os tipos de relatório

**Menu:** grupo "Concorrência Logística" adicionado ao sidebar

**Migration:** `b3d9e2f1a7c5_v3_1_bid_concorrencia_logistica.py`

**Testes:** `test_bid_smoke.py` — 22 testes cobrindo fluxo completo, isolamento multi-empresa e suite original intacta

**Débitos técnicos V3.1:**
- Isolamento de testes: `test_smoke.py` e `test_bid_smoke.py` devem ser executados separadamente (conflito de `DATABASE_URL` em módulo compartilhado)
- Permissões de role (Analista/Visualizador) declaradas no backend mas não aplicadas em middleware — a ser implementado quando usuários tiverem `empresa_id`
