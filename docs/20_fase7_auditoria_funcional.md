# 20 · Fase 7 — Auditoria Funcional e Regras de Negócio

> **Escopo**: exclusivamente diagnóstico — nenhum arquivo de código, cálculo, regra ou schema foi alterado nesta fase. Auditoria realizada por leitura direta e cruzada do código-fonte contra as regras documentadas em [`06_regras_de_negocio.md`](06_regras_de_negocio.md) (RN-01 a RN-57 — o bloco RN-58 a RN-66, de RBAC/segurança, já foi coberto na Fase 5 e não é repetido aqui). Metodologia: quatro frentes de investigação independentes e paralelas, cada uma revalidando um cluster de regras contra o código real, com evidência de arquivo:linha. Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) e relatórios das Fases 1-6.

---

## 1. Resumo Executivo

O "cérebro" da plataforma está matematicamente bem construído: das 57 regras de negócio auditadas (RN-01 a RN-57), a esmagadora maioria tem a **fórmula exata batendo com o código** — percentis estilo numpy, penalização logarítmica do score OD, pesos do MCL (40/25/20/10/5), score de transportadora do BID (40/30/20/10), score logístico da IA (30/20/20/15/15), thresholds de classificação em cascata. Isso é o oposto de um sistema que "parece certo mas não é" — a matemática documentada é, ponto a ponto, a matemática implementada.

O problema real não está nas fórmulas — está na **camada de seleção de dados que alimenta essas fórmulas**, e ele é sistêmico, não pontual. A regra mais fundamental de todo o sistema analítico — **RN-09: apenas CT-e com `status=ATIVO` entra nos totais financeiros** — foi corretamente implementada apenas no módulo que a originou (Diagnóstico e DLG). Ela **não foi propagada** para nenhum dos ~8 módulos analíticos construídos depois: Benchmark legado/Dashboard Executivo, Benchmark por Corredor OD, Benchmark Observado (V2), Indicadores Regionais V2, Score Logístico (IA), Insights automáticos, Oportunidades automáticas e MBL. Isso foi confirmado de forma **convergente e independente** pelas duas frentes de auditoria que passaram por esses módulos, cada uma sem visibilidade do trabalho da outra — o tipo de confirmação cruzada que eleva a confiança do achado. Na prática: sempre que existir um CT-e cancelado no período (algo que o próprio sistema trata como normal — RN-56 assume ~3% de cancelamento como limiar aceitável), o Diagnóstico, o Dashboard Executivo, o Benchmark e o Score Logístico **vão mostrar números diferentes para o mesmo mês, a mesma rota, a mesma transportadora** — sem qualquer explicação visível ao usuário da causa raiz.

O segundo eixo de risco está concentrado no **motor de decisão de BID (MCL)**: a referência de custo (MBL) usada tanto para rejeitar propostas caras (RN-35) quanto para pontuá-las (RN-34/36) é uma **média nacional simples**, desconectada do corredor/segmento real do BID — o que pode rejeitar uma proposta competitiva para uma rota estruturalmente cara, ou premiar uma proposta ruim para uma rota estruturalmente barata. Some-se a isso uma dupla contagem real de peso/frete quando o BID gera escopo em mais de um agrupamento, a ausência de filtro de CT-e ativo no escopo do BID, e a possibilidade de alterar escopo/propostas/decisão de um BID já `ENCERRADO`/`CANCELADO` — quatro achados que, juntos, comprometem a confiabilidade do número mais sensível do sistema: a economia apresentada ao cliente para justificar a troca de transportadora.

No módulo de Inteligência IA, a arquitetura estrutural está correta — a IA **não calcula**, apenas **narra** números que já vêm prontos do SQL/Python, com instrução explícita ao modelo nesse sentido, e o isolamento do RAG por empresa está corretamente implementado. Mas o mecanismo de `eval()` "restrito" usado nos insights automáticos **não é uma sandbox de verdade** (removível/contornável via introspecção de objetos Python), hoje inofensivo apenas porque não existe endpoint que exponha edição de regras — um risco latente que se torna real no dia em que essa tela for construída.

