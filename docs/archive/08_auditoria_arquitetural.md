# Auditoria Arquitetural — GD Frete Diagnóstico
**GD Conecta · GD LogInsight · Junho 2026**

> **Nota metodológica:** Este relatório foi produzido com base na leitura integral do código-fonte — todos os 52 arquivos Python do backend, 33 componentes JSX, scripts de infraestrutura e migrações. Nenhuma afirmação é baseada em suposição. Os problemas apontados têm número de linha e arquivo referenciados.

---

## RELATÓRIO EXECUTIVO

O GD Frete Diagnóstico está em **boa forma para um produto na fase em que se encontra**. A escolha da Clean Architecture foi executada corretamente, o código é legível, testável e bem organizado para uma equipe pequena. A plataforma está pronta para rodar em produção com PostgreSQL e Docker, e pode receber melhorias incrementais sem grandes reescritas.

O problema central **não é o código que existe, mas o que falta**: ausência de rate limiting, CNPJ sem validação real, Swagger aberto em produção, JWT no localStorage, XML sem proteção contra ataques, e — o mais crítico para o roadmap futuro — ausência total de infraestrutura assíncrona, caching, isolamento de transportadoras por empresa e qualquer preparação para IA ou benchmarking coletivo.

A plataforma está bem posicionada para V3 (BID de Frete) se adicionado isolamento de dados por empresa. Para V4 (IA) e além, precisará de mudanças arquiteturais mais profundas, não apenas de código, mas de modelo de dados e infraestrutura.

**Notas gerais:**

| Dimensão | Nota |
|---|---|
| Arquitetura Geral | 76 / 100 |
| Segurança | 54 / 100 |
| Performance | 58 / 100 |
| Multi-empresa | 61 / 100 |
| Manutenibilidade | 82 / 100 |
| Cloud Readiness | 72 / 100 |
| Prontidão para IA | 28 / 100 |
| Escalabilidade | 55 / 100 |

---

## 1. ARQUITETURA GERAL

### Avaliação: BOA

A Clean Architecture está corretamente implementada. A regra de dependência (camadas externas dependem das internas, nunca o contrário) é respeitada em quase todo o código. Os ports/adapters (interfaces de repositório em domain/repositories) garantem que trocar SQLite por PostgreSQL não exigiu tocar nos use cases — prova empírica de que a arquitetura funciona.

### O que está bem

- Separação clara domain → application → infrastructure → presentation.
- Entidades de domínio são dataclasses Python puras, sem dependência de ORM ou framework.
- Repositórios com interfaces abstratas (ABC) — trocar implementação é cirúrgico.
- DI via FastAPI Depends é consistente e testável.
- Parser de CT-e é robusto, trata variações reais de XML, e tem testes de regressão específicos.

### Problemas encontrados

**P-01 — VIOLAÇÃO DE ENCAPSULAMENTO (Alta)**
`benchmark.py` acessa métodos privados do `DiagnosticoUseCase` diretamente:
```python
# benchmark.py linhas 134, 156, 181, 212
ind = self.diagnostico._indicador_nacional(ctes)
indicadores = self.diagnostico._indicadores_regionais(ctes)
indicadores = self.diagnostico._indicadores_transportadora(ctes)
```
Prefixo `_` em Python indica que o método é interno. Isso cria acoplamento estrutural: qualquer refatoração de `DiagnosticoUseCase` silenciosamente quebra o `BenchmarkUseCase`. A solução correta é extrair esses cálculos para um serviço compartilhado (`IndicadoresService`) ou expô-los via interface.

**P-02 — INSTANCIAÇÃO DE USE CASES DUPLICADA EM ROUTERS (Média)**
`DiagnosticoUseCase` e `BenchmarkUseCase` são construídos manualmente em três routers diferentes:
- `dashboard.py` linha 21: `_build_uc(...)` com 5 parâmetros
- `relatorios.py` linha 31: `_gerar_diag(...)` com os mesmos 5 parâmetros
- `benchmark_analise.py` linha 33: `_build_uc(...)` ainda diferente, com 6 parâmetros

Se a assinatura do construtor mudar (ex.: adicionar um serviço de cache), há três lugares para atualizar. O padrão correto é expor os use cases como dependências no `dependencies.py`.

