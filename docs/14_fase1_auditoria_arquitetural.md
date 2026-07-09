# 14 · Fase 1 — Auditoria Técnica da Arquitetura

> **Escopo**: exclusivamente diagnóstico — nenhum arquivo de código, configuração ou banco de dados foi alterado nesta fase. Toda evidência abaixo foi coletada por leitura direta do código-fonte em 2026-07-07 (contagem de linhas, grep, leitura de trecho), não por inferência. Base oficial: `/docs` (Fase 0) e [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md).

---

## 1. Resumo Executivo

O GD Frete Diagnóstico tem uma **fundação arquitetural real e consistentemente aplicada nos módulos originais** (cadastro, importação, diagnóstico clássico, BID) — Clean Architecture com camadas de fato desacopladas, sem framework vazando para o domínio. Essa fundação, no entanto, **não foi mantida à mesma disciplina nos módulos construídos a partir da V4/v6.x** (DLG, MBL, MCL, Insights, Oportunidades, Score Logístico, Diagnóstico IA, RAG, Assistente, Recomendações, Benchmark V2/Observado/Setorial): 16 dos 25 use cases (64%) desses módulos importam e usam `sqlalchemy.orm.Session` diretamente, executando consultas SQL/ORM dentro da camada de aplicação em vez de passar pela camada de repositório que o resto do sistema respeita.

Isso não quebrou nada — o sistema funciona, os 68 testes passam, a Fase 0 encontrou e corrigiu as lacunas de segurança mais graves — mas significa que a arquitetura hoje é **duas arquiteturas coexistindo sob o mesmo nome**: uma Clean Architecture de livro-texto para ~36% do backend, e uma abordagem pragmática "use case com SQL embutido" para os outros 64%, que são justamente os módulos mais recentes e mais prováveis de crescer.

Paralelamente, encontrei três lacunas concretas de capacidade de crescimento que precisam de decisão agora, não depois: (1) o endpoint mais usado do sistema (`GET /dashboard/{empresa_id}`) ainda carrega todos os CT-e do período em memória Python para dois dos cinco componentes do diagnóstico; (2) o índice composto mais importante do banco (`empresa_id, data_emissao` em `ctes`) existe em produção via migration, mas **não existe** se o schema for criado via `create_all()` (o caminho de desenvolvimento local documentado); (3) o frontend carrega as ~44 páginas da aplicação inteira num único bundle inicial — não há nenhum code-splitting por rota.

Nenhum desses três é um incêndio hoje. Todos os três se tornam dolorosos exatamente quando o produto tiver o volume e o número de clientes que o roadmap pretende (ver [`10_roadmap.md`](10_roadmap.md)).

## 2. Nota da Arquitetura

# **66 / 100**

Fundação sólida, aplicação inconsistente, gaps de escala conhecidos e concretos — nenhum bloqueador imediato, várias decisões que precisam ser tomadas antes do próximo salto de volume/clientes.

## 3. Avaliação por Área

| Área | Nota | Leitura |
|---|---|---|
| Arquitetura Geral | 72/100 | Camadas reais e bem desenhadas nos módulos originais; erosão de consistência nos módulos novos |
| Backend | 68/100 | Bem organizado por router/use case, mas com dívida de acoplamento não resolvida há 2+ versões |
| Frontend | 62/100 | Consistente em convenções e tratamento de erro; zero code-splitting e adoção marginal de cache de dados |
| APIs | 70/100 | RBAC/multi-tenant agora consistente (pós Fase 0); contrato de resposta tipado ausente em um módulo inteiro |
| Banco de Dados | 68/100 | Modelagem sólida; índice crítico ausente no caminho de dev; 2 componentes de diagnóstico ainda em memória |
| Infraestrutura | 58/100 | Docker/Nginx corretos para o porte atual; zero observabilidade, sem backup versionado, prod sem fila |
| Escalabilidade | 55/100 | Os três gaps do resumo executivo são especificamente gaps de escala, não de funcionalidade |
| Manutenibilidade | 74/100 | Documentação agora completa (Fase 0); nomenclatura consistente; mas dois "estilos" de use case a aprender |

## 4. Pontos Fortes

- **Regra de dependência real, não só nominal**: zero import de `fastapi` dentro de `domain/`ou `application/`; zero import de `sqlalchemy` dentro de `domain/`. A separação apresentação→aplicação→domínio é respeitada na direção correta em toda a base.
- **RBAC e isolamento multi-tenant hoje consistentes** nos 19 routers, após a correção da Fase 0 (era a maior lacuna real do sistema; está fechada).
- **Tratamento de erro no frontend é uniforme**: as 44 páginas usam `extrairErro()` (100% de cobertura confirmada por grep) — não há inconsistência de "algumas telas mostram erro, outras engolem".
- **Agregações SQL corretas onde foram aplicadas**: os 3 indicadores principais do diagnóstico (nacional/regional/transportadora) usam `GROUP BY` no banco, não Python — a correção de performance da v3.0.0 nesses três pontos é real e continua vigente.
- **Documentação técnica agora completa e rastreável** (Fase 0) — reduz drasticamente o risco de auditar código sem contexto, que era o estado anterior.
- **Módulo de IA desacoplado do provedor**: a troca de "modo simulado" para modelos reais é uma flag de configuração, não uma reescrita.

