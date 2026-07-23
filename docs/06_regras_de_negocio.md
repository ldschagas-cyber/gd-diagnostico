# 06 · Regras de Negócio

> Consolida as regras de negócio antes espalhadas em `01_especificacao_funcional.md`, `especificacao_funcional_benchmark_od_v2.1.docx` e implícitas no código. Cada regra recebe um código `RN-xx` estável para referência cruzada. Fonte: `app/application/use_cases/*.py`, auditado em 2026-07-07.

## Importação

| # | Regra |
|---|---|
| RN-01 | O CNPJ do tomador do CT-e deve corresponder à matriz ou a uma filial cadastrada da empresa; CT-es de CNPJ desconhecido são rejeitados. |
| RN-02 | Deduplicação de CT-e por chave de acesso (44 dígitos); CT-e já importado não é substituído. |
| RN-03 | Peso taxado = `max(peso bruto, peso cubado)`, excluindo unidades de Volumes (`cUnid=03`) e Cubagem em m³ (`cUnid=00`). |
| RN-04 | `valor_mercadoria` vem de `infCarga/vCarga`, com busca recursiva pois pode estar aninhado em `infCTeNorm`. |
| RN-05 | Composição do frete é categorizada em 8 categorias: Frete Peso, Frete Valor, Pedágio, GRIS, Seguro, Ademe, Despacho, Outros. |
| RN-06 | Importação via Excel usa chave sintética `EXCEL-{empresa_id}-{nota_fiscal}-{linha}` para deduplicação, evitando colisão entre notas de mesmo número de empresas (ou linhas) diferentes. |
| RN-07 | Limites de upload: XML — máx. 500 arquivos por lote, 10 MB por arquivo; Excel — máx. 20 MB por arquivo; validação de assinatura (magic bytes) antes de processar. |
| RN-08 | Cancelamento de CT-e: evento aceito apenas se homologado pela SEFAZ; localizado pela chave no escopo da empresa; duplicidade (CT-e já cancelado ou evento repetido) é registrada sem interromper o lote. |
| RN-08a | Carta de Correção (CCe, tpEvento 110110): reconhecida e registrada no log de auditoria (mesma tabela do cancelamento, `resultado` prefixado `CCE_`), mas **nunca aplicada automaticamente** ao CT-e já importado — nenhum campo do CT-e é alterado. Motivo: a CCe é disciplinada pelo Art. 58-B do Convênio SINIEF 06/89 e não deveria, por regra, corrigir variáveis que determinam o valor da prestação (ex.: quantidade/peso de carga) — na prática, porém, emissores usam a CCe para isso, então a correção proposta fica registrada para revisão manual do analista (v6.11.0). |

## Diagnóstico e indicadores

| # | Regra |
|---|---|
| RN-09 | Apenas CT-es com `status=ATIVO` entram nos totais financeiros dos indicadores; `pct_cancelados` é calculado à parte. |
| RN-10 | Frete R$/kg = `valor_frete / peso`; % Frete = `valor_frete / valor_mercadoria * 100`. |
| RN-11 | OTIF (prazo) é calculado como aderência ao prazo entre `data_saida` e `data_entrega`. |
| RN-12 | Macro-região de destino é derivada da UF via `macro_regiao.py`. |

**Nota de propagação (correção CONS-01, v6.6.0)**: até a v6.5.1, a RN-09 era aplicada corretamente apenas em Diagnóstico e DLG — Benchmark (legado, OD, Observado), MBL, Indicadores Regionais V2, Score Logístico, Insights, Oportunidades, Diagnóstico IA e Benchmark Setorial liam CT-e sem filtrar por status, deixando cancelamentos contaminar seus totais. A partir da v6.6.0, todos esses módulos filtram por `CTE_STATUS_ATIVO` (constante em `app/domain/entities/__init__.py`), tornando a RN-09 consistente em toda a plataforma. **Exceção ainda pendente**: o escopo do BID (`bid_escopo.py`) e o motor MCL não aplicam esse filtro — achado correlato BID-01/MCL-02 (`docs/20_fase7_auditoria_funcional.md`), tratado na Etapa 2 do plano diretor técnico (`docs/22_plano_diretor_tecnico.md`).

