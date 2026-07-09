# 02 · Especificação Funcional

> Consolida e substitui `archive/01_especificacao_funcional.md`, `archive/especificacao_funcional.docx` e `archive/especificacao_funcional_benchmark_od_v2.1.docx`. Versão do sistema: **6.5.1**.

## 1. Objetivo da plataforma

Dar a uma empresa embarcadora (ou à consultoria que a atende) visibilidade completa sobre seus custos de frete: quanto paga, como isso se compara ao mercado e ao seu próprio histórico, onde estão as maiores oportunidades de economia, e uma via estruturada (BID) para renegociar com transportadoras — com uma camada de IA que narra e prioriza, mas nunca calcula (todo número vem de SQL determinístico).

## 2. Módulos e fluxos principais

### 2.1 Cadastros base

Empresas (embarcadores-clientes da plataforma) e suas Filiais, Transportadoras, Regiões Logísticas, Cidades, Metas (nacional e por macrorregião), e Usuários com papel de acesso. Toda entidade operacional (transportadora, CT-e, BID, insight etc.) pertence a uma empresa (`empresa_id`) — ver seção 5 sobre isolamento multi-tenant. Regiões, cidades, metas e o benchmark "legado" (seção 2.5, item 1) permanecem cadastros **globais** da plataforma, compartilhados por todas as empresas — essa é uma decisão de design mantida desde o MVP, não uma lacuna.

### 2.2 Importação de dados

- **CT-e XML** — upload de múltiplos arquivos (máx. 500 por lote, 10 MB por arquivo, validação de assinatura/magic bytes, parser com proteção `defusedxml` contra XML bomb). Extrai peso taxado, valor de frete, valor de mercadoria, composição do frete, transportadora (auto-cadastrada por CNPJ se desconhecida, sempre vinculada à empresa importadora), origem/destino.
- **Excel** — importação alternativa quando não há XML, com opção de atualizar registros já importados.
- **Cancelamento de CT-e via XML de evento oficial** — localiza o CT-e pela chave de acesso no escopo da empresa, marca como `CANCELADO`, registra protocolo/data/número do evento; toda ocorrência (sucesso, duplicado, CT-e não encontrado, erro) fica registrada em log auditável.
- **Regiões via CSV** e **Cidades via Excel** (com modelo de download e derivação automática da macrorregião pela UF).
- **Clusters do cliente via Excel** (mapeamento UF/município → hub logístico).
- **Propostas de BID via Excel** (com modelo pré-preenchido por transportadora convidada × grupo do escopo).

### 2.3 Diagnóstico Logístico (Dashboard)