**P-03 — LÓGICA DE SEED NO main.py (Baixa)**
`main.py` tem 174 linhas e mistura: configuração do app, registro de middlewares, CORS, healthcheck e lógica de negócio do seed (criação de usuário admin, metas e benchmarks). Isso viola o SRP (Single Responsibility Principle) e dificulta testes unitários do seed isoladamente.

**P-04 — REPOSITÓRIOS, DTOs E SCHEMAS EM __init__.py MONOLÍTICOS (Média)**
- `infrastructure/database/repositories/__init__.py`: 472 linhas contendo TODOS os repositórios
- `application/dtos/__init__.py`: 178 linhas com TODOS os DTOs
- `presentation/schemas/__init__.py`: 340 linhas com TODOS os schemas

Para a fase atual é gerenciável. Para o roadmap com 10+ módulos, esses arquivos se tornarão imensamente difíceis de manter. A expansão para V3, V4, V5 exigirá refatoração obrigatória.

**P-05 — AUSÊNCIA DE CAMADA DE SERVIÇO DE APLICAÇÃO (Baixa → Alta futura)**
Hoje cada use case é independente, o que é correto. Mas quando V4 introduzir IA e V5 introduzir benchmark coletivo, haverá lógica transversal (auditoria, anonimização, consentimento, eventos) que não terá onde morar. A ausência de um `ApplicationService` ou camada de middleware de negócio vai gerar "soluções" acopladas.

---

## 2. BACKEND FASTAPI

### Avaliação: BOA

### O que está bem

- Todos os endpoints têm `response_model` com tipagem Pydantic.
- Tratamento de erros consistente (`HTTPException` com códigos corretos).
- Upload de CT-es com `UploadFile` correto, async onde necessário.
- Autenticação e autorização separadas (`get_current_user` vs `get_current_superuser`).
- Logging estruturado com `get_logger`.

### Problemas encontrados

**P-06 — SWAGGER/REDOC ABERTO EM PRODUÇÃO (Alta/Segurança)**
```python
# main.py linhas 147-149
docs_url="/docs",       # → /docs aberto em produção
redoc_url="/redoc",     # → /redoc aberto em produção
openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
```
Documentação da API exposta em produção é um vetor de reconhecimento. Qualquer atacante obtém todos os endpoints, schemas e parâmetros sem precisar reverter a API. Deve ser desabilitado (ou protegido) quando `ENVIRONMENT=production`.