## 5. Pontos Fracos

- Camada de aplicação com duas disciplinas arquiteturais coexistindo (repositório vs. sessão direta), sem que isso esteja documentado como uma decisão consciente em lugar algum.
- Endpoint mais usado do sistema com um padrão de carga em memória que a própria organização já identificou como "maior risco de performance" há 2 versões, mas só corrigiu parcialmente.
- Frontend sem qualquer estratégia de carregamento incremental — todo o app é uma única entrega inicial.
- Zero observabilidade e zero backup versionado — a operação de produção depende inteiramente de intervenção manual bem-sucedida.
- Arquivos monolíticos que estavam "gerenciáveis" na auditoria anterior cresceram 2-3× e continuam sem divisão.
- Um módulo de API inteiro (Inteligência IA, 26 endpoints) sem contrato de resposta tipado.

## 6. Achados Técnicos

Cada achado é o resultado de leitura direta do código, com arquivo:linha citado. Classificação P0 (crítico) a P3 (baixo) conforme definido no escopo da Fase 1.

---

### A-01 — Use cases da camada de aplicação executam SQL/ORM diretamente, sem passar pela camada de repositório

- **Prioridade**: P2 — Médio
- **Descrição**: 16 dos 25 use cases (`dlg.py`, `mcl.py`, `mbl.py`, `insights.py`, `oportunidades.py`, `score_logistico.py`, `diagnostico_ia.py`, `recomendacoes.py`, `benchmark_v2.py`, `benchmark_observado.py`, `benchmark_setorial.py`, `assistente.py`, `assistente_tools.py`, `rag_service.py`, `relatorio_ia.py`, `bid_escopo.py`) recebem uma `sqlalchemy.orm.Session` diretamente no construtor e chamam `self.db.execute(...)`/`db.query(...)` dentro da própria regra de negócio.
- **Impacto**: a interface de repositório (`domain/repositories`) deixou de ser o único ponto de acesso a dados para todo módulo construído a partir da V4. Esses use cases não são testáveis sem um banco (real ou fake) — não dá para unit-testar a regra de negócio isoladamente.
- **Causa provável**: os módulos mais recentes precisam de agregação SQL pesada (`GROUP BY`, percentis, joins) que a interface de repositório genérica original não previa — a equipe optou por pragmatismo (SQL direto no use case) em vez de estender a camada de repositório.
- **Arquivos**: `app/application/use_cases/{dlg,mcl,mbl,insights,oportunidades,score_logistico,diagnostico_ia,recomendacoes,benchmark_v2,benchmark_observado,benchmark_setorial,assistente,assistente_tools,rag_service,relatorio_ia,bid_escopo}.py`
- **Risco de não corrigir**: nenhum risco funcional imediato. Risco de manutenibilidade: um novo desenvolvedor que aprende Clean Architecture pelos módulos antigos vai escrever código incompatível com o padrão real dos módulos novos, ou vice-versa.
- **Solução recomendada**: não é necessário reverter isso — dado o volume de agregação SQL necessário, faz sentido introduzir uma camada explícita de "query objects" ou "read models" na infraestrutura, mantendo o use case livre de `Session`, mas sem forçar tudo pela interface de repositório genérica original.
- **Esforço estimado**: Alto (arquitetural, não pontual) — decisão de design + migração incremental módulo a módulo.

---

### A-02 — `BenchmarkUseCase` acessa métodos privados de `DiagnosticoUseCase`

- **Prioridade**: P2 — Médio
- **Descrição**: `benchmark.py:137,179,204,235` chama `self.diagnostico._indicador_nacional(...)`, `self.diagnostico._indicadores_regionais(...)`, `self.diagnostico._indicadores_transportadora(...)` — métodos com prefixo `_` (privados por convenção) de outra classe.
- **Impacto**: qualquer refatoração de `DiagnosticoUseCase` pode quebrar `BenchmarkUseCase` silenciosamente, sem erro de import nem de tipo.
- **Causa provável**: identificado como P-01 na auditoria original (v2.0.0) e nunca resolvido — não foi esquecido, foi conscientemente adiado.
- **Arquivos**: `app/application/use_cases/benchmark.py:137,179,204,235`
- **Risco de não corrigir**: baixo no curto prazo (o código funciona), cresce a cada nova mudança em `DiagnosticoUseCase`.
- **Solução recomendada**: extrair os três métodos para um `IndicadoresService` compartilhado, ou promovê-los a métodos públicos com contrato estável.
- **Esforço estimado**: Baixo (poucas horas).

---

### A-03 — Duplicação literal da função de cálculo de percentil

