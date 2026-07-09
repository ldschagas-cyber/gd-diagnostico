# 17 · Fase 4 — Auditoria de Banco de Dados

> **Escopo**: exclusivamente diagnóstico — nenhuma tabela, migration, índice, modelo ORM ou configuração de banco foi alterada nesta fase. Toda evidência foi coletada por leitura direta de `app/infrastructure/database/models/__init__.py`, `alembic/versions/*.py` e dos repositórios, em 2026-07-07. Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md), [`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md), [`15_fase2_qualidade_codigo.md`](15_fase2_qualidade_codigo.md), [`16_fase3_performance.md`](16_fase3_performance.md) — vários achados de banco já apontados nessas fases são retomados aqui com o código do banco (`BD-xx`) para consolidação, sem duplicar a análise.

---

## 1. Inventário do Banco de Dados

| Item | Valor |
|---|---|
| SGBD (produção) | PostgreSQL 16 (`postgres:16-alpine`) |
| SGBD (dev sem Docker) | SQLite |
| Extensões pretendidas | `pgvector` (para embeddings do RAG) |
| Extensões efetivamente criadas via migration | **Nenhuma** — ver BD-02 |
| Tabelas | 44 |
| Modelos SQLAlchemy | 53 (alguns módulos com mais de uma classe por tabela) |
| Migrations Alembic | 10, de `faa05e1d23e5` (2026-06-19) a `c9f4a2e7b1d8` (2026-07-04) |
| Foreign Keys declaradas | 51 |
| Relationships ORM com cascade Python (`cascade="all, delete-orphan"`) | 9 |
| Foreign Keys com `ON DELETE` a nível de banco | **0** — ver BD-03 |

Visão geral do modelo de dados, domínios e relacionamento entre entidades já documentados em [`04_modelo_de_dados.md`](04_modelo_de_dados.md) — não duplicado aqui.

## 2. Análise da Modelagem de Dados

- **Chaves primárias**: `id INTEGER` autoincremento em todas as 44 tabelas — consistente.
- **Chaves estrangeiras**: 51 declaradas via `ForeignKey(...)`, todas apontando corretamente para a PK da tabela-mãe (nenhuma FK solta/órfã encontrada).
- **Tipos de dado**: consistentes para texto (`String` com tamanho definido) e datas (`Date`/`DateTime`). **Inconsistente para dinheiro** — ver BD-01.
- **Campos obrigatórios/opcionais**: `empresa_id` é `nullable=True` em `users`, `transportadoras`, `regras_insight` e `usage_logs` — nos três primeiros casos é intencional (superusuário global, transportadora legada pré-v3.0.0, regra global), documentado em [`02_especificacao_funcional.md`](02_especificacao_funcional.md). Em `usage_logs`, não há documentação explícita do motivo — provavelmente para registrar uso de IA em contexto sem empresa (ex.: teste interno), mas vale confirmar a intenção.
- **Redundância**: não foi encontrada duplicação óbvia de dado entre tabelas (nenhum campo que deveria ser só FK armazenado também como texto redundante).

## 3. Auditoria das Entidades Principais

Já cobertas por domínio, com volume esperado e estratégia de isolamento, em [`04_modelo_de_dados.md`](04_modelo_de_dados.md) e [`02_especificacao_funcional.md`](02_especificacao_funcional.md) (tabela "global vs. isolado por empresa"). Destaques desta fase:

- **`ctes`**: a tabela de maior volume esperado (documentos fiscais importados, potencialmente milhões de linhas ao longo dos anos). Índices em produção corretos (`empresa_id`, `chave` único, `status`, composto `empresa_id+data_emissao` e `empresa_id+transportadora_id` via migration `a2f8c1e4b9d3`). Sem estratégia de particionamento ou arquivamento — ver BD-08.
- **`documentos_vetoriais`** (embeddings do RAG): cresce continuamente por empresa, sem filtro de período natural na busca — ver BD-06 (retomado da Fase 3, achado PF-03).
- **`bid_propostas`**: única tabela com padrão de soft-delete explícito (coluna `deleted`) — ver BD-10.
- **`insights`, `chat_mensagens`, `usage_logs`**: todas com índice em `empresa_id` e `created_at`, adequado para consulta por período recente; sem estratégia de retenção de longo prazo (mesma observação de BD-08, em menor escala).

## 4. Auditoria das Migrations

- **Organização**: 10 migrations em cadeia linear (`down_revision` consistente), sem branch nem merge conflitante — histórico limpo.
- **Consistência migration vs. modelo atual**: majoritariamente consistente, com duas exceções relevantes:
  1. As tabelas de Inteligência IA (15 entidades: `insights`, `diagnosticos_ia`, `scores_logisticos`, `oportunidades`, `chat_sessoes` etc.) **não têm nenhuma migration correspondente** — foram introduzidas via `create_all()`/alterações incrementais em `main.py`, nunca formalizadas em `alembic/versions/`.
  2. As mudanças de segurança v6.5.0/v6.5.1 (nenhuma alteração de schema, mas vale registrar que não há migration "marco" nem para elas).
- **Alterações manuais fora do fluxo Alembic**: `app/main.py` (`_aplicar_alteracoes_incrementais`) mantém uma lista de `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` e `CREATE TABLE IF NOT EXISTS` aplicada em desenvolvimento — isso cobre a maior parte, mas não os dois índices compostos de `ctes` (ver BD-05, já registrado na Fase 1/3 como A-07/PF-02).
- **Extensão `pgvector`**: nunca criada via `CREATE EXTENSION` em nenhuma migration — ver BD-02.

## 5. Auditoria de Índices

Cobertura confirmada nas tabelas de maior tráfego:

| Tabela | Índices confirmados | Observação |
|---|---|---|
| `ctes` | `empresa_id`, `chave` (único), `status`, `empresa_id+data_emissao`, `empresa_id+transportadora_id` | Composto só existe via migration — ver BD-05 |
| `insights` | `empresa_id`, `created_at` | Adequado para "insights recentes por empresa" |
| `chat_mensagens` | `sessao_id`, `empresa_id` | Adequado |
| `usage_logs` | `empresa_id`, `feature`, `created_at` | Adequado |
| `bid_auditorias` | `bid_id` | Adequado |
| `documentos_vetoriais` | `empresa_id`, `tipo_documento` | Sem índice/estrutura de busca vetorial — ver BD-06 |

Não foram encontrados índices redundantes (dois índices cobrindo exatamente a mesma coluna) nem índices claramente desnecessários.

## 6. Auditoria de Consultas

Os pontos de consulta pesada já foram identificados e quantificados na Fase 3 — não duplicados aqui em detalhe, só referenciados com o código de banco correspondente:

- Composição de frete e OTIF carregando todos os CT-e do período em memória Python (Fase 3, PF-01) — do ponto de vista de banco, a consulta em si (`SELECT * FROM ctes WHERE empresa_id=? AND data_emissao BETWEEN ? AND ? AND status='ATIVO'`) é bem indexada; o problema é o que a aplicação faz com o resultado depois (materializar tudo), não a consulta.
- Busca RAG (Fase 3, PF-03): a consulta em si (`SELECT * FROM documentos_vetoriais WHERE empresa_id=? OR empresa_id=0`) também é bem indexada; o problema é о cálculo de similaridade pós-consulta ser feito em Python sobre 100% dos resultados.
- Não foram encontradas consultas com `JOIN` complexo (mais de 2-3 tabelas) nem ordenação pesada sem índice de suporte.

## 7. Escalabilidade do Banco

| Cenário | Avaliação |
|---|---|
| **Atual** (poucas empresas, volume atual de CT-e) | Sem risco — schema e índices atuais suportam confortavelmente. |
| **Crescimento médio** (dezenas de empresas, milhões de registros) | Os índices em `ctes` já suportam esse volume bem, **desde que** BD-05 (gap de índice em dev) não se repita em produção e BD-01 (Float) não gere problema de precisão acumulado em relatórios financeiros consolidados. |
| **Escala SaaS** (centenas/milhares de empresas, grande volume histórico) | É aqui que a ausência de estratégia de particionamento/retenção (BD-08) e a ausência de RLS como defesa em profundidade (BD-09) passam de "não urgente" para "decisão que precisa existir antes, não depois". |

## 8. Multi-tenancy e Isolamento de Dados

O isolamento por `empresa_id` a nível de **aplicação** está hoje consistente nos 19 routers (correção da Fase 0 fechou as lacunas que existiam em BID/MCL/Transportadoras/Inteligência IA). A nível de **banco de dados**, porém, não há nenhum mecanismo que **imponha** esse isolamento independentemente da aplicação:

- Não há Row-Level Security (RLS) do PostgreSQL configurada — nenhuma `CREATE POLICY` encontrada em nenhuma migration.
- O isolamento depende 100% de todo `SELECT`/`UPDATE`/`DELETE` do código incluir corretamente a cláusula `WHERE empresa_id = ?` — o que hoje é verdade (confirmado nas Fases 0-2), mas é uma garantia de disciplina de código, não uma garantia estrutural do banco.
- Isso é aceitável para o porte atual (uma aplicação, um time, código auditado); passa a ser um risco real de defesa em profundidade se a plataforma crescer para múltiplos times desenvolvendo, ou se surgir qualquer acesso direto ao banco fora da aplicação (ex.: uma ferramenta de BI conectando direto no Postgres).

## 4. Pontos Fortes

- Nenhuma FK solta, nenhuma tabela órfã, nenhuma duplicação de dado encontrada.
- Índices presentes exatamente nos pontos que a aplicação mais consulta (`empresa_id` em praticamente toda tabela multi-tenant, mais os compostos de `ctes`).
- Cadeia de migrations limpa e linear — sem conflito de merge, sem branch divergente.
- Todo `delete()` de repositório verificado carrega o objeto antes de deletar (`db.get()` + `db.delete()`), respeitando o cascade Python declarado — nenhum bypass de cascade (`.filter(...).delete()` direto) encontrado em nenhum repositório.
- Nomenclatura de tabela e coluna 100% consistente em português, sem mistura de idioma.
- Constraints `UNIQUE` corretas e bem escolhidas em todas as tabelas de referência/configuração (ex.: `benchmarks_corredor` único por par de hubs, `clusters_cliente` único por empresa+UF+município).

## 5. Achados Técnicos

---

### BD-01 — Valores financeiros armazenados como `Float`, nunca `Numeric`/`Decimal`

- **Descrição**: todo campo monetário do schema (`valor_frete`, `valor_mercadoria`, `valor_rs_kg`, `frete_rs_kg`, `economia_estimada`, `custo_usd`, `custo_brl`, entre outros — 12+ ocorrências confirmadas) usa o tipo `Float` (`Mapped[float]` / SQLAlchemy `Float`, que mapeia para `DOUBLE PRECISION` no PostgreSQL).
- **Tabela/arquivo relacionado**: `app/infrastructure/database/models/__init__.py` (CTeModel, BidEscopoModel, BidPropostaModel, RecomendacaoModel, OportunidadeModel, UsageLogModel, entre outros).
- **Evidência**: `grep -n "Float"` retorna 12+ colunas monetárias mapeadas como ponto flutuante binário.
- **Impacto**: `Float`/`DOUBLE PRECISION` não representa valores decimais de forma exata (é binário) — somas e agregações repetidas de muitos valores monetários (ex.: soma de milhares de `valor_frete` num relatório anual) podem acumular erro de arredondamento perceptível, especialmente em comparações de igualdade ou em auditorias financeiras de precisão (o próprio objetivo do produto).
- **Prioridade**: P1 — Alto
- **Risco futuro**: cresce com o volume agregado — quanto mais CT-e um relatório soma, maior a chance de o erro acumulado se tornar visível (na casa de centavos, mas em um produto de auditoria de custo isso importa).
- **Recomendação**: migrar para `Numeric(precision, scale)` (ex.: `Numeric(14, 2)` para reais, `Numeric(10, 4)` para R$/kg) em todos os campos monetários — mudança de schema com migration de dados, não trivial, mas de alto valor para um produto financeiro.
- **Esforço estimado**: Alto (migration de todas as tabelas monetárias + validação de que nenhum cálculo em Python quebra com `Decimal` em vez de `float`).

---

### BD-02 — Extensão `pgvector` nunca criada via migration

- **Descrição**: nenhuma migration executa `CREATE EXTENSION IF NOT EXISTS vector` (ou equivalente). A documentação (Fase 0) registrava "a extensão já está instalada no seu container PostgreSQL" como um fato — mas isso não é reproduzível a partir do histórico de migrations; depende de alguém ter habilitado manualmente, fora de controle de versão.
- **Tabela/arquivo relacionado**: `alembic/versions/*.py` (ausência), `documentos_vetoriais` (tabela que teoricamente se beneficiaria da extensão)
- **Impacto**: hoje, nulo na prática — o RAG armazena embeddings como JSON, não como coluna `vector`, então a extensão não é sequer usada pelo código atual (consistente com o achado PF-03 da Fase 3). O problema é de **reprodutibilidade**: um banco de produção novo, criado do zero só a partir das migrations, não teria a extensão disponível caso alguém decida efetivamente usá-la no futuro.
- **Prioridade**: P2 — Médio
- **Risco futuro**: baixo até o dia em que alguém decidir de fato implementar a otimização vetorial nativa recomendada na Fase 3 (PF-03) — nesse momento, a ausência de uma migration formal para a extensão vira um bloqueio de deploy descoberto tarde.
- **Recomendação**: adicionar uma migration que declare `CREATE EXTENSION IF NOT EXISTS vector`, mesmo que a coluna `vector` só seja usada depois — documenta a intenção e garante reprodutibilidade.
- **Esforço estimado**: Baixo (uma migration).

---

### BD-03 — Nenhuma Foreign Key tem `ON DELETE` a nível de banco — cascade depende inteiramente da disciplina da aplicação

- **Descrição**: das 51 Foreign Keys declaradas, nenhuma tem `ondelete="CASCADE"`/`"SET NULL"`/`"RESTRICT"` especificado. O comportamento de cascade que existe (`cascade="all, delete-orphan"` em 9 relationships) é **inteiramente do lado do SQLAlchemy/Python** — só funciona se o objeto for carregado e deletado através da sessão ORM.
- **Tabela/arquivo relacionado**: `app/infrastructure/database/models/__init__.py` (todas as 51 `ForeignKey(...)`)
- **Evidência**: verificação confirmou que todos os `delete()` de repositório hoje seguem o padrão correto (`db.get()` + `db.delete()`), então não há bug em produção **hoje**. Mas a garantia de integridade não está no schema, está no hábito de quem escreve código novo.
- **Impacto**: qualquer operação de exclusão que não passe pela sessão ORM (um script de manutenção com SQL direto, uma ferramenta administrativa futura, uma migration de dados) pode falhar com violação de FK (se a constraint padrão do PostgreSQL bloquear) ou deixar registro órfão, dependendo de como for escrita.
- **Prioridade**: P2 — Médio
- **Risco futuro**: cresce se a equipe crescer (mais pessoas escrevendo código de acesso a dados sem conhecer essa convenção implícita) ou se surgir necessidade de scripts de manutenção em massa fora da aplicação.
- **Recomendação**: declarar `ondelete=` explicitamente nas FKs onde o cascade Python já existe (torna a garantia estrutural, não só de convenção), e decidir conscientemente `RESTRICT`/`SET NULL` para as que não devem cascatear.
- **Esforço estimado**: Médio (migration alterando constraints existentes, com cuidado para não quebrar dados já gravados).

---

### BD-04 — Migrations ausentes para as 15 tabelas de Inteligência IA (retomado de achados anteriores)

- **Descrição**: já registrado como débito técnico desde a Fase 0 ([`10_roadmap.md`](10_roadmap.md)) e como achado A-14/DT-14 na Fase 1 — consolidado aqui com o código de banco. Nenhuma das 15 tabelas do módulo de IA tem migration Alembic própria.
- **Tabela/arquivo relacionado**: `insights`, `regras_insight`, `insight_execucoes`, `diagnosticos_ia`, `diagnostico_historicos`, `scores_logisticos`, `score_historicos`, `benchmarks_setoriais`, `oportunidades`, `planos_acao`, `chat_sessoes`, `chat_mensagens`, `usage_logs`, `documentos_vetoriais`, `embedding_jobs`.
- **Impacto**: um ambiente de produção criado do zero **só** com `alembic upgrade head` não teria essas 15 tabelas — dependeria também de rodar a aplicação uma vez em modo não-produção para o `create_all()` incremental agir, o que contradiz a premissa de "produção gerenciada exclusivamente por Alembic" documentada em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md).
- **Prioridade**: P1 — Alto
- **Risco futuro**: um novo ambiente de produção (ex.: para um cliente que exige instância dedicada) criado seguindo à risca a documentação de deploy ficaria sem o módulo de IA funcional, sem erro óbvio até alguém tentar usar a funcionalidade.
- **Recomendação**: gerar uma migration `alembic revision --autogenerate` capturando o estado atual dessas 15 tabelas, validada contra um banco de desenvolvimento já populado por `create_all()`.
- **Esforço estimado**: Médio (gerar + validar cuidadosamente para não haver divergência entre o autogenerate e o schema real já em produção).

---

### BD-05 — Índice composto crítico de `ctes` ausente no caminho `create_all()` (retomado — já é A-07/PF-02)

- **Descrição**: consolidado aqui pela terceira vez (Fase 1 e Fase 3 já o registraram) porque é fundamentalmente um achado de banco de dados. Sem alteração na análise: os índices `ix_ctes_empresa_data_emissao` e `ix_ctes_empresa_transportadora` existem só via migration, não no modelo ORM.
- **Prioridade**: P1 — Alto (mantida)
- **Recomendação**: mesma das fases anteriores — declarar em `__table_args__`.

---

### BD-06 — Busca RAG sem estrutura de índice vetorial (retomado — já é PF-03)

- **Descrição**: consolidado aqui pela lente de banco de dados: a tabela `documentos_vetoriais` armazena o embedding como `JSON`, não como tipo `vector` do pgvector — mesmo com a coluna sendo, na prática, um vetor denso de 1536 dimensões (`EMBEDDING_DIM=1536`). Armazenar isso como JSON impede qualquer índice de proximidade (`ivfflat`/`hnsw`) e força a aplicação a desserializar e calcular a distância de cada linha em Python.
- **Prioridade**: P2 — Médio (mantida da Fase 3)
- **Recomendação**: migrar a coluna para `vector(1536)` nativo do pgvector (depende de BD-02 ser resolvido primeiro).

---

### BD-07 — Sem script de backup versionado (retomado — já é A-12 da Fase 1)

- **Descrição**: sem alteração — nenhum script de backup existe no repositório; o procedimento é só documentação.
- **Prioridade**: P2 — Médio (mantida)

---

### BD-08 — Sem estratégia de particionamento ou retenção/arquivamento para tabelas de crescimento indefinido

- **Descrição**: `ctes` (potencialmente milhões de linhas por empresa ao longo dos anos), `documentos_vetoriais`, `insights`, `chat_mensagens` e `usage_logs` crescem indefinidamente, sem qualquer mecanismo de particionamento (`PARTITION BY`, nativo do PostgreSQL 16) nem política de retenção/arquivamento (ex.: mover CT-e com mais de N anos para uma tabela "fria" ou storage externo).
- **Tabela/arquivo relacionado**: `ctes`, `documentos_vetoriais`, `insights`, `chat_mensagens`, `usage_logs`
- **Impacto**: nenhum hoje — os volumes atuais estão longe de justificar particionamento.
- **Prioridade**: P3 — Baixo hoje / tendência para P1 em escala SaaS de vários anos de operação
- **Risco futuro**: é uma decisão de design que fica progressivamente mais cara de introduzir depois que a tabela já é grande (particionar uma tabela de milhões de linhas em produção é uma operação delicada; decidir o esquema de particionamento desde pequeno é trivial).
- **Recomendação**: não implementar agora, mas decidir a estratégia (particionamento de `ctes` por `empresa_id` ou por ano de `data_emissao`) como parte do planejamento de longo prazo, antes que a tabela chegue a um tamanho que torne a migração de particionamento arriscada.
- **Esforço estimado**: Baixo agora (é só decisão/documentação); Alto se adiado até virar necessidade urgente.

---

### BD-09 — Isolamento multi-tenant garantido só pela aplicação, sem Row-Level Security como defesa em profundidade

- **Descrição**: nenhuma `CREATE POLICY`/RLS do PostgreSQL configurada — o isolamento por `empresa_id` (hoje correto, pós-correções da Fase 0) depende inteiramente de todo código de acesso a dados incluir o filtro certo.
- **Tabela/arquivo relacionado**: todas as tabelas com `empresa_id`
- **Impacto**: nenhum hoje, dado que o código foi auditado e corrigido (Fase 0). É uma ausência de camada extra de proteção, não um bug ativo.
- **Prioridade**: P2 — Médio
- **Risco futuro**: cresce com o tamanho do time (mais gente escrevendo consulta sem saber da convenção) e com qualquer acesso direto ao banco fora da aplicação (BI, relatórios ad-hoc, suporte técnico consultando o banco diretamente).
- **Recomendação**: considerar RLS como camada adicional (não substituta) de proteção antes de abrir acesso de leitura direto ao banco para qualquer ferramenta externa (BI, analytics).
- **Esforço estimado**: Médio-Alto (RLS exige revisão cuidadosa de todas as roles/conexões de banco).

---

### BD-10 — Três padrões diferentes de "estado ativo/removido" coexistindo, sem convenção única

- **Descrição**: o sistema usa três abordagens diferentes para "algo não está mais ativo": `empresas.status` (`ATIVO`/`INATIVO`, enum de texto), `ctes.status` (`ATIVO`/`CANCELADO`, enum de texto com significado de negócio específico, não genérico), e `bid_propostas.deleted` (booleano de soft-delete puro). Não há um padrão único de "registro removido logicamente" aplicado de forma consistente onde caberia.
- **Tabela/arquivo relacionado**: `empresas`, `ctes`, `bid_propostas`
- **Impacto**: baixo — cada um faz sentido no contexto do próprio domínio (o "cancelamento" de um CT-e é um evento de negócio real com data/protocolo, bem diferente de uma simples exclusão lógica), então não é necessariamente um erro, mas dificulta que um novo desenvolvedor saiba, sem olhar, qual convenção usar ao adicionar soft-delete a uma tabela nova.
- **Prioridade**: P3 — Baixo
- **Recomendação**: documentar em [`09_manutencao.md`](09_manutencao.md) quando usar cada padrão (enum de status de negócio vs. boolean de soft-delete genérico), não necessariamente unificar os já existentes.
- **Esforço estimado**: Trivial (documentação).

---

### BD-11 — Pool de conexão modesto para o número de tenants que o produto pretende suportar (retomado — já é PF-08)

- **Descrição**: sem alteração — `pool_size=5, max_overflow=10` por worker, 2 workers em produção, 30 conexões simultâneas no total.
- **Prioridade**: P1 — Alto (mantida da Fase 3, aqui pela lente específica de capacidade de banco)

---

## 6. Riscos para Escala SaaS

| Cenário | Principais riscos de banco |
|---|---|
| **10 empresas** | Nenhum dos achados desta fase se manifesta. |
| **100 empresas** | BD-11 (pool de conexão) é o primeiro a merecer atenção; BD-01 (Float) começa a importar se relatórios financeiros consolidados forem auditados com rigor de centavo. |
| **1.000 empresas** | BD-08 (sem particionamento/retenção) e BD-09 (sem RLS) deixam de ser "boas práticas futuras" e passam a ser decisões de arquitetura que, se adiadas até esse ponto, ficam caras de implementar retroativamente. |

## 7. Roadmap de Evolução do Banco

### Curto prazo

- BD-02: migration criando a extensão `pgvector` (mesmo sem uso imediato).
- BD-04: gerar as migrations faltantes para as 15 tabelas de IA.
- BD-05: declarar os índices compostos de `ctes` no modelo ORM.
- BD-07: versionar script de backup.
- BD-10: documentar convenção de status/soft-delete.

### Médio prazo

- BD-03: declarar `ondelete=` explícito nas FKs com cascade Python já existente.
- BD-06: migrar embeddings para coluna `vector` nativa (após BD-02).
- BD-11: revisar `pool_size`/`--workers` como parte do planejamento comercial de novos clientes.

### Longo prazo — preparação para escala

- BD-01: migração de `Float` para `Numeric`/`Decimal` nos campos monetários (mudança de maior esforço e maior valor para um produto financeiro).
- BD-08: decidir e documentar estratégia de particionamento/retenção de `ctes` antes que o volume torne a migração arriscada.
- BD-09: avaliar RLS como camada adicional antes de qualquer acesso direto ao banco por ferramenta externa (BI/analytics).

---

## Nota de Banco de Dados

# **64 / 100**

## Avaliação por Área

| Área | Nota |
|---|---|
| Modelagem | 65/100 |
| Integridade | 62/100 |
| Performance | 65/100 *(consistente com a nota de banco da Fase 3)* |
| Índices | 70/100 |
| Migrations | 62/100 |
| Escalabilidade | 58/100 |
| Multi-tenancy | 72/100 |
| Governança | 55/100 |

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma alteração de banco de dados, migration, índice ou modelo foi feita durante esta auditoria.*
