# 03 · Arquitetura Técnica

> Substitui `archive/02_arquitetura_tecnica.md`. Versão do sistema: **6.5.1**.

## 1. Visão geral

Clean Architecture no backend, com regra de dependência respeitada (camadas externas dependem das internas, nunca o contrário):

```
presentation (FastAPI routers, schemas Pydantic)
        ↓ depende de
application (use cases — regra de negócio pura)
        ↓ depende de
domain (entidades dataclass + interfaces de repositório — sem ORM, sem framework)
        ↑ implementado por
infrastructure (SQLAlchemy models, repositórios concretos, parsers, IA, relatórios, Celery)
```

Entidades de domínio são dataclasses Python puras (`app/domain/entities/__init__.py`) — não dependem de SQLAlchemy nem de FastAPI. Os repositórios concretos (em `infrastructure/database/repositories/`) fazem o mapeamento entre entidade e modelo ORM. Trocar o banco (SQLite→PostgreSQL) não exigiu tocar em nenhum use case — é a prova prática de que a separação funciona.

## 2. Stack tecnológica (versões mínimas reais, de `requirements.txt`/`package.json`)

### Backend

| Componente | Versão mínima |
|---|---|
| FastAPI | 0.115.0 |
| Uvicorn (standard) | 0.34.0 |
| SQLAlchemy | 2.0.0 (síncrono) |
| Alembic | 1.14.0 |
| Pydantic | 2.10.0 |
| pydantic-settings | 2.7.0 |
| python-jose[cryptography] | 3.3.0 |
| bcrypt | 4.2.0 (sem passlib — compatibilidade com Python 3.14+) |
| python-multipart | 0.0.20 |
| openpyxl | 3.1.0 |
| reportlab | 4.2.0 |
| email-validator | 2.2.0 |
| psycopg2-binary | 2.9.0 |
| defusedxml | 0.7.0 |
| slowapi | 0.1.9 |
| celery | 5.3.0 |
| redis | 5.0.0 |
| openai | 1.50.0 |
| anthropic | 0.40.0 |
| pgvector | 0.3.0 |
| python-docx | 1.1.0 |
| python-pptx | 0.6.23 |

### Frontend

| Componente | Versão |
|---|---|
| React / React DOM | ^18.3.1 |
| React Router DOM | ^6.28.0 |
| MUI (`@mui/material`, `@mui/icons-material`) | ^6.2.0 |
| `@mui/x-data-grid` | ^7.23.1 |
| TanStack React Query | ^5.62.7 |
| Axios | ^1.7.9 |
| Recharts | ^2.13.3 |
| Vite | ^6.0.3 |

## 3. Estrutura de pastas

```
backend/
  app/
    domain/            # entidades (dataclass) + interfaces de repositório (ABC)
    application/
      use_cases/        # 25 arquivos — regra de negócio, sem SQL direto de infra
      dtos/
    infrastructure/
      database/
        models/          # 53 modelos SQLAlchemy → 44 tabelas
        repositories/     # implementações concretas dos repositórios
      parsers/           # CT-e XML (defusedxml), evento de cancelamento, Excel, macro-região
      reports/           # Excel/PDF (diagnóstico, benchmark, BID)
      ai/                # llm_client (abstração OpenAI/Anthropic + modo simulado), cache, usage_logger
      tasks/             # tarefas Celery (ai_tasks.py)
      celery_app.py
    presentation/
      api/
        dependencies.py   # DI: repositórios, get_current_user, verificar_acesso_empresa, bloquear_visualizador...
        v1/                # 19 routers, 148 endpoints
      schemas/            # schemas Pydantic (request/response)
    core/
      config.py          # Settings (pydantic-settings)
      database.py
      security.py        # hash/verify de senha, criação/validação de JWT, cookies httpOnly
      logging_config.py
    main.py              # app FastAPI, CORS, rate limiter, seed inicial, lifespan
  alembic/versions/       # 10 migrations
  tests/                  # 7 arquivos, 68 casos

frontend/
  src/
    api/                 # client.js (axios), endpoints.js, queries.js (React Query), queryKeys.js
    contexts/            # AuthContext, EmpresaContext
    layouts/             # AppLayout (menu lateral + topbar)
    components/          # componentes reutilizáveis
    pages/               # ~50 páginas
    theme/                # paleta e tipografia GD Conecta
```