Nenhuma das divergências encontradas envolve fraude, dado inventado do zero, ou fórmula matematicamente errada — o risco real é **inconsistência entre telas** e **contaminação silenciosa da base de comparação**, que é precisamente o tipo de defeito mais perigoso para uma plataforma de "inteligência" que vende confiança analítica: números levemente errados, sem aviso, são piores do que a ausência de número.

## 2. Nota Funcional Geral

# **64 / 100**

Fundação matemática sólida (fórmulas corretas em quase todas as 57 regras auditadas), mas um defeito sistêmico de consistência de dados (RN-09 não propagada) atravessa praticamente todos os módulos analíticos construídos após o Diagnóstico original, e o motor de decisão de BID (MCL) tem falhas reais que podem levar a uma decisão de troca de transportadora equivocada.

## 3. Avaliação por Módulo

| Módulo | Nota | Justificativa resumida |
|---|---|---|
| Importação | 70/100 | Núcleo sólido (RN-01 a RN-08 majoritariamente corretos), mas deduplicação de CT-e é global entre tenants (não por empresa) e a chave sintética do Excel depende da posição da linha. |
| Indicadores / Diagnóstico | 74/100 | RN-09/10 corretos na origem; RN-11 ("OTIF") é nomeado incorretamente e trata prazo negativo de forma diferente do Benchmark V2. |
| Diagnóstico Logístico (DLG) | 88/100 | Todas as RN-25 a RN-29 confirmadas; único módulo analítico com filtro de CT-e ativo correto desde a origem; achados restantes são de precisão estatística, não de erro. |
| Benchmark (legado + OD + V2) | 55/100 | Fórmulas de score, percentis e classificação corretas em praticamente 100% dos casos — mas os três modelos de benchmark, sem exceção, herdam CT-e cancelado nos totais. |
| MBL | 58/100 | Percentis e classificação corretos, mas é o "Source of Truth" declarado do sistema e também não filtra CT-e cancelado — o que contamina, a jusante, o próprio MCL. Versionamento sem retenção histórica real. |
| MCL | 55/100 | Pesos e normalizações batem com a fórmula documentada, mas a referência MBL usada é desconectada do segmento do BID, a decisão pode ser recalculada sem checar o estado do BID, e há dupla contagem de peso/frete em cenários plausíveis. |
| BID de Frete | 60/100 | Máquina de estados principal é fechada e correta; porém entidades subordinadas (escopo, propostas, convites) não respeitam os estados terminais, e o escopo não filtra CT-e cancelado. |
| Recomendações | 90/100 | RN-56/57 confirmadas sem divergência material; preservação de status manual do usuário testada e correta. |
| Inteligência IA | 72/100 | Separação cálculo/interpretação estrutural correta e isolamento de RAG correto; `eval()` de regras é um risco latente de segurança, e há duas fórmulas divergentes de "economia potencial" entre módulos. |

## 4. Pontos Fortes Funcionais