- **Prioridade**: P2 — Médio
- **Descrição**: a função `_percentil` (interpolação linear, mesmo docstring "método igual ao numpy default") existe de forma duplicada em `benchmark_observado.py:30` e `mbl.py:46`.
- **Impacto**: uma correção de bug ou mudança de método de interpolação precisa ser aplicada em dois lugares; já divergiram uma vez do que o docstring promete (ambas dizem "igual ao numpy default" — não verificado nesta auditoria se ainda são idênticas byte a byte).
- **Causa provável**: os dois módulos (Benchmark V2 e MBL) foram desenvolvidos em momentos próximos, sem checagem de reuso.
- **Arquivos**: `app/application/use_cases/benchmark_observado.py:30`, `app/application/use_cases/mbl.py:46`
- **Risco de não corrigir**: baixo hoje, mas cresce se um terceiro módulo (ex.: um futuro benchmark setorial estatístico) reimplementar a mesma função pela terceira vez.
- **Solução recomendada**: extrair para `app/application/use_cases/_stats_utils.py` ou similar, compartilhado.
- **Esforço estimado**: Baixo (1-2 horas, com testes de regressão).

---

### A-04 — Instanciação manual repetida de `DiagnosticoUseCase`/`BenchmarkUseCase`

- **Prioridade**: P2 — Médio
- **Descrição**: `DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)` é reconstruído manualmente, com os mesmos 5 parâmetros, em 4 pontos diferentes: `dashboard.py:24`, `relatorios.py:32`, `relatorios.py:91`, `benchmark_analise.py:44`.
- **Impacto**: qualquer mudança na assinatura do construtor exige atualizar 4 lugares; já é exatamente o achado P-02 da auditoria v2.0.0, sem alteração desde então.
- **Causa provável**: nunca foi centralizado como uma dependency do FastAPI (`Depends()`), apesar do padrão já existir para outros use cases mais simples.
- **Arquivos**: `app/presentation/api/v1/dashboard.py:23-24`, `relatorios.py:32,91-92`, `benchmark_analise.py:40-46`
- **Risco de não corrigir**: baixo-médio — funcional hoje, mas é o tipo de duplicação que gera bug de "esqueci de atualizar um dos 4 lugares" na próxima mudança.
- **Solução recomendada**: mover para uma função `get_diagnostico_uc()`/`get_benchmark_uc()` em `dependencies.py`, como já é feito para outros use cases.
- **Esforço estimado**: Baixo (poucas horas).

---

### A-05 — Módulo de Inteligência IA sem contrato de resposta tipado

- **Prioridade**: P1 — Alto
- **Descrição**: nenhum dos 26 endpoints de `inteligencia.py` declara `response_model`. Toda resposta é um `dict` Python cru.
- **Impacto**: o Swagger/OpenAPI gerado para esse router não documenta o formato de resposta (schema vazio/genérico); clientes de API (incluindo o próprio frontend) não têm contrato tipado para validar contra mudanças; um campo renomeado ou removido no dict de resposta não gera nenhum erro de tipo em tempo de desenvolvimento, só quebra em runtime no frontend.
- **Causa provável**: desenvolvimento rápido do módulo de IA, retornando estruturas de dicionário ad-hoc por conveniência durante a fase de modo simulado.
- **Arquivos**: `app/presentation/api/v1/inteligencia.py` (todos os 26 endpoints)
- **Risco de não corrigir**: sobe conforme o módulo de IA cresce e ganha mais consumidores (ex.: se um dia houver um cliente de API externo, ou um app mobile).
- **Solução recomendada**: criar schemas Pydantic de resposta para cada família de endpoint (Insight, Score, Diagnóstico, Oportunidade, RAG) e declarar `response_model`.
- **Esforço estimado**: Médio (schemas para ~10 formatos de resposta distintos + testes).

---

### A-06 — `GET /dashboard/{empresa_id}` ainda carrega todos os CT-e do período em memória para 2 de 5 componentes

- **Prioridade**: P1 — Alto
- **Descrição**: `diagnostico.py:75-79` chama `self.cte_repo.list_by_empresa(empresa_id, data_inicio, data_fim, apenas_ativos=True)`, que retorna **todos os registros de CT-e do período como objetos Python**, usados só para calcular a composição do frete (`_composicao_frete`, linha 282) e os indicadores de prazo/OTIF (`listar_prazos`, linha 73). Os outros 3 componentes (nacional/regional/transportadora) já usam `GROUP BY` no banco.
- **Impacto**: para uma empresa com dezenas de milhares de CT-e no período selecionado, esse endpoint — o mais usado do sistema — materializa todos esses registros em memória Python a cada chamada, exatamente o padrão que a auditoria v2.0.0 chamou de "maior risco de performance" (P-21).
- **Causa provável**: a correção de performance da v3.0.0 (FASE 3) migrou 3 dos 5 componentes para SQL, mas composição de frete (que depende de um campo JSON, `composicao_frete`) e prazo (que precisa das datas individuais) ficaram de fora — provavelmente por serem tecnicamente mais difíceis de agregar em SQL puro (JSON aggregation, cálculo de intervalo de datas).
- **Arquivos**: `app/application/use_cases/diagnostico.py:73-79,282-290`
- **Risco de não corrigir**: sobe diretamente com o volume de CT-e por empresa — é o único dos achados desta auditoria com risco de degradar na frente do usuário (timeout de request) conforme uma empresa cliente cresce sua base histórica.
- **Solução recomendada**: agregação de `composicao_frete` via operadores JSON do PostgreSQL (`jsonb_each`, `json_agg`) diretamente no banco; para OTIF, considerar agregação com `AVG`/`COUNT` no SQL em vez de carregar cada CT-e individual.
- **Esforço estimado**: Médio-Alto (requer SQL específico de PostgreSQL, quebra a portabilidade com SQLite do modo dev, precisa de plano de teste).

