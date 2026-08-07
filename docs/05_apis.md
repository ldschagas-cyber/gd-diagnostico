# 05 · Catálogo de APIs

> Substitui `archive/04_catalogo_apis.md` (que cobria uma fração pequena dos endpoints reais). Base URL: `/api/v1`. Fonte: os 19 arquivos de `app/presentation/api/v1/`, auditados em 2026-07-07. **Total: 148 endpoints.**

## Convenções

- **Autenticação**: cookie `httpOnly` (fluxo do navegador) ou header `Authorization: Bearer` (fluxo de API/scripts) — ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#5-autenticação-e-autorização).
- Coluna **Auth** lista a(s) dependency(ies) de autorização aplicada(s), além da autenticação básica.
- `verificar_acesso_empresa` = exige que `empresa_id` (path ou query) pertença ao usuário logado.
- `bloquear_visualizador` = papel VISUALIZADOR recebe 403 nesse endpoint.
- `get_bid_com_acesso` / `get_transportadora_com_acesso` = carregam o recurso pelo ID do path e já validam a empresa dona dele.

## 1. `auth.py` — `/auth` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/auth/login` | Login (OAuth2 password flow, `username`=e-mail); rate limit 10/min/IP; grava cookies httpOnly | — |
| POST | `/auth/refresh` | Novo access token a partir do refresh (cookie ou body); rate limit 30/min | — |
| POST | `/auth/logout` | Limpa os cookies de autenticação | — |
| GET | `/auth/me` | Usuário autenticado atual | `get_current_user` |

## 2. `usuarios.py` — `/usuarios` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/usuarios` | Lista usuários (admin global: todos; ADMIN de empresa: só a própria) | `get_current_superuser` |
| POST | `/usuarios` | Cria usuário | `get_current_superuser` |
| PUT | `/usuarios/{user_id}` | Atualiza usuário (bloqueia escalonamento de privilégio entre empresas) | `get_current_superuser` |
| DELETE | `/usuarios/{user_id}` | Remove usuário | `get_current_superuser` |

## 3. `empresas.py` — `/empresas` (9 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/empresas` | Lista empresas visíveis ao usuário | `get_current_user` |
| GET | `/empresas/{empresa_id}` | Obtém uma empresa | `verificar_acesso_empresa` |
| POST | `/empresas` | Cria empresa | `require_admin` |
| PUT | `/empresas/{empresa_id}` | Atualiza empresa | `verificar_acesso_empresa` + `bloquear_visualizador` |
| DELETE | `/empresas/{empresa_id}` | Inativação lógica | `require_admin` |
| GET | `/empresas/{empresa_id}/filiais` | Lista filiais | `verificar_acesso_empresa` |
| POST | `/empresas/{empresa_id}/filiais` | Cria filial | `verificar_acesso_empresa` + `bloquear_visualizador` |
| PUT | `/empresas/filiais/{filial_id}` | Atualiza filial | `bloquear_visualizador` |
| DELETE | `/empresas/filiais/{filial_id}` | Remove filial | `bloquear_visualizador` |

## 4. `transportadoras.py` — `/transportadoras` (5 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/transportadoras` | Lista transportadoras de uma empresa (`empresa_id` obrigatório) | `verificar_acesso_empresa` |
| GET | `/transportadoras/{tid}` | Obtém uma transportadora | `get_transportadora_com_acesso` |
| POST | `/transportadoras` | Cria transportadora (CNPJ único por empresa) | `verificar_acesso_empresa` + `bloquear_visualizador` |
| PUT | `/transportadoras/{tid}` | Atualiza transportadora | `get_transportadora_com_acesso` + `bloquear_visualizador` |
| DELETE | `/transportadoras/{tid}` | Remove transportadora | `get_transportadora_com_acesso` + `bloquear_visualizador` |

## 5. `regioes.py` — sem prefixo próprio (11 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/regioes` | Lista regiões logísticas | `get_current_user` |
| POST | `/regioes` | Cria região | `bloquear_visualizador` |
| PUT | `/regioes/{rid}` | Atualiza região | `bloquear_visualizador` |
| DELETE | `/regioes/{rid}` | Remove região | `bloquear_visualizador` |
| POST | `/regioes/importar-csv` | Importa regiões via CSV | `bloquear_visualizador` |
| GET | `/cidades` | Lista cidades | `get_current_user` |
| POST | `/cidades` | Cria cidade | `bloquear_visualizador` |
| PUT | `/cidades/{cid}` | Atualiza cidade | `bloquear_visualizador` |
| DELETE | `/cidades/{cid}` | Remove cidade | `bloquear_visualizador` |
| GET | `/cidades/modelo` | Baixa planilha-modelo de importação | `get_current_user` |
| POST | `/cidades/importar` | Importa cidades via Excel | `bloquear_visualizador` |