- **As fórmulas batem com a documentação, quase sem exceção**: percentis (estilo numpy), penalização logarítmica do score OD (`log1p`), pesos do MCL (40/25/20/10/5), score de transportadora do BID (40/30/20/10), score logístico da IA (30/20/20/15/15) e todos os thresholds de classificação em cascata (Benchmark, OD, DLG, MBL, Score) foram conferidos linha a linha e correspondem exatamente ao texto das RN.
- **DLG é o módulo mais maduro do sistema**: dedup de transportadoras por identidade real (raiz de CNPJ ou nome normalizado), detecção de outliers por dois critérios independentes, e é o único módulo que corretamente propaga o filtro de CT-e ativo para tudo que consome dele.
- **Recomendações trata corretamente o caso mais delicado de UX de dado**: reprocessar as regras nunca sobrescreve o status que um usuário mudou manualmente — testado mentalmente contra o código e confirmado.
- **Máquina de estados do BID é fechada no ponto de escrita principal** (`alterar_status`): não existe transição de estado inválida possível através dele.
- **Clamp de economia de proposta nunca fica negativo** (RN-40) — verificado nos três pontos de cálculo.
- **Arquitetura de IA é estruturalmente honesta**: o próprio prompt de sistema instrui "os números já foram calculados, não invente valores", e de fato nenhum KPI oficial (score, economia, R$/kg) é gerado pelo LLM — vem sempre de SQL/Python determinístico antes de chegar ao prompt.
- **RAG isolado corretamente por empresa**, com legislação global (`empresa_id=0`) alimentada só por seed estático, sem vetor de poluição cruzada.
- **Escopo do BID é agregação SQL real** (`GROUP BY`), não um loop Python carregando CT-es em memória — boa decisão de performance que também é funcionalmente correta em sua mecânica de agregação.

## 5. Inconsistências Encontradas

### Achados P1 — Alto (podem gerar decisão executiva incorreta)

---

**CONS-01 — RN-09 (excluir CT-e CANCELADO) não é aplicada em ~8 dos ~10 módulos analíticos**
- **Módulos**: Benchmark legado/Dashboard Executivo, Benchmark OD, Benchmark Observado, Indicadores Regionais V2, Score Logístico, Insights, Oportunidades, MBL, Diagnóstico IA.
- **RN**: RN-09.
- **Evidência**: `benchmark.py:119-123` (`_ctes`, chama `list_by_empresa` sem `apenas_ativos=True`); `repositories/__init__.py:589-624` (`agregar_por_uf_od`, sem cláusula de status, e a interface `ICTeRepository` nem declara esse parâmetro); `benchmark_observado.py:83-88`; `indicadores_regionais.py:44-49`; `score_logistico.py:99-147`; `insights.py:122-155`; `oportunidades.py:53-156`; `mbl.py:108-114`; `diagnostico_ia.py:133-157`. Em contraste, `diagnostico.py:105-106` e `dlg.py:148-151` filtram corretamente.
- **Impacto**: cancelamento de CT-e (RN-08) marca `status='CANCELADO'` mas não zera valores financeiros (`repositories/__init__.py:812-827`). O mesmo período/rota/transportadora produz R$/kg, %frete, score e "economia potencial" diferentes entre o Diagnóstico (correto) e todo o resto do sistema (contaminado) — inclusive o MBL, que se declara "Source of Truth" e alimenta o MCL.
- **Recomendação**: centralizar a leitura analítica de CT-e em um ponto único (`listar_ctes_para_analise(empresa_id, ..., apenas_ativos=True por padrão)`) e migrar os 8 módulos afetados. Adicionar teste de regressão com CT-e cancelado presente, comparando totais entre telas.

---

**IMP-01 — Deduplicação de CT-e por chave é global entre empresas, não isolada por tenant**
- **Módulo**: Importação XML. **RN**: RN-02, RN-59.
- **Evidência**: `importacao.py:77` chama `cte_repo.get_by_chave(chave)` sem `empresa_id`; `repositories/__init__.py:398-400` confirma ausência do filtro; `models/__init__.py:165` — constraint `UNIQUE(chave)` na tabela inteira, não composta com `empresa_id`. O fluxo de cancelamento, em contraste, usa corretamente `get_model_by_chave_empresa`.
- **Impacto**: se uma chave de 44 dígitos já foi importada por **qualquer** empresa da plataforma, nenhuma outra empresa consegue importar CT-e com essa chave — falha silenciosa contabilizada como "duplicado", sem aviso de que pertence a outro tenant. Relevante para contas de demonstração, grupos econômicos com múltiplos tenants, ou migração entre ambientes.
- **Recomendação**: `get_by_chave` deve receber e filtrar por `empresa_id`; migrar constraint para `UNIQUE(empresa_id, chave)`.