---

### A-07 — Índice composto mais importante do sistema ausente no caminho de criação de schema via `create_all()`

- **Prioridade**: P1 — Alto
- **Descrição**: os índices `ix_ctes_empresa_data_emissao` e `ix_ctes_empresa_transportadora` (criados pela migration `a2f8c1e4b9d3`, especificamente para acelerar a query mais comum do sistema) **não estão declarados em `__table_args__` do `CTeModel`** (`app/infrastructure/database/models/__init__.py`), e **não estão na lista de alterações incrementais** que `app/main.py` aplica em ambiente de desenvolvimento (`_aplicar_alteracoes_incrementais`).
- **Impacto**: um banco de desenvolvimento criado do zero via `create_all()` (o caminho documentado para "ambiente local sem Docker" em [`08_instalacao_deploy.md`](08_instalacao_deploy.md)) **não tem esses índices** — só um banco que passou por `alembic upgrade head` os tem. Isso significa que testes de performance feitos localmente sem rodar as migrations vão parecer bons ou ruins de forma enganosa (não refletem o schema de produção).
- **Causa provável**: os índices foram adicionados via `batch_op.create_index()` direto na migration, sem replicar a declaração no modelo ORM nem na lista de `ALTER TABLE... IF NOT EXISTS` que o `main.py` mantém para paridade de dev.
- **Arquivos**: `app/infrastructure/database/models/__init__.py:158` (CTeModel, falta o índice composto em `__table_args__`), `app/main.py` (função `_aplicar_alteracoes_incrementais`, não lista esses dois índices), `alembic/versions/a2f8c1e4b9d3_...py:47-54` (onde os índices realmente são criados)
- **Risco de não corrigir**: médio — não afeta produção (que usa Alembic corretamente), mas gera uma falsa sensação de que "funciona bem localmente" que pode não se sustentar em produção sob volume real, ou o inverso (alguém agrega esses índices só na migration e esquece de portar para o create_all, criando divergência silenciosa entre ambientes).
- **Solução recomendada**: declarar os índices compostos também em `__table_args__` do `CTeModel` (isso os torna parte do `create_all()` automaticamente) ou adicioná-los à lista de alterações incrementais do `main.py`.
- **Esforço estimado**: Baixo (uma linha de código + teste local).

---

### A-08 — `docker-compose.prod.yml` não inclui Redis/Celery — job diário de insights nunca executa em produção

- **Prioridade**: P1 — Alto
- **Descrição**: o compose de produção tem exatamente 3 serviços (`db`, `backend`, `frontend`) — nenhum Redis, worker ou beat do Celery. Investigação confirmou que **as ações de IA acionadas pelo usuário via API não usam Celery** (ex.: `POST /inteligencia/insights/gerar` roda o use case de forma síncrona, sem `.delay()`) — só a tarefa agendada (`ai_tasks.py:69`, `gerar_insights_empresa.delay(empresa_id)`, disparada pelo Celery Beat) depende dessa infraestrutura.
- **Impacto**: o impacto real é mais restrito do que pareceria à primeira vista — as telas de IA continuam funcionando normalmente (o usuário clica "gerar insights" e funciona, síncrono). O que **não acontece** é a geração automática diária de insights para todas as empresas — silenciosamente, sem erro visível a ninguém, porque não há processo tentando e falhando; simplesmente não há Beat rodando.
- **Causa provável**: o compose de produção foi construído antes ou sem revisão pós-módulo de IA (v5.0.0); Redis/Celery foram adicionados ao `docker-compose.dev.yml` mas o de produção não foi atualizado em paralelo.
- **Arquivos**: `docker-compose.prod.yml` (serviços declarados), `app/infrastructure/tasks/ai_tasks.py:60-72` (beat schedule), `app/infrastructure/celery_app.py:43` (`beat_schedule`)
- **Risco de não corrigir**: baixo-médio — feature "silenciosamente ausente", não bug visível; mas mina a confiança na automação de IA se alguém assumir que os insights diários estão sendo gerados.
- **Solução recomendada**: adicionar serviços `redis`, `celery_worker`, `celery_beat` ao `docker-compose.prod.yml`.
- **Esforço estimado**: Baixo-Médio (configuração de infraestrutura + teste de deploy).

---

### A-09 — Frontend sem code-splitting por rota

- **Prioridade**: P1 — Alto
- **Descrição**: `App.jsx` importa as ~44 páginas de forma estática no topo do arquivo (0 ocorrências de `React.lazy`/`Suspense` para rotas). Todo o código de todas as telas (incluindo módulos que uma empresa pode nunca usar, como BID ou IA) entra no bundle JavaScript inicial.
- **Impacto**: consistente com o aviso já emitido pelo próprio `vite build` ("chunks maiores que 900 kB" no bundle do MUI) — o usuário baixa e faz parse de código de telas que talvez nunca abra, aumentando o tempo até a aplicação ficar interativa, especialmente em conexões mais lentas.
- **Causa provável**: o app cresceu de um MVP pequeno (poucas páginas) para ~44 páginas sem que a estratégia de carregamento fosse revisitada.
- **Arquivos**: `frontend/src/App.jsx` (todos os `import` de `src/pages/*.jsx`)
- **Risco de não corrigir**: sobe proporcionalmente ao número de páginas novas adicionadas — cada módulo futuro (V5/V6) piora o tempo de carregamento inicial de todo mundo, mesmo quem nunca usa esse módulo.
- **Solução recomendada**: `React.lazy()` + `Suspense` por rota, agrupado por módulo (ex.: todas as páginas de BID em um chunk, todas as de IA em outro) — o `vite.config.js` já tem `manualChunks` para bibliotecas, falta o equivalente para código próprio.
- **Esforço estimado**: Médio (mudança mecânica, mas toca todas as rotas — precisa de teste de regressão visual).

