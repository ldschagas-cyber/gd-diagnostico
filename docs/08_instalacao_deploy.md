# 08 · Instalação e Deploy

> Substitui `archive/05_guia_deploy_ubuntu.md` e `archive/10_guia_instalacao_v4_ia.md`, corrigindo as divergências encontradas na auditoria (ver `archive/README.md`).

## 1. Ambiente local sem Docker

Requisitos: Python 3.12+, Node.js 20+.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
cp .env.example .env   # ajuste DATABASE_URL para sqlite:///./gd_frete.db
uvicorn app.main:app --reload

# Frontend (outro terminal)
cd frontend
npm install
npm run dev
```

Login inicial (seed automático): `admin@gdconecta.com.br` / senha definida em `FIRST_SUPERUSER_PASSWORD` no `.env` (default de código: `admin123` — **troque em qualquer ambiente que não seja seu próprio laptop de desenvolvimento**).

## 2. Ambiente local com Docker (desenvolvimento)

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

Sobe 3 serviços: `db` (PostgreSQL 16, porta 5432), `backend` (hot-reload, roda `alembic upgrade head` automaticamente no start, porta 8000), `frontend` (Vite dev server, porta 5173). No Windows, os scripts `iniciar.bat`/`parar.bat` automatizam esse ciclo (verificam Docker Desktop, criam `.env` a partir do `.env.example` se ausente, aguardam o backend responder, abrem o navegador).

## 3. Inteligência Logística com IA — infraestrutura adicional (Redis + Celery)

O módulo de IA (insights automáticos, diagnóstico executivo, relatórios) precisa de Redis e Celery além do backend/frontend padrão.

```bash
# Redis (se não estiver usando docker-compose.dev.yml, que já inclui infraestrutura de IA)
docker run -d --name gd-redis -p 6379:6379 redis:7-alpine

# Terminal do Celery worker (na pasta backend, com venv ativado)
celery -A app.infrastructure.celery_app worker --loglevel=info --pool=solo   # --pool=solo é necessário no Windows