## Metas e Benchmark legado (regional)

| # | Regra |
|---|---|
| RN-13 | Meta nacional é um singleton; existem 5 metas regionais (uma por macrorregião). Ambas globais, editáveis só por ADMIN/superusuário. |
| RN-14 | Classificação de % frete (faixa fixa): ≤5% Excelente, ≤8% Muito Bom, ≤12% Atenção, ≤18% Crítico, >18% Muito Crítico. |
| RN-15 | Classificação de R$/kg vs. benchmark médio (faixa relativa): razão ≤1,0 Excelente, ≤1,10 Bom, ≤1,20 Atenção, >1,20 Crítico. |
| RN-16 | Potencial de economia = excesso do custo acima do benchmark × peso movimentado; projeções mensal/trimestral/semestral/anual = economia mensal × 1/3/6/12; `n_meses = (data_max − data_min).dias / 30`, mínimo 1. |

## Benchmark por Corredor OD / Hubs (V2.1)

| # | Regra |
|---|---|
| RN-17 | Resolução do corredor de um CT-e: cluster do cliente por município (precedência) → cluster por UF → UF como hub implícito → busca a referência global do par de hubs. |
| RN-18 | Score por componente: 100 se valor ≤ referência; acima da referência, penalização logarítmica suavizada `log1p(desvio_ajustado × 1,75) / log1p(1,75)`, com tolerância ampliada pela dispersão cadastrada do corredor (0 a 1). |
| RN-19 | Combinação final do score do corredor: 60% R$/kg + 40% % frete. Score global da empresa = média ponderada por peso/volume dos corredores com referência disponível. |
| RN-20 | Classificação do score OD: 90–100 Excelente, 75–89 Muito Bom, 60–74 Regular, 40–59 Crítico, <40 Muito Crítico. *(Escala diferente da RN-14/RN-15 — este é um score numérico 0-100, não uma faixa direta de %/R$ kg.)* |
| RN-21 | O benchmark regional legado (RN-13 a RN-16) permanece no banco como referência de fallback do indicador nacional — não é substituído pelo modelo OD. |

## Benchmark V2 — Matriz de Mercado

| # | Regra |
|---|---|
| RN-22 | Hierarquia de resolução de referência: **CLIENTE** (override manual, `benchmark_cliente`) > **MERCADO** (fonte de verdade global, `benchmark_mercado`) > indisponível. |
| RN-23 | Comparação de um valor observado contra a referência: faixa ABAIXO_P50, ENTRE_P50_P75 ou ACIMA_P75. |
| RN-24 | Benchmark Observado (por empresa) usa os mesmos 5 percentis (P10/P25/P50/P75/P90) calculados sobre os CT-e reais da empresa, por período (`periodo_ref`), com interpolação linear estilo numpy; idempotente por período. |

## DLG — Diagnóstico Logístico Analítico

| # | Regra |
|---|---|
| RN-25 | Classificação por desvio: desvio ≤0% EFICIENTE, ≤15% ATENÇÃO, >15% CRÍTICO. |
| RN-26 | Outlier por R$/kg: valor > média + 2 desvios-padrão (tipo `RS_KG_2DP`). |
| RN-27 | Outlier por % frete: valor > limite configurado (`meta_nacional × 1,5`, ou 15% se não houver meta cadastrada) (tipo `PCT_FRETE`). |
| RN-28 | Deduplicação de transportadoras por identidade real: raiz de 8 dígitos do CNPJ ou nome normalizado sem sufixos societários — consolida matriz e filiais do mesmo grupo transportador em uma única entidade de análise. |
| RN-29 | Considera apenas CT-es `status=ATIVO`; suporta modo consolidado (agrega meses do intervalo) e modo mensal (uma linha por entidade/mês). |

### DLG — Dimensão Cliente (v6.7.0)