---

### A-10 — Adoção de React Query é marginal (não parcial)

- **Prioridade**: P1 — Alto
- **Descrição**: apenas 3 das ~44 páginas usam hooks de `src/api/queries.js` (React Query). As demais ~38 fazem fetch manual via `useState`+`useEffect`, chamando `endpoints.js` diretamente.
- **Impacto**: cache, deduplicação de requisição, invalidação automática e refetch em foco/reconexão — tudo isso que o React Query já está configurado para fazer (`queryClient.js`) — só se aplica a ~7% das telas. As outras ~93% refazem a mesma requisição toda vez que a tela monta, mesmo que o dado não tenha mudado, e não compartilham cache entre telas que mostram a mesma informação (ex.: lista de transportadoras).
- **Causa provável**: a migração para React Query foi iniciada, mas não finalizada — a Fase 0 já havia registrado isso como "adoção parcial"; a investigação desta auditoria mostra que o termo era otimista.
- **Arquivos**: 3 arquivos usam `from "../api/queries"`; os demais ~38 usam `useEffect` com fetch direto — lista completa disponível via `grep -l "from \"../api/queries\"" frontend/src/pages/*.jsx`.
- **Risco de não corrigir**: sobe com o número de usuários simultâneos por empresa (mais requisições redundantes ao backend) e com o número de telas que mostram o mesmo dado.
- **Solução recomendada**: completar a migração, priorizando as páginas com maior tráfego (Dashboard, listagens de cadastro).
- **Esforço estimado**: Alto (mecânico, mas em ~38 arquivos, com risco de regressão por arquivo).

---

### A-11 — Zero observabilidade

- **Prioridade**: P2 — Médio
- **Descrição**: busca por `sentry`, `prometheus`, `opentelemetry` em todo o backend (código e `requirements.txt`) não retorna nenhuma ocorrência.
- **Impacto**: um erro em produção só é percebido se um usuário reportar ou se alguém observar os logs manualmente (`docker compose logs`). Não há alerta automático, não há métrica de latência/taxa de erro, não há rastreamento distribuído.
- **Causa provável**: nunca priorizado frente às features de negócio.
- **Arquivos**: N/A (ausência, não presença)
- **Risco de não corrigir**: sobe com o número de clientes em produção simultaneamente — hoje, um incidente pode passar despercebido por horas.
- **Solução recomendada**: no mínimo, Sentry (self-hosted ou cloud) para captura de exceção; métricas básicas via Prometheus/Grafana ficam para quando houver mais de um cliente em produção.
- **Esforço estimado**: Baixo-Médio (Sentry é integração rápida; Prometheus/Grafana é mais trabalho).

---

### A-12 — Sem script de backup versionado no repositório

- **Prioridade**: P2 — Médio
- **Descrição**: busca por qualquer arquivo com "backup" no nome, em todo o repositório, não encontra nada. O procedimento de backup existe só como comando `pg_dump` documentado em texto ([`08_instalacao_deploy.md`](08_instalacao_deploy.md)), nunca como script versionado/testável.
- **Impacto**: o procedimento de backup depende de alguém copiar e colar o comando certo manualmente (ou de um cron configurado fora do repositório, não auditável em code review).
- **Arquivos**: N/A (ausência)
- **Risco de não corrigir**: alto em termos de continuidade de negócio SE nunca for de fato configurado; a documentação existir não garante que o backup está de fato rodando em produção hoje.
- **Solução recomendada**: script `scripts/backup.sh` versionado + configuração de cron/systemd timer documentada a partir do script, não do comando solto.
- **Esforço estimado**: Baixo (poucas horas).

---

### A-13 — Arquivos monolíticos cresceram desde a última auditoria em vez de serem divididos

- **Prioridade**: P3 — Baixo (hoje) / tendência para P2
- **Descrição**: comparado à auditoria anterior (v2.0.0): `schemas/__init__.py` foi de 340 para 830 linhas; `dtos/__init__.py` de 178 para 274; `repositories/__init__.py` de 472 para 1.538; `main.py` de 174 para 474.
- **Impacto**: cada um desses arquivos concentra todos os módulos numa única unidade de código — qualquer PR que toque em qualquer módulo gera diff nesses arquivos gigantes, aumentando risco de conflito de merge e dificultando revisão de código.
- **Arquivos**: `app/presentation/schemas/__init__.py` (830 linhas), `app/infrastructure/database/repositories/__init__.py` (1.538 linhas), `app/application/dtos/__init__.py` (274 linhas), `app/main.py` (474 linhas)
- **Risco de não corrigir**: baixo hoje (funciona), mas a tendência de crescimento (2-3× em poucas versões) sugere que isso vira dor real dentro de 1-2 gerações de módulo novo.
- **Solução recomendada**: dividir por módulo (ex.: `schemas/bid.py`, `schemas/inteligencia.py`, etc.), como já é feito para `dlg_schemas.py` (única exceção já dividida corretamente).
- **Esforço estimado**: Alto (mecânico, mas toca imports em toda a base).

