# 11 · Changelog

> Substitui `archive/07_changelog.md`, reordenado em ordem estritamente cronológica e estendido com as versões v6.0.0 a v6.5.1, que não tinham registro. Nomenclatura: cada entrada traz o número semver do changelog e, entre parênteses, o "nome de versão de produto" usado historicamente pela equipe (que não correspondia 1:1 ao semver nos documentos antigos — ver nota no fim).
>
> Política de versionamento (PATCH/MINOR/MAJOR) oficializada em [`00_contexto_oficial.md`](00_contexto_oficial.md), Seção 11, e [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 20.

## [1.0.0] — MVP

**Backend**: Clean Architecture (domain → application → infrastructure → presentation). Módulos: Autenticação JWT, Empresas, Filiais, Transportadoras, Regiões, Cidades, Usuários. Importação de CT-e XML v3.00 e Excel. Dashboard com indicadores nacionais/regionais/por transportadora/prazos (OTIF). Metas nacionais e regionais. Relatórios Excel/PDF. Banco SQLite (dev), preparado para PostgreSQL.

**Frontend**: React 18 + Vite + MUI v6 + Recharts. Autenticação JWT com `AuthContext` + `ProtectedRoute`. `EmpresaContext` com seletor de empresa ativa. Paleta GD Conecta (Indigo/Amber/Blue/Ivory).

## [1.1.0] — Correções do parser de CT-e

Bug fix: `infCarga` aninhado em `infCTeNorm` não era encontrado (corrigido com busca recursiva). Bug fix: peso taxado agora é o **máximo** entre os pesos em kg (antes retornava o primeiro valor/peso bruto). 6 gráficos no Dashboard (`GraficosDiagnostico.jsx`).

## [1.2.0] — Benchmark Logístico, Fase A (fundação)

Entidade `Benchmark` + enum de macrorregiões. Tabela `benchmarks` + repositório. Seed automático de valores de referência por região. CRUD admin (`GET/PUT /benchmarks`).

## [1.3.0] — Benchmark Logístico, Fases B e C

`BenchmarkUseCase` (nacional/regional/transportadoras). Classificação automática de frete/kg e % frete. Páginas Benchmark Nacional/Regional/Transportadoras.

## [1.4.0] — Benchmark Logístico, Fase D

Potencial de economia, evolução mensal, dashboard executivo. Páginas Potencial de Economia e Dashboard Executivo.

## [1.5.0] — Benchmark Logístico, Fases E e F

Relatórios PDF/Excel consolidados de benchmark.

## [2.0.0] — Infraestrutura PostgreSQL e Docker

Migração de SQLite para PostgreSQL (produção). Dockerfiles atualizados, `docker-compose.dev.yml`/`docker-compose.prod.yml` criados. `.env.example` reescrito. Documentação inicial (docs 01–07) criada.

## [3.0.0] — Correções críticas de segurança e performance

**Segurança (P0)**: `defusedxml` confirmado no parser de CT-e; `slowapi` (rate limit 10/min login, 200/min global); limites de upload (10 MB/500 lote XML, 20 MB Excel, validação de magic bytes); Swagger/Redoc desabilitados em produção; CORS restritivo (métodos/headers explícitos).

**Isolamento multi-empresa**: `empresa_id` adicionado a `transportadoras` (antes global); constraint `(empresa_id, cnpj)`; auto-cadastro de transportadora escopado por empresa; chave sintética Excel corrigida (`+linha`).

**Performance**: índice composto `(empresa_id, data_emissao)` em `ctes`; `DiagnosticoUseCase.gerar()` refatorado para agregação SQL.

**Outras**: validação de CNPJ (dígito verificador); política de senha (8+letra+número); `ErrorBoundary` no frontend.

## [4.0.0] (produto: "V3.1") — Concorrência Logística / BID de Frete

6 entidades novas (`Bid`, `BidEscopo`, `BidTransportadora`, `BidProposta`, `BidSimulacao`, `BidAuditoria`). 28 endpoints. Máquina de estados (Rascunho→Aberto→Em Cotação→Encerrado/Cancelado). Score de transportadora (Preço 40%+Prazo 30%+Cobertura 20%+Avaliação 10%). Campo `role` (ADMIN/ANALISTA/VISUALIZADOR) em `users`. 10 páginas React novas. `test_bid_smoke.py` (22 testes).

## [~2.1] (sem versão semver própria nos docs originais) — Benchmark por Corredor OD / Hubs

Correção do modelo de benchmark: passa a considerar o fluxo Origem→Destino via **Hub Logístico** (catálogo global) e **Cluster do Cliente** (mapa UF/município→hub por empresa), em vez de comparar só pelo destino. Nova entidade `BenchmarkCorredor` (referência global por par de hubs). Score por componente com penalização logarítmica suavizada; combinação 60% R$/kg + 40% % frete. Migration `c5e1a9f4d2b7`.

## [5.0.0] (produto: "V4") — Inteligência Logística com IA

Camada de abstração de LLM (`llm_client.py`): modo simulado + GPT-4.1 (OpenAI) + Claude Haiku (Anthropic), com tool-calling. Celery + Redis (processamento assíncrono, *beat schedule* de insights diários). Cache híbrido (Redis + memória). `usage_logger` (tokens, custo USD/BRL por empresa/feature). 15 entidades novas de IA. Módulos: Insights Automáticos, Diagnóstico IA, Score Logístico (pesos 30/20/20/15/15), Benchmark Setorial, Oportunidades Automáticas, Assistente Logístico (tool-calling, 8 ferramentas SQL), RAG (busca semântica com isolamento por empresa, legislação ANTT global). Relatório Executivo em PDF/Word/PowerPoint. Router `/api/v1/inteligencia` (25+ endpoints). `test_inteligencia_smoke.py` (14 testes).

## [6.0.0] — Benchmark V2 (Matriz de Mercado) e soft delete

Novo modelo de benchmark: matriz global de mercado por região OD com percentis P10–P90 (`benchmark_mercado`), Benchmark Observado calculado dos CT-e reais da empresa (`benchmark_observado`), override manual do cliente (`benchmark_cliente`). Hierarquia de resolução CLIENTE > MERCADO > indisponível. Soft delete (`deleted`) em `bid_propostas`. Migration `e8c4a1f6d3b2`.

## [6.1.0] — DLG e MBL

**DLG** (Diagnóstico Logístico Analítico): KPIs e classificação de eficiência por Filial/Rota/Transportadora/Região, com detecção de outliers estatísticos (`RS_KG_2DP`, `PCT_FRETE`) e deduplicação de transportadoras por identidade real (raiz de CNPJ). **MBL** (Benchmark Logístico estatístico): percentis próprios do cliente por dimensão×métrica×período, excluindo outliers do DLG, com marcação `low_confidence` para amostras pequenas. Migration `f3a9d6b2c1e8`.

## [6.3.0] — MCL, motor de decisão de BID

Motor de decisão determinístico e versionado: score ponderado (40% custo + 25% DLG + 20% MBL + 10% SLA + 5% estabilidade), rejeição de propostas >20% acima da referência MBL, simulação de sensibilidade de preço. Migration `a7c2e9f1b4d6`.

## [6.3.1] — Setor do embarcador

Coluna `setor` (obrigatória, 19 segmentos) em `empresas`, usada para comparação com o Benchmark Setorial da IA. Migration `b8e3f1a2c9d4`.

## [6.4.0] — Cancelamento de CT-e e Recomendações

Importação de eventos de cancelamento de CT-e via XML oficial da SEFAZ, com log auditável (`cte_cancelamentos`). Módulo de **Recomendações**: consolidação determinística e idempotente de ações priorizadas a partir do diagnóstico e do DLG. Dimensão DLG `CLIENTE` renomeada para `FILIAL` (dado histórico migrado). Migration `c9f4a2e7b1d8`. `test_melhorias_v64.py` e `test_v640_smoke.py`.

## [6.5.0] — Auditoria e correção de segurança multi-tenant

Auditoria de segurança identificou e corrigiu **falhas de isolamento multi-tenant (IDOR)** nos módulos BID, MCL, Transportadoras e Inteligência IA — endpoints que confiavam em `empresa_id` de query string sem validar contra o usuário autenticado. Corrigido escalonamento de privilégio no módulo de Usuários (um ADMIN de uma empresa podia editar/listar usuários de outra empresa ou se autopromover a superusuário global). Novas dependencies reutilizáveis: `get_bid_com_acesso`, `get_transportadora_com_acesso`. Novo teste `test_isolamento_v6_5_1.py`.

## [6.5.1] — RBAC de VISUALIZADOR e cookies httpOnly

**Enforcement do papel VISUALIZADOR**: nova dependency `bloquear_visualizador`, aplicada em todo endpoint de escrita do sistema que não fosse já restrito a admin — usuários com esse papel passam a receber 403 em qualquer ação de escrita, exceto operações que apenas calculam sem persistir.

**Migração de JWT para cookie `httpOnly`**: login/refresh passam a gravar cookies `httpOnly`/`SameSite=Lax` (`Secure` em produção); novo endpoint `POST /auth/logout`; `get_current_user` aceita cookie ou header Bearer, com o header tendo prioridade quando ambos presentes. Frontend (`client.js`, `AuthContext.jsx`) para de usar `localStorage` para o token, fechando o vetor de roubo via XSS. Novo teste `test_cookie_auth_v6_5_1.py`.

Correção adicional: `PUT /usuarios/{id}` sem o campo `senha` não zera mais o hash de senha existente (regressão pré-existente).

## [6.6.0] — Consistência de RN-09 nos módulos analíticos (CONS-01)

**Correção do achado mais crítico do programa de auditoria de 2026-07-07** (CONS-01, `docs/20_fase7_auditoria_funcional.md`; Etapa 1 do `docs/22_plano_diretor_tecnico.md`): a regra RN-09 (excluir CT-e `CANCELADO` dos totais financeiros analíticos) estava implementada corretamente apenas em Diagnóstico e DLG. Nove outros módulos liam `CTeModel` sem filtrar por status, produzindo números diferentes para a mesma rota/período entre telas do sistema sempre que havia cancelamento.

**Módulos corrigidos** (10 — os 9 do achado original + 1 encontrado durante a implementação com o mesmo padrão de bug): Benchmark legado, Benchmark OD, Benchmark Observado, MBL, Indicadores Regionais V2, Score Logístico, Insights, Oportunidades, Diagnóstico IA, e Benchmark Setorial (achado adicional, mesma causa raiz, fora da lista original da Fase 7).

**Mudança técnica**: nova constante de domínio `CTE_STATUS_ATIVO`/`CTE_STATUS_CANCELADO` (`app/domain/entities/__init__.py`), usada em todos os pontos de leitura analítica de CT-e no lugar do literal `"ATIVO"` espalhado. Interface `ICTeRepository` e o método `agregar_por_uf_od` do repositório (que não tinha nenhum filtro de status) atualizados para expor `apenas_ativos`. Correção cirúrgica nas queries existentes — não migra os use cases legados (`Session.query()`) para o padrão de repositório, débito à parte já catalogado (A-01) e deliberadamente fora de escopo desta correção.

**Mudança de comportamento (não de contrato de API)**: dashboards/relatórios com CT-e cancelado no período agora retornam totais financeiros, percentis e scores menores, refletindo apenas CT-es ativos — nenhum schema de request/response mudou. Dados já persistidos (MBL, Benchmark Observado, Insights, Oportunidades) só refletem a correção após reprocessamento (`.../processar`, `.../gerar`, `.../detectar`); recomenda-se disparar esses endpoints para empresas ativas após o deploy.

**Sem migration**: correção de filtro de leitura, sem alteração de schema.

**Testes**: novo `backend/tests/test_cons01_propagacao_rn09.py` (10 testes) — cobre os 10 módulos corrigidos e um teste de consistência cruzada Diagnóstico vs. Benchmark reproduzindo e corrigindo o sintoma literal do achado ("duas telas mostram números diferentes"). Suíte completa (78 testes em 8 arquivos) validada sem regressão.

**Escopo residual conhecido**: o escopo do BID (`bid_escopo.py`) e o motor MCL continuam sem esse filtro — achado correlato BID-01/MCL-02, agrupado deliberadamente na Etapa 2 do plano diretor técnico, que depende desta correção estar pronta primeiro.

## [6.7.0] — Dimensão Cliente no DLG

**Cliente** (destinatário da mercadoria) passa a ser a **5ª dimensão** do motor genérico do DLG (`CLIENTE_FINAL`), ao lado de Filial/Rota/Transportadora/Região — mesma tabela `dlg_analitico`, mesmo `DlgUseCase`, mesma classificação (RN-25). Além de medir custo, a dimensão Cliente **diagnostica a causa** do desvio quando identificável (componentes adicionais de frete e/ou fragmentação operacional), reforçando o princípio "IA interpreta, nunca calcula" — o diagnóstico causal é 100% determinístico (RN-76).

**Schema**: `ctes.destinatario_cnpj`/`destinatario_nome` (novo, nullable, sem backfill) + `dlg_analitico.composicao_frete` (JSON, genérico às 5 dimensões). Migration `d4b8f2a6c1e9` (reversível).

**Motor DLG**: nova agregação `_agregar_clientes` com deduplicação por identidade real (RN-68 — raiz de 8 dígitos do CNPJ ou nome normalizado, mesmo padrão já usado pela RN-28 de transportadoras); campos derivados novos aplicáveis às 5 dimensões (`peso_medio`, `ticket_medio`, `impacto_financeiro_potencial`, `frete_transporte_principal`, `pct_componentes_adicionais`, `ranking_componentes`); sinal de fragmentação operacional (RN-75, nível de despacho — nunca "pedido fragmentado", pois não existe entidade Pedido no domínio) e diagnóstico causal (RN-76) calculados sob demanda para clientes ATENÇÃO/CRÍTICO.

**Parser**: granularização de `_CATEGORIAS_COMP` (`cte_parser.py`) e `COMPONENTES` (`excel_parser.py`) — TDE e TDA ganham categoria própria (antes agrupadas em "Outros"); nova categoria "Estadia" (RN-73). **Limitação de retroatividade**: CT-e importados antes desta versão mantêm `destinatario_*` vazio e a composição de frete com TDE/TDA/Estadia ainda agrupados em "Outros" — não há reprocessamento automático, e reimportar o mesmo XML pela tela normal não corrige o registro (bloqueado pela deduplicação por chave, RN-02). **Correção disponível (DT-27)**: `backend/scripts/backfill_destinatario_v670.py` relê os XML originais e atualiza o CT-e existente por chave (nunca cria registro novo, nunca altera dado financeiro), idempotente — ver [`09_manutencao.md`](09_manutencao.md#scripts-de-manutenção).

**API**: `GET /dlg/{empresa}/analitico` aceita `dimensao=CLIENTE_FINAL` e ganha paginação server-side opcional (`page`/`page_size`, CA-16) — disponível às 5 dimensões, sem alterar o comportamento das 4 já existentes quando os parâmetros não são informados. `DlgResumoOut` ganha `top_clientes_finais`.

**Recomendações**: `_recomendacoes_dlg_clientes` gera automaticamente recomendação causal para o top-5 cliente CRÍTICO (nomeando a causa) e top-3 SEM_REF, além de alerta de concentração de risco financeiro em um único cliente (RN-71).

**IA**: novas ferramentas do Assistente Logístico `get_pior_cliente` e `get_ofensor_cliente` — narram a causa já calculada por RN-76, nunca recalculam.

**Frontend**: `DiagnosticoDLG.jsx` ganha "Cliente" como 5ª opção do seletor de dimensão, sem alterar o comportamento das 4 existentes; tabela expansível (linha sempre visível + painel de diagnóstico sob demanda, com gráfico de composição, métricas de adicionais/fragmentação e texto causal); ranking próprio da dimensão (7 critérios) e paginação.

**Sem regressão**: FILIAL/ROTA/TRANSPORTADORA/REGIAO preservam 100% do comportamento e valores financeiros já testados, apenas ganhando o campo genérico `composicao_frete` (aditivo).

**Testes**: novo `backend/tests/test_v670_dimensao_cliente.py` (23 testes) — RN-68 (dedup), RN-72/73/74 (composição/parser/ranking), RN-75 (fragmentação, limite exato de janela), RN-76 (diagnóstico causal, 4 combinações), RN-77 (recomendação causal), ferramenta de IA, extração de destinatário do XML, backfill de destinatário/composição (DT-27, incluindo isolamento multi-tenant e idempotência), e regressão das 4 dimensões existentes.

## [6.7.1] — Reagrupamento visual do menu Benchmark Logístico

Os 8 itens do menu "Benchmark Logístico" (`frontend/src/layouts/AppLayout.jsx`) estavam em lista plana, misturando três lógicas diferentes no mesmo nível (escopo geográfico, base de comparação, ação/resultado). Reorganizados em 4 subseções visuais, do mais amplo ao mais específico: **Visão geral** (Dashboard Executivo), **Escala geográfica** (Nacional, Regional, Corredores OD), **Comparação de mercado** (Matriz OD/Mercado, Benchmark/MBL) e **Ação e resultado** (Transportadoras, Potencial de Economia).

**Mudança técnica**: config do grupo (array `GRUPOS`) ganha campo opcional `subgrupos` (lista de `{ titulo, itens }`) como alternativa ao `itens` plano já existente; usado apenas pelo grupo Benchmark Logístico, sem alterar a forma dos demais 7 grupos do menu. Cada subgrupo renderiza um rótulo não-clicável (mesmo estilo visual do cabeçalho do grupo — maiúsculas, cinza, letter-spacing — porém sem `onClick`/collapse próprio); o `Collapse` único do grupo é preservado.

**Sem mudança de comportamento**: ícones, rotas e a lógica de destaque do item ativo (`isAtivo`) preservados exatamente como estavam; nenhum item removido, criado ou renomeado; nenhuma rota, contrato de API, cálculo ou dado alterado. PATCH puro de navegação/IA.

## [6.7.2] — Ajustes de legibilidade na tela Benchmark Nacional

Seis ajustes de UI em `frontend/src/pages/BenchmarkNacional.jsx` e `frontend/src/components/BenchmarkComparacao.jsx`, sem alteração de cálculo, regra de negócio, API ou dado: (1) subtítulo fixo "Comparativo da operação com o mercado brasileiro", no lugar do nome da empresa concatenado; (2) rótulos dos 4 cards com unidade explícita ("Frete Total (R$)", "Mercadoria (R$)", "Peso Transportado (kg)", "Custo Médio (R$/kg)"); (3) rótulos "mín/médio/máx" trocados por "Mercado: Mínimo/Média/Máximo" nos blocos de comparação; (4) confirmado que a classificação (Excelente/Bom/Atenção/Crítico) já era exibida como selo colorido (`Chip`) — nenhuma mudança necessária; (5) desvio percentual passa de formato compacto com sinal (ex.: "-16,5%") para rótulo por extenso (ex.: "16,5% abaixo da média nacional"), em função local `rotuloDesvio` — os utilitários compartilhados `fmtDesvio`/`corDesvio` (usados em colunas de tabela de Regional/Corredores/Transportadoras/BID) não foram alterados; (6) texto extenso de critério de classificação no rodapé substituído por botão "ⓘ Critérios de classificação" que abre modal (`Dialog`) com o mesmo conteúdo.

**Sem regressão**: `BenchmarkComparacao` é usado exclusivamente por esta tela — nenhuma outra página do Benchmark foi afetada pela mudança de rótulos.

---

## Nota sobre nomenclatura de versão

Os documentos originais misturavam "nome de versão de produto" (ex.: "V3.1 — BID de Frete", "V4 — Inteligência com IA") com o número semver do próprio changelog, sem correspondência direta (produto "V3.1" = changelog `4.0.0`; produto "V4" = changelog `5.0.0`). A partir da v6.0.0, o changelog usa só o semver, sem nome de produto paralelo, para eliminar essa ambiguidade.

*Changelog mantido seguindo o espírito de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), com correção de ordem cronológica em relação à versão anterior deste documento (`archive/07_changelog.md`).*