---

**IMP-02 — Chave sintética de dedup do Excel depende da posição da linha, não do conteúdo**
- **Módulo**: Importação Excel. **RN**: RN-06.
- **Evidência**: `importacao.py:125,172` — `chave_sintetica = f"EXCEL-{empresa_id}-{linha.nota_fiscal}-{i}"`, onde `i` é o índice da linha no arquivo.
- **Impacto**: reenvio de planilha corrigida com linhas inseridas/removidas/reordenadas muda o índice `i` de notas já importadas — o sistema reimporta essas notas como registros novos, duplicando valores financeiros, sem exigir nem sinalizar isso ao usuário (só é evitado se o cliente marcar explicitamente `atualizar_existentes=True`).
- **Recomendação**: usar chave de negócio estável (nota fiscal + hash dos campos), independente da posição da linha — replicando a lógica que `buscar_excel_existente` já usa no modo de atualização.

---

**MCL-02 — Referência MBL usada no motor de decisão é uma média nacional, desconectada do segmento real do BID**
- **Módulo**: MCL. **RN**: RN-34, RN-35, RN-36.
- **Evidência**: `mcl.py:175-185` (`_mbl_p50`) — média simples dos P50 regionais de R$/kg, sem relação com a segmentação (região/UF/transportadora/filial/faixa de peso) do BID em questão.
- **Impacto**: pode **rejeitar** (RN-35, corte de +20%) uma proposta competitiva para um corredor estruturalmente caro, ou **premiar** (score MBL) uma proposta ruim para um corredor estruturalmente barato — risco direto à escolha da transportadora vencedora.
- **Recomendação**: derivar a referência MBL da dimensão/segmentação efetiva do escopo gerado para aquele BID, não de uma média nacional agregada.

---

**MCL-03 — Decisão MCL pode ser recalculada e versionada sem checar o estado do BID**
- **Módulo**: MCL. **RN**: RN-37, RN-38.
- **Evidência**: `mcl.py` (endpoints `GET/POST /mcl/{bid_id}/decidir`, `mcl.py:39-63`) e `mcl.py:88-97` (`decidir`) só checam existência do BID e presença de propostas — nenhuma checagem de `bid.status`.
- **Impacto**: combinado com BID-04, permite gerar uma nova "decisão oficial" versionada sobre um BID já `ENCERRADO`/`CANCELADO`, sem passar pela transição formal de estado — mina a integridade do histórico usado para justificar a troca de transportadora.
- **Recomendação**: bloquear `decidir(persistir=True)` fora dos estados válidos (`EM_COTACAO`/`ENCERRADO`, conforme definição de negócio).

---

**MCL-04 / BID-07 — Dupla contagem de peso/frete quando o BID tem escopo gerado em mais de um `tipo_agrupamento`**
- **Módulos**: MCL (simulação) e BID (economia). **RN**: RN-40, RN-42.
- **Evidência**: `repositories/__init__.py:1263-1265` (`list_by_bid` retorna todas as linhas de `bid_escopos`, sem filtrar por `tipo_agrupamento`); `bid_escopo.py:68-72` (regeneração só apaga o mesmo tipo, tipos diferentes coexistem); `mcl.py:298-304` e `bid_economia.py:162` somam irrestrito.
- **Impacto**: cada `tipo_agrupamento` é uma decomposição completa e alternativa do mesmo universo de CT-es — gerar escopo em mais de um agrupamento para o mesmo BID (fluxo não bloqueado hoje) soma o mesmo frete/peso múltiplas vezes, inflando `peso_total_kg`, `custo_total_simulado` e "economia potencial" apresentados ao cliente.
- **Recomendação**: toda agregação sobre `bid_escopos` deve filtrar por um único `tipo_agrupamento` canônico do BID, ou os endpoints devem receber explicitamente qual agrupamento usar como base.