---

### A-14 — Router `bid.py` e use case `dlg.py` concentram um módulo inteiro em um único arquivo

- **Prioridade**: P3 — Baixo
- **Descrição**: `bid.py` (router, 753 linhas, 27 endpoints) e `dlg.py` (use case, 756 linhas) são os dois arquivos isolados mais longos do sistema — cada um sozinho maior que a soma de vários routers/use cases inteiros de outros módulos.
- **Impacto**: navegação e revisão de código mais difícil dentro de um único módulo já grande; ainda assim, mais fácil de justificar do que os arquivos monolíticos multi-módulo do achado A-13, já que pelo menos representam um módulo coeso.
- **Arquivos**: `app/presentation/api/v1/bid.py`, `app/application/use_cases/dlg.py`
- **Risco de não corrigir**: baixo — é o tipo de arquivo grande que ainda é internamente coeso (um assunto só), diferente do A-13.
- **Solução recomendada**: se crescer mais, dividir `bid.py` por sub-recurso (escopo, propostas, simulação, relatórios) em sub-routers agregados.
- **Esforço estimado**: Médio, e não urgente.

---

### A-15 — Nenhum handler de exceção global/centralizado no FastAPI

- **Prioridade**: P3 — Baixo
- **Descrição**: `main.py` só registra middlewares de CORS e rate-limit, e um único exception handler (`RateLimitExceeded`). Não há um handler genérico para exceções não previstas que padronize o formato de erro e garanta log estruturado.
- **Impacto**: um erro não tratado em qualquer endpoint retorna o 500 padrão do FastAPI/Starlette, sem garantia de log estruturado nem de formato de resposta consistente para o frontend tratar.
- **Arquivos**: `app/main.py` (ausência de `@app.exception_handler(Exception)`)
- **Risco de não corrigir**: baixo — os `except Exception` pontuais já observados (achado A-16) cobrem os pontos mais sensíveis; isso é uma rede de segurança adicional, não uma lacuna crítica.
- **Solução recomendada**: adicionar um handler global que loga a exceção com contexto (request-id, empresa, usuário) e retorna um corpo de erro padronizado.
- **Esforço estimado**: Baixo.

---

### A-16 — Uso de `except Exception` genérico em 12 pontos (avaliado — risco real é baixo)

- **Prioridade**: P3 — Baixo
- **Descrição**: 12 ocorrências de `except Exception` no backend, todas marcadas com `# noqa: BLE001` (supressão deliberada do linter). Leitura de 2 exemplos (`assistente.py:87`, `insights.py:215`) confirma que são decisões conscientes de degradação graciosa (ex.: "RAG é complementar; falha não bloqueia o chat"; avaliador de regra retorna `False` em vez de propagar erro).
- **Impacto**: risco real baixo — não é código que engole erro por descuido, é uma política de "módulo secundário não deve derrubar o fluxo principal" aplicada de forma consistente. O ponto fraco é que essa política não está documentada como convenção, então um novo desenvolvedor pode não replicá-la corretamente ou pode assumir (erradamente) que é descuido e "corrigir" removendo o fallback.
- **Arquivos**: 11 arquivos, incluindo `assistente.py:87`, `assistente_tools.py:78`, `cancelamento.py:37,129`, `diagnostico.py:148`, `diagnostico_ia.py:121`, `importacao.py:59,178`, `insights.py:100,215`, `rag_service.py:235`, `inteligencia.py:343`
- **Risco de não corrigir**: baixo — é mais um item de documentação de convenção do que de correção de código.
- **Solução recomendada**: documentar em [`09_manutencao.md`](09_manutencao.md) a convenção "IA/RAG são complementares — falhas nesses caminhos degradam graciosamente, não propagam".
- **Esforço estimado**: Trivial (só documentação).

---

### A-17 — `bulk_create` usa loop de `db.add()` individual

- **Prioridade**: P3 — Baixo
- **Descrição**: `bulk_create` de CT-e (`repositories/__init__.py:425-433`) e de propostas de BID (linha 1372) fazem um `db.add()` por objeto dentro de um loop, com um único `commit()` ao final — não usam `bulk_insert_mappings`/`session.add_all()`.
- **Impacto**: real, mas limitado — o lote já é limitado a 500 registros por arquivo (limite de segurança da v3.0.0), então o custo de overhead do ORM por linha é tolerável na escala atual.
- **Arquivos**: `app/infrastructure/database/repositories/__init__.py:425-433,1372`
- **Risco de não corrigir**: baixo hoje; sobe só se o limite de lote for aumentado no futuro.
- **Solução recomendada**: migrar para `bulk_insert_mappings` quando/se o limite de lote for revisado para cima.
- **Esforço estimado**: Baixo.

---

