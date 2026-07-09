# 10 · Roadmap e Débitos Técnicos

> Consolida a avaliação de roadmap de `archive/08_auditoria_arquitetural.md` (histórica, sobre a v2.0.0) com o estado real observado em 2026-07-07. As notas percentuais de prontidão abaixo **não foram remedidas nesta auditoria** — são citadas como referência histórica e sinalizadas onde já sabemos que mudaram.
>
> Priorização deste roadmap: ver [`00_contexto_oficial.md`](00_contexto_oficial.md) (Seção 9 — Estratégia de Evolução) e [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) (Seções 8-9 — ordem ideal de implementação e roadmap de 24 meses).

## Estado atual por fase de roadmap

| Fase | O que é | Status |
|---|---|---|
| MVP / V1 | Diagnóstico básico de custos | ✅ Implementado |
| V2 | Benchmark regional (legado) | ✅ Implementado |
| V2.1 | Benchmark por Corredor OD / Hubs | ✅ Implementado |
| V3 (BID) | Concorrência Logística / BID de Frete | ✅ Implementado |
| V3.x | MCL — Motor de Decisão de BID | ✅ Implementado |
| V4 (IA) | Inteligência Logística com IA | ✅ Implementado (modo simulado por padrão) |
| v6.x | DLG, MBL, Recomendações, cancelamento de CT-e | ✅ Implementado |
| v6.5.x | Segurança: isolamento multi-tenant reforçado, RBAC VISUALIZADOR, cookies httpOnly | ✅ Implementado (auditoria de 2026-07-07, ver [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md)) |
| v6.7.0 | Dimensão Cliente no DLG (5ª dimensão, diagnóstico causal de adicionais/fragmentação) | ✅ Implementado (ver [`11_changelog.md`](11_changelog.md) [6.7.0]) |
| **V5** | Benchmark Coletivo Anonimizado entre clientes (k-anonimato, consentimento LGPD) | ❌ **Não implementado** |
| **V6** | Inteligência de Mercado Logístico (fontes externas: ANTT, IBGE, câmbio, combustível; API pública) | ❌ **Não implementado** |

A avaliação de prontidão original (auditoria v2.0.0) estimava V3 em 60% e V4 em 28% de prontidão — **ambos os módulos já foram concluídos** desde então, tornando essas notas obsoletas. Não há uma reavaliação formal de V5/V6 pós-implementação de V3/V4; recomenda-se refazer essa análise antes de iniciar qualquer um dos dois, dado que a arquitetura mudou substancialmente desde a avaliação original.

## Débitos técnicos conhecidos (consolidado de `09_relatorio_implementacao_v3` + achados desta auditoria)

