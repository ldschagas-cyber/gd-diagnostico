# 09 · Guia de Manutenção

> Substitui `archive/06_guia_manutencao.md`, com os números de teste e comandos corrigidos.

## Testes automatizados

**8 arquivos, 101 casos de teste no total.** A maioria autentica como `admin@gdconecta.com.br`/`admin123` contra um SQLite temporário isolado (criado antes de importar `app.main`); `test_v670_dimensao_cliente.py` é independente disso — usa uma sessão SQLAlchemy isolada em memória, sem subir a aplicação FastAPI nem depender de login (ver nota abaixo).

| Arquivo | Casos | Cobertura |
|---|---|---|
| `test_smoke.py` | 11 | Fluxos principais: health check, login, seed de metas, importação+dashboard+relatórios, deduplicação, parsing de peso taxado, classificação de benchmark, validação de setor obrigatório |
| `test_bid_smoke.py` | 22 | Fluxo completo de BID: CRUD, máquina de estados, escopo, transportadoras, propostas, comparativo, economia, score, simulação, relatórios, auditoria, isolamento multi-empresa |
| `test_inteligencia_smoke.py` | 14 | Módulo IA em modo simulado: status, score, insights, diagnóstico, oportunidades, benchmark setorial, assistente, RAG, isolamento multi-empresa, relatório executivo |
| `test_melhorias_v64.py` | 6 | Cancelamento de CT-e, log de cancelamentos, recomendações |
| `test_v640_smoke.py` | 7 | Regressão v6.4.0: cancelamento, cards do dashboard, recomendações, dimensão FILIAL do DLG |
| `test_isolamento_v6_5_1.py` | 4 | Isolamento multi-tenant de BID/MCL/transportadoras/inteligência; bloqueio de escalonamento de privilégio entre empresas; enforcement de VISUALIZADOR; regressão de update de usuário sem senha |
| `test_cookie_auth_v6_5_1.py` | 4 | Cookies httpOnly: login grava cookies, chamada autenticada só com cookie, refresh via cookie, logout revoga acesso |
| `test_v670_dimensao_cliente.py` | 23 | Dimensão Cliente do DLG (v6.7.0): dedup RN-68, granularização de parser RN-73, composição/ranking RN-72/74, fragmentação RN-75, diagnóstico causal RN-76, recomendação causal RN-77, ferramenta de IA, backfill de destinatário/composição (DT-27), regressão das 4 dimensões existentes |

> **Nota de ambiente**: os arquivos que dependem de login via HTTP (todos exceto `test_v670_dimensao_cliente.py`) podem falhar com `401 Unauthorized` em alguns ambientes mesmo sem nenhuma mudança de código — reproduzido em 2026-07-08 rodando `test_bid_smoke.py` isolado e sem alterações. Antes de investigar uma regressão, confirme que o problema não é esse (rode um arquivo de smoke não relacionado à sua mudança e veja se ele também falha).

**Rodar os testes** — cada arquivo isoladamente (há um conflito conhecido de `DATABASE_URL` compartilhado quando múltiplos arquivos de teste rodam no mesmo processo pytest):

```bash
cd backend
for f in tests/test_*.py; do python -m pytest "$f" -q; done
```

## Ambiente local