## 6. `metas.py` — `/metas` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/metas/nacional` | Obtém meta nacional | `get_current_user` |
| PUT | `/metas/nacional` | Upsert de meta nacional | `get_current_superuser` |
| GET | `/metas/regionais` | Lista metas regionais | `get_current_user` |
| PUT | `/metas/regionais` | Upsert de meta regional | `get_current_superuser` |

## 7. `benchmarks.py` — `/benchmarks` (2 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/benchmarks` | Lista benchmarks (todas as regiões + nacional) | `get_current_user` |
| PUT | `/benchmarks/{regiao}` | Upsert de benchmark de uma região | `get_current_superuser` |

## 8. `benchmark_analise.py` — `/benchmark` (6 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/benchmark/nacional/{empresa_id}` | Comparação com benchmark nacional | `verificar_acesso_empresa` |
| GET | `/benchmark/regional/{empresa_id}` | Comparação por macrorregião | `verificar_acesso_empresa` |
| GET | `/benchmark/transportadoras/{empresa_id}` | Ranking por transportadora | `verificar_acesso_empresa` |
| GET | `/benchmark/economia/{empresa_id}` | Potencial de economia + projeções | `verificar_acesso_empresa` |
| GET | `/benchmark/executivo/{empresa_id}` | Dashboard executivo consolidado | `verificar_acesso_empresa` |
| GET | `/benchmark/corredores/{empresa_id}` | Benchmark por corredor Hub OD | `verificar_acesso_empresa` |

## 9. `benchmark_od_config.py` — 3 sub-rotas (13 endpoints)

**Hubs** (`/hubs` — catálogo global):

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/hubs` | Lista hubs logísticos | `get_current_user` |
| POST | `/hubs` | Cria hub | `get_current_superuser` |
| PUT | `/hubs/{hub_id}` | Atualiza hub | `get_current_superuser` |
| DELETE | `/hubs/{hub_id}` | Remove hub | `get_current_superuser` |

**Clusters** (`/empresas/{empresa_id}/clusters`):

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/empresas/{empresa_id}/clusters` | Lista clusters da empresa | `verificar_acesso_empresa` |
| POST | `/empresas/{empresa_id}/clusters` | Cria cluster | `verificar_acesso_empresa` |
| GET | `/empresas/{empresa_id}/clusters/modelo` | Baixa modelo de importação | `verificar_acesso_empresa` |
| POST | `/empresas/{empresa_id}/clusters/importar` | Importa clusters via Excel | `verificar_acesso_empresa` |
| PUT | `/empresas/{empresa_id}/clusters/{cluster_id}` | Atualiza cluster | `verificar_acesso_empresa` |
| DELETE | `/empresas/{empresa_id}/clusters/{cluster_id}` | Remove cluster | `verificar_acesso_empresa` |