| # | Débito | Prioridade | Status |
|---|---|---|---|
| DT-01 | JWT em `localStorage` (risco de XSS) | Alta | ✅ **Resolvido em v6.5.1** — migrado para cookie `httpOnly` |
| DT-02 | Usuários sem `empresa_id` | Alta | ✅ Resolvido (migration `d7f2b8c3e9a1`) |
| DT-03 | Metas/benchmark legado sem `empresa_id` | Baixa | Decisão de design mantida — são cadastros globais intencionalmente (ver RN-60) |
| DT-04 | Composição de frete agregada em Python, não SQL | Média | Não revalidado nesta auditoria — recomenda-se checar `diagnostico.py` numa Fase 1 técnica |
| DT-05 | Sem refresh token | Alta | ✅ Resolvido desde v3.0.0 (access+refresh) |
| DT-06 | `repositories/__init__.py`, `schemas/__init__.py`, `dtos/__init__.py` monolíticos | Baixa/crescente | Ainda presente — não é urgente, mas vai doer se o número de módulos continuar crescendo |
| DT-07 | Sem testes de frontend (Vitest/Testing Library) | Média | Ainda presente |
| DT-08 | `BenchmarkUseCase` acessando métodos privados (`_indicador_nacional` etc.) de `DiagnosticoUseCase` | Baixa | Não revalidado nesta auditoria |
| DT-09 | Sem caching (Redis) para dashboard/benchmarks | Média | Parcialmente mitigado — Redis já está na infraestrutura (Celery), mas não confirmado uso para cache de dashboard |
| DT-10 | Relatórios gerados de forma síncrona (bloqueiam o worker HTTP) | Média | Não revalidado — Celery já existe na stack para outras finalidades, poderia ser reaproveitado |
| DT-11 | Swagger "desabilitado" em produção, mas não removido do build | Baixa | Comportamento mantido (é o padrão adequado — `docs_url=None` quando `ENVIRONMENT=production`) |
| DT-12 | Sem observabilidade (Sentry/OpenTelemetry) | Média | Ainda presente |
| DT-13 | Sem ADRs (Architecture Decision Records) | Baixa | Ainda presente — esta documentação (Fase 0) é um primeiro passo nessa direção |
| DT-14 | Migrations Alembic ausentes para tabelas de IA e para as mudanças de segurança v6.5.x | Média | **Novo achado desta auditoria** — ver [`04_modelo_de_dados.md`](04_modelo_de_dados.md#migrations) |
| DT-15 | Frontend não esconde ações de escrita para o papel VISUALIZADOR (backend já bloqueia com 403) | Baixa | **Novo achado desta auditoria** |
| DT-16 | Sem token CSRF (double-submit) complementar ao `SameSite=Lax` | Baixa | **Novo achado desta auditoria** — `SameSite=Lax` já cobre a maior parte do risco prático |
| DT-17 | `docker-compose.prod.yml` não inclui Redis/Celery — módulo de IA em produção exige adição manual | Média | **Novo achado desta auditoria** |
| DT-18 | Migração de React Query parcial — várias páginas mais antigas ainda usam `useState`/`useEffect` com chamada direta à API em vez dos hooks de `queries.js` | Baixa | Observado nesta auditoria |

## Débitos funcionais (Fase 7 — Auditoria Funcional e Regras de Negócio)

> Relatório completo em [`20_fase7_auditoria_funcional.md`](20_fase7_auditoria_funcional.md). Validou RN-01 a RN-57 contra o código real: as fórmulas batem quase integralmente com a documentação; o risco concentrado está na consistência de dados entre módulos analíticos e no motor de decisão de BID.

| # | Débito | Prioridade | Módulo(s) |
|---|---|---|---|
| DT-19 | **CONS-01** — RN-09 (excluir CT-e cancelado dos totais) não é propagada a ~8 módulos analíticos (Benchmark legado/OD/V2, Indicadores Regionais, Score Logístico, Insights, Oportunidades, MBL, Diagnóstico IA) | **Alta** | ✅ **Resolvido em v6.6.0** — filtro `status=ATIVO` (constante `CTE_STATUS_ATIVO`) propagado aos 9 módulos do achado original + Benchmark Setorial (achado adicional, mesma causa raiz). Débito residual do escopo de BID/MCL rastreado em DT-22/DT-23. |
| DT-20 | Deduplicação de CT-e por chave é global entre empresas, não isolada por tenant (IMP-01) | Alta | Importação |
| DT-21 | Chave sintética de dedup do Excel depende da posição da linha, não do conteúdo (IMP-02) | Alta | Importação |
| DT-22 | Referência MBL do motor MCL é média nacional, desconectada do segmento real do BID (MCL-02); decisão MCL sem trava de ciclo de vida do BID (MCL-03); dupla contagem de peso/frete com múltiplos agrupamentos de escopo (MCL-04/BID-07) | Alta | MCL, BID |
| DT-23 | Escopo do BID sem filtro de CT-e ativo (BID-01); escopo/propostas/decisão editáveis após BID `ENCERRADO`/`CANCELADO` (BID-04) | Alta | BID |
| DT-24 | `eval()` "restrito" das regras de Insights não é sandbox segura — risco latente de RCE se regras se tornarem editáveis (IA-01); duas fórmulas divergentes de "economia potencial anualizada" entre módulos de IA (IA-02) | Alta (latente) / Média | Inteligência IA |
| DT-25 | Fórmula de agregação regional reimplementada de forma independente em ≥4 módulos, sem serviço único (CONS-02/03) | Média | Indicadores, Benchmark |
| DT-26 | "OTIF" (RN-11) não é OTIF real (sem data prometida por CT-e) e trata prazo negativo de forma diferente entre Diagnóstico e Indicadores V2 (DIAG-01) | Média | Diagnóstico |
| DT-27 | CT-e importados antes da v6.7.0 não têm `destinatario_cnpj`/`nome` nem a granularização de TDE/TDA/Estadia em `composicao_frete` — não há reprocessamento automático nem correção via reimportação (bloqueada por RN-02) | ✅ **Resolvido (2026-07-08)** — script `backend/scripts/backfill_destinatario_v670.py` relê os XML originais e atualiza o CT-e existente por chave (nunca cria registro novo, nunca altera dado financeiro); idempotente; testado em `test_v670_dimensao_cliente.py`. Continua sendo uma ação manual (o operador precisa ter os XML originais e rodar o script), não um reprocessamento automático — ver [`09_manutencao.md`](09_manutencao.md#scripts-de-manutenção) |

## Recomendações estratégicas (mantidas da auditoria original, ainda válidas)

1. **A fundação está certa — não reconstruir, evoluir.** Clean Architecture corretamente aplicada é um ativo raro; a estrutura suportou 5 gerações de módulo (MVP → Benchmark → BID → IA → v6.x) sem reescrita.
2. **Antes de V5 (Benchmark Coletivo)**: resolver primeiro a arquitetura legal (consentimento LGPD, anonimização) — é o gargalo real, não o técnico.
3. **Antes de V6 (Inteligência de Mercado)**: é o módulo mais distante da realidade atual; exige fontes de dados externas e arquitetura de pipeline que não existem hoje.
4. **Gerar as migrations Alembic faltantes (DT-14)** antes de qualquer deploy de produção que dependa exclusivamente de `alembic upgrade head`.
5. **Fechar DT-15/DT-16** é trabalho pequeno e complementa a auditoria de segurança de 2026-07-07.

## Próximo passo recomendado

Uma **Fase 1 — Auditoria Técnica** revalidando pontualmente os débitos marcados "não revalidado nesta auditoria" acima (DT-04, DT-06, DT-08, DT-09, DT-10), já que a auditoria arquitetural original (`archive/08_auditoria_arquitetural.md`) audita uma versão de código (v2.0.0) com uma fração pequena dos endpoints/tabelas de hoje — seus números de linha específicos não são mais confiáveis.