### A-18 — Bloco de filtro de período duplicado em pelo menos 5 páginas de benchmark

- **Prioridade**: P3 — Baixo
- **Descrição**: confirmado — `BenchmarkNacional.jsx`, `BenchmarkRegional.jsx`, `BenchmarkTransportadoras.jsx`, `PotencialEconomia.jsx`, `DashboardExecutivo.jsx` reimplementam individualmente o mesmo par de `<TextField type="date">` + estado local, sem um componente `FiltroPeriodo` compartilhado.
- **Impacto**: mudança de UX no filtro de período (ex.: adicionar atalho "últimos 30 dias") precisa ser replicada em 5 lugares.
- **Arquivos**: as 5 páginas citadas, em `frontend/src/pages/`
- **Risco de não corrigir**: baixo — cosmético/produtividade de desenvolvimento, não funcional.
- **Solução recomendada**: extrair `<FiltroPeriodo />` como componente compartilhado em `src/components/`.
- **Esforço estimado**: Baixo.

---

### A-19 — Páginas mais longas do frontend concentram múltiplas responsabilidades

- **Prioridade**: P3 — Baixo
- **Descrição**: `Empresas.jsx` (624 linhas) e `Dashboard.jsx` (564 linhas) são as duas páginas mais longas — `Empresas.jsx` mistura CRUD de empresa, CRUD de filial e importação em lote de filiais via CNPJ (integração com BrasilAPI) num único arquivo.
- **Impacto**: mais difícil de revisar/testar isoladamente cada responsabilidade.
- **Arquivos**: `frontend/src/pages/Empresas.jsx`, `frontend/src/pages/Dashboard.jsx`
- **Risco de não corrigir**: baixo.
- **Solução recomendada**: extrair subcomponentes (ex.: `ImportacaoFiliaisCnpj`, dentro de `Empresas.jsx`).
- **Esforço estimado**: Baixo-Médio.

---

### A-20 — Ausência de `HEALTHCHECK` no Dockerfile do backend e de limites de recurso em produção

- **Prioridade**: P3 — Baixo
- **Descrição**: `backend/Dockerfile` não declara `HEALTHCHECK` (o `frontend/Dockerfile` declara). `docker-compose.prod.yml` não define `deploy.resources.limits` (CPU/memória) para nenhum serviço.
- **Impacto**: orquestradores que dependem de healthcheck do container (não só do `depends_on: condition: service_healthy` do Postgres) não têm como saber se o backend está saudável além de "o processo não morreu". Sem limite de recurso, um vazamento de memória ou pico de CPU em um serviço pode afetar os demais no mesmo host.
- **Arquivos**: `backend/Dockerfile`, `docker-compose.prod.yml`
- **Risco de não corrigir**: baixo no porte atual (host único, poucos clientes); sobe se a operação crescer para múltiplos hosts/orquestração mais sofisticada (Kubernetes, Swarm).
- **Solução recomendada**: adicionar `HEALTHCHECK` batendo em `/` ou um endpoint `/health` dedicado; declarar limites de recurso conservadores.
- **Esforço estimado**: Baixo.

---

## Respostas às perguntas diretas do escopo

**A arquitetura atual é adequada para a evolução da plataforma nos próximos 3 a 5 anos?**
Parcialmente. A fundação (Clean Architecture, separação de camadas, isolamento multi-tenant) é adequada e já provou suportar 5 gerações de módulo. Mas os achados A-01 (duas disciplinas de use case coexistindo), A-06/A-07 (gaps de performance em memória/índice no fluxo mais usado do sistema) e A-09/A-10 (frontend sem code-splitting nem cache real) são decisões que precisam ser tomadas **agora**, porque cada módulo novo adicionado sem resolver isso aumenta o custo de resolver depois. Não é necessário trocar de arquitetura — é necessário decidir conscientemente o padrão de "use case com SQL" (formalizá-lo em vez de deixá-lo acontecer per-módulo) e fechar os 3 gaps de escala.

**A estrutura de banco de dados suporta crescimento para milhões de documentos, múltiplas empresas, múltiplos usuários e novos módulos?**
Para múltiplas empresas e múltiplos usuários: sim, o isolamento por `empresa_id` e os índices em `empresa_id` estão presentes em praticamente todas as tabelas relevantes. Para milhões de CT-e por empresa: **condicionalmente** — os índices certos existem em produção (via Alembic), mas dois dos cinco componentes do diagnóstico mais usado (`composicao_frete`, prazo/OTIF) ainda carregam a lista completa de CT-e do período em memória Python (achado A-06), o que não escala linearmente com o volume. Para novos módulos: a modelagem por domínio (cada módulo com suas próprias tabelas, isolamento por `empresa_id` desde o desenho) se mostrou repetível 5 vezes — não há sinal de que isso pare de funcionar.

**Um novo desenvolvedor conseguiria evoluir a plataforma com segurança?**
Sim, para os módulos de cadastro/CRUD e para seguir os padrões de autorização (agora bem documentados em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) e [`09_manutencao.md`](09_manutencao.md)). Com ressalva para os módulos analíticos/SQL-pesados (DLG, MBL, MCL, IA): um desenvolvedor que aprender Clean Architecture pelo passo-a-passo documentado em [`09_manutencao.md`](09_manutencao.md) vai encontrar um padrão diferente do que os módulos mais recentes de fato seguem (achado A-01) — vale atualizar esse guia para descrever os dois padrões explicitamente, para não confundir quem chega agora.