A partir dos CT-e ativos (não cancelados) de uma empresa e período, calcula: indicador nacional (custo/kg, % frete, comparação com meta), indicadores regionais (por macrorregião), indicadores por transportadora, indicadores de prazo (OTIF), composição do frete por categoria, e oportunidades textuais. Ver fórmulas em [`06_regras_de_negocio.md`](06_regras_de_negocio.md#diagnóstico-e-indicadores).

### 2.4 DLG — Diagnóstico Logístico Analítico

Motor mais granular e mais recente que o Diagnóstico clássico: calcula KPIs (R$/kg, % frete, custo por entrega) por cinco dimensões — Filial, Rota, Transportadora, Região e **Cliente** (destinatário da mercadoria, v6.7.0) — com classificação automática de eficiência e detecção de outliers estatísticos. Suporta modo consolidado (agrega múltiplos meses) e modo mensal. É processado sob demanda (idempotente) e alimenta o MBL, o MCL e as Recomendações.

A dimensão **Cliente** vai além de medir custo: diagnostica a causa dominante do desvio quando identificável — participação de componentes adicionais de frete (TDE, TDA, Estadia, Pedágio, GRIS, Seguro, Ademe, Despacho) e/ou fragmentação operacional (múltiplos despachos em janela curta para o mesmo destinatário) — sempre de forma 100% determinística (RN-72 a RN-77, `docs/06_regras_de_negocio.md`), nunca inferida por IA.

### 2.5 Benchmark Logístico — três gerações de modelo coexistindo

O sistema hoje sustenta **três modelos de benchmark simultâneos**, cada um com seu propósito, sem que o mais novo substitua o mais antigo:

1. **Benchmark regional legado (v1)** — referência única por macrorregião + Nacional, cadastrada manualmente por um administrador. É a referência mais simples e a mais antiga; permanece no banco como fallback.
2. **Benchmark por Corredor OD / hubs (v2.1)** — corrige o viés do modelo v1 de comparar apenas pelo destino, ignorando a origem (ex.: um frete Recife→Porto Alegre e um Recife→Recife eram injustamente comparados à mesma referência regional). Introduz **Hub Logístico** (catálogo global de clusters macro), **Cluster do Cliente** (mapa UF/município → hub, específico da empresa) e **Benchmark de Corredor** (referência Hub-origem→Hub-destino, global). O corredor de cada CT-e é resolvido por: cluster do cliente por município → cluster por UF → UF como hub implícito.
3. **Benchmark V2 / Matriz de Mercado (v6.0)** — o modelo mais atual: uma matriz global de mercado por região OD com percentis P10/P25/P50/P75/P90 (fonte de verdade editável por admin), mais um **Benchmark Observado** calculado a partir dos próprios CT-e da empresa (mesmos percentis, por período). Resolve a referência do cliente com hierarquia **CLIENTE (override manual) > MERCADO (fonte de verdade) > indisponível**.

Adicionalmente, o **MBL (Benchmark Logístico estatístico)** calcula percentis próprios da base do cliente (por Região/Cluster/Rota × métrica), **excluindo os outliers já detectados pelo DLG** — é o benchmark usado internamente pelo motor de decisão de BID (MCL), não uma referência de mercado externa.

### 2.6 Recomendações

Consolida automaticamente, de forma determinística (sem IA), uma lista priorizada de ações a partir dos indicadores e do DLG: cancelamento acima do limiar, custo/kg acima da meta, % frete acima da meta, concentração excessiva em uma transportadora, regiões acima da meta, rotas críticas do DLG e rotas sem referência de benchmark (upsell de cadastro). Cada recomendação é idempotente (upsert por chave natural) e preserva o status editado manualmente pelo usuário mesmo quando reprocessada.

### 2.7 Concorrência Logística — BID de Frete

Fluxo completo de cotação eletrônica entre transportadoras:

1. **Criar BID** (nome, objetivo, período de análise, segmentação opcional por região/cidade/região logística).
2. **Gerar escopo** — agregação SQL dos CT-e do período por tipo de agrupamento (Região, UF, Transportadora, Filial ou faixas de peso livres).
3. **Convidar transportadoras** (do cadastro da própria empresa) e acompanhar status de participação.
4. **Coletar propostas** (inclusão manual ou importação em massa via Excel).
5. **Comparar** propostas entre si, contra o custo atual e contra a referência de mercado (P50/P75 do Benchmark V2).
6. **Simular cenários** de distribuição de carga entre transportadoras, com cálculo de economia.
7. **Decidir (MCL)** — motor de decisão pondera preço, histórico de eficiência (DLG/MBL), prazo e estabilidade para apontar a vencedora, com decisão versionada e rastreável.
8. **Relatórios** — pacote de cotação (sem dados sensíveis), comparativo, ranking, economia, resultado final — em PDF/Excel.

A máquina de estados do BID é: `RASCUNHO → ABERTO → EM_COTACAO → ENCERRADO`, com `CANCELADO` acessível a partir de qualquer estado não-terminal. Toda ação relevante gera um registro de auditoria.

### 2.8 Inteligência Logística com IA

Camada de IA que **narra e prioriza; nunca calcula** — todo número vem de SQL. Funciona com modo simulado por padrão (sem custo de API) e pode ser ativada com chaves reais da OpenAI/Anthropic sem alteração de código.

- **Insights automáticos** — motor de regras configuráveis (armazenadas no banco, não hardcoded) que gera alertas classificados (Informativo/Atenção/Crítico/Oportunidade).
- **Diagnóstico IA** — análise executiva narrativa em seções fixas, com cache por hash de contexto (evita custo de IA se nada mudou desde a última geração).
- **Score Logístico** — nota 0-100 combinando cinco componentes ponderados (ver [`06`](06_regras_de_negocio.md#score-logístico)), com histórico temporal.
- **Benchmark Setorial** — compara a operação com médias de 6 segmentos de mercado.
- **Oportunidades automáticas** — detecção de BID, Consolidação, Redistribuição, Renegociação e Concentração, com economia estimada e plano de ação.
- **Assistente Logístico** — chat com *tool-calling* sobre 8 ferramentas que executam SQL real (nunca a IA calculando por conta própria), com histórico de conversa por empresa.
- **RAG / Base de Conhecimento** — indexação e busca semântica (similaridade de cosseno) sobre diagnósticos, relatórios, BIDs encerrados e legislação ANTT pré-carregada (conhecimento global).
- **Relatório Executivo IA** — exportável em PDF, Word e PowerPoint a partir do Diagnóstico IA.

### 2.9 Relatórios

Diagnóstico e Benchmark em Excel/PDF; conjunto completo de relatórios de BID (executivo, comparativo, ranking, economia, resultado final, pacote de cotação) em PDF/Excel; Relatório Executivo IA em PDF/Word/PowerPoint.

## 3. Regras de negócio

Todas as fórmulas, pesos, limiares e classificações estão consolidados em [`06_regras_de_negocio.md`](06_regras_de_negocio.md), organizados por módulo, para evitar duplicação entre este documento e o catálogo de regras.

## 4. Controle de acesso

Ver [`01_visao_geral.md`](01_visao_geral.md#papéis-de-acesso) para o resumo dos papéis, e [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#autenticação-e-autorização) para o detalhamento técnico de como cada papel é aplicado em cada endpoint.

## 5. O que é global vs. o que é isolado por empresa (multi-tenant)

Esta é a pergunta mais importante para quem vai estender o sistema — e a resposta **não é uniforme**, por decisão de design em cada caso:

| Entidade | Escopo | Observação |
|---|---|---|
| CT-e, NF-e | Por empresa | Sempre foi isolado |
| Transportadoras | Por empresa | Isolado desde a migração `a2f8c1e4b9d3` (v3.0.0) — antes era global |
| BID e todos os seus artefatos (escopo, propostas, simulações, auditoria) | Por empresa | Isolado desde a introdução do módulo (v3.1) |
| Clusters do Cliente | Por empresa | Mapa UF/município → hub é específico de cada empresa |
| Benchmark Observado, Benchmark Cliente (V2) | Por empresa | |
| DLG, MBL, MCL, Recomendações | Por empresa | |
| Insights, Diagnóstico IA, Score Logístico, Oportunidades, Chat/RAG, Uso de IA | Por empresa | Isolamento obrigatório desde a concepção do módulo (v4.0.0/v5.0.0) |
| Usuários | Por empresa (exceto superusuário global, sem `empresa_id`) | Um ADMIN de empresa só vê/edita usuários da própria empresa |
| **Regiões e Cidades** | **Global** | Cadastro compartilhado por toda a plataforma — decisão de design mantida |
| **Metas (nacional e regional)** | **Global** | Idem — só ADMIN/superusuário pode editar |
| **Benchmark legado (por macrorregião)** | **Global** | Idem |
| **Hubs Logísticos** | **Global** (catálogo) | Cada empresa mapeia seu próprio cluster para os hubs globais |
| **Benchmark de Corredor (OD)** e **Matriz de Mercado (V2)** | **Global** | São a "fonte de verdade" de mercado, editável só por admin — cada empresa tem seu Benchmark Observado próprio para comparar contra essa referência global |
| **Benchmark Setorial** | **Global** | Referências de mercado por segmento |

## 6. Limitações conhecidas nesta versão (6.5.1)

- O papel VISUALIZADOR é aplicado no backend (todo endpoint de escrita retorna 403), mas o frontend ainda não esconde os botões de ação correspondentes para esse papel — a tela permanece "clicável", só que a ação falha.
- Não há testes automatizados de frontend.
- Alguns arquivos de repositório/schema/DTO do backend são monolíticos (um único arquivo por camada, não por módulo) — funcional, mas vai exigir refatoração se o número de módulos continuar crescendo.
- O modelo de roadmap V5 (Benchmark Coletivo Anonimizado entre clientes) e V6 (Inteligência de Mercado Logístico com fontes externas) **não estão implementados** — ver [`10_roadmap.md`](10_roadmap.md).