# Terminal do Celery beat (agendador de insights diários)
celery -A app.infrastructure.celery_app beat --loglevel=info
```

Variáveis relevantes no `.env`: `AI_SIMULATION_MODE`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — ver lista completa na seção 5.

**Validação da infraestrutura de IA:**

```bash
python -c "from app.infrastructure.celery_app import celery_disponivel; print(celery_disponivel())"
# Deve retornar True
```

**Modo simulado vs. real**: com `AI_SIMULATION_MODE=True` (padrão), todos os números continuam vindo de SQL real — só o texto narrativo da IA é simulado, sem custo de API. Para ativar modelos reais, defina `AI_SIMULATION_MODE=False` e preencha `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`.

**RAG**: busca por similaridade de cosseno funciona igual em SQLite e PostgreSQL (embeddings armazenados em JSON). A extensão `pgvector` já vem instalada na imagem PostgreSQL usada pelo `docker-compose.dev.yml`/`docker-compose.prod.yml`; um índice `ivfflat` nativo é uma otimização futura para grandes volumes, não necessária hoje.

## 4. Deploy em produção (Ubuntu Server 24.04 LTS)

### 4.1 Pré-requisitos

- Docker Engine + Docker Compose plugin instalados.
- Firewall (`ufw`) liberando apenas 80/443/22.
- Domínio apontado para o servidor (para HTTPS via Certbot).

### 4.2 Deploy

```bash
git clone <repositório> gd-frete-diagnostico && cd gd-frete-diagnostico
cp backend/.env.example backend/.env   # editar com valores de produção (seção 5)
docker compose -f docker-compose.prod.yml up -d --build
```

`docker-compose.prod.yml` isola `db` e `backend` numa rede interna — **só o `frontend` (Nginx) expõe portas** (80/443). O `backend` roda com 2 workers Uvicorn, sem porta exposta ao host.

**Redis/Celery em produção**: `docker-compose.prod.yml`, na versão atual, **não inclui** serviços de Redis/Celery worker/beat — se o módulo de Inteligência IA for usado em produção, esses serviços precisam ser adicionados manualmente ao compose de produção (ver pendência registrada em [`10_roadmap.md`](10_roadmap.md)).

### 4.3 Nginx externo (proxy reverso) + HTTPS

Se o `frontend` do compose não expuser 80/443 diretamente (ex.: múltiplos sites no mesmo servidor), configure um Nginx externo fazendo proxy para o container do frontend, e Certbot para o certificado TLS. O Nginx **interno** do container frontend (`frontend/nginx.conf`) já aplica:

- `client_max_body_size 25M` no bloco raiz do site, e `50M` no bloco `/api/` (para upload de XML/Excel).
- Proxy `/api/` → `backend:8000/api/`.
- Cache de 1 ano para assets estáticos.

### 4.4 Schema do banco em produção

Em produção, o schema é responsabilidade **exclusiva** do Alembic — `create_all`/seed automático (usado em dev) são desativados quando `ENVIRONMENT=production`. Rode `alembic upgrade head` antes de subir o backend, ou garanta que o entrypoint do container o faça (ver `docker-compose.dev.yml` para o padrão de referência).

> **Pendência conhecida**: não existem migrations Alembic para as tabelas de IA (Insights, DiagnosticoIA, ScoreLogistico, Oportunidade, ChatSessao/Mensagem, UsageLog, DocumentoVetorial, EmbeddingJob) nem para as mudanças de segurança de v6.5.0/6.5.1 — essas foram aplicadas via `create_all` em dev. Antes de um deploy de produção que dependa só de `alembic upgrade head`, gere as migrations faltantes (ver [`10_roadmap.md`](10_roadmap.md)).

### 4.5 Backup

```bash
# backup.sh (via cron diário, ex.: 2h da manhã)
docker exec gd_frete_db pg_dump -U gd_user gd_frete | gzip > backup_$(date +%Y%m%d).sql.gz
# Retenção sugerida: 30 dias
```

Restore:

```bash
gunzip -c backup_AAAAMMDD.sql.gz | docker exec -i gd_frete_db psql -U gd_user gd_frete
```

### 4.6 Atualização de versão

Forma recomendada — script único que faz `git pull` + rebuild + espera o
backend responder, e para com uma mensagem clara se algo falhar:

```bash
./atualizar_producao.sh
```

Equivalente manual, passo a passo (o que o script acima faz por trás):

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

As migrações do Alembic já rodam sozinhas dentro do container (ver
`command:` do serviço `backend` em `docker-compose.prod.yml`) — não é
necessário rodar `alembic upgrade head` manualmente depois do `up`.

**Passos extras pontuais de uma versão específica** (ex.: um script de
backfill de dado) aparecem só no changelog/anúncio daquela versão — não
fazem parte da rotina de toda atualização.

### 4.7 Monitoramento básico

```bash
docker stats
docker compose -f docker-compose.prod.yml logs -f backend
```

Não há integração com observabilidade externa (Sentry, OpenTelemetry, Datadog) nesta versão — ver débito técnico em [`10_roadmap.md`](10_roadmap.md).

## 5. Variáveis de ambiente (referência completa)

| Variável | Default (código) | Obrigatória em produção | Finalidade |
|---|---|---|---|
| `ENVIRONMENT` | `development` | Sim (`production`) | Alterna comportamento dev/produção |
| `DEBUG` | `True` | Sim (`False`) | Bloqueia o boot em produção se `True` |
| `DATABASE_URL` | `sqlite:///./gd_frete.db` | Sim (`postgresql+psycopg2://...`) | Conexão com o banco |
| `SECRET_KEY` | placeholder inseguro | Sim (única, ≥32 chars, `openssl rand -hex 32`) | Assinatura JWT — boot falha em produção se for o placeholder |
| `ALGORITHM` | `HS256` | Não | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Não | Expiração do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Não | Expiração do refresh token |
| `BACKEND_CORS_ORIGINS` | `localhost:5173,127.0.0.1:5173,...` | Sim (domínio real) | Origens permitidas |
| `FIRST_SUPERUSER_EMAIL` | `admin@gdconecta.com.br` | Recomendado alterar | Seed do admin inicial |
| `FIRST_SUPERUSER_PASSWORD` | `admin123` | Sim (senha forte) | Boot falha em produção com senhas fracas conhecidas |
| `MAX_CTE_BATCH` | `10000` | Não | Limite lógico de CT-es por lote (distinto do limite físico de 500 arquivos/lote do upload) |
| `AI_SIMULATION_MODE` | `True` | Depende do uso de IA real | Liga/desliga chamadas reais a LLM |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | vazio | Só se `AI_SIMULATION_MODE=False` | Chaves de API |
| `AI_MODEL_PRINCIPAL` / `AI_MODEL_VOLUME` | `gpt-4.1` / `claude-haiku-4-5` | Não | Modelos usados |
| `USD_TO_BRL` | `5.90` | Não | Câmbio para custo estimado |
| `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://localhost:6379/...` | Sim, se módulo de IA em uso | Fila assíncrona |
| `AI_CACHE_TTL` | `86400` | Não | TTL do cache de diagnóstico IA |
| `RAG_ENABLED` | `True` | Não (exige PostgreSQL) | Habilita busca semântica |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `text-embedding-3-small` / `1536` | Não | Configuração de embeddings |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_HOST` / `POSTGRES_PORT` | `gd_user`/`gd_pass`/`gd_frete`/`db`/`5432` | Sim, se usando o Postgres do compose | Credenciais do container de banco |

Ver a validação automática de segurança em produção em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#6-segurança--controles-ativos).