**Referências de corredor** (`/benchmarks-corredor` — global):

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/benchmarks-corredor` | Lista referências de corredor | `get_current_user` |
| PUT | `/benchmarks-corredor` | Upsert de referência | `get_current_superuser` |
| DELETE | `/benchmarks-corredor/{corredor_id}` | Remove referência | `get_current_superuser` |

## 10. `benchmark_v2_api.py` — `/benchmark-v2` (8 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/benchmark-v2/observado/gerar` | (Re)gera benchmark observado a partir dos CT-e | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/benchmark-v2/observado` | Lista benchmark observado | `verificar_acesso_empresa` |
| GET | `/benchmark-v2/observado-vs-mercado` | Compara observado vs. mercado | `verificar_acesso_empresa` |
| GET | `/benchmark-v2/mercado` | Lista matriz de mercado | `get_current_user` |
| PUT | `/benchmark-v2/mercado` | Upsert de linha de mercado | `get_current_superuser` |
| DELETE | `/benchmark-v2/mercado/{mid}` | Remove linha de mercado | `get_current_superuser` |
| GET | `/benchmark-v2/indicadores-regionais` | Indicadores regionais derivados | `verificar_acesso_empresa` |
| GET | `/benchmark-v2/resolver` | Resolve referência cliente→mercado | `verificar_acesso_empresa` |

## 11. `bid.py` — `/bid` (27 endpoints — maior router do sistema)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/bid` | Lista BIDs da empresa | `verificar_acesso_empresa` |
| POST | `/bid` | Cria BID | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/bid/dashboard` | KPIs consolidados de todos os BIDs | `verificar_acesso_empresa` |
| GET | `/bid/{bid_id}` | Obtém um BID | `get_bid_com_acesso` |
| PUT | `/bid/{bid_id}` | Atualiza BID | `bloquear_visualizador` + `get_bid_com_acesso` |
| PATCH | `/bid/{bid_id}/status` | Altera status (máquina de estados) | `bloquear_visualizador` + `get_bid_com_acesso` |
| DELETE | `/bid/{bid_id}` | Deleta BID | `bloquear_visualizador` + `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/escopo/gerar` | Gera escopo via SQL GROUP BY | `get_bid_com_acesso` + `bloquear_visualizador` |
| GET | `/bid/{bid_id}/escopo` | Lista itens de escopo | `get_bid_com_acesso` |
| DELETE | `/bid/{bid_id}/escopo/{escopo_id}` | Remove item de escopo | `get_bid_com_acesso` + `bloquear_visualizador` |
| GET | `/bid/{bid_id}/transportadoras` | Lista transportadoras convidadas | `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/transportadoras` | Convida transportadora | `bloquear_visualizador` + `get_bid_com_acesso` |
| PUT | `/bid/{bid_id}/transportadoras/{bt_id}` | Atualiza participante | `get_bid_com_acesso` + `bloquear_visualizador` |
| PATCH | `/bid/{bid_id}/transportadoras/{bt_id}/status` | Altera status do participante | `bloquear_visualizador` + `get_bid_com_acesso` |
| DELETE | `/bid/{bid_id}/transportadoras/{bt_id}` | Remove participante | `get_bid_com_acesso` + `bloquear_visualizador` |
| GET | `/bid/{bid_id}/propostas` | Lista propostas | `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/propostas` | Inclui proposta manual | `bloquear_visualizador` + `get_bid_com_acesso` |
| GET | `/bid/{bid_id}/propostas/modelo` | Baixa modelo de propostas pré-preenchido | `get_current_user` + `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/propostas/importar` | Importa propostas via Excel | `bloquear_visualizador` + `get_bid_com_acesso` |
| DELETE | `/bid/{bid_id}/propostas/{pid}` | Remove proposta | `get_bid_com_acesso` + `bloquear_visualizador` |
| GET | `/bid/{bid_id}/comparativo` | Comparativo por grupo (+ referência de mercado) | `get_bid_com_acesso` |
| GET | `/bid/{bid_id}/economia` | Motor de economia | `get_bid_com_acesso` |
| GET | `/bid/{bid_id}/score` | Score das transportadoras | `get_bid_com_acesso` |
| GET | `/bid/{bid_id}/simulacoes` | Lista simulações salvas | `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/simulacoes/calcular` | Calcula cenário sem persistir | `get_bid_com_acesso` |
| POST | `/bid/{bid_id}/simulacoes` | Calcula e salva simulação | `bloquear_visualizador` + `get_bid_com_acesso` |
| DELETE | `/bid/{bid_id}/simulacoes/{sim_id}` | Remove simulação | `get_bid_com_acesso` + `bloquear_visualizador` |
| GET | `/bid/{bid_id}/auditoria` | Trilha de auditoria | `get_bid_com_acesso` |

## 12. `mcl.py` — `/mcl` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/mcl/{bid_id}/decidir` | Prévia do ranking/vencedora, sem persistir | `get_bid_com_acesso` |
| POST | `/mcl/{bid_id}/decidir` | Calcula e persiste decisão versionada | `get_bid_com_acesso` + `bloquear_visualizador` |
| POST | `/mcl/{bid_id}/simular` | Sensibilidade de preço (não persiste) | `get_bid_com_acesso` |
| GET | `/mcl/{bid_id}/historico` | Histórico de decisões | `get_bid_com_acesso` |

## 13. `dlg.py` — `/dlg` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/dlg/{empresa_id}/processar` | Reprocessa o motor DLG | `verificar_acesso_empresa` + `bloquear_visualizador` |
| GET | `/dlg/{empresa_id}/analitico` | Resultados por dimensão (`FILIAL\|ROTA\|TRANSPORTADORA\|REGIAO\|CLIENTE_FINAL`, v6.7.0)/período/classificação. Paginação opcional `page`/`page_size` (CA-16) | `verificar_acesso_empresa` |
| GET | `/dlg/{empresa_id}/outliers` | Outliers detectados | `verificar_acesso_empresa` |
| GET | `/dlg/{empresa_id}/resumo` | KPIs consolidados (inclui `top_clientes_finais`, v6.7.0) | `verificar_acesso_empresa` |

