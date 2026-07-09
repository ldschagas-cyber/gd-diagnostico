# Arquitetura Técnica — GD Frete Diagnóstico
**Versão:** 2.0.0 · **Data:** Junho 2026 · **GD Conecta**

---

## 1. Visão Geral

O sistema segue **Clean Architecture** com separação rígida entre domínio, aplicação, infraestrutura e apresentação. A comunicação entre camadas respeita a regra de dependência: camadas externas dependem das internas, nunca o contrário.

```
┌─────────────────────────────────────────────────────────┐
│  APRESENTAÇÃO (FastAPI Routers + Pydantic Schemas)       │
├─────────────────────────────────────────────────────────┤
│  APLICAÇÃO (Use Cases + DTOs)                            │
├─────────────────────────────────────────────────────────┤
│  DOMÍNIO (Entities + Repository Interfaces/Ports)        │
├─────────────────────────────────────────────────────────┤
│  INFRAESTRUTURA (ORM Models + Repositories + Parsers)    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológica

### Backend
| Componente | Tecnologia | Versão |
|---|---|---|
| Framework API | FastAPI | ≥ 0.115 |
| Runtime Python | CPython | 3.12+ |
| ORM | SQLAlchemy | ≥ 2.0 (síncrono) |
| Migrations | Alembic | ≥ 1.14 |
| Validação | Pydantic v2 | ≥ 2.10 |
| Autenticação | JWT (python-jose) | ≥ 3.3 |
| Criptografia | bcrypt | ≥ 4.2 |
| Banco DEV | SQLite | — |
| Banco PROD | PostgreSQL | 16 |
| Relatórios Excel | OpenPyXL | ≥ 3.1 |
| Relatórios PDF | ReportLab | ≥ 4.2 |
| Servidor WSGI | Uvicorn | ≥ 0.34 |

### Frontend
| Componente | Tecnologia | Versão |
|---|---|---|
| Framework UI | React | 18 |
| Build Tool | Vite | 6 |
| Componentes | Material UI (MUI) | 6 |
| Gráficos | Recharts | — |
| HTTP Client | Axios | — |
| Roteamento | react-router-dom | — |

### Infraestrutura
| Componente | Tecnologia |
|---|---|
| Containerização | Docker + Docker Compose |
| Servidor Web / Proxy | Nginx (Alpine) |
| Banco de Dados | PostgreSQL 16 |

---

## 3. Estrutura de Pastas

```
gd-frete-diagnostico/
├── backend/
│   ├── app/
│   │   ├── core/                    # Configurações e utilitários centrais
│   │   │   ├── config.py            # Settings (Pydantic BaseSettings)
│   │   │   ├── database.py          # Engine + SessionLocal + Base ORM
│   │   │   ├── security.py          # Hash de senhas (bcrypt)
│   │   │   └── logging_config.py
│   │   ├── domain/                  # Camada de domínio — sem dependências externas
│   │   │   ├── entities/            # Dataclasses de domínio puras
│   │   │   └── repositories/        # Interfaces (ABC) dos repositórios
│   │   ├── application/             # Casos de uso e DTOs
│   │   │   ├── use_cases/
│   │   │   │   ├── auth.py
│   │   │   │   ├── diagnostico.py   # RF011-RF014 (indicadores)
│   │   │   │   ├── importacao.py    # RF009-RF010 (importação CT-e/Excel)
│   │   │   │   └── benchmark.py     # Módulo Benchmark Logístico
│   │   │   └── dtos/                # Data Transfer Objects
│   │   ├── infrastructure/          # Implementações concretas
│   │   │   ├── database/
│   │   │   │   ├── models/          # ORM SQLAlchemy
│   │   │   │   └── repositories/    # Implementações dos repositórios
│   │   │   ├── parsers/
│   │   │   │   ├── cte_parser.py    # Parser XML CT-e v3.00
│   │   │   │   ├── excel_parser.py  # Parser planilha TMS
│   │   │   │   └── macro_regiao.py  # Mapeamento UF → macro-região
│   │   │   ├── reports/
│   │   │   │   ├── excel_report.py  # Relatório diagnóstico Excel
│   │   │   │   ├── pdf_report.py    # Relatório diagnóstico PDF
│   │   │   │   └── benchmark_report.py # Relatório benchmark PDF+Excel
│   │   │   └── security/            # Segurança infra
│   │   └── presentation/            # Camada de API (FastAPI)
│   │       ├── api/
│   │       │   ├── dependencies.py  # DI: get_db, repos, autenticação
│   │       │   └── v1/              # Routers versionados
│   │       │       ├── auth.py
│   │       │       ├── empresas.py
│   │       │       ├── filiais.py (via empresas)
│   │       │       ├── transportadoras.py
│   │       │       ├── regioes.py
│   │       │       ├── usuarios.py
│   │       │       ├── metas.py
│   │       │       ├── benchmarks.py
│   │       │       ├── benchmark_analise.py
│   │       │       ├── importacao.py
│   │       │       ├── dashboard.py
│   │       │       └── relatorios.py
│   │       └── schemas/             # Pydantic response/request schemas
│   ├── alembic/                     # Migrations de banco
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   └── test_smoke.py
│   ├── migrate_sqlite_to_pg.py      # Script de migração de dados
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── .env.dev
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.js            # Instância Axios + interceptors
│   │   │   └── endpoints.js         # Funções de API por domínio
│   │   ├── components/              # Componentes reutilizáveis
│   │   ├── contexts/                # AuthContext, EmpresaContext
│   │   ├── layouts/                 # AppLayout (sidebar + header)
│   │   ├── pages/                   # Páginas (1 por rota)
│   │   ├── theme/                   # Paleta GD Conecta + tema MUI
│   │   └── utils/                   # Formatadores, helpers benchmark
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docs/                            # Documentação do projeto
├── docker-compose.dev.yml
├── docker-compose.prod.yml
└── .gitignore
```

---

## 4. Backend — Fluxo de Requisição

```
HTTP Request
    │
    ▼