## 4. Fluxo de requisição e injeção de dependência

FastAPI `Depends()` encadeia: `get_db` → repositório concreto → (opcional) use case → dependency de autorização → função do endpoint. Exemplo típico de um endpoint escopado por empresa e bloqueado para escrita por VISUALIZADOR:

```python
@router.post("/{empresa_id}/processar")
def processar(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    uc: DlgUseCase = Depends(_uc),
):
    ...
```

## 5. Autenticação e autorização

### 5.1 Autenticação — JWT via cookie `httpOnly` (desde v6.5.1)

- `POST /auth/login` autentica (bcrypt) e emite **access token** (30 min) e **refresh token** (7 dias), gravados como cookies `httpOnly`, `SameSite=Lax`, `Secure` em produção. O cookie de refresh tem `path` restrito a `/api/v1/auth`, reduzindo a superfície de exposição.
- O corpo da resposta de login/refresh **também** devolve os tokens em JSON, mantido por compatibilidade com clientes de API/scripts que não usam cookie — o frontend web ignora esse campo e depende só do cookie.
- `get_current_user` aceita o token tanto do cookie quanto de um header `Authorization: Bearer` explícito — o header, quando presente, tem prioridade sobre o cookie ambiente (importante para múltiplas identidades numa mesma sessão HTTP, como em testes automatizados).
- `POST /auth/logout` limpa os cookies no servidor — necessário porque JavaScript não consegue apagar um cookie `httpOnly` sozinho.
- O frontend (`client.js`) não lê nem armazena o token em `localStorage` — o cookie é anexado automaticamente pelo navegador (`withCredentials: true`), fechando o vetor de roubo de token via XSS que existia antes da v6.5.1.

### 5.2 Autorização — dependencies reutilizáveis

| Dependency | O que garante |
|---|---|
| `get_current_user` | Usuário autenticado (cookie ou Bearer) |
| `get_current_superuser` / `require_admin` | `is_superuser=True` OU papel `ADMIN` |
| `verificar_acesso_empresa` | O `empresa_id` do path/query pertence ao usuário logado (ou o usuário é superusuário global) |
| `bloquear_visualizador` | Papel do usuário não é `VISUALIZADOR` — aplicado em todo endpoint de escrita que não seja já admin-only |
| `get_bid_com_acesso` | Carrega o BID pelo `bid_id` do path e garante acesso à empresa dona dele — o `empresa_id` efetivo de qualquer operação subsequente vem do próprio BID, nunca de um parâmetro de query enviado pelo cliente |
| `get_transportadora_com_acesso` | Idem, para transportadora por `tid` |

### 5.3 Papéis (RBAC)

`RoleEnum`: `ADMIN`, `ANALISTA`, `VISUALIZADOR`. `ADMIN` de uma empresa administra usuários/dados só da própria empresa; um superusuário global (`is_superuser=True`, `empresa_id=None`) administra qualquer empresa. `VISUALIZADOR` é bloqueado em toda escrita, exceto ações que não persistem dado (ex.: `calcular_simulacao`, `mcl/simular`, `rag/buscar` — cálculos de prévia).

## 6. Segurança — controles ativos

| Controle | Onde |
|---|---|
| Rate limiting (10 req/min login, 200 req/min global) | `slowapi`, `main.py`/`auth.py` |
| Proteção XML Bomb (`defusedxml`) | `cte_parser.py` |
| Limite de upload (10 MB/arquivo XML, 500/lote, 20 MB Excel) + validação de magic bytes | `importacao.py` |
| Swagger/Redoc desabilitados em produção | `main.py` (`ENVIRONMENT=production`) |
| CORS restritivo (métodos e headers explícitos, sem `*`) | `main.py` |
| Validação de CNPJ (dígito verificador, módulo 11) | `schemas/__init__.py` |
| Política de senha (mínimo 8 caracteres + 1 letra + 1 número na criação) | `schemas/__init__.py` |
| `SECRET_KEY`/senha fraca bloqueiam o boot em produção | `config.py` (`_validar_seguranca_producao`) |
| Isolamento multi-tenant por `empresa_id` em toda entidade operacional | `verificar_acesso_empresa`, `get_bid_com_acesso`, `get_transportadora_com_acesso` |
| Cookies `httpOnly` para JWT | `security.py`, `auth.py` |