**P-07 — CORS PERMISSIVO DEMAIS (Alta/Segurança)**
```python
# main.py linhas 158-159
allow_methods=["*"],
allow_headers=["*"],
```
`allow_methods=["*"]` permite métodos como TRACE e CONNECT, que podem ser usados em ataques CSRF e XST (Cross-Site Tracing). O correto é listar explicitamente: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`.

**P-08 — SEM RATE LIMITING EM NENHUM ENDPOINT (Alta/Segurança)**
Zero proteção contra brute force no `POST /auth/login`. Um atacante pode testar centenas de senhas por segundo sem bloqueio. Em uma aplicação B2B com dados de clientes, isso é crítico. Solução: `slowapi` (1 linha de código sobre o endpoint de login).

**P-09 — SEM LIMITE DE TAMANHO NO UPLOAD DE ARQUIVOS (Alta/Segurança)**
```python
# importacao.py — sem verificação de content_length
arquivos: list[UploadFile] = File(...)
```
Um atacante pode enviar um arquivo XML de 10 GB. O `UploadFile` vai ler tudo para memória antes de qualquer validação. Isso causa OOM (Out of Memory) e derruba o servidor. FastAPI tem `request.body()` com limite configurável — mas não foi usado.

**P-10 — XML SEM DEFENSA CONTRA XML BOMB (Alta/Segurança)**
O `defusedxml` está no ambiente (`pip show defusedxml` retorna resultado positivo), mas o parser **usa `xml.etree.ElementTree` puro**:
```python
# cte_parser.py linha 11
from xml.etree import ElementTree as ET
# ...
root = ET.fromstring(xml_bytes)  # VULNERÁVEL
```
Um atacante pode enviar um "billion laughs attack" XML com entidades expandidas que consomem GBs de RAM em milissegundos. Trocar `ET.fromstring` por `defusedxml.ElementTree.fromstring` é uma mudança de uma linha.

**P-11 — VALIDAÇÃO DE CNPJ APENAS SINTÁTICA (Média)**
```python
# schemas/__init__.py linha 50
cnpj_matriz: str   # aceita qualquer string
```
Não há validação do dígito verificador do CNPJ. É possível cadastrar empresas com CNPJs inválidos (ex.: "00.000.000/0000-00"), o que vai gerar problemas no cruzamento com CT-es reais. A biblioteca `validate-docbr` ou implementação própria do algoritmo do CNPJ resolve isso.

**P-12 — SENHA SEM POLÍTICA (Baixa)**
```python
# schemas/__init__.py
senha: str = Field(min_length=6)
```
Apenas comprimento mínimo de 6 caracteres. Sem exigência de maiúscula, número, caractere especial. Em um sistema B2B com dados financeiros, isso é insuficiente.

**P-13 — SEM REFRESH TOKEN (Média)**
O JWT expira em 8 horas e não existe endpoint de refresh. Quando o token expira, o usuário é forçado a um novo login. Para sistemas operacionais acessados durante o dia inteiro, isso prejudica a UX. Para V3/V4 com usuários simultâneos, a ausência de refresh tokens também impede implementar revogação de sessão.

**P-14 — ENDPOINTS SEM PAGINAÇÃO (Média → Alta futura)**
```python
# transportadoras.py
def listar(...): return repo.list(limit=1000)
```
`limit=1000` está hardcoded em vários lugares. Para o benchmark coletivo (V5) com milhares de transportadoras, isso não escala. Os endpoints de listagem (transportadoras, empresas, etc.) não têm `skip`/`limit` como parâmetros de query.

**P-15 — TRANSPORTADORA AUTO-CADASTRO GLOBAL (Alta para multi-tenant)**
```python
# importacao.py linhas 169-188
def _resolver_transportadora(self, cnpj, nome):
    criada = self.transp_repo.create(
        Transportadora(razao_social=nome or cnpj, cnpj=cnpj)
    )