Ver [`08_instalacao_deploy.md`](08_instalacao_deploy.md#1-ambiente-local-sem-docker) para o passo-a-passo completo (sem Docker e com Docker).

## Migrations

```bash
cd backend
alembic revision -m "descricao_da_mudanca"   # gera novo arquivo em alembic/versions/
alembic upgrade head                          # aplica migrations pendentes
alembic downgrade -1                          # reverte a última
```

Ver a lista cronológica completa em [`04_modelo_de_dados.md`](04_modelo_de_dados.md#migrations).

## Scripts de manutenção

### Backfill de destinatário/composição (v6.7.0, DT-27)

CT-e importados **antes** do deploy da v6.7.0 não têm `destinatario_cnpj`/`destinatario_nome` (aparecem como "Cliente não identificado" na dimensão Cliente do DLG) nem a categorização granular de TDE/TDA/Estadia em `composicao_frete` (ficam agrupados em "Outros") — esses campos só são escritos pelo parser no momento da importação, e reimportar o mesmo XML é bloqueado como duplicado (RN-02) sem atualizar o registro existente.

`backend/scripts/backfill_destinatario_v670.py` corrige isso relendo os **XML originais** já importados e atualizando o CT-e existente por chave (nunca cria registro novo, nunca altera peso/valor_frete/valor_mercadoria):

```bash
cd backend
python scripts/backfill_destinatario_v670.py --empresa-id 1 --dir ./xmls_originais
# ou, para arquivos avulsos:
python scripts/backfill_destinatario_v670.py --empresa-id 1 arquivo1.xml arquivo2.xml
```

Idempotente (pode rodar mais de uma vez sobre os mesmos arquivos). Depois de rodar, dispare `POST /dlg/{empresa_id}/processar` (botão "Processar diagnóstico") para o DLG recalcular a dimensão Cliente com o dado corrigido. Cobertura de teste em `backend/tests/test_v670_dimensao_cliente.py` (atualização, isolamento multi-tenant, idempotência, fim a fim com reprocessamento).

## Criar um novo módulo (Clean Architecture)

1. **Entidade de domínio** — dataclass em `app/domain/entities/__init__.py`, sem dependência de ORM.
2. **Interface de repositório** — ABC em `app/domain/repositories/__init__.py`.
3. **Modelo ORM** — classe SQLAlchemy em `app/infrastructure/database/models/__init__.py`.
4. **Migration** — `alembic revision` para a(s) tabela(s) nova(s).
5. **Repositório concreto** — implementação da interface em `app/infrastructure/database/repositories/__init__.py`, com mapeamento entidade↔modelo.
6. **Use case** — regra de negócio pura em `app/application/use_cases/`, recebendo repositórios via construtor.
7. **Router + schemas + dependencies** — endpoint FastAPI em `app/presentation/api/v1/`, schemas Pydantic em `app/presentation/schemas/`, registrado em `app/presentation/api/v1/__init__.py`.

Ao criar um endpoint novo escopado por empresa, use `verificar_acesso_empresa` (ou `get_bid_com_acesso`/`get_transportadora_com_acesso` para sub-recursos) — **nunca confie em um `empresa_id` de query/body sem validar contra o usuário logado**. Para qualquer endpoint de escrita que não seja já admin-only, adicione `bloquear_visualizador`. Ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#5-autenticação-e-autorização) e o histórico de por que isso importa em [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md).

## Convenções de código

- **Backend**: nomenclatura de domínio em português (`Empresa`, `Transportadora`, `gerar_escopo`); docstrings em funções públicas explicando o "porquê", não o "o quê"; use cases não importam FastAPI nem SQLAlchemy diretamente.
- **Frontend**: componentes de página em `src/pages/`, hooks de dados em `src/api/queries.js` (React Query) quando possível — nota: várias páginas mais antigas ainda usam `useState`/`useEffect` com chamada direta a `endpoints.js` em vez de React Query; a migração é parcial (ver [`10_roadmap.md`](10_roadmap.md)).

## Comandos úteis de diagnóstico

```bash
# Ver tabelas do banco (Postgres)
docker compose -f docker-compose.dev.yml exec db psql -U gd_user -d gd_frete -c '\dt'

# Ver logs do backend
docker compose -f docker-compose.dev.yml logs -f backend

# Recriar containers do zero (preserva volumes/dados)
docker compose -f docker-compose.dev.yml down && docker compose -f docker-compose.dev.yml up --build -d
```

## Referência rápida de variáveis de ambiente

Ver tabela completa em [`08_instalacao_deploy.md`](08_instalacao_deploy.md#5-variáveis-de-ambiente-referência-completa).