---

**BID-01 — Escopo do BID não filtra CT-es cancelados**
- **Módulo**: BID. **RN**: RN-42 (e princípio da RN-09).
- **Evidência**: `bid_escopo.py:112-124` (`_base_query`) filtra só `empresa_id` e data — sem `status == "ATIVO"`, ao contrário do padrão já usado no DLG.
- **Impacto**: CT-es cancelados entram no `peso_total`/`valor_frete_total` usado como baseline "atual" de comparação contra propostas — distorce a economia calculada (RN-40) e a competitividade aparente de cada proposta.
- **Recomendação**: adicionar `CTeModel.status == "ATIVO"` em `_base_query`.

---

**BID-04 — Escopo, convites e propostas podem ser alterados mesmo com BID `ENCERRADO`/`CANCELADO`**
- **Módulo**: BID. **RN**: RN-38, RN-39.
- **Evidência**: `gerar_escopo`, `convidar_transportadora`, `incluir_proposta`, `importar_propostas_excel` (`bid.py:204-229, 282-306, 365-386, 482-560`) dependem só de `get_bid_com_acesso` + `bloquear_visualizador` — nenhum verifica `bid.status`.
- **Impacto**: permite, na prática, reabrir um BID já fechado (novas propostas, novos convites, escopo recalculado) sem transição formal de estado — combinado a MCL-03, permite gerar uma nova decisão "oficial" sobre um processo supostamente encerrado.
- **Recomendação**: adicionar checagem de status nesses endpoints, espelhando a trava já existente para edição de BID encerrado.

---

**IA-01 — `eval()` "restrito" de regras de insights não é uma sandbox segura**
- **Módulo**: Inteligência IA (Insights automáticos). **RN**: RN-51.
- **Evidência**: `insights.py:209-216` — `eval(expressao, {"__builtins__": {}}, ctx)`.
- **Impacto**: remover `__builtins__` não impede acesso a `os`/`subprocess` via introspecção de objetos literais (`().__class__.__base__.__subclasses__()...`) — técnica clássica de bypass, independente de builtins. **Mitigador confirmado**: hoje não existe nenhum endpoint que exponha edição de `RegraInsightModel.expressao` — só as 4 regras seed hardcoded chegam ao `eval()`, então não há exploração possível via API pública atualmente.
- **Recomendação**: antes de expor qualquer tela de administração de regras (já sugerida no desenho do módulo), substituir por parser de expressão real restrito (`asteval`/`simpleeval`/AST customizado).

---

### Achados P2 — Médio