```
Quando um CT-e é importado com uma transportadora desconhecida, ela é auto-cadastrada globalmente — **visível para TODOS os clientes da plataforma**. Se amanhã a GD Conecta tiver Empresa A e Empresa B como clientes, as transportadoras importadas pela Empresa A aparecem nas listas da Empresa B. Isso é uma violação de isolamento de dados.

---

## 3. FRONTEND REACT

### Avaliação: BOA

### O que está bem

- Separação clara: contexts (estado global), pages (lógica de tela), components (reutilizáveis), api (comunicação), utils (formatação), theme (identidade visual).
- EmpresaContext e AuthContext bem projetados e coerentes.
- `client.js` centraliza autenticação e tratamento de erros.
- Interceptors Axios implementados corretamente (token injection, 401 redirect).
- Chunks separados no Vite (react, mui, charts) — build otimizado.
- Paleta e tema GD extraídos em `theme/index.js` — identidade visual consistente.

### Problemas encontrados

**P-16 — JWT NO LOCALSTORAGE (Alta/Segurança)**
```javascript
// client.js linha 9-11
get: () => localStorage.getItem(TOKEN_KEY),
set: (t) => localStorage.setItem(TOKEN_KEY, t),
```
JWT no localStorage é vulnerável a XSS. Se qualquer script terceiro (CDN, dependência npm comprometida) for executado na página, ele pode ler o token. O padrão atual de segurança é usar `httpOnly cookies`, que são inacessíveis via JavaScript. Para B2B com dados financeiros, isso é risco médio-alto. A migração exige mudança no backend (resposta de login via `Set-Cookie`) e no frontend (remover tokenStore).

**P-17 — AUSÊNCIA DE ERROR BOUNDARY (Alta/UX)**
```javascript
// App.jsx — sem ErrorBoundary em nenhum nível
<BrowserRouter><FeedbackProvider><AuthProvider>...
```
Se qualquer componente filho lançar uma exceção não tratada em runtime, React desmonta toda a árvore e exibe uma tela em branco. Sem um Error Boundary, o usuário vê uma página vazia sem nenhuma mensagem de erro. Em produção, isso é crítico para diagnóstico de problemas.

**P-18 — CÓDIGO DE FILTRO DUPLICADO EM PÁGINAS DE BENCHMARK (Baixa)**
Todas as páginas de benchmark (BenchmarkNacional, BenchmarkRegional, BenchmarkTransportadoras, PotencialEconomia, DashboardExecutivo) têm o mesmo bloco de filtro de período (date pickers + botão Aplicar) implementado de forma independente. Um componente `FiltrosPeriodo` reutilizável eliminaria ~40 linhas duplicadas em 5 arquivos.

**P-19 — SEM TESTES UNITÁRIOS NO FRONTEND (Alta)**
Zero testes em `frontend/src/`. Não há Vitest, Jest nem Testing Library configurados. Para o roadmap com IA e benchmark coletivo, a ausência de testes no frontend significa que qualquer mudança em contextos ou lógica de negócio (ex.: cálculos de benchmark no cliente) pode quebrar silenciosamente.

**P-20 — EmpresaContext CARREGA TODAS AS EMPRESAS SEM PAGINAÇÃO (Baixa → Média futura)**
```javascript
// EmpresaContext.jsx
const lista = await empresasApi.listar(); // todas as empresas
```
Hoje a GD Conecta tem poucos clientes. Quando escalar para dezenas, o seletor de empresa vai lentificar. Não é crítico agora, mas deve ser resolvido antes de escalar.

---

## 4. BANCO DE DADOS

### Avaliação: BOA

### O que está bem

- Modelo normalizado, sem desnormalização desnecessária.
- Índices nas colunas certas: `ctes.empresa_id` (FK + index), `ctes.chave` (unique + index), `users.email` (unique + index).
- Uso de `JSONB` (PostgreSQL) para `composicao_frete` — correto para dados semiestruturados.
- Migrações com Alembic configuradas.

### Problemas encontrados

**P-21 — CARGA TOTAL DE CT-ES EM MEMÓRIA (Crítica/Performance)**
```python
# diagnostico.py linha 56
ctes = self.cte_repo.list_by_empresa(empresa_id, data_inicio, data_fim)
# → retorna TODOS os CT-es da empresa de uma vez
# → passa para 5 funções de cálculo que iteram sobre a lista
```
Este é o maior risco de performance do sistema. Para uma empresa com 50.000 CT-es, o dashboard vai:
1. Fazer uma query que retorna 50.000 linhas do banco
2. Materializar 50.000 objetos Python `CTe` em memória
3. Iterar sobre eles 5 vezes (nacional, regional, transportadora, prazo, composição)

Cada `CTe` tem ~20 campos. A 50k registros, isso é ~40-80MB de RAM por requisição — e cada request simultâneo duplica esse consumo. A solução correta é aggregação no banco (SQL `GROUP BY`, `SUM`, `COUNT`), não em Python.

**P-22 — bulk_create USANDO LOOP (Média/Performance)**
```python
# repositories/__init__.py
def bulk_create(self, ctes: List[CTe]) -> int:
    for e in ctes:
        m = self._to_model(e)
        self.db.add(m)     # loop individual
    self.db.commit()       # único commit (ok)