| # | Regra |
|---|---|
| RN-67 | Cliente é a 5ª dimensão do motor genérico do DLG (valor interno `CLIENTE_FINAL`) — "Cliente" aqui é o **destinatário da mercadoria**, não a filial tomadora (FILIAL) nem o "cliente" da hierarquia de benchmark V2 (`benchmark_cliente`). Reaproveita 100% da classificação (RN-25) e da mesma referência nacional das demais dimensões financeiras. |
| RN-68 | Deduplicação de cliente por identidade real: raiz de 8 dígitos do `destinatario_cnpj`, ou nome normalizado (minúsculas, sem acentos/pontuação, sem sufixos societários LTDA/ME/EPP/EIRELI/SA) quando não há CNPJ; CT-e sem nenhum dos dois é agrupado sob "Cliente não identificado", nunca omitido ou fundido incorretamente — mesmo padrão de identidade já usado pela RN-28 (transportadoras), adaptado para ler diretamente de `CTeModel` em vez de uma tabela de cadastro. |
| RN-69 | Campos financeiros base da linha Cliente (frete/peso/mercadoria/R$/kg/% frete/custo médio) calculados pelo mesmo `_agregar_*` genérico das demais dimensões. |
| RN-70 | Impacto Financeiro Potencial = `max(0, rs_kg − rs_kg_ref) × peso_total` — derivado na leitura, sem coluna nova; aplicável às 5 dimensões. |
| RN-71 | Recomendação de concentração de risco: quando um único cliente responde por parcela do frete total acima do limiar (25%, `LIMIAR_CONCENTRACAO_CLIENTE_PCT`), gera recomendação automática. |
| RN-72 | Frete Transporte Principal = `composicao_frete["Frete Peso"] + composicao_frete["Frete Valor"]`; % Componentes Adicionais = `(frete_total − Frete Transporte Principal) / frete_total × 100`. **`None` (nunca 0 nem 100) quando o CT-e/lote não tem nenhuma composição detalhada** — ausência de dado é um estado próprio, mesma filosofia de `SEM_REF`. |
| RN-73 | Granularização de categorias do parser: `TDE` e `TDA` ganham categoria própria (antes agrupadas em "Outros"); nova categoria "Estadia" (substring, `cte_parser.py`) reconhecida a partir de `ESTADIA`; "TDA/TDE" (item combinado) permanece em "Outros" por não ser decomponível sem premissa arbitrária. Réplica exata (match por cabeçalho, sem heurística de substring) no `excel_parser.py`. **CT-e importados antes desta mudança mantêm a categorização antiga indefinidamente** — não há reprocessamento automático nem correção via reimportação (bloqueada pela deduplicação por chave, RN-02). |
| RN-74 | Ranking de componentes ofensores por cliente: ordenação decrescente das categorias de `composicao_frete`, exceto Frete Peso/Frete Valor — derivado na leitura. |
| RN-75 | Sinal de fragmentação operacional, em duas partes: **Parte A** — peso médio por CT-e do cliente abaixo de 50% (`LIMIAR_PESO_MEDIO_BAIXO`) da mediana de peso médio entre os clientes do mesmo período; **Parte B** — ≥3 CT-e (`MIN_CTES_FRAGMENTACAO`) do mesmo cliente em janela de até 7 dias corridos (`JANELA_DIAS_FRAGMENTACAO`). Só avaliada para clientes já classificados ATENÇÃO/CRÍTICO (RN-25) com Parte A positiva — nunca para todos os clientes do período. Nível de despacho, não de pedido (não existe entidade Pedido no domínio). |
| RN-76 | Diagnóstico causal determinístico: cliente ATENÇÃO/CRÍTICO com % adicionais acima da mediana da empresa no período (limiar relativo) e/ou sinal de fragmentação (RN-75) recebe causa "ADICIONAIS", "FRAGMENTACAO", "AMBAS" ou "NENHUMA" — nunca inventada quando nenhum sinal está presente. Cliente EFICIENTE/SEM_REF nunca recebe causa (não há desvio a explicar). 100% Python determinístico, nunca LLM. |
| RN-77 | Recomendações causais: o motor de Recomendações (`_recomendacoes_dlg_clientes`) gera texto para o top-5 cliente CRÍTICO por desvio (nomeando a causa RN-76) e top-3 SEM_REF (oportunidade de cadastro de benchmark), reaproveitando o mesmo motor DLG — upsert idempotente pela mesma chave natural já usada (RN-57). |