Ver [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md) para o histórico completo de achados e correções de segurança, incluindo a auditoria de 2026-07-07 que descobriu e corrigiu lacunas de isolamento multi-tenant nos módulos BID, MCL, Transportadoras e Inteligência IA.

## 7. Banco de dados

- **Produção**: PostgreSQL 16, com extensão `pgvector` para embeddings do RAG.
- **Desenvolvimento local sem Docker**: SQLite (`sqlite:///./gd_frete.db`).
- **Schema gerenciado por Alembic** em produção; em desenvolvimento, o `lifespan` do FastAPI roda `create_all` + um conjunto de alterações incrementais idempotentes (`ADD COLUMN IF NOT EXISTS`) + seed automático, para tolerar divergência de schema local sem exigir `alembic upgrade head` manual a cada mudança.
- 44 tabelas, 10 migrations — ver [`04_modelo_de_dados.md`](04_modelo_de_dados.md) para o detalhamento completo.

## 8. Inteligência Artificial — infraestrutura

- **Abstração de LLM** (`infrastructure/ai/llm_client.py`): modo simulado (mock determinístico, sem custo) por padrão; GPT-4.1 (OpenAI) e Claude Haiku (Anthropic) via *tool-calling* quando `AI_SIMULATION_MODE=False` e há chave configurada.
- **Celery + Redis**: processamento assíncrono e *beat schedule* de insights diários.
- **Cache**: híbrido Redis com fallback em memória; diagnóstico IA cacheado por hash SHA-256 do contexto (evita custo de IA se nada mudou).
- **RAG**: embeddings armazenados em JSON (portável entre SQLite/PostgreSQL); busca por similaridade de cosseno calculada em Python — compatível com uma futura otimização via índice `pgvector`/`ivfflat` nativo, hoje não necessária para o volume atual.
- **`usage_logger`**: registra tokens e custo estimado (USD/BRL) por empresa e funcionalidade.

## 9. Infraestrutura e deploy

| Arquivo | Ambiente | O que sobe |
|---|---|---|
| `docker-compose.yml` (raiz) | Legado/simplificado | Backend (SQLite em volume) + Frontend, sem Postgres/Redis |
| `docker-compose.dev.yml` | Desenvolvimento | Postgres 16 + Backend (hot-reload, `alembic upgrade head` no start) + Frontend (Vite dev server) |
| `docker-compose.prod.yml` | Produção | Rede interna isolando `db`/`backend` do host; só o `frontend` (Nginx) expõe portas 80/443; `backend` com 2 workers, sem porta exposta |

`frontend/nginx.conf`: serve o SPA React, gzip, `client_max_body_size` 25M (raiz) / 50M (`/api/`, uploads de XML/Excel), proxy reverso `/api/` → `backend:8000/api/`, cache de 1 ano para assets estáticos.

Scripts Windows (`iniciar.bat`/`parar.bat`) automatizam o ciclo de desenvolvimento local via `docker-compose.dev.yml`.

Ver [`08_instalacao_deploy.md`](08_instalacao_deploy.md) para o passo-a-passo completo (local, Docker, produção Ubuntu).

## 10. Migrations Alembic

Ver a lista cronológica completa em [`04_modelo_de_dados.md`](04_modelo_de_dados.md#migrations).

## 11. Frontend — contextos e API client

- **`AuthContext`**: expõe `{ usuario, carregando, login, logout }`. Restaura a sessão chamando `GET /auth/me` (o cookie, se válido, autentica automaticamente); nunca lê nem decodifica o JWT no cliente.
- **`EmpresaContext`**: gerencia a "empresa ativa" (seleção persistida em `localStorage`, chave não sensível — só um ID de preferência de UI); seleciona automaticamente a primeira empresa `ATIVO` quando a lista carrega.
- **`client.js`**: instância Axios (`baseURL=/api/v1`, `withCredentials: true`), com fila de retentativa automática em 401 via `/auth/refresh`.

## 12. Relatórios

Excel via `openpyxl`, PDF via `reportlab`, Word via `python-docx`, PowerPoint via `python-pptx` — todos com a paleta de identidade visual GD Conecta (Indigo `#2D3561`, Amber `#C9A84C`, Blue `#0077A8`, Ivory `#F5F1EB`).