```
Um loop de `db.add()` por objeto é correto para preservar relacionamentos (NFes vinculadas), mas é mais lento que `session.bulk_insert_mappings()`. Para importações de 1.000+ CT-es, a diferença é perceptível.

**P-23 — ÍNDICE COMPOSTO AUSENTE EM ctes (Média)**
A query mais importante do sistema é:
```sql
SELECT * FROM ctes WHERE empresa_id = ? AND data_emissao BETWEEN ? AND ?
```
Existe `ix_ctes_empresa_id` separado e não há índice em `data_emissao`. Para filtros por período (uso cotidiano), o banco faz full scan na tabela `ctes` filtrando apenas por `empresa_id` e depois filtrando `data_emissao` em memória. Um índice composto `(empresa_id, data_emissao)` tornaria essa query ordens de magnitude mais rápida.

**P-24 — ÚNICA MIGRAÇÃO ALEMBIC (Baixa)**
Existe apenas `faa05e1d23e5_estrutura_inicial_...py`. Todas as mudanças de schema feitas durante o desenvolvimento foram aplicadas diretamente no SQLite local. Não há histórico de migrations incrementais. Isso significa que qualquer schema novo (V3, V4) exigirá cuidado extra para não quebrar produção.

**P-25 — TABELAS GLOBAIS SEM empresa_id (Alta para multi-tenant real)**

| Tabela | Problema |
|---|---|
| `transportadoras` | Todas as empresas-cliente compartilham o mesmo cadastro |
| `meta_nacional` | Uma única meta global — não por empresa-cliente |
| `meta_regional` | Idem — não por empresa-cliente |
| `benchmarks` | Valores de referência únicos para todos |
| `users` | Sem vínculo com empresa-cliente |

Para a GD Conecta operar como consultoria atendendo UMA empresa por vez, isso é aceitável. Para um **produto SaaS** (V3+) com múltiplos clientes simultâneos, o isolamento é obrigatório.

---

## 5. ANÁLISE DE MULTIEMPRESA

### Avaliação: REGULAR

**O que está garantido:**
CT-es e Filiais estão corretamente isolados por `empresa_id`. Todo repositório de CT-e filtra por `empresa_id` na query. Um usuário logado que acessa `/dashboard/{empresa_id}` vê apenas os dados daquela empresa.

**O que NÃO está garantido:**

1. **Autorização de empresa:** Um usuário autenticado pode acessar `/dashboard/999` mesmo que não seja da empresa 999. O endpoint só verifica autenticação (`get_current_user`), não se o usuário tem acesso àquela empresa específica. Hoje todos os usuários são admin da GD Conecta, então não é problema. Em um SaaS multi-cliente, um cliente poderia acessar dados de outro cliente apenas trocando o `empresa_id` na URL.

2. **Transportadoras compartilhadas:** Dados de transportadoras (incluindo contatos, e-mails, performance) são compartilhados globalmente. Para o benchmark coletivo anonimizado (V5), isso é a camada errada de abstração.

3. **Metas e benchmarks globais:** Empresa A e Empresa B compartilham as mesmas metas regionais e benchmarks de mercado. Para consultorias que querem metas diferentes por cliente, isso é uma limitação.

4. **Risco de vazamento de chave sintética (Excel):**
```python
# importacao.py linha 120
chave_sintetica = f"EXCEL-{empresa_id}-{linha.nota_fiscal}"
```
A chave de deduplicação para Excel usa apenas `empresa_id + nota_fiscal`. Se duas empresas tiverem NF de mesmo número (o que acontece regularmente), a segunda importação é silenciosamente ignorada como "duplicada" — mesmo sendo de empresas diferentes.

---

## 6. SEGURANÇA

### Avaliação: REGULAR (riscos sérios presentes)

#### Mapa de riscos de segurança

| # | Problema | Severidade | Impacto |
|---|---|---|---|
| S-01 | XML sem defusedxml | Alta | RCE / DoS via XML Bomb |
| S-02 | Upload sem limite de tamanho | Alta | DoS por esgotamento de memória |
| S-03 | Sem rate limiting no login | Alta | Brute force de credenciais |
| S-04 | JWT no localStorage | Média-Alta | Roubo de sessão via XSS |
| S-05 | Swagger aberto em produção | Média | Reconhecimento e enumeração de API |
| S-06 | CORS allow_methods=["*"] | Média | Habilitação de TRACE (XST attack) |
| S-07 | CNPJ sem validação real | Média | Dados corrompidos no banco |
| S-08 | Sem refresh token / revogação | Média | Token roubado válido por 8h |
| S-09 | Senha padrão admin123 | Média | Acesso se .env não configurado |
| S-10 | Política de senha fraca (min 6) | Baixa | Senhas fáceis de adivinhar |
| S-11 | Sem validação MIME em uploads | Baixa | Arquivo não-XML enviado como XML |
| S-12 | Autorização por empresa ausente | Alta (SaaS) | Usuário acessa dados de outra empresa |

---

## 7. PERFORMANCE

### Avaliação: REGULAR (aceitável agora, problemática em escala)

#### Análise de gargalos

**Gargalo 1 — Dashboard (crítico em escala)**
O endpoint `GET /dashboard/{empresa_id}` carrega todos os CT-es da empresa em Python, passa pela função `gerar()` que chama 5 métodos de agregação sequencialmente sobre a mesma lista. Com 10.000 CT-es, já haverá latência perceptível. Com 100.000, o sistema trava.

Solução: mover os cálculos de `SUM`, `COUNT`, `AVG` para SQL (`GROUP BY macro_regiao_destino`, etc.) e manter o Python apenas para lógica de negócio que não é SQL pura.

**Gargalo 2 — N+1 na listagem de transportadoras**
```python
# diagnostico.py linha 123
nomes = {t.id: (t.nome_fantasia or t.razao_social)
         for t in self.transp_repo.list(limit=1000)}