**Nota de performance (CA-16)**: `GET /dlg/{empresa}/analitico` aceita `page`/`page_size` opcionais (paginação server-side, aplicada após ordenação/filtro), disponível a todas as dimensões mas sobretudo relevante para `CLIENTE_FINAL` — a de maior cardinalidade potencial das 5.

## MBL — Benchmark Estatístico

| # | Regra |
|---|---|
| RN-30 | Percentis (P10 a P90, média, desvio-padrão) calculados por dimensão (Região/Cluster/Rota) × métrica (R$/kg, % frete, custo/entrega) × período mensal, **excluindo os outliers já detectados pelo DLG**. |
| RN-31 | Amostra mínima por segmento: 5 (`THRESHOLD_AMOSTRA_PADRAO`); abaixo disso, o resultado é marcado `low_confidence`. |
| RN-32 | Classificação de faixa: valor ≤P25 EFICIENTE, valor ≥P75 INEFICIENTE, senão NORMAL. |
| RN-33 | Idempotente, com versionamento incremental por período. |

## MCL — Motor de Decisão de BID

| # | Regra |
|---|---|
| RN-34 | Score da proposta = `0,40 × custo + 0,25 × DLG + 0,20 × MBL + 0,10 × SLA + 0,05 × estabilidade`. |
| RN-35 | Propostas com preço mais de 20% acima da referência MBL são rejeitadas (`LIMITE_ACIMA_MBL_PCT = 20,0`). |
| RN-36 | Normalização por componente: custo/prazo via min-max invertido; DLG via mapa `{EFICIENTE: 1,0, ATENÇÃO: 0,6, CRÍTICO: 0,2, SEM_REF: 0,5}`; MBL via `0,5 − desvio_pct/40` (clamp 0–1); estabilidade via `1 − |desvio_dlg|/50`. |
| RN-37 | Decisão é determinística e versionada (tabela `mcl_decisoes`); histórico completo preservado a cada nova versão. |

## BID de Frete

| # | Regra |
|---|---|
| RN-38 | Máquina de estados: `RASCUNHO → ABERTO ou CANCELADO`; `ABERTO → EM_COTAÇÃO ou CANCELADO`; `EM_COTAÇÃO → ENCERRADO ou CANCELADO`; `ENCERRADO`/`CANCELADO` são terminais. |
| RN-39 | Toda transição de estado e ação relevante (convite, proposta, simulação) gera registro em `bid_auditorias`. |
| RN-40 | Economia de uma proposta = `(frete_rs_kg_atual − proposta_rs_kg) × peso_movimentado`, nunca negativa. |
| RN-41 | Score de transportadora no comparativo: Preço 40% (menor R$/kg → 100, normalização min-max invertida) + Prazo 30% (menor prazo → 100) + Cobertura 20% (percentual direto) + Avaliação do usuário 10% (nota 0–10 × 10). Classificação: ≥80 Excelente, ≥65 Boa, ≥50 Regular, <50 Crítica. |
| RN-42 | Escopo do BID é gerado via SQL `GROUP BY` (sem carregar CT-es em memória), por Região, UF, Transportadora, Filial ou faixas de peso livres, com filtro de segmentação opcional aplicado antes da agregação. |

## Score Logístico (IA)

| # | Regra |
|---|---|
| RN-43 | Score 0–100 = `Nacional × 0,30 + Regional × 0,20 + Transportadoras × 0,20 + Filiais × 0,15 + Economia × 0,15`. |
| RN-44 | Score por razão (componentes Nacional/Regional): `score = 75 − (razão − 1) × 125`, onde razão = valor/referência; clamp [0, 100]. |
| RN-45 | Score de Transportadoras: concentração ≤40% → 100; ≥80% → 30; entre esses valores → `100 − (concentração − 40) × 1,75`. |
| RN-46 | Score de Filiais: baseado no coeficiente de variação do custo entre filiais — `max(30, 100 − CV × 100)`. |
| RN-47 | Score de Economia: `max(20, 100 − pct_excesso × 2)`. |
| RN-48 | Classificação do score total: ≥90 Excelente, ≥75 Muito Bom, ≥60 Regular, ≥40 Crítico, <40 Muito Crítico. |

