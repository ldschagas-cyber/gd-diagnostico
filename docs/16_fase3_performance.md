# 16 · Fase 3 — Auditoria de Performance

> **Escopo**: exclusivamente diagnóstico — nenhum arquivo de código, configuração, índice, cache ou infraestrutura foi alterado nesta fase. Nenhuma medição foi feita contra uma instância rodando com carga real (não há ambiente de staging com volume de produção disponível para benchmark) — toda análise é **estática** (leitura de código, contagem de consultas, análise de padrão de acesso a dados), não medição de tempo de resposta real. Isso está declarado explicitamente onde relevante. Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md), [`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md), [`15_fase2_qualidade_codigo.md`](15_fase2_qualidade_codigo.md).

---

## 1. Resumo Executivo

A performance do GD Frete Diagnóstico hoje é **adequada para o volume atual e arriscada para o volume que o roadmap declara como objetivo** (SaaS multiempresa). Não há gargalo que afete o uso atual — os problemas encontrados são todos de **degradação futura previsível**, não de lentidão presente.

Três achados já registrados na Fase 1 (A-06, A-07, A-09/A-10) são, na prática, os mesmos três gargalos centrais de performance desta fase — a Fase 1 os identificou pela lente arquitetural, esta fase os quantifica pela lente de volume/carga e adiciona um quarto: a **busca semântica do RAG faz uma varredura completa (O(n) em Python) de todos os documentos indexados da empresa a cada consulta**, apesar de o PostgreSQL de produção já ter a extensão `pgvector` instalada — o índice vetorial nativo (`ivfflat`/`hnsw`) nunca foi criado nem usado.

A capacidade de concorrência do backend hoje é modesta por desenho: 2 workers Uvicorn em produção, cada um com pool de conexão de banco de 5+10 (15 conexões), totalizando **30 conexões simultâneas ao banco no máximo**. Isso é suficiente para o número de clientes que a plataforma tem hoje, mas é uma decisão que precisa ser revisitada antes de "100 empresas" — não antes de "10".

Relatórios (PDF/Excel/Word/PowerPoint) e importação de CT-e são gerados de forma síncrona, dentro do próprio request HTTP, bloqueando um worker pelo tempo total do processamento — sem paralelismo entre eles nem fila. Isso é aceitável hoje (poucos usuários simultâneos, lotes limitados a 500 CT-e) e se torna um ponto de atenção direto conforme o número de empresas ativas simultaneamente cresce.

## 2. Nota de Performance

# **62 / 100**

Sem gargalo presente perceptível ao usuário hoje; múltiplos gargalos previsíveis e já identificáveis no código antes de qualquer crescimento significativo de volume ou de clientes.

## 3. Avaliação por Área

| Área | Nota | Leitura |
|---|---|---|
| Backend | 68/100 | Bem otimizado onde foi otimizado (agregação SQL); RAG e 2 componentes do diagnóstico não |
| Banco de Dados | 65/100 | Índices corretos em produção; pool de conexão modesto; gap dev/produção já conhecido (A-07) |
| Frontend | 55/100 | Zero code-splitting, cache de dados marginal — pesa mais a cada página nova |
| APIs | 62/100 | Sem paginação real na maioria das listagens; volume de resposta cresce sem limite em várias rotas |
| Dashboard | 60/100 | 3 de 5 componentes otimizados; os outros 2 escalam com o volume de CT-e por empresa |
| Importações | 65/100 | Limites de lote adequados; processamento 100% síncrono, sem fila |
| Relatórios | 60/100 | Sem N+1 (bom); geração 100% síncrona, sem limite de tamanho testado |
| Infraestrutura | 55/100 | 2 workers, pool de 30 conexões total, sem limite de recurso, sem autoscaling |

## 4. Principais Gargalos Encontrados

---

### PF-01 — Composição de frete e OTIF carregam todos os CT-e do período em memória Python

- **Descrição**: idêntico ao achado A-06 da Fase 1, aqui quantificado pela ótica de performance: `diagnostico.py:73-79` chama `cte_repo.list_by_empresa(...)`, materializando cada CT-e do período como objeto Python, para calcular só 2 dos 5 componentes do diagnóstico (composição de frete e prazo/OTIF) — os outros 3 (nacional, regional, transportadora) já usam `GROUP BY` no banco.
- **Evidência técnica**: `app/application/use_cases/diagnostico.py:73-79,282-290`.
- **Impacto atual**: baixo — os volumes de CT-e por empresa hoje são pequenos o suficiente para não gerar lentidão perceptível.
- **Impacto futuro**: alto — é o endpoint mais chamado do sistema (`GET /dashboard/{empresa_id}`). Para uma empresa com dezenas/centenas de milhares de CT-e no período selecionado, essa chamada cresce linearmente em tempo e em memória a cada CT-e adicional, sem limite superior.
- **Prioridade**: P1 — Alto
- **Recomendação**: mover a agregação de composição de frete para SQL nativo do PostgreSQL (`jsonb_each`/`json_agg`), e a de prazo/OTIF para `AVG`/`COUNT` agregados, mantendo só o que realmente precisa de objeto individual em Python.

---

### PF-02 — Índice composto crítico ausente no caminho de criação de schema via `create_all()`

- **Descrição**: idêntico ao achado A-07 da Fase 1. Os índices `ix_ctes_empresa_data_emissao` e `ix_ctes_empresa_transportadora` existem em produção (via Alembic), mas não estão declarados no modelo ORM nem na lista de alterações incrementais que o `main.py` aplica em desenvolvimento.
- **Evidência técnica**: `app/infrastructure/database/models/__init__.py:158` (ausência em `__table_args__`), `alembic/versions/a2f8c1e4b9d3_...py:47-54` (onde de fato existem).
- **Impacto atual**: nenhum em produção; em desenvolvimento, gera uma falsa sensação de performance (para melhor ou pior) que não reflete o ambiente real.
- **Impacto futuro**: qualquer teste de performance ou de carga feito localmente sem rodar `alembic upgrade head` primeiro vai medir um cenário que não existe em produção.
- **Prioridade**: P1 — Alto
- **Recomendação**: declarar os índices no modelo ORM (torna o `create_all()` consistente automaticamente).

---

### PF-03 — Busca semântica do RAG é uma varredura completa em Python, sem índice vetorial

- **Descrição**: `RagService.buscar()` carrega **todos** os documentos indexados da empresa (+ documentos globais) com `q.all()`, depois calcula similaridade de cosseno em um loop Python para cada um, antes de ordenar e cortar pelo `top_k`. O PostgreSQL de produção já tem a extensão `pgvector` instalada, mas não há coluna `vector` nem índice `ivfflat`/`hnsw` em uso — os embeddings são armazenados como JSON.
- **Evidência técnica**: `app/application/use_cases/rag_service.py:151-178`.
- **Impacto atual**: baixo — o volume de documentos indexados por empresa hoje é pequeno (diagnósticos, relatórios e BIDs encerrados de poucos meses de uso).
- **Impacto futuro**: cresce de forma acumulativa e silenciosa — diferente da maioria dos gargalos desta auditoria (que escalam com o volume de CT-e, que o usuário controla via filtro de período), este escala com **o tempo de uso da plataforma por aquela empresa** (todo diagnóstico e relatório gerado é auto-indexado) e não tem filtro de período para conter o crescimento. Depois de alguns anos de uso intenso de uma empresa grande, cada busca do Assistente Logístico pode ficar perceptivelmente mais lenta, sem que nada tenha "quebrado" — só cresceu.
- **Prioridade**: P2 — Médio (baixo hoje, mas é o único gargalo desta lista sem um limite natural de contenção)
- **Recomendação**: migrar o armazenamento de embedding para coluna `vector` nativa do `pgvector` com índice `ivfflat`, e/ou aplicar um limite de janela temporal (ex.: só os últimos N documentos ou últimos X meses) na busca por padrão.

---

### PF-04 — Zero code-splitting no frontend

- **Descrição**: idêntico ao achado A-09 da Fase 1. `App.jsx` importa as ~44 páginas estaticamente; nenhuma usa `React.lazy`.
- **Evidência técnica**: `frontend/src/App.jsx` (todos os imports de página no topo do arquivo); aviso do próprio `vite build` de chunk de ~920 kB (MUI).
- **Impacto atual**: tempo de carregamento inicial da aplicação maior do que precisaria ser, para todo usuário, independente de quais módulos ele usa.
- **Impacto futuro**: cada módulo novo (V5/V6) piora esse tempo para 100% dos usuários, mesmo os que nunca abrem esse módulo novo.
- **Prioridade**: P1 — Alto
- **Recomendação**: `React.lazy` + `Suspense` por rota/módulo.

---

### PF-05 — Cache de dados do frontend cobre ~7% das telas

- **Descrição**: idêntico ao achado A-10 da Fase 1. Só 3 de ~44 páginas usam os hooks de React Query já configurados (`queryClient.js`, `staleTime` 5min); as demais fazem fetch manual sem cache nem deduplicação.
- **Evidência técnica**: `grep -l "from \"../api/queries\"" frontend/src/pages/*.jsx` retorna 3 arquivos.
- **Impacto atual**: requisições redundantes ao backend a cada navegação entre telas que mostram o mesmo dado (ex.: lista de transportadoras).
- **Impacto futuro**: cresce com o número de usuários simultâneos por empresa — cada usuário gera sua própria carga redundante, sem se beneficiar de cache compartilhado.
- **Prioridade**: P1 — Alto
- **Recomendação**: completar a migração para React Query, priorizando as telas de maior tráfego (Dashboard, cadastros).

---

### PF-06 — Ausência de paginação real na maioria das listagens

- **Descrição**: a maior parte dos endpoints de listagem (`GET` que retorna lista) não expõe `skip`/`limit` como parâmetro de query — vários usam um `limit=1000` fixo no código (ex.: listagem de transportadoras) em vez de paginação de verdade controlada pelo cliente.
- **Evidência técnica**: padrão `limit=1000` já documentado desde a auditoria original (P-14) e reconfirmado presente em código de repositório (`repositories/__init__.py`, chamadas com `limit=1000` hardcoded).
- **Impacto atual**: baixo — nenhuma empresa hoje tem 1000+ transportadoras ou registros cadastrais.
- **Impacto futuro**: médio — cresce especificamente com o número de transportadoras/clusters/regras cadastradas por empresa, não com o volume de CT-e (que já tem outros controles).
- **Prioridade**: P2 — Médio
- **Recomendação**: expor `skip`/`limit` real nos endpoints de listagem de cadastro, com um teto configurável em vez de fixo em 1000.

---

### PF-07 — Relatórios e importação são 100% síncronos, sem fila

- **Descrição**: geração de relatório (PDF/Excel/Word/PowerPoint) e importação de CT-e/Excel rodam inteiramente dentro do ciclo de vida do request HTTP — nenhum dos dois usa Celery (confirmado: só a tarefa agendada de insights diários usa `.delay()`; toda ação disparada pelo usuário via API, incluindo relatórios e importação, é síncrona).
- **Evidência técnica**: ausência de `.delay()`/`.apply_async()` em `app/infrastructure/reports/*.py` e em `app/application/use_cases/importacao.py`; confirmado por grep que só `ai_tasks.py:69` usa Celery.
- **Impacto atual**: baixo-médio — não há N+1 dentro da geração de relatório (verificado: os loops de montagem de Excel/PDF iteram sobre dados já carregados em memória, sem consulta adicional por linha), mas o tempo total do request é proporcional ao volume de dados do relatório (ex.: 12 meses de diagnóstico com muitas regiões/transportadoras).
- **Impacto futuro**: com só 2 workers Uvicorn em produção (achado PF-08), um relatório grande ou uma importação de lote cheio (500 arquivos) ocupa um dos 2 workers pelo tempo total da operação — outro usuário de **outra empresa** pode notar lentidão na mesma janela, já que os workers são compartilhados entre todos os tenants.
- **Prioridade**: P1 — Alto
- **Recomendação**: mover geração de relatório e importação de lotes grandes para Celery (já disponível na stack para IA), com endpoint de status/polling — como já documentado como padrão em uso para insights.

---

### PF-08 — Capacidade de concorrência do backend é modesta por desenho

- **Descrição**: `docker-compose.prod.yml` sobe o backend com `--workers 2`; cada worker (processo Uvicorn) abre seu próprio pool de conexão SQLAlchemy (`pool_size=5, max_overflow=10` — 15 conexões por worker). Total: **2 workers × 15 conexões = 30 conexões simultâneas ao banco**, no máximo, para toda a plataforma.
- **Evidência técnica**: `docker-compose.prod.yml` (`--workers 2`), `app/core/database.py:27-30` (`pool_size=5, max_overflow=10, pool_timeout=30`).
- **Impacto atual**: nenhum — a base de clientes atual está muito abaixo desse teto.
- **Impacto futuro**: direto — é o número que primeiro estoura conforme o número de empresas-cliente simultaneamente ativas cresce. Sem medição de carga real, não é possível cravar "até quantos usuários simultâneos" — mas é a variável mais fácil de monitorar e mais barata de aumentar (mais workers, pool maior, ou um pooler como PgBouncer) antes que vire problema.
- **Prioridade**: P1 — Alto
- **Recomendação**: instrumentar (mesmo que rudimentarmente) o uso do pool de conexão em produção, e revisitar `--workers`/`pool_size` como parte do planejamento de onboarding de novos clientes-âncora (grandes).

---

### PF-09 — Ausência de limite de recurso (CPU/memória) por container

- **Descrição**: nenhum serviço em `docker-compose.prod.yml` declara `deploy.resources.limits`.
- **Impacto atual**: baixo (host único, poucos serviços).
- **Impacto futuro**: sem limite, um pico de uso (ex.: geração de relatório grande, ou a varredura RAG do achado PF-03 crescendo) pode consumir memória/CPU além do previsto e afetar os outros containers no mesmo host, incluindo o banco de dados.
- **Prioridade**: P2 — Médio
- **Recomendação**: declarar limites conservadores por serviço.

---

## 5. Cenários de Crescimento

> Estimativas qualitativas baseadas em leitura de código, não em benchmark medido — não há ambiente de carga disponível para esta auditoria produzir números de latência real.

| Cenário | Avaliação |
|---|---|
| **10 empresas** | Sem problema. Nenhum dos achados desta fase se manifesta de forma perceptível nesse volume — inclusive o pool de 30 conexões e a ausência de code-splitting/cache são invisíveis ao usuário final nessa escala. |
| **100 empresas** | Ainda provavelmente confortável **se o uso simultâneo for baixo** (poucos usuários logados ao mesmo tempo por empresa), mas é o ponto em que os achados PF-04/PF-05 (frontend) começam a ficar perceptíveis a cada usuário individual, e o primeiro ponto razoável para revisitar o pool de conexão (PF-08) antes que vire um problema real, não depois. |
| **1.000 empresas** | Risco concreto sem intervenção prévia: PF-08 (pool de 30 conexões) é a primeira variável que provavelmente precisa mudar; PF-07 (relatórios/importação síncronos competindo pelos mesmos 2 workers entre *todos* os tenants) passa de "hipotético" para "observável" nesse volume; PF-01 (memória do dashboard) depende do volume de CT-e por empresa individual, não do número de empresas, mas com 1.000 empresas a chance de ter pelo menos algumas com volume alto de CT-e cresce. |
| **Grande volume de CT-e por empresa** (não depende do número de empresas) | É onde PF-01 e PF-02 se manifestam diretamente — uma única empresa grande, mesmo sendo a única cliente da plataforma, já sentiria esses dois achados ao acumular histórico de CT-e ao longo de anos. |

## 6. Quick Wins (baixo esforço, alto impacto)

- PF-02: declarar os índices compostos de `ctes` em `__table_args__` do modelo (uma linha de código).
- PF-06: expor `skip`/`limit` real nos 3-4 endpoints de listagem mais usados (transportadoras, clusters).
- PF-09: declarar limites de recurso conservadores no compose de produção.
- PF-04 (início): aplicar `React.lazy` primeiro só nos módulos maiores/menos usados por todos (BID, IA) — não precisa ser em todas as 44 páginas de uma vez para já reduzir o bundle inicial.

## 7. Melhorias Estruturais

**Médio prazo**:
- PF-01: mover composição de frete e OTIF para agregação SQL nativa do PostgreSQL.
- PF-05: completar a migração para React Query nas telas de maior tráfego.
- PF-07: mover geração de relatório e importação de lotes grandes para Celery, com endpoint de status.

**Longo prazo**:
- PF-03: migrar embeddings do RAG para coluna `vector` nativa com índice `ivfflat`/`hnsw`.
- PF-08: revisitar arquitetura de concorrência (mais workers, pool maior, ou PgBouncer) como parte do planejamento de crescimento de clientes, não como reação a um incidente.

## 8. Roadmap de Performance

### Curto prazo

- PF-02, PF-06 (parcial), PF-09 — todos de baixo esforço, sem dependência entre si.
- Instrumentar minimamente o uso do pool de conexão em produção (PF-08) para ter visibilidade antes de precisar agir.

### Médio prazo

- PF-01 (agregação SQL de composição/OTIF).
- PF-04/PF-05 (code-splitting + React Query) no frontend.
- PF-07 (mover relatórios/importação de lote para Celery).

### Longo prazo — preparação para escala SaaS

- PF-03 (índice vetorial nativo do RAG).
- PF-08 (revisão de arquitetura de concorrência do backend) — condicionado ao número real de clientes-âncora contratados, não a um número arbitrário.
- Reavaliação completa de performance com medição real de carga (benchmark/load test), algo que esta auditoria não pôde fazer por falta de ambiente de carga disponível — recomendado antes do primeiro cliente-âncora de grande volume.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma alteração de código, configuração, índice ou infraestrutura foi feita durante esta auditoria.*