```
A cada cálculo de indicadores de transportadora, busca todas as 1.000 transportadoras do banco. Se chamado pelo benchmark (que chama `_indicadores_transportadora` em cada análise), há várias queries redundantes por request.

**Gargalo 3 — Relatórios síncronos**
PDF e Excel são gerados sincroneamente no thread do HTTP request. Para um relatório com 12 meses de dados (potencialmente 50k CT-es), isso bloqueia o worker por vários segundos. A solução é processamento assíncrono com fila (Celery + Redis) e polling de status.

**Gargalo 4 — Sem caching**
Cada requisição ao dashboard recalcula tudo. Para os benchmarks, os valores mudam raramente (benchmarks de mercado são editados manualmente). Um cache de 5-10 minutos (Redis) reduziria a carga em 90% para a maioria dos acessos.

---

## 8. CLOUD READINESS

### Nota: 72 / 100

**Pronto:**
- Docker Compose para dev e produção.
- PostgreSQL como banco principal.
- Variáveis de ambiente via `pydantic-settings`.
- Frontend com nginx servindo SPA.
- Proxy reverso `/api` configurado.

**Não pronto:**
- Sem healthcheck no container backend (Dockerfile menciona netcat mas não configura `HEALTHCHECK`).
- Sem graceful shutdown.
- Swagger exposto em produção.
- Sem secrets management (HashiCorp Vault, AWS Secrets Manager).
- Sem horizontal scaling (Uvicorn síncrono com 1-2 workers — não escala horizontalmente sem adaptação).
- Sem observabilidade (logs estruturados existem, mas não há integração com OpenTelemetry, Datadog, Sentry, etc.).

---

## 9. MANUTENIBILIDADE

### Nota: 82 / 100

**Pontos fortes:**
- Código bem nomeado em português, consistente com o domínio.
- Docstrings em funções públicas.
- Comentários explicam "por quê", não "o quê".
- Estrutura previsível — um desenvolvedor novo encontra rapidamente onde está cada funcionalidade.
- 9 testes de smoke cobrindo fluxos críticos.
- Migrações com Alembic (histórico de schema).

**Pontos de atenção:**
- Arquivos monolíticos (`repositories/__init__.py` com 472 linhas) dificultarão manutenção em escala.
- Ausência de testes unitários no frontend.
- Acesso a métodos privados de use cases (`_indicador_nacional`) — armadilha para manutenção futura.
- Sem documentação de decisões arquiteturais (ADR — Architecture Decision Records).

**Nota para manutenção por IA:** **9 / 10.** O código tem estrutura clara, nomenclatura consistente e comentários adequados. Um assistente de IA consegue navegar e modificar o código com alta precisão.

---

## 10. AVALIAÇÃO DO ROADMAP FUTURO

### V3 — BID de Frete

**Prontidão: Média (60%)**

O BID de Frete (licitação eletrônica de fretes) precisa de: entidade `Licitacao`, rotas de cotação, aceite de proposta, histórico de preços, notificações em tempo real (WebSocket ou polling).

O que favorece: a Clean Architecture permite adicionar novos módulos sem alterar os existentes. O modelo de Empresa/Transportadora já existe.

O que bloqueia: o isolamento de transportadoras por empresa é obrigatório para um BID real (Empresa A não pode ver as cotações da Empresa B). Transportadoras precisam de `empresa_id`. Sem isso, o BID vazará dados entre clientes.

### V4 — Inteligência Artificial

**Prontidão: Baixa (28%)**

IA logística exige: processamento assíncrono (Celery), armazenamento de features (feature store), pipeline de ML (retreinamento periódico), armazenamento de modelos (MLflow, S3), endpoints de inferência separados dos CRUD, dados históricos em série temporal.

O que existe: dados históricos de CT-es com timestamps — é o ponto de partida.

O que falta: tudo o mais. FastAPI síncrono bloqueia durante inferência de modelos pesados. Não há fila de tarefas. Não há separação de serviço de IA. Não há dados de feedback (OTIF real vs predito). Não há pipeline de feature engineering. Adicionar IA sobre a arquitetura atual resultaria em código embaraçoso e dificilmente escalável.

**Recomendação:** antes de V4, adicionar Celery + Redis + serviço separado de IA (FastAPI assíncrono ou Flask ML service).

### V5 — Benchmark Coletivo Anonimizado

**Prontidão: Muito Baixa (18%)**

Este módulo requer: consentimento explícito das empresas para compartilhar dados, pipeline de anonimização (k-anonymity, diferential privacy), arquitetura de dados separada (data warehouse ou lake), computação de benchmarks a partir dos dados reais dos clientes (não valores manuais), e garantias legais (LGPD).

O que existe: estrutura de benchmark manual — ponto de partida conceitual.

O que falta: toda a infraestrutura técnica e legal. O modelo atual de benchmarks (editados manualmente por admin) é o oposto do benchmark coletivo automatizado. Seria necessário criar uma camada de dados completamente separada, com ETL periódico, anonimização e agregação.

### V6 — Inteligência de Mercado Logístico

**Prontidão: Muito Baixa (12%)**

Este módulo é essencialmente um produto de dados B2B (market intelligence). Requer: fontes externas de dados (ANTT, IBGE, câmbio, combustível), event-driven architecture, pub/sub (Kafka ou similar), API pública para consumo por clientes, data warehouse histórico, dashboards especializados por segmento.

A arquitetura atual não tem nenhuma dessas peças. É o passo mais distante da realidade atual.

---

## MATRIZ DE RISCOS

| Risco | Probabilidade | Impacto | Score | Prioridade |
|---|---|---|---|---|
| DoS por XML sem proteção | Alta | Crítico | 🔴 25 | P0 |
| Brute force no login | Média | Alto | 🔴 20 | P0 |
| Upload sem limite derruba servidor | Média | Alto | 🔴 20 | P0 |
| Dashboard falha em escala (50k+ CT-es) | Alta | Alto | 🔴 20 | P1 |
| Usuário acessa empresa alheia (SaaS) | Média | Crítico | 🔴 20 | P1 |
| Swagger exposto em produção | Alta | Médio | 🟡 15 | P1 |
| JWT no localStorage (XSS) | Média | Alto | 🟡 15 | P2 |
| Transportadoras globais (isolamento) | Alta | Alto | 🔴 20 | P1 |
| Relatórios síncronos bloqueando servidor | Média | Médio | 🟡 12 | P2 |
| Ausência de caching (performance) | Alta | Médio | 🟡 15 | P2 |
| Sem testes de frontend | Alta | Médio | 🟡 15 | P2 |
| Arquivos monolíticos (manutenção V3+) | Alta | Baixo | 🟢 10 | P3 |

---

## PLANO DE CORREÇÕES PRIORITÁRIAS

### Curto Prazo — Antes de qualquer novo cliente ou feature (1-2 semanas)

1. **defusedxml:** Trocar `ET.fromstring` por `defusedxml.ElementTree.fromstring` em `cte_parser.py` — 1 linha.
2. **Limite de upload:** Adicionar `Content-Length` máximo no nginx e verificação em bytes no endpoint de importação.
3. **Rate limiting:** `slowapi` no endpoint `POST /auth/login` — 5 tentativas por minuto por IP.
4. **Desabilitar Swagger em produção:** `docs_url=None if settings.is_production else "/docs"`.
5. **CORS restritivo:** Listar métodos explicitamente em vez de `["*"]`.

### Médio Prazo — Antes de V3 / onboarding de novos clientes (1-2 meses)

6. **Índice composto:** `(empresa_id, data_emissao)` na tabela `ctes` — uma migration.
7. **Autorização por empresa:** Middleware que valida que o `empresa_id` da URL pertence ao usuário logado.
8. **Transportadoras por empresa:** Adicionar `empresa_id` à tabela, migration, ajustar repositório e use cases.
9. **Validação de CNPJ:** Implementar dígito verificador no schema Pydantic.
10. **Aggregações SQL no diagnóstico:** Mover `SUM`, `COUNT`, `AVG` para SQL via `GROUP BY` — maior impacto de performance.
11. **Error Boundary no React:** Componente padrão em `App.jsx`.
12. **Componente FiltrosPeriodo:** Eliminar duplicação nas 5 páginas de benchmark.

### Longo Prazo — Habilitadores para V4+ (3-6 meses)

13. **Celery + Redis:** Fila de tarefas para relatórios, importações grandes e futura IA.
14. **Caching com Redis:** Dashboard e benchmarks com TTL de 5-10 minutos.
15. **Refatoração dos arquivos monolíticos:** Separar repositórios, DTOs e schemas por módulo.
16. **BenchmarkUseCase desacoplado:** Extrair `IndicadoresService` com métodos públicos, remover acesso a `_métodos` privados.
17. **Testes frontend:** Vitest + Testing Library para contextos e componentes críticos.
18. **Refresh token + cookie httpOnly:** Migrar JWT para cookies para eliminar risco de XSS.
19. **Observabilidade:** Sentry para erros, estrutura para OpenTelemetry.
20. **ADRs:** Documentar as principais decisões arquiteturais tomadas.

---

## RECOMENDAÇÕES ESTRATÉGICAS

**1. A fundação está certa — não reconstrua, evoluia.**
Clean Architecture corretamente aplicada é um ativo raro. A tentação de reescrever do zero para "escalar" geralmente resulta em perda de funcionalidades e regressões. A abordagem correta é adição incremental de camadas (caching, filas, observabilidade) sobre a fundação existente.

**2. O gargalo de escala mais urgente é o dashboard.**
Mover os cálculos do dashboard para SQL é o investimento com melhor ROI de performance. Uma query bem escrita com `GROUP BY` vai substituir milhares de iterações Python. Faça isso antes de qualquer novo cliente com volume relevante de CT-es.

**3. Resolva o isolamento de transportadoras antes de qualquer novo cliente.**
É a mudança arquitetural de mais impacto para viabilizar o produto como SaaS. Não é uma mudança difícil (adicionar `empresa_id`, migration, ajustar repositório), mas se postergada, acumula dívida técnica exponencial.

**4. Para chegar ao V4 (IA), adicionar processamento assíncrono é obrigatório.**
Não é uma otimização — é um habilitador. Sem Celery + Redis, qualquer inferência de ML vai bloquear o servidor. A boa notícia: FastAPI + Celery é uma combinação consagrada e a adição é incremental.

**5. Para o benchmark coletivo (V5), comece com arquitetura legal antes de arquitetura técnica.**
O produto técnico mais sofisticado do mundo não adianta se não houver consentimento LGPD, cláusula contratual de compartilhamento de dados e metodologia de anonimização. A recomendação é consultar assessoria jurídica especializada em LGPD + dados logísticos antes de qualquer linha de código para V5.

**6. A denominação "GD LogInsight" merece arquitetura de "platform product".**
Se o objetivo estratégico é se tornar uma plataforma nacional de inteligência logística, a recomendação arquitetural de longo prazo é separar o sistema em serviços com responsabilidades claras: `diagnóstico-service`, `benchmark-service`, `bid-service`, `ai-service`, com comunicação via API gateway. Isso não precisa acontecer hoje, mas as fronteiras entre módulos devem ser desenhadas com essa separação futura em mente.

---

## NOTAS FINAIS

Nenhum sistema perfeito existe em fase de desenvolvimento. O GD Frete Diagnóstico tem uma base técnica honesta, com escolhas sensatas para o contexto de uma consultoria B2B que desenvolve seu primeiro produto digital. Os problemas encontrados são, em grande maioria, riscos de crescimento — não falhas de concepção. Com as correções de segurança urgentes implementadas e o plano de evolução seguido, a plataforma tem capacidade real de se tornar o ativo tecnológico diferenciador que a GD Conecta busca.
