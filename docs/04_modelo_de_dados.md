# 04 · Modelo de Dados

> Substitui `archive/03_dicionario_dados.md` (que cobria só 11 das 44 tabelas reais). Fonte: `app/infrastructure/database/models/__init__.py`, auditado em 2026-07-07.

## Convenções

- Todas as tabelas usam `id INTEGER PRIMARY KEY` (SERIAL no PostgreSQL).
- `empresa_id` presente = isolamento multi-tenant (ver [`02_especificacao_funcional.md`](02_especificacao_funcional.md#5-o-que-é-global-vs-o-que-é-isolado-por-empresa-multi-tenant) para a lista do que é global vs. isolado).
- Colunas `created_at`/`updated_at` são `TIMESTAMP DEFAULT NOW()`, omitidas na tabela abaixo quando presentes por padrão, para não poluir.

## 1. Cadastro base

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `users` | nome, email (único), hashed_password, is_active, is_superuser, role, empresa_id | → `empresas.id` (nullable — superusuário global não tem empresa) |
| `empresas` | razao_social, nome_fantasia, cnpj_matriz (único), status, setor (indexado) | 1:N filiais, transportadoras, ctes... |
| `filiais` | empresa_id, razao_social, cnpj, cidade, uf | → `empresas.id` |
| `transportadoras` | empresa_id (nullable — herança histórica pré-v3.0.0), razao_social, nome_fantasia, cnpj, endereco, cidade, uf, cep, contato, telefone, email, status | → `empresas.id` |
| `regioes` | nome (único), descricao | Global |
| `cidades` | nome, uf, regiao_id, macro_regiao | → `regioes.id` |
| `meta_nacional` | meta_rs_kg, meta_pct_frete | Global (singleton) |
| `meta_regional` | macro_regiao (único), meta_rs_kg, meta_pct_frete, prazo_medio_meta | Global |
| `benchmarks` | regiao (único), frete_kg_min/medio/max, frete_pct_min/medio/max | Global — modelo legado |

## 2. CT-e / NF-e

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `ctes` | empresa_id, transportadora_id, chave (único), numero, serie, data_emissao, tomador_cnpj, **destinatario_cnpj, destinatario_nome** (v6.7.0 — nullable, sem backfill, RN-68), peso, valor_frete, valor_mercadoria, municipio/uf origem+destino, macro_regiao_destino, data_saida, data_entrega, origem_importacao (XML\|EXCEL), composicao_frete (JSON), status (indexado), cancelado_em, protocolo_cancelamento, numero_evento_cancelamento | → `empresas.id`, `transportadoras.id` |
| `nfes` | cte_id, chave, numero, data_emissao, valor_mercadoria, peso, municipio_destino | → `ctes.id` (cascade delete-orphan) |
| `cte_cancelamentos` | empresa_id, cte_id (nullable), chave, protocolo, numero_evento, tipo_evento, data_cancelamento, resultado (indexado), mensagem, arquivo, xml_evento | → `empresas.id`, `ctes.id` |

## 3. Benchmark — modelo por Corredor OD / Hubs (V2.1)

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `hubs_logisticos` | codigo (único), nome, descricao, ativo | Global |
| `clusters_cliente` | empresa_id, uf, municipio, hub_id — `UNIQUE(empresa_id, uf, municipio)` | → `empresas.id`, `hubs_logisticos.id` |
| `benchmarks_corredor` | hub_origem_codigo, hub_destino_codigo (par único), frete_kg_min/medio/max, frete_pct_min/medio/max, volume_referencia, dispersao_kg, observacoes | Global |

## 4. Benchmark V2 — Matriz de Mercado

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `benchmark_mercado` | origem_regiao, destino_regiao, modal, tipo_operacao, faixa_peso_min/max, rs_kg_p10..p90, fonte — único por (origem, destino, modal, tipo, faixas) | Global — fonte de verdade |
| `benchmark_observado` | empresa_id + mesmas dimensões + qtd_embarques, rs_kg_p10..p90, media, desvio_padrao, periodo_ref | → `empresas.id` |
| `benchmark_cliente` | empresa_id, origem_regiao, destino_regiao, modal, rs_kg_medio, ativo, observacoes | → `empresas.id` — override manual do cliente |

## 5. DLG / MBL / MCL

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `dlg_analitico` | empresa_id, dimensao (indexado — FILIAL\|ROTA\|TRANSPORTADORA\|REGIAO\|**CLIENTE_FINAL**, v6.7.0), chave (indexado), chave_label, periodo_ref (indexado), qtd_ctes, peso_total, frete_total, mercadoria_total, rs_kg, pct_frete, custo_medio_entrega, rs_kg_ref, desvio_pct, classificacao, **composicao_frete** (JSON, v6.7.0 — genérico às 5 dimensões, RN-72/RN-73) — único por (empresa, dimensao, chave, periodo_ref). Campos `peso_medio`/`ticket_medio`/`impacto_financeiro_potencial`/`frete_transporte_principal`/`pct_componentes_adicionais`/`ranking_componentes` são derivados na leitura (não persistidos); `sinal_fragmentacao`/`causa_dominante` (RN-75/RN-76) são calculados sob demanda e atribuídos em memória, também não persistidos. | → `empresas.id` |
| `dlg_outliers` | empresa_id, cte_id, periodo_ref, tipo_outlier, valor_real, valor_limite, desvio_pct — único por (empresa, cte, periodo, tipo) | → `empresas.id`, `ctes.id` |
| `mbl_benchmark` | empresa_id, dimensao, segmento, metrica, periodo_ref, amostra, p10..p90, media, desvio_padrao, low_confidence (indexado), outliers_excluidos, versao — único por (empresa, dimensao, segmento, metrica, periodo_ref) | → `empresas.id` |
| `mcl_decisoes` | bid_id, empresa_id, versao, vencedora_bt_id, vencedora_transp_id, vencedora_nome, score_vencedora, diferenca_segunda, peso_custo (0.40)/peso_dlg (0.25)/peso_mbl (0.20)/peso_sla (0.10)/peso_estabilidade (0.05), ranking (JSON), justificativa, propostas_rejeitadas (JSON) | → `bids.id`, `empresas.id` |

## 6. Concorrência Logística (BID)

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `bids` | empresa_id, nome, descricao, objetivo, observacoes, status, segmentacao_tipo, segmentacao_valor, data_inicio, data_encerramento, periodo_analise_inicio/fim, created_by | → `empresas.id`, `users.id`; 1:N escopos/transportadoras/propostas/simulacoes/auditoria (todos cascade delete-orphan) |
| `bid_escopos` | bid_id, tipo_agrupamento, valor_grupo, peso_total, valor_frete_total, valor_mercadoria_total, qtd_embarques, frete_rs_kg, frete_pct | → `bids.id` |
| `bid_transportadoras` | bid_id, transportadora_id, status, observacoes, avaliacao_usuario | → `bids.id`, `transportadoras.id` |
| `bid_propostas` | bid_id, bid_transportadora_id, tipo_agrupamento, valor_grupo, valor_rs_kg, valor_minimo, prazo_dias, cobertura_pct, observacoes, origem, deleted (soft delete) | → `bids.id`, `bid_transportadoras.id` |
| `bid_simulacoes` | bid_id, nome, descricao, itens (JSON), custo_atual, custo_proposto, economia_total, reducao_pct | → `bids.id` |
| `bid_auditorias` | bid_id, user_id, acao, detalhe (JSON) | → `bids.id`, `users.id` |

## 7. Recomendações

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `recomendacoes` | empresa_id, titulo, descricao, indicador (indexado), chave_origem, valor_encontrado, valor_recomendado, impacto, economia_estimada, prioridade (indexado), origem, status, dados (JSON) — único por (empresa, indicador, chave_origem) | → `empresas.id` |

## 8. Inteligência Logística com IA

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `regras_insight` | empresa_id (nullable=global), nome, categoria, classificacao, expressao, titulo_template, descricao_template, ativa | → `empresas.id` |
| `insights` | empresa_id, regra_id, categoria, classificacao, titulo, descricao, impacto_financeiro, prioridade, dados (JSON), lido, created_at (indexado) | → `empresas.id`, `regras_insight.id` |
| `insight_execucoes` | empresa_id, total_insights, duracao_ms, status, erro | → `empresas.id` |
| `diagnosticos_ia` | empresa_id, periodo_inicio/fim, resumo_executivo, pontos_fortes, pontos_atencao, principais_desvios, economia_potencial, plano_acao, score_logistico, modelo_usado, cache_hash (indexado) | → `empresas.id` |
| `diagnostico_historicos` | empresa_id, diagnostico_id, score, economia_potencial, resumo | → `empresas.id`, `diagnosticos_ia.id` |
| `scores_logisticos` | empresa_id, score_total, score_benchmark_nacional/regional, score_transportadoras, score_filiais, score_economia, classificacao, periodo_referencia | → `empresas.id` |
| `score_historicos` | empresa_id, score_total, classificacao, periodo_referencia | → `empresas.id` |
| `benchmarks_setoriais` | segmento (indexado), frete_kg_medio, frete_pct_medio, custo_medio, regiao | Global |
| `oportunidades` | empresa_id, tipo, titulo, descricao, economia_estimada, impacto, complexidade, prioridade, justificativa, status, dados (JSON) | → `empresas.id` |
| `planos_acao` | empresa_id, oportunidade_id, acao, impacto, economia_estimada, prioridade, prazo_dias, status | → `empresas.id`, `oportunidades.id` |
| `chat_sessoes` | empresa_id, user_id, titulo | → `empresas.id`, `users.id`; 1:N mensagens (cascade) |
| `chat_mensagens` | sessao_id, empresa_id, papel, conteudo, ferramentas_usadas (JSON), tokens | → `chat_sessoes.id`, `empresas.id` |
| `usage_logs` | empresa_id, user_id, feature (indexado), modelo, tokens_input/output, custo_usd, custo_brl, simulado, created_at (indexado) | → `empresas.id`, `users.id` |
| `documentos_vetoriais` | empresa_id, tipo_documento (indexado), titulo, conteudo, data_referencia, doc_metadata (coluna real `metadata`, JSON), embedding (JSON), indexado | → `empresas.id` |
| `embedding_jobs` | empresa_id, documento_id, status, erro | → `empresas.id`, `documentos_vetoriais.id` |

## 9. Portal do Cliente (v6.18.0)

> Audiência separada de `users` — ver `05_apis.md` §20 e Especificação Técnica `docs/specs/v6.18.0/`. Nenhuma tabela do motor analítico foi alterada para esta funcionalidade.

| Tabela | Campos principais | Relacionamentos |
|---|---|---|
| `clientes_portal_users` | empresa_id (obrigatório, diferente de `users.empresa_id` que é nullable), nome, email (único globalmente), hashed_password, ativo, ultimo_acesso | → `empresas.id` |
| `portal_oportunidade_flags` | recomendacao_id, empresa_id, cliente_portal_user_id, priorizada, atualizado_em — único por (recomendacao_id, cliente_portal_user_id) | → `recomendacoes.id`, `empresas.id`, `clientes_portal_users.id` |

**Total: 46 tabelas** em 55 modelos SQLAlchemy declarados (alguns modelos compartilham tabela via `extend_existing`).

## Migrations

Ordem cronológica real (por data de criação do arquivo, não só pela cadeia `down_revision`):

| # | Revisão | Data | O que faz |
|---|---|---|---|
| 1 | `faa05e1d23e5` | 2026-06-19 | Estrutura inicial: empresas, meta_nacional, meta_regional, regioes, transportadoras, users, cidades, ctes, filiais, nfes |
| 2 | `a2f8c1e4b9d3` | 2026-06-19 | Segurança + isolamento multiempresa + performance: `empresa_id` em transportadoras (antes global), índices compostos em `ctes` (empresa+data_emissao, empresa+transportadora) |
| 3 | `b3d9e2f1a7c5` | 2026-06-20 | BID de Frete: `role` em users; tabelas `bids`, `bid_escopos`, `bid_transportadoras`, `bid_propostas`, `bid_simulacoes`, `bid_auditorias` |
| 4 | `c5e1a9f4d2b7` | 2026-06-21 | Benchmark OD (V2.1): `hubs_logisticos`, `clusters_cliente`, `benchmarks_corredor` + seed dos 5 hubs padrão |
| 5 | `d7f2b8c3e9a1` | 2026-06-22 | Hardening: `users.empresa_id`, constraints UNIQUE em clusters/corredores |
| 6 | `e8c4a1f6d3b2` | 2026-06-24 | Benchmark V2 (matriz OD): `benchmark_mercado`, `benchmark_observado`, `benchmark_cliente`; soft delete em `bid_propostas` |
| 7 | `f3a9d6b2c1e8` | 2026-06-24 | DLG e MBL: `dlg_analitico`, `dlg_outliers`, `mbl_benchmark` |
| 8 | `a7c2e9f1b4d6` | 2026-06-24 | MCL: `mcl_decisoes` |
| 9 | `b8e3f1a2c9d4` | 2026-06-26 | Setor do embarcador: coluna `setor` em `empresas` |
| 10 | `c9f4a2e7b1d8` | 2026-07-04 | Cancelamento de CT-e, recomendações e dimensão FILIAL: colunas de cancelamento em `ctes`, tabelas `cte_cancelamentos` e `recomendacoes`, renomeia dimensão DLG `CLIENTE`→`FILIAL` |
| 11 | `d4b8f2a6c1e9` | 2026-07-08 | Dimensão Cliente (v6.7.0): `ctes.destinatario_cnpj`/`destinatario_nome` (nullable, sem backfill); `dlg_analitico.composicao_frete` (JSON, genérico às 5 dimensões). Reversível. |

> **Nota de rastreabilidade:** não existe migration Alembic específica para as mudanças de v6.5.0/v6.5.1 (cookies `httpOnly`, reforço de isolamento multi-tenant, enforcement de VISUALIZADOR) porque essas mudanças são de **código de autorização**, não de schema — não alteram tabela alguma. As tabelas de IA (Insights, DiagnosticoIA, ScoreLogistico, Oportunidade, ChatSessao/Mensagem, UsageLog, DocumentoVetorial, EmbeddingJob) também não têm uma migration própria neste diretório — foram criadas via `create_all`/alterações incrementais no `lifespan` do FastAPI (ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#7-banco-de-dados)). Recomenda-se gerar as migrations Alembic faltantes antes de qualquer deploy que dependa exclusivamente de `alembic upgrade head` (ver pendência em [`10_roadmap.md`](10_roadmap.md)).