---

## 7. Dívida Técnica Arquitetural

| Dívida | Origem | Impacto | Recomendação |
|---|---|---|---|
| Use cases com SQL direto (A-01) | Pragmatismo ao adicionar módulos analíticos (V4+) | Duas disciplinas arquiteturais coexistindo | Formalizar como "query objects"/read models explícitos, não reverter |
| Acesso a método privado entre use cases (A-02) | Adiado desde a auditoria v2.0.0 | Acoplamento oculto, risco de quebra silenciosa | Extrair serviço compartilhado — esforço baixo, sem desculpa para adiar mais |
| Composição de frete/OTIF em memória (A-06) | Dificuldade técnica de agregação JSON em SQL portátil (SQLite+PostgreSQL) | Não escala com volume de CT-e por empresa | Aceitar SQL específico de PostgreSQL para esse caso, já que produção não usa SQLite |
| Ausência de code-splitting no frontend (A-09) | App cresceu de poucas para ~44 páginas sem revisar a estratégia de carregamento | Tempo de carregamento inicial cresce a cada módulo novo | Introduzir `React.lazy` por módulo antes do próximo módulo grande (V5/V6) |
| Adoção marginal de React Query (A-10) | Migração iniciada e nunca concluída | Requisições redundantes, sem cache compartilhado | Priorizar páginas de maior tráfego primeiro |
| Zero observabilidade (A-11) | Nunca priorizado | Incidentes em produção dependem de report manual | Integrar Sentry como primeiro passo, é barato |
| Migrations Alembic ausentes para tabelas de IA e segurança v6.5.x (já registrado na Fase 0) | Uso de `create_all()` em dev sem retroalimentar Alembic | Schema real não é 100% reproduzível só com `alembic upgrade head` | Gerar as migrations faltantes antes do próximo deploy que dependa só delas |

## 8. Recomendações Estratégicas

Decisões que, na avaliação desta auditoria, devem ser tomadas **agora** (não como próximo item de backlog, mas como decisão consciente antes de continuar adicionando módulos):

1. **Formalizar o padrão de "use case com SQL direto"** como uma segunda camada de acesso a dados válida (ex.: "read models" em `infrastructure/queries/`), em vez de deixá-lo como um desvio silencioso do padrão de repositório. Isso não é reverter nada — é documentar o que já está acontecendo, para que pare de ser uma inconsistência não-intencional.
2. **Resolver o gap de performance do dashboard (A-06) e o gap de índice em dev (A-07) antes de qualquer cliente com volume alto de CT-e.** São os dois achados com risco mais direto de virar um incidente visível ao usuário (timeout de request), não só dívida de manutenção.
3. **Decidir a estratégia de carregamento do frontend (A-09) antes do próximo módulo grande** (V5 Benchmark Coletivo ou V6 Inteligência de Mercado) — cada módulo novo adicionado sem isso piora o tempo de carregamento para todo mundo, inclusive quem nunca vai abrir aquele módulo.
4. **Fechar o gap de observabilidade (A-11) antes de operar mais de um cliente em produção simultaneamente** — hoje, um incidente de produção só é descoberto se alguém notar.
5. **Não é necessário trocar de arquitetura.** A Clean Architecture aplicada nos módulos originais é um ativo real — a recomendação é consolidar a disciplina que já existe, não reconstruir.

## 9. Roadmap Arquitetural

### Curto prazo (semanas)

- A-07: declarar os índices compostos de `ctes` em `__table_args__` do modelo (fecha a divergência dev/produção).
- A-12: versionar o script de backup.
- A-11: integrar Sentry (captura de exceção mínima).
- A-02, A-03, A-04: resolver os três achados de acoplamento pontuais no backend (esforço baixo cada).
- A-08: adicionar Redis/Celery worker/beat ao `docker-compose.prod.yml`.
- A-20: `HEALTHCHECK` no Dockerfile do backend.

### Médio prazo (1–2 trimestres)

- A-06: mover composição de frete e OTIF para agregação SQL nativa do PostgreSQL.
- A-09: introduzir code-splitting por módulo no frontend.
- A-10: completar a migração para React Query, priorizando as telas de maior tráfego.
- A-05: adicionar `response_model` tipado a todo o módulo de Inteligência IA.
- A-13: começar a dividir `schemas/__init__.py` e `repositories/__init__.py` por módulo, a partir do próximo módulo novo (não retroativamente em um único esforço).

### Longo prazo (2+ trimestres / pré-requisito para V5/V6)

- A-01: consolidar a camada de "read models"/query objects como um padrão de primeira classe da arquitetura, documentado e aplicado retroativamente aos 16 use cases atuais.
- Observabilidade completa (métricas + rastreamento distribuído), não só captura de exceção.
- Reavaliar a necessidade de separar o módulo de IA em um serviço próprio (mencionado como visão de longo prazo na auditoria original v2.0.0) — só se justifica se o volume de processamento de IA justificar escala independente do resto do backend.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma alteração de código foi feita durante esta auditoria.*