## Insights automáticos (IA)

| # | Regra |
|---|---|
| RN-49 | Regras seed padrão: (1) frete regional > benchmark × 1,15 → ATENÇÃO; (2) concentração de transportadora >60% → CRÍTICO; (3) economia potencial > R$ 50.000 → OPORTUNIDADE; (4) variação mensal >10% → ATENÇÃO (regra placeholder, avaliação ainda não implementada). |
| RN-50 | Economia potencial anualizada = excesso sobre o benchmark × 12. |
| RN-51 | Avaliação de regra via `eval()` restrito (sem builtins) sobre um contexto numérico controlado — regras são configuráveis no banco, não hardcoded no código. |

## Oportunidades automáticas (IA)

| # | Regra |
|---|---|
| RN-52 | **Renegociação**: frete regional > benchmark × 1,15 → economia anualizada ×12. |
| RN-53 | **Concentração**: uma transportadora responde por >60% do volume. |
| RN-54 | **Consolidação**: ≥3 transportadoras com <5% de volume cada, quando há mais de 3 transportadoras no total. |
| RN-55 | **BID**: top-2 regiões por volume com custo acima do benchmark geram plano de ação automático sugerindo processo de cotação. |

## Recomendações

| # | Regra |
|---|---|
| RN-56 | Gatilhos: cancelamento acima do limiar (`LIMIAR_CANCELAMENTO_PCT`, 3%), custo/kg acima da meta, % frete acima da meta, concentração em transportadora acima de 50% (`LIMIAR_CONCENTRACAO_PCT`), regiões acima da meta, rotas críticas do DLG (top 5 por desvio), rotas sem referência de benchmark (top 3, oportunidade de cadastro). |
| RN-57 | Upsert idempotente por chave natural (`empresa_id + indicador + chave_origem`); recomendações órfãs de origem=REGRA são removidas ao reprocessar, mas o status editado manualmente pelo usuário é preservado. |

## Controle de acesso (RBAC) e multi-tenant

| # | Regra |
|---|---|
| RN-58 | Três papéis: `ADMIN` (administra a própria empresa; ou qualquer empresa, se superusuário global sem `empresa_id`), `ANALISTA` (leitura + escrita operacional), `VISUALIZADOR` (somente leitura). |
| RN-59 | Toda entidade operacional (CT-e, transportadora, BID e seus artefatos, DLG/MBL/MCL, insights, score, oportunidades, chat/RAG, uso de IA) é isolada por `empresa_id` — um usuário só acessa a empresa a que pertence, exceto superusuário global. |
| RN-60 | Regiões, cidades, metas, benchmark legado, hubs logísticos, matriz de mercado (V2) e benchmark setorial são cadastros **globais** da plataforma — não isolados por empresa; edição restrita a ADMIN/superusuário. |
| RN-61 | Um ADMIN de empresa não pode conceder `is_superuser`, nem listar/editar/excluir usuários de outra empresa — apenas um superusuário global tem esse alcance. |
| RN-62 | VISUALIZADOR é bloqueado em toda operação de escrita, exceto ações que apenas calculam sem persistir (`calcular_simulacao` do BID, `mcl/simular`, `rag/buscar`). |

## Segurança

| # | Regra |
|---|---|
| RN-63 | CNPJ é validado por dígito verificador (algoritmo módulo 11) em todo cadastro que o exige (empresa, filial, transportadora). |
| RN-64 | Senha de novo usuário exige mínimo 8 caracteres, pelo menos 1 letra e 1 número. |
| RN-65 | Login com rate limit de 10 tentativas/minuto por IP; demais endpoints, 200 requisições/minuto globais. |
| RN-66 | JWT de acesso e de refresh trafegam via cookie `httpOnly`, nunca expostos a JavaScript no navegador. |