| Código | Módulo | RN | Achado | Recomendação |
|---|---|---|---|---|
| CONS-02 | Indicadores | RN-10, RN-12 | Fórmula de agregação regional (R$/kg, %frete) reimplementada de forma independente em ≥4 módulos | Extrair para função/serviço único, reutilizado por todos |
| CONS-03 | Indicadores/Benchmark | RN-09 | `BenchmarkUseCase` ainda usa métodos legados em memória do `DiagnosticoUseCase`, já abandonados pelo fluxo principal — é a causa raiz técnica de CONS-01 no Benchmark legado | Migrar Benchmark para consumir as versões SQL com `apenas_ativos=True`, ou remover os métodos legados |
| DIAG-01 | Diagnóstico | RN-11 | "OTIF" documentado não é OTIF real (sem data prometida por CT-e; é aderência a meta regional); tratamento de prazo negativo diverge entre Diagnóstico e Indicadores V2 | Renomear/documentar como "aderência de prazo/SLA"; padronizar exclusão de prazos negativos em todos os módulos |
| MBL-03 | MBL | RN-33 | Versionamento incremental sem retenção histórica real — constraint única exclui `versao`, reprocessamentos anteriores são irrecuperáveis apesar do contador sugerir histórico | Mover `versao` para o índice único com flag `vigente`, ou ajustar a documentação/docstring |
| MCL-01 | MCL | RN-35, RN-36 | Normalização de custo/prazo calculada incluindo propostas que serão rejeitadas por preço abusivo, inflando o score das elegíveis | Calcular limites de normalização só sobre o subconjunto elegível |
| BID-02 | BID | RN-39 | Exclusão de proposta, remoção de transportadora e regeração de escopo não geram registro em `bid_auditorias`, ao contrário de convite/proposta/simulação | Padronizar log de auditoria em toda operação de escrita relevante, inclusive DELETE |
| BID-03 | BID | RN-38 | `CANCELADO` não bloqueia edição/exclusão do BID (só `ENCERRADO` é checado) | Bloquear também para `CANCELADO`, ou documentar a assimetria como intencional |
| BID-05 | BID | RN-40, RN-41 | Importação de propostas via Excel ignora validações do schema (`cobertura_pct` 0-100, `prazo_dias`>0) | Validar essas faixas também no fluxo de importação Excel |
| IA-02 | IA | RN-50 | Duas fórmulas divergentes de "economia potencial anualizada": excesso×peso×12 (Insights/Oportunidades) vs. heurística derivada do score×0,5 (Diagnóstico IA/Assistente) — mesmo rótulo, valores diferentes no relatório executivo | Unificar em uma única função de cálculo, reutilizada pelos 4 pontos |
| IA-03 | IA | qualitativa | Narrativa livre do LLM não passa por validação numérica pós-geração contra o contexto de origem | Extrair valores numéricos do texto e comparar contra o contexto antes de persistir/exibir |
| IA-05 | IA | qualitativa | RAG permite que qualquer usuário da própria empresa indexe conteúdo livre injetado no prompt de sistema do assistente — risco de manipulação interna (não há vazamento entre empresas) | Moderar conteúdo antes de indexar; restringir indexação manual a papéis administrativos |

### Achados P3 — Baixo

| Código | Módulo | Achado |
|---|---|---|
| IMP-03 | Importação | `MAX_CTE_BATCH` configurado para 10.000, mas o limite real de 500 vem de constante hardcoded no router — inofensivo hoje, mas enganoso para novos consumidores do use case |
| IMP-04 | Importação | Fallback do tomador do CT-e cai para o destinatário quando `toma3`/`toma4` ausentes — pode atribuir CNPJ incorreto em XML fora do padrão (cenário raro) |
| IMP-05 | Importação | RN-03 implementada por inclusão de palavra-chave, não por exclusão explícita de `cUnid` como o texto da regra sugere — resultado prático idêntico nos casos reais |
| BENCH-04 | Benchmark legado | Fórmula de `n_meses` no código usa `dias+1` (inclusivo), não documentado na RN-16 |
| DLG-01 | DLG | Outlier RS_KG_2DP usa desvio-padrão amostral (`stdev`, n-1), não populacional — mais permissivo em lotes pequenos |
| DLG-02 | DLG | Meta regional cadastrada como `0` é tratada como "ausente" (falsy trap do Python), caindo para outra referência silenciosamente |
| MBL-02 | MBL | Campo `outliers_excluidos` reporta total do período inteiro, não do segmento específico da linha |
| V2-01 | Benchmark V2 | Seleção da linha "mais genérica" de `benchmark_mercado` não filtra `tipo_operacao`, só ordena por faixa de peso |
| V2-02 | Benchmark V2 | Lógica de faixa (RN-23) duplicada em `comparar()` e `faixa_de()` — risco de manutenção, não de bug atual |
| BID-06 | BID | Normalização min-max com 1 única proposta atribui 100 pontos automaticamente — comportamento correto da fórmula, mas sem aviso de "não comparativo" na UI |
| IA-04 | IA | Nomes de transportadora/filial (dado de terceiro) injetados sem sanitização no contexto do LLM — risco de prompt injection indireto, mitigado por tools serem só-leitura |
| IA-06 | IA | Prompt final enviado ao LLM não é persistido — rastreabilidade forense incompleta para o Diagnóstico IA |
| IA-07 | IA | RN-49(4) confirmado como placeholder inerte (variação mensal sempre 0, regra nunca dispara) — consistente com a documentação, mas visível na lista de regras "ativas" sem aviso |

