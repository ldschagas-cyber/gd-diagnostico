# GD Diagnóstico Logístico — Backend (API)

API REST do **GD Diagnóstico Logístico**, construída em **FastAPI** com **Clean Architecture** (domínio → aplicação → infraestrutura → apresentação). Versão atual: **6.5.1**.

> Este README cobre o essencial para rodar e navegar o backend localmente. A documentação completa e oficial do projeto (especificação funcional, arquitetura, modelo de dados, catálogo de API, regras de negócio, deploy) está em [`../docs/00_README.md`](../docs/00_README.md) — comece por lá para qualquer coisa além do dia a dia de desenvolvimento.

## Stack

- Python 3.12+, FastAPI, Uvicorn
- SQLAlchemy 2.0 (síncrono) + Alembic (migrações)
- **Banco de dados**: PostgreSQL 16 em produção (com extensão `pgvector` para IA); SQLite disponível para desenvolvimento local sem Docker
- Autenticação JWT via **cookie `httpOnly`** (`python-jose` + `bcrypt` puro, sem passlib — compatibilidade com Python 3.14+)
- Celery + Redis (processamento assíncrono do módulo de IA)
- OpenPyXL / ReportLab / python-docx / python-pptx (relatórios Excel, PDF, Word, PowerPoint)
- Pydantic v2 / pydantic-settings

## Arquitetura (camadas)

```
app/
├── domain/            # Entidades puras (dataclasses) e interfaces de repositório (ports)
├── application/       # Casos de uso (regras de negócio) — 25 arquivos
├── infrastructure/    # ORM, repositórios concretos, parsers XML/Excel, IA, relatórios, Celery
└── presentation/      # API FastAPI: 19 routers / 148 endpoints, schemas Pydantic, DI
```

A regra de dependência aponta sempre para dentro: a apresentação depende da aplicação, que depende do domínio; a infraestrutura implementa as interfaces do domínio. Isso manteve o núcleo de negócio testável e independente de framework mesmo depois de 5 gerações de módulos adicionados por cima (Benchmark → BID → IA → DLG/MBL/MCL) sem reescrita.

Detalhamento completo em [`../docs/03_arquitetura_tecnica.md`](../docs/03_arquitetura_tecnica.md).

## Como executar localmente (sem Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# ajuste SECRET_KEY; DATABASE_URL pode ficar como sqlite:///./gd_frete.db para dev local
uvicorn app.main:app --reload
```

Na primeira execução, as tabelas são criadas automaticamente e o **seed** cria:

- Usuário administrador: `admin@gdconecta.com.br` / senha definida em `FIRST_SUPERUSER_PASSWORD` (default de código: `admin123`)
- Meta nacional (zerada), 5 metas regionais, benchmarks regionais de referência, 5 hubs logísticos padrão

> Em qualquer ambiente que não seja seu próprio laptop de desenvolvimento, troque a senha do administrador e a `SECRET_KEY` — o boot da aplicação **recusa subir em produção** (`ENVIRONMENT=production`) com valores padrão/fracos.

Para o módulo de Inteligência IA (Redis + Celery) e para deploy em produção, ver [`../docs/08_instalacao_deploy.md`](../docs/08_instalacao_deploy.md).

### Documentação interativa

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

(Ambas desabilitadas automaticamente quando `ENVIRONMENT=production`.)

## Migrações (Alembic)

```bash
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

`alembic/env.py` lê `DATABASE_URL` das configurações da aplicação — a mesma sequência de migrações funciona para SQLite e PostgreSQL. Lista completa das 10 migrations existentes em [`../docs/04_modelo_de_dados.md`](../docs/04_modelo_de_dados.md#migrations).

> Nem toda tabela do schema atual tem uma migration correspondente neste diretório (algumas foram criadas via `create_all` automático em desenvolvimento) — ver a nota de rastreabilidade no link acima antes de assumir que `alembic upgrade head` sozinho recria o schema inteiro em um banco novo de produção.

## Testes

```bash
# cada arquivo isoladamente — há um conflito conhecido de DATABASE_URL
# compartilhado quando múltiplos arquivos de teste rodam no mesmo processo pytest
for f in tests/test_*.py; do python -m pytest "$f" -q; done
```

**68 casos de teste em 7 arquivos**, cobrindo: fluxos de fumaça (auth, importação, dashboard, relatórios), módulo BID completo, módulo de Inteligência IA, cancelamento de CT-e e recomendações, isolamento multi-tenant e RBAC, e o ciclo de autenticação via cookie `httpOnly`. Detalhamento por arquivo em [`../docs/09_manutencao.md`](../docs/09_manutencao.md).

## Endpoints

**148 endpoints em 19 routers.** Catálogo completo, com o requisito de autorização de cada rota, em [`../docs/05_apis.md`](../docs/05_apis.md). Visão rápida dos módulos principais:

| Módulo | Prefixo | Endpoints |
|---|---|---|
| Autenticação | `/auth` | 4 |
| Usuários / Empresas / Filiais / Transportadoras | `/usuarios`, `/empresas`, `/transportadoras` | 18 |
| Regiões / Cidades / Metas / Benchmarks (legado) | `/regioes`, `/cidades`, `/metas`, `/benchmarks` | 17 |
| Benchmark OD / V2 (hubs, clusters, corredores, matriz de mercado) | `/benchmark/*`, `/hubs`, `/benchmark-v2` | 27 |
| Importação (CT-e, Excel, cancelamento) | `/importacao` | 8 |
| Dashboard / Relatórios | `/dashboard`, `/relatorios` | 6 |
| Concorrência Logística (BID) + MCL | `/bid`, `/mcl` | 31 |
| DLG / MBL / Recomendações | `/dlg`, `/mbl`, `/recomendacoes` | 11 |
| Inteligência Logística com IA | `/inteligencia` | 26 |

## Regras de negócio (resumo)

- **Vínculo CT-e × empresa**: um CT-e só é importado se o tomador for a matriz ou uma filial cadastrada da empresa; CT-es sem vínculo são ignorados.
- **Deduplicação**: a chave de 44 dígitos do CT-e evita reimportação (dentro do lote e contra o banco).
- **Limites de importação**: até 500 arquivos XML por lote / 10 MB por arquivo, 20 MB por planilha Excel (segurança); `MAX_CTE_BATCH=10000` é um limite lógico separado, configurável.
- **Multi-tenant**: toda entidade operacional (CT-e, transportadora, BID e seus artefatos, DLG/MBL/MCL, insights/score/oportunidades de IA) é isolada por `empresa_id`; regiões, cidades, metas e benchmarks de referência são cadastros globais da plataforma por decisão de design.
- **RBAC**: papéis ADMIN (administra a própria empresa), ANALISTA (leitura+escrita operacional) e VISUALIZADOR (somente leitura, bloqueado em toda escrita).

Catálogo completo de regras (fórmulas, pesos, limiares, classificações), com código estável `RN-xx` para referência, em [`../docs/06_regras_de_negocio.md`](../docs/06_regras_de_negocio.md).