## 14. `mbl.py` — `/mbl` (3 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/mbl/{empresa_id}/processar` | Recalcula benchmark estatístico | `verificar_acesso_empresa` + `bloquear_visualizador` |
| GET | `/mbl/{empresa_id}/benchmark` | Consulta datasets percentílicos | `verificar_acesso_empresa` |
| GET | `/mbl/{empresa_id}/comparar` | Compara valor real vs. benchmark | `verificar_acesso_empresa` |

## 15. `recomendacoes.py` — `/recomendacoes` (4 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/recomendacoes/{empresa_id}/consolidar` | Reprocessa recomendações | `verificar_acesso_empresa` + `bloquear_visualizador` |
| GET | `/recomendacoes/{empresa_id}` | Lista recomendações | `verificar_acesso_empresa` |
| GET | `/recomendacoes/{empresa_id}/resumo` | Contagem por prioridade + economia | `verificar_acesso_empresa` |
| PATCH | `/recomendacoes/{empresa_id}/{rec_id}/status` | Atualiza status | `verificar_acesso_empresa` + `bloquear_visualizador` |

## 16. `inteligencia.py` — `/inteligencia` (26 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/inteligencia/status` | Modo simulado/real, modelos configurados | `get_current_user` |
| POST | `/inteligencia/insights/gerar` | Executa motor de regras | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/insights` | Lista insights | `verificar_acesso_empresa` |
| PATCH | `/inteligencia/insights/{insight_id}/lido` | Marca insight como lido | `bloquear_visualizador` + `verificar_acesso_empresa` |
| POST | `/inteligencia/score/calcular` | Calcula e salva score | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/score` | Último score (calcula se ausente) | `verificar_acesso_empresa` |
| GET | `/inteligencia/score/historico` | Histórico de scores | `verificar_acesso_empresa` |
| POST | `/inteligencia/diagnostico/gerar` | Gera diagnóstico IA (com cache) | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/diagnostico` | Último diagnóstico | `verificar_acesso_empresa` |
| GET | `/inteligencia/diagnostico/historico` | Histórico de diagnósticos | `verificar_acesso_empresa` |
| POST | `/inteligencia/oportunidades/detectar` | Detecta oportunidades | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/oportunidades` | Lista oportunidades | `verificar_acesso_empresa` |
| POST | `/inteligencia/assistente/sessoes` | Cria sessão de chat | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/assistente/sessoes` | Lista sessões | `verificar_acesso_empresa` |
| GET | `/inteligencia/assistente/sessoes/{sessao_id}/mensagens` | Lista mensagens da sessão | `verificar_acesso_empresa` |
| POST | `/inteligencia/assistente/sessoes/{sessao_id}/mensagens` | Envia mensagem (tool-calling) | `bloquear_visualizador` + `verificar_acesso_empresa` |
| GET | `/inteligencia/benchmark-setorial` | Compara com benchmark setorial | `verificar_acesso_empresa` |
| GET | `/inteligencia/benchmark-setorial/segmentos` | Lista segmentos disponíveis | `get_current_user` |
| GET | `/inteligencia/rag/status` | Estatísticas de RAG da empresa | `verificar_acesso_empresa` |
| GET | `/inteligencia/rag/documentos` | Lista documentos indexados | `verificar_acesso_empresa` |
| POST | `/inteligencia/rag/documentos` | Indexa novo documento | `bloquear_visualizador` + `verificar_acesso_empresa` |
| POST | `/inteligencia/rag/buscar` | Busca semântica (cosseno) | `verificar_acesso_empresa` |
| POST | `/inteligencia/rag/seed-legislacao` | Indexa legislação ANTT (global) | `bloquear_visualizador` |
| GET | `/inteligencia/relatorio/{formato}` | Relatório executivo IA (pdf/word/powerpoint) | `verificar_acesso_empresa` |
| GET | `/inteligencia/dashboard` | KPIs de inteligência | `verificar_acesso_empresa` |
| GET | `/inteligencia/uso` | Consumo/custo de IA | `verificar_acesso_empresa` |

## 17. `importacao.py` — `/importacao` (8 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/importacao/cte/{empresa_id}` | Upload de múltiplos XMLs de CT-e (máx. 500/lote, 10 MB/arquivo) | `verificar_acesso_empresa` + `bloquear_visualizador` |
| POST | `/importacao/cte/cancelamento/{empresa_id}` | Importa eventos de cancelamento via XML | `verificar_acesso_empresa` + `bloquear_visualizador` |
| GET | `/importacao/dados/{empresa_id}/cancelamentos` | Log de cancelamentos importados | `verificar_acesso_empresa` |
| GET | `/importacao/excel/modelo` | Baixa planilha-modelo | `get_current_user` |
| POST | `/importacao/excel/{empresa_id}` | Importação alternativa via Excel (máx. 20 MB) | `verificar_acesso_empresa` + `bloquear_visualizador` |
| GET | `/importacao/dados/{empresa_id}/contagem` | Conta registros importados por origem | `verificar_acesso_empresa` + `require_admin` |
| GET | `/importacao/dados/{empresa_id}/competencias` | CT-es por competência (mês/ano) | `verificar_acesso_empresa` |
| DELETE | `/importacao/dados/{empresa_id}` | Exclui dados importados (confirmação exata da quantidade) | `verificar_acesso_empresa` + `require_admin` |