## 6. Avaliação da Confiabilidade dos Indicadores

**Os indicadores podem ser usados para decisões executivas, com uma ressalva importante.** Dentro de um único módulo, a matemática é confiável — percentis, scores e classificações batem com a fórmula documentada. O risco real está em **comparar dois módulos entre si**: sempre que houver CT-e cancelado no período (algo comum, não uma exceção), Diagnóstico, Dashboard Executivo, Benchmark e Score vão divergir silenciosamente para o mesmo recorte de dado. Recomenda-se resolver CONS-01 antes de tratar qualquer comparação entre telas como equivalente — e, especificamente para BID/MCL, resolver MCL-02/MCL-04/BID-01/BID-04 antes de tratar a "economia estimada" apresentada ao cliente como um número auditável.

## 7. Avaliação da Proposta de Valor

**Sim, a plataforma entrega uma análise de governança de frete real, não apenas consolidação de dados.** DLG, MBL, MCL e Recomendações vão além de um dashboard passivo: detectam outlier estatisticamente, comparam contra referência de mercado segmentada, rankeiam propostas de transportadora com score multi-critério, e geram plano de ação priorizado — isso é o comportamento esperado de uma ferramenta de decisão, não de um relatório. A camada de IA reforça essa proposta ao interpretar (sem calcular) esses números para um público não técnico.

O risco à proposta de valor não está na ambição analítica — está na ausência de uma camada única de acesso a dados analíticos (causa raiz de CONS-01/02/03), que faz o sistema "parecer" inconsistente exatamente no momento em que um cliente compara duas telas para validar um número antes de agir sobre ele.

## 8. Roadmap Funcional

### Curto prazo
- **CONS-01**: centralizar o filtro `status=ATIVO` num único ponto de leitura de CT-e para fins analíticos, corrigindo os 8 módulos afetados.
- **IMP-01**: isolar deduplicação de CT-e por `empresa_id` (constraint composta).
- **IMP-02**: chave de dedup do Excel independente da posição da linha.
- **BID-01, BID-04, MCL-03**: filtro de status ativo no escopo do BID; travar escopo/propostas/decisão contra estados terminais do BID.
- **IA-02**: unificar a fórmula de "economia potencial anualizada" num único ponto.

### Médio prazo
- **CONS-02/03**: extrair agregação regional para serviço único; eliminar dependência do Benchmark nos métodos legados do Diagnóstico.
- **MCL-01/MCL-02**: corrigir contaminação de normalização por propostas rejeitadas; segmentar a referência MBL usada no MCL.
- **MBL-03**: decidir entre reter histórico real de versões ou ajustar a documentação para não sugerir isso.
- **BID-02/BID-03/BID-05**: completar cobertura de auditoria; travar edição de BID cancelado; validar campos na importação Excel de propostas.

### Longo prazo
- **IA-01**: substituir `eval()` por parser de expressão real antes de expor qualquer tela de edição de regras de insight.
- **IA-03/IA-05/IA-06**: validação numérica pós-geração da narrativa do LLM; moderação de conteúdo indexado no RAG; persistência do prompt final para auditoria forense.
- **DIAG-01**: renomear/documentar "OTIF" como aderência de prazo/SLA; padronizar tratamento de prazo negativo entre todos os módulos que calculam lead time.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhum código, cálculo ou regra foi alterado durante esta auditoria — todos os achados (FUNC-P1 a FUNC-P3) ficam pendentes de autorização explícita para implementação em fase futura.*