FastAPI Router (presentation/api/v1/)
    │  ← Pydantic valida entrada
    │  ← Depends() injeta: sessão DB, repositórios, usuário autenticado
    ▼
Use Case (application/use_cases/)
    │  ← Recebe entidades de domínio via repositórios
    │  ← Executa regras de negócio
    │  ← Retorna DTOs
    ▼
Repository Interface (domain/repositories/)
    │
    ▼
Repository Implementation (infrastructure/database/repositories/)
    │  ← SQLAlchemy ORM
    │  ← Mapeia ORM Model → Domain Entity
    ▼
PostgreSQL / SQLite
```

---

## 5. Injeção de Dependências

O FastAPI usa o padrão `Depends()`. Todas as dependências estão em `presentation/api/dependencies.py`:

```python
get_db()                  # sessão de banco por requisição
get_current_user()        # JWT → User entity
get_current_superuser()   # apenas admin
get_empresa_repo()        # EmpresaRepository
get_cte_repo()            # CTeRepository
get_benchmark_repo()      # BenchmarkRepository
# ... demais repositórios
```

---

## 6. Frontend — Arquitetura

### Contextos React
- **AuthContext:** mantém o usuário autenticado, token JWT e função de logout. Token salvo no `localStorage`.
- **EmpresaContext:** mantém a empresa ativa selecionada (selector no header). Persiste `empresa_id` no `localStorage`. Todas as telas de análise dependem deste contexto.

### API Client
- `client.js`: instância Axios com `baseURL=/api/v1`, interceptor de token (Bearer) e interceptor de erro (401 → logout, erro → mensagem amigável).
- `endpoints.js`: funções agrupadas por domínio (`empresasApi`, `benchmarkApi`, `relatoriosApi`, etc.).

### Paleta GD Conecta
```
Indigo    #2D3561   (primária, menu, títulos)
Amber     #C9A84C   (acentuação, linhas de benchmark)
Blue      #0077A8   (informações, gráficos)
Ivory     #F5F1EB   (fundo alternativo tabelas)
```
Fontes: **Sora** (títulos), **Inter** (corpo).

---

## 7. Banco de Dados

### Modelos ORM e Relacionamentos

```
empresas (1) ──── (N) filiais
empresas (1) ──── (N) ctes
ctes     (1) ──── (N) nfes
ctes     (N) ──── (1) transportadoras
```

### Tabelas Globais (sem empresa_id)
- `users`, `transportadoras`, `regioes`, `cidades`
- `meta_nacional`, `meta_regional`, `benchmarks`

### Isolamento Multi-tenant
O isolamento é garantido por `empresa_id` nas tabelas operacionais (`ctes`, `filiais`). Todos os repositórios operacionais filtram por `empresa_id` na consulta. Transportadoras e configurações (metas/benchmarks) são globais por decisão de design MVP.

---

## 8. Segurança

- **Autenticação:** JWT (HS256). Token válido por 8 horas (configurável).
- **Autorização:** Decorador `get_current_superuser` em endpoints admin. Endpoints de leitura requerem `get_current_user`.
- **Senhas:** bcrypt com salt automático (não usa passlib — compatibilidade Python 3.14).
- **Secrets:** Via variáveis de ambiente (`.env`). `SECRET_KEY` nunca hardcoded.
- **CORS:** Lista explícita de origens em `BACKEND_CORS_ORIGINS`.
- **Em produção:** DEBUG=false, SECRET_KEY forte (openssl rand -hex 32), HTTPS via Nginx.

---

## 9. Migrações Alembic

- Uma migration inicial: `faa05e1d23e5` — cria todas as tabelas.
- `render_as_batch=True` apenas para SQLite. PostgreSQL usa ALTER TABLE nativo.
- Comando de upgrade: `python -m alembic upgrade head`
- Para gerar nova migration: `python -m alembic revision --autogenerate -m "descricao"`

---

## 10. Relatórios

### PDF (ReportLab)
- Estilos `_estilos()`: GDTitulo (indigo), GDSub (blue), GDInfo (cinza).
- Tabelas `_tabela()`: cabeçalho indigo, linhas alternadas ivory.
- Helper `_br()`: formata float para padrão BR (vírgula decimal, ponto milhar).

### Excel (OpenPyXL)
- Múltiplas abas por tipo de relatório.
- Cabeçalho com fundo indigo, fonte branca bold.
- Auto-fit de colunas (`_autofit()`).
- Paleta exportada como constantes: `INDIGO="2D3561"`, `AMBER="C9A84C"`, etc.