## 18. `dashboard.py` — `/dashboard` (1 endpoint)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/dashboard/{empresa_id}` | Diagnóstico completo (nacional, regional, transportadoras, prazos, composição) | `verificar_acesso_empresa` |

## 19. `relatorios.py` — `/relatorios` (5 endpoints)

| Método | Path | Descrição | Auth |
|---|---|---|---|
| GET | `/relatorios/diagnostico/{empresa_id}/excel` | Relatório de diagnóstico (Excel) | `verificar_acesso_empresa` |
| GET | `/relatorios/diagnostico/{empresa_id}/pdf` | Relatório de diagnóstico (PDF) | `verificar_acesso_empresa` |
| GET | `/relatorios/benchmark/{empresa_id}/excel` | Relatório de benchmark (Excel) | `verificar_acesso_empresa` |
| GET | `/relatorios/benchmark/{empresa_id}/pdf` | Relatório de benchmark (PDF) | `verificar_acesso_empresa` |
| GET | `/relatorios/bid/{bid_id}/{tipo}/{formato}` | Relatórios de BID (executivo/comparativo/ranking/economia/resultado/pacote_cotacao; pdf/excel) | `verificar_acesso_empresa` |

## 20. `portal_cliente.py` — `/portal` (7 endpoints) — v6.18.0

> Audiência separada (Portal do Cliente) — cookies `gd_frete_cliente_*`, claim `aud=portal_cliente`, nunca aceitos por `get_current_user` (interno) nem vice-versa. Nenhuma rota recebe `empresa_id` de path/query — sempre derivado de `current_user.empresa_id` (dependency `get_current_cliente_user`). Todo dado de leitura reaproveita `ScoreLogisticoUseCase`, `BenchmarkUseCase` e `RecomendacoesUseCase`, sem cálculo paralelo. Ver Especificação Técnica `docs/specs/v6.18.0/v6.18.0_especificacao_tecnica_portal_executivo.md`.

| Método | Path | Descrição | Auth |
|---|---|---|---|
| POST | `/portal/auth/login` | Login do usuário-cliente (OAuth2 password flow) | rate-limited 10/min |
| POST | `/portal/auth/refresh` | Renova access token (cookie ou body) | `gd_frete_cliente_refresh` |
| POST | `/portal/auth/logout` | Limpa cookies do Portal | — |
| GET | `/portal/auth/me` | Dados do usuário-cliente + empresa | `get_current_cliente_user` |
| GET | `/portal/dashboard` | Resumo executivo, 5 KPIs, evolução, benchmark, custo por macrorregião, potencial de economia, plano de ação | `get_current_cliente_user` |
| GET | `/portal/oportunidades` | Lista de recomendações ordenada por impacto | `get_current_cliente_user` |
| PATCH | `/portal/oportunidades/{recomendacao_id}/priorizar` | Alterna "priorizada pelo cliente" (`portal_oportunidade_flags`, não altera `recomendacoes`) | `get_current_cliente_user` |

## Contagem total

| Router | Endpoints |
|---|---|
| auth | 4 |
| usuarios | 4 |
| empresas | 9 |
| transportadoras | 5 |
| regioes/cidades | 11 |
| metas | 4 |
| benchmarks | 2 |
| benchmark_analise | 6 |
| benchmark_od_config (hubs+clusters+corredores) | 13 |
| benchmark_v2_api | 8 |
| bid | 27 |
| mcl | 4 |
| dlg | 4 |
| mbl | 3 |
| recomendacoes | 4 |
| inteligencia | 26 |
| importacao | 8 |
| dashboard | 1 |
| relatorios | 5 |
| portal_cliente (v6.18.0) | 7 |
| **Total** | **155** |
