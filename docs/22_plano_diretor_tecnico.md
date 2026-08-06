# 22 · Plano Diretor Técnico do GD Frete Diagnóstico

> **Natureza deste documento**: não é uma nova auditoria — é a consolidação executiva das 9 fases de auditoria realizadas em 2026-07-07 (Fase 0 — Consolidação da Documentação; Fases 1 a 8 — Arquitetura, Qualidade de Código, Performance, Banco de Dados, Segurança, UX/UI, Funcional/Regras de Negócio, Produto SaaS). Nenhum código, arquitetura, banco de dados ou infraestrutura foi alterado na produção deste documento. Toda nota, achado e recomendação aqui citados remetem a um relatório de fase já aprovado como diagnóstico oficial — este documento não introduz achado novo, apenas organiza, prioriza e sequencia o que já foi encontrado. Fontes: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md), [`14`](14_fase1_auditoria_arquitetural.md) a [`21`](21_fase8_produto_saas.md), [`10_roadmap.md`](10_roadmap.md), [`11_changelog.md`](11_changelog.md).
>
> **Revisão estratégica (2026-07-08)**: este documento incorpora agora as Seções 12 a 21 e 24, formalizando a visão estratégica do produto, os perfis de usuário, os princípios do produto, a visão arquitetural conceitual, a estratégia de evolução, o processo oficial de desenvolvimento, o papel do Relatório Executivo HTML, os princípios arquiteturais reforçados, a política de versionamento e a governança do produto. Nenhum conteúdo técnico das Seções 1-11 foi alterado, removido ou reinterpretado nesta revisão. Ver histórico completo logo abaixo.
>
> **Camada de governança do projeto (2026-07-08)**: o conteúdo estratégico das Seções 12-21 foi consolidado, de forma concisa e permanente, em [`00_contexto_oficial.md`](00_contexto_oficial.md) — o novo documento mestre e principal referência oficial do projeto. Em caso de divergência futura entre os dois, `00_contexto_oficial.md` prevalece como definição oficial, e este Plano Diretor Técnico deve ser atualizado no mesmo ciclo. Ver também [`README_AI.md`](README_AI.md) para o processo oficial de desenvolvimento e a ordem obrigatória de leitura por agentes de IA.

## Histórico de Revisões deste Documento

| Versão | Data | Natureza | O que mudou |
|---|---|---|---|
| v1.0 | 2026-07-07 | Consolidação técnica (Fase 9) | Documento original: consolidação executiva das Fases 0-8 — nota geral, os 20 problemas mais importantes, dívida técnica consolidada, ordem ideal de implementação (12 etapas), roadmap de 24 meses, escalabilidade e preparação comercial (Seções 1-11 e antigas 12-14). |
| v1.0.1 | 2026-07-07 | Atualização de acompanhamento | Seção 8 (Etapa 1) atualizada para registrar a conclusão de CONS-01 na v6.6.0, conforme `11_changelog.md` [6.6.0]. |
| v1.1 | 2026-07-08 | Revisão estratégica | Adicionadas as Seções 13-21 e 24 (perfis de usuário, princípios do produto, visão arquitetural conceitual, estratégia de evolução, processo oficial de desenvolvimento, papel do Relatório Executivo HTML, princípios arquiteturais reforçados, política de versionamento, governança do produto, confirmação de compatibilidade e ajustes futuros recomendados). A antiga Seção 12 (Visão Estratégica do Produto) foi reformulada para expressar o posicionamento estratégico oficial do produto — a nota de revisão dentro da própria seção explica o que mudou e por quê. As antigas Seções 13 e 14 (Recomendações Estratégicas, Conclusão Final) foram renumeradas para 22 e 23, com conteúdo preservado e um adendo estratégico ao final da Seção 23. **Nenhum conteúdo das Seções 1-11 foi alterado. Nenhuma arquitetura, roadmap técnico, regra de negócio, API, schema ou item de dívida técnica foi modificado nesta revisão** — ver confirmação formal na Seção 24. |
| **v1.2 (atual)** | 2026-08-06 | Registro de decisão comercial | Seção 16 (Estratégia de Evolução do Produto) ganhou a subseção "Atualização (2026-08-06) — decisão comercial tomada", registrando que a GD Conecta decidiu iniciar a Fase Posterior e priorizar um primeiro recorte do Portal do Cliente, avaliado contra o checklist de Governança do Produto (Seção 21). Ver Validação Estratégica e PRD em `specs/v6.18.0/`. **A Regra de Priorização da Seção 16 não foi revogada, nenhuma outra seção foi alterada, e nenhum código, schema, API ou item do roadmap técnico (Seções 8-9) foi modificado nesta revisão** — a Especificação Técnica correspondente ainda está pendente. |

## Índice

1. [Resumo Executivo](#1-resumo-executivo)
2. [Nota Geral da Plataforma](#2-nota-geral-da-plataforma)
3. [Panorama Geral da Plataforma](#3-panorama-geral-da-plataforma)
4. [Os 20 Problemas Mais Importantes](#4-os-20-problemas-mais-importantes)
5. [O Que Deve Ser Corrigido Antes da Expansão Comercial](#5-o-que-deve-ser-corrigido-antes-da-expansão-comercial)
6. [O Que Pode Esperar](#6-o-que-pode-esperar)
7. [Dívida Técnica Consolidada](#7-dívida-técnica-consolidada)
8. [Ordem Ideal das Implementações](#8-ordem-ideal-das-implementações)
9. [Roadmap dos Próximos 24 Meses](#9-roadmap-dos-próximos-24-meses)
10. [Escalabilidade](#10-escalabilidade)
11. [Preparação Comercial](#11-preparação-comercial)
12. [Visão Estratégica do Produto](#12-visão-estratégica-do-produto) *(reformulada em 2026-07-08)*
13. [Perfis de Usuários da Plataforma](#13-perfis-de-usuários-da-plataforma) *(novo)*
14. [Princípios do Produto](#14-princípios-do-produto) *(novo)*
15. [Visão Arquitetural Conceitual](#15-visão-arquitetural-conceitual) *(novo)*
16. [Estratégia de Evolução do Produto](#16-estratégia-de-evolução-do-produto) *(novo)*
17. [Processo Oficial de Desenvolvimento](#17-processo-oficial-de-desenvolvimento) *(novo)*
18. [O Relatório Executivo HTML como Artefato Central](#18-o-relatório-executivo-html-como-artefato-central) *(novo)*
19. [Princípios Arquiteturais Reforçados](#19-princípios-arquiteturais-reforçados) *(novo)*
20. [Política de Versionamento](#20-política-de-versionamento) *(novo)*
21. [Governança do Produto](#21-governança-do-produto) *(novo)*
22. [Recomendações Estratégicas](#22-recomendações-estratégicas) *(antiga Seção 13, preservada)*
23. [Conclusão Final](#23-conclusão-final) *(antiga Seção 14, preservada + adendo estratégico)*
24. [Confirmação de Compatibilidade e Ajustes Futuros Recomendados](#24-confirmação-de-compatibilidade-e-ajustes-futuros-recomendados) *(novo)*

---

## 1. Resumo Executivo

O GD Frete Diagnóstico é uma plataforma tecnicamente madura em sua fundação e **inconsistente em governança de dados entre módulos** — esse é o resumo de nove fases de auditoria em uma frase. A arquitetura (Clean Architecture, multi-tenancy real, RBAC de três papéis) suportou cinco gerações de módulo sem reescrita, e as fórmulas de negócio (DLG, MBL, MCL, Score, Insights) batem quase integralmente com o que está documentado. Isso não é pouco: é a diferença entre um produto que precisa ser reconstruído e um produto que precisa ser **arrumado com precisão cirúrgica em pontos conhecidos**.

O padrão que atravessa as nove fases, porém, é sempre o mesmo tipo de defeito, em domínios diferentes: **uma regra correta, aplicada de forma inconsistente entre os módulos que deveriam compartilhá-la.** Isso apareceu como RN-09 (filtro de CT-e ativo) não propagada a 8 módulos analíticos (Fase 7), como RBAC de VISUALIZADOR esquecido em 3 endpoints de cluster (Fase 5), como padrão de repositório abandonado em 16 de 25 use cases (Fase 1), como cobertura de logging em só 44% dos use cases (Fase 2), como ausência de identidade visual justamente na única tela que todo prospect vê primeiro (Fase 6). O sistema não tem um problema de "não saber a coisa certa a fazer" — tem um problema recorrente de **não aplicar a coisa certa em todo lugar onde ela deveria estar**, e isso é, ao mesmo tempo, a notícia mais tranquilizadora (a correção é conhecida, não é pesquisa) e o padrão de risco mais importante a vigiar daqui para frente.

O achado mais crítico de todo o programa de auditoria é o **CONS-01** (Fase 7): a exclusão de CT-e cancelado dos totais financeiros — a regra mais fundamental do sistema analítico — foi implementada corretamente apenas no módulo original (Diagnóstico/DLG) e nunca propagada a Benchmark (em todas as suas 3 gerações), MBL, Score Logístico, Insights, Oportunidades e Diagnóstico IA. Isso significa que, hoje, **duas telas do mesmo sistema podem mostrar números diferentes para o mesmo mês, a mesma rota, a mesma transportadora**, sempre que existir cancelamento no período — algo comum, não excepcional. Diretamente relacionado, o motor de decisão de BID (MCL) — o módulo com maior potencial de venda ("comprove economia trocando de transportadora") — carrega quatro achados que comprometem esse número específico (MCL-02, MCL-04/BID-07, BID-01, BID-04, Fase 7).

O segundo achado mais crítico é novo, revelado só na Fase 8: **não existe nenhuma base técnica de plano ou licenciamento** — `EmpresaModel` não tem campo de plano, limite de usuário, limite de volume ou módulo contratado, e a criação de uma nova empresa-cliente não exige superusuário (qualquer ADMIN de qualquer empresa pode chamar `POST /empresas`). Isso não é um bug — é a ausência completa de uma peça que qualquer expansão comercial além de um punhado de clientes bem conhecidos manualmente vai exigir.

A plataforma está pronta para operar como SaaS **com um modelo de venda consultivo, a dezenas de clientes bem acompanhados** — não para uma expansão agressiva ou self-service. Nenhum dos achados críticos exige descobrir algo novo: as nove fases já mapearam exatamente o quê corrigir, onde, e em que ordem (Seções 4 e 8 deste documento).

## 2. Nota Geral da Plataforma

### Metodologia

Cada uma das 8 fases técnicas produziu uma nota de 0 a 100 numa dimensão distinta, com a mesma metodologia (leitura direta do código-fonte, mesma data-base, mesmo padrão de classificação de achados por prioridade). A nota geral consolidada é a **média aritmética simples das 8 notas de fase**, sem peso diferenciado entre dimensões — a mesma escolha metodológica usada em cada fase individual para não injetar um julgamento subjetivo novo que nenhuma das nove fases originais fez.

| # | Dimensão | Nota | Fonte |
|---|---|---|---|
| 1 | Arquitetura | 66/100 | [`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md) |
| 2 | Qualidade do Código | 67/100 | [`15_fase2_qualidade_codigo.md`](15_fase2_qualidade_codigo.md) |
| 3 | Performance | 62/100 | [`16_fase3_performance.md`](16_fase3_performance.md) |
| 4 | Banco de Dados | 64/100 | [`17_fase4_banco_de_dados.md`](17_fase4_banco_de_dados.md) |
| 5 | Segurança | 71/100 | [`18_fase5_seguranca.md`](18_fase5_seguranca.md) |
| 6 | UX/UI | 67/100 | [`19_fase6_ux_ui.md`](19_fase6_ux_ui.md) |
| 7 | Funcional / Regras de Negócio | 64/100 | [`20_fase7_auditoria_funcional.md`](20_fase7_auditoria_funcional.md) |
| 8 | Produto SaaS | 60/100 | [`21_fase8_produto_saas.md`](21_fase8_produto_saas.md) |

# **Nota Geral: 65 / 100**

**Leitura complementar por risco de negócio** (não substitui a nota geral, contextualiza-a): as três dimensões com maior consequência direta e imediata para o cliente pagante — Segurança (71), Funcional (64) e Produto SaaS (60) — já estão entre as notas mais analisadas e corrigíveis do conjunto; nenhuma está criticamente baixa isoladamente, mas Produto SaaS é a mais baixa das oito, e é também a que trata diretamente da pergunta "isso escala comercialmente?".

### Classificação de Maturidade

| Faixa | Classificação |
|---|---|
| 90-100 | Excelente |
| 80-89 | Muito Bom |
| 70-79 | Bom |
| 55-69 | Em evolução |
| < 55 | Imaturo |

**O GD Frete Diagnóstico está classificado como "Em Evolução" (65/100).** Não é "Imaturo" — nenhuma dimensão ficou abaixo de 60, a fundação arquitetural é real e as fórmulas de negócio majoritariamente batem com a documentação. Não é "Bom" ainda — para chegar lá, a plataforma precisa fechar a lacuna de consistência de dado entre módulos (CONS-01 e correlatos) e construir a peça de modelo comercial que hoje não existe (EMPRESA-01/02), ambas endereçáveis sem redesenho.

## 3. Panorama Geral da Plataforma

**Áreas de maior maturidade** (consolidadas, risco residual baixo):
- **Segurança de autenticação/autorização** (71/100, Fase 5) — cookie `httpOnly`, RBAC de 3 papéis, isolamento multi-tenant de aplicação, rate limiting, proteção XML Bomb — tudo já corrigido e verificado numa rodada anterior de correção (v6.5.0/6.5.1), com só uma regressão pontual (SEC-01) e lacunas de auditoria (SEC-02/03) pendentes, ambas triviais de corrigir.
- **Modelagem de dados e índices** (Fase 4) — 44 tabelas, nenhuma FK solta, índices presentes exatamente onde a aplicação mais consulta, cadeia de migrations limpa.
- **DLG — Diagnóstico Logístico Analítico** (Fase 7) — o módulo mais maduro de todo o backend: todas as RN-25 a RN-29 confirmadas, dedup de transportadora por identidade real, único módulo que corretamente propaga o filtro de CT-e ativo desde a origem.
- **Recomendações** (Fase 7, 90/100) — upsert idempotente que preserva corretamente o status editado manualmente pelo usuário, testado e confirmado.

**Áreas de maior risco** (requerem ação, não observação):
- **Consistência de dado entre módulos analíticos** (CONS-01, Fase 7) — o achado transversal mais grave de toda a auditoria.
- **Motor de decisão de BID/MCL** (Fase 7) — quatro achados P1 comprometendo justamente o número mais vendável da plataforma.
- **Modelo comercial/licenciamento** (Fase 8) — ausente por completo, não é uma questão de correção pontual, é uma peça a construir.
- **Concorrência de infraestrutura sob múltiplos tenants** (Fases 3/4) — pool de 30 conexões e 2 workers compartilhados por toda a plataforma; hoje folgado, torna-se a primeira restrição real ao crescer.

**Áreas já consolidadas o suficiente para não exigir nova rodada de auditoria no curto prazo**: autenticação/cookie, modelagem de banco, RBAC de aplicação, DLG, Recomendações, arquitetura de camadas dos módulos originais (cadastro, importação, diagnóstico clássico, BID em sua máquina de estados principal).

## 4. Os 20 Problemas Mais Importantes

Consolidado de **quase 100 achados técnicos distintos** identificados ao longo das 9 fases (após eliminar duplicidade entre relatórios — vários achados foram identificados independentemente por mais de uma fase, o que reforça sua validade em vez de inflar a contagem). Ordenados pelo impacto combinado em confiabilidade de decisão, risco comercial/reputacional e segurança — não necessariamente pela ordem de execução mais eficiente (essa está na Seção 8).

| # | Código | Origem | Descrição | Impacto | Risco | Benefício da correção | Depende de |
|---|---|---|---|---|---|---|---|
| 1 | **CONS-01** | Fase 7 | RN-09 (excluir CT-e cancelado) não propagada a ~8 módulos analíticos (Benchmark×3, MBL, Score, Insights, Oportunidades, Diagnóstico IA) | Duas telas mostram números diferentes para o mesmo dado | Crítico — mina a confiança em qualquer comparação entre telas | Restaura consistência numérica em toda a plataforma de uma vez | Nenhuma — é o item raiz de que outros dependem |
| 2 | **EMPRESA-01** | Fase 8 | Zero base técnica de plano/licenciamento em `EmpresaModel` | Impossível diferenciar comercialmente clientes hoje | Crítico — bloqueia expansão comercial estruturada | Habilita precificação por plano/módulo | Nenhuma |
| 3 | **EMPRESA-02** | Fase 8 | `POST /empresas` aceita qualquer ADMIN, não só superusuário | Onboarding de cliente é chamada de API aberta, sem controle comercial | Crítico | Onboarding vira etapa controlada de processo de venda | Nenhuma |
| 4 | **MCL-02** | Fase 7 | Referência MBL do motor de decisão é média nacional, desconectada do corredor do BID | Pode rejeitar proposta boa ou premiar proposta ruim | Alto — decisão de troca de transportadora equivocada | Corrige o núcleo do argumento comercial do BID | Item 1 (MBL precisa estar limpo de CT-e cancelado antes) |
| 5 | **MCL-04 / BID-07** | Fase 7 | Dupla contagem de peso/frete com múltiplos agrupamentos de escopo do BID | Economia/custo inflados nos números apresentados ao cliente | Alto | Números de economia do BID tornam-se auditáveis | Independente |
| 6 | **BID-01** | Fase 7 | Escopo do BID sem filtro de CT-e ativo | Baseline "atual" de comparação distorcido | Alto | Consistente com item 1 | Item 1 |
| 7 | **BID-04 / MCL-03** | Fase 7 | Escopo/propostas/decisão do BID editáveis após estado terminal | Permite "reabrir" um processo de decisão supostamente encerrado | Alto | Integridade do histórico de decisão de BID | Independente |
| 8 | **IMP-01** | Fase 7 | Deduplicação de CT-e por chave é global entre empresas, não por tenant | Perda silenciosa de importação entre clientes diferentes | Alto — quebra de isolamento multi-tenant | Fecha lacuna de RN-59 na importação | Independente |
| 9 | **IMP-02** | Fase 7 | Chave sintética de dedup do Excel depende da posição da linha | Duplicação de valores financeiros ao reimportar planilha reordenada | Alto | Elimina risco de dado financeiro duplicado | Independente |
| 10 | **SEC-02 / SEC-03** | Fase 5 | Gestão de usuários e exclusão de dados sem log de auditoria | Sem rastreabilidade da ação mais sensível do sistema | Alto (governança) | Rastreabilidade forense completa | Independente, trivial |
| 11 | **SEC-01** | Fase 5 | Endpoints de cluster sem bloqueio de VISUALIZADOR | Regressão de RBAC — usuário de leitura consegue escrever | Alto (segurança), esforço trivial | Fecha a última lacuna de RBAC conhecida | Independente |
| 12 | **BD-01** | Fase 4 | Valores monetários como `Float`, nunca `Numeric`/`Decimal` | Erro de arredondamento acumulado em relatórios financeiros | Alto, cresce com volume | Precisão de centavo garantida num produto de auditoria financeira | Quanto mais cedo, mais barato (volume histórico só cresce) |
| 13 | **A-06 / PF-01** | Fases 1/3 | `GET /dashboard/{empresa_id}` carrega todos os CT-e em memória para 2 de 5 componentes | Risco direto de timeout com alto volume por empresa | Alto, é o endpoint mais usado do sistema | Elimina o único achado com risco de falha visível ao usuário | Independente |
| 14 | **A-07 / PF-02 / BD-05** | Fases 1/3/4 | Índice composto crítico de `ctes` ausente no caminho `create_all()` | Divergência de performance entre dev e produção | Alto, esforço trivial | Paridade real dev/produção | Independente |
| 15 | **PF-08 / BD-11** | Fases 3/4 | Pool de conexão modesto (30 total) compartilhado por todos os tenants | Primeira variável a estourar com crescimento de uso simultâneo | Alto em escala | Aumenta o teto real de concorrência multi-tenant | Depende de decisão de nº de clientes-âncora esperado |
| 16 | **PF-07** | Fase 3 | Relatórios e importação síncronos competem pelos mesmos 2 workers entre **todos** os tenants | Um cliente com lote grande pode atrasar outro cliente | Alto (efeito "vizinho barulhento") | Isola o impacto de operações pesadas por tenant | Depende de Celery já disponível na stack |
| 17 | **BD-04** | Fases 1/4 | Migrations Alembic ausentes para as 15 tabelas de Inteligência IA | Deploy de produção só com `alembic upgrade head` fica sem o módulo de IA | Alto para qualquer novo ambiente dedicado | Reprodutibilidade real de schema | Independente, esforço médio (autogenerate + validação) |
| 18 | **A-09 / PF-04** | Fases 1/3 | Zero code-splitting no frontend (~44 páginas num bundle único) | Tempo de carregamento inicial cresce a cada módulo novo, para todo usuário | Médio-Alto, cumulativo | Carregamento inicial proporcional ao uso real | Independente |
| 19 | **A-10 / PF-05** | Fases 1/3 | Adoção de React Query cobre só ~7% das telas | Requisições redundantes, sem cache compartilhado | Médio-Alto, cresce com usuários simultâneos | Reduz carga redundante no backend | Independente |
| 20 | **UX-01** | Fase 6 | Tela de login sem nenhuma identidade visual do produto | Primeira impressão de qualquer demonstração comercial | Médio (mas altíssima visibilidade comercial) | Reforça percepção de valor desde o primeiro contato | Independente, esforço baixo |

## 5. O Que Deve Ser Corrigido Antes da Expansão Comercial

### Obrigatório
*(sem isso, vender em maior escala é assumir risco material de dado, dinheiro ou reputação)*

- **CONS-01** (#1) — nenhum número apresentado a um cliente novo deve depender de qual tela ele está olhando.
- **EMPRESA-01, EMPRESA-02** (#2, #3) — sem isso, cada cliente novo é uma exceção manual, não um processo repetível.
- **Cluster MCL/BID** (#4-#7) — o argumento de venda mais forte ("comprove economia") não pode ser vendido como número auditável até esses quatro estarem corrigidos.
- **IMP-01, IMP-02** (#8, #9) — trazer clientes novos sem isso é risco direto de perda ou duplicação de dado fiscal logo na primeira importação.
- **SEC-01, SEC-02, SEC-03** (#10, #11) — já aprovados como achados oficiais desde a Fase 5, triviais de corrigir, sem justificativa técnica para adiar.

### Recomendável
*(reduz risco real, mas a plataforma pode operar sem, com atenção manual próxima)*

- **BD-01** (#12) — quanto mais cedo, mais barato; adiar só aumenta o volume de dado histórico que precisará de migração.
- **A-06/PF-01, A-07/PF-02/BD-05** (#13, #14) — nenhum dos dois é incêndio hoje, mas são os dois achados de performance com risco mais direto de virar timeout perceptível ao usuário conforme o volume de CT-e por cliente cresce.
- **BD-04** (#17) — resolver antes do primeiro cliente que exigir instância própria ou deploy formal só via Alembic.

### Desejável
*(melhora a experiência e a eficiência operacional, sem risco material de adiar)*

- **PF-08/BD-11, PF-07** (#15, #16) — folgados para o volume atual; revisitar quando houver decisão concreta de expandir a base de clientes de forma agressiva.
- **A-09/PF-04, A-10/PF-05** (#18, #19) — pesam na experiência, não na correção.
- **UX-01** (#20) — baixo esforço, alto retorno de imagem em demonstração comercial, mas não bloqueia nenhuma venda.

## 6. O Que Pode Esperar

Itens que permanecem conscientemente como dívida técnica, sem prazo de correção imediato:

| Item | Risco de esperar | Impacto se não corrigido logo | Prazo aceitável |
|---|---|---|---|
| **A-01** — use cases com SQL direto, sem passar por repositório (Fase 1) | Baixo — não quebra nada, dificulta unit-test isolado | Cresce só se a equipe de desenvolvimento crescer sem essa convenção documentada | Formalizar como "read models" quando houver janela de refatoração, não urgente |
| **BD-08** — sem particionamento/retenção de `ctes` (Fase 4) | Nenhum hoje | Fica caro de introduzir só depois que a tabela já for grande | Decidir a estratégia (não implementar) nos próximos 12 meses |
| **BD-09/SEC-06** — sem Row-Level Security (Fases 4/5) | Nenhum hoje (isolamento de aplicação já corrigido e auditado) | Relevante só se surgir acesso direto ao banco por ferramenta externa (BI) | Antes de conceder esse tipo de acesso, nunca antes |
| **PF-03/BD-06** — RAG sem índice vetorial nativo (Fases 3/4) | Baixo hoje, cresce com o tempo de uso por empresa | Lentidão gradual do Assistente Logístico em contas antigas | Resolver quando o volume de documentos indexados por empresa começar a incomodar na prática |
| **A-11** — zero observabilidade (Fase 1) | Médio — incidente só é descoberto por relato manual | Cresce com o número de clientes em produção simultaneamente | Sentry (captura de exceção) é barato — fazer no médio prazo, não é longo prazo real |
| **A-08** — Redis/Celery ausente em `docker-compose.prod.yml` (Fase 1) | Baixo-médio — feature "silenciosamente ausente" (insights diários automáticos não rodam) | Não afeta uso interativo, só a automação em segundo plano | Resolver ao decidir usar IA real (não simulada) em produção |
| **IA-01** — `eval()` de regras não é sandbox real (Fase 7) | Nenhum hoje — não há endpoint que exponha edição de regra | Vira crítico no dia em que essa tela for construída | Corrigir **antes** de expor qualquer edição de regra, não depois |
| **Q-01, Q-09, Q-10** — métodos longos, testes só de integração, zero teste de frontend (Fase 2) | Médio, cresce com a complexidade das fórmulas | Retrabalho e investigação mais lenta a cada nova regra de negócio | Contínuo, acompanhar cada mudança nos módulos analíticos, não é um projeto isolado |
| **UX-04, UX-06** — menu extenso sem busca, layout de tablet (Fase 6) | Baixo | Fricção de uso, não bloqueio | Médio prazo, sem urgência |
| Achados P3 residuais de todas as fases (DLG-01/02, V2-01/02, BENCH-04, MBL-02/03, A-13/A-14, Q-03/Q-05/Q-07/Q-08, BD-02/03/10, SEC-04/05/07/08/09/10/11) | Baixo individualmente | Nenhum sozinho justifica prioridade, mas o conjunto merece uma janela de "faxina técnica" periódica | Agrupar numa sprint de qualidade a cada trimestre |

## 7. Dívida Técnica Consolidada

**Quase 100 achados técnicos distintos** identificados ao longo de 9 fases de auditoria (Fase 0 + Fases 1-8), classificados por área:

| Área | Achados | Gravidade predominante |
|---|---|---|
| Arquitetura (A-xx) | 20 | P1-P3, nenhum crítico isolado |
| Qualidade de Código (Q-xx) | 10 | P1-P3 |
| Performance (PF-xx) | 9 (5 exclusivos, 4 sobrepostos com Arquitetura) | P1-P2 |
| Banco de Dados (BD-xx) | 11 (7 exclusivos, 4 sobrepostos) | P1-P3, 1 achado (BD-01) de gravidade Alta |
| Segurança (SEC-xx) | 11 (8 exclusivos, 3 sobrepostos) | Nenhum P0; 3 P1 pendentes de implementação |
| UX/UI (UX-xx) | 10 | 2 P1, resto P2/P3 |
| Funcional (Fase 7, múltiplos prefixos) | 37 | **13 P1** — a fase com maior concentração de achados críticos |
| Produto SaaS (Fase 8) | 2 novos (EMPRESA-01/02) + releitura comercial dos achados já existentes | 2 críticos |

### Custo técnico da dívida atual

| Classificação | Critério | O que se enquadra |
|---|---|---|
| **Crítico** | Gera risco de decisão executiva incorreta, perda/duplicação de dado, ou bloqueia expansão comercial estruturada | CONS-01, EMPRESA-01/02, cluster MCL/BID (4 itens), IMP-01/02 |
| **Alto** | Compromete confiabilidade, segurança ou performance de forma real, mas com raio de impacto mais contido ou já parcialmente mitigado | SEC-01/02/03, BD-01, A-06/PF-01, A-07/PF-02/BD-05, PF-07, PF-08/BD-11, BD-04 |
| **Médio** | Pesa em manutenibilidade e velocidade de evolução futura, não gera erro perceptível hoje | A-01, A-02 a A-05, Q-01, Q-02, Q-09, BD-03, BD-09, A-09/PF-04, A-10/PF-05, UX-04/06/08 |
| **Baixo** | Cosmético, de precisão de documentação, ou esforço trivial sem urgência | Todos os achados P3 residuais listados na Seção 6, mais A-13/A-14/A-15/A-17/A-18/A-19/A-20, Q-03/05/07/08 |

**Critério de classificação usado**: a gravidade não foi atribuída por módulo de origem, mas por **consequência prática se o achado permanecer sem correção pelos próximos 6 a 12 meses** — um achado "Crítico" causa dano real e mensurável (dado perdido, decisão errada, venda perdida) nesse horizonte; um achado "Alto" degrada confiabilidade mas de forma mais contida ou mais fácil de mitigar manualmente enquanto não corrigido; "Médio" e "Baixo" descrevem principalmente custo de manutenção futura, não risco imediato.

## 8. Ordem Ideal das Implementações

Sequência construída para minimizar retrabalho — corrigir um item antes de outro que depende dele, e agrupar por área de conhecimento para reduzir troca de contexto da equipe.

**Etapa 1 — Fundação de confiança de dado. ✅ Concluída em v6.6.0.** Filtro `status=ATIVO` (constante `CTE_STATUS_ATIVO`) propagado aos 9 módulos afetados do achado original, incluindo o MBL, mais Benchmark Setorial (achado adicional, mesma causa raiz, encontrado durante a implementação). Ver `docs/11_changelog.md` [6.6.0] e `docs/06_regras_de_negocio.md` (nota de propagação da RN-09). *Por que primeiro*: corrigir o MCL (Etapa 2) antes disso seria retrabalho — a referência MBL que o MCL consome (MCL-02) só fica genuinamente limpa depois que o próprio MBL parar de incluir CT-e cancelado. **Nota**: apenas a Etapa 1 foi entregue nesta rodada — as Etapas 3, 4 e 5 citadas na projeção de "Curto prazo — 0 a 3 meses" (Seção 9) continuam pendentes de implementação.

**Etapa 2 — Integridade do motor de decisão de BID/MCL.** MCL-02 (referência segmentada), MCL-04/BID-07 (dupla contagem), BID-01 (filtro de ativo no escopo), BID-04/MCL-03 (trava de estado terminal). *Depende da Etapa 1.*

**Etapa 3 — Governança comercial** (paralela às Etapas 1-2, sem dependência técnica entre elas). EMPRESA-01 (campo de plano/limite em `EmpresaModel`), EMPRESA-02 (restringir criação de empresa a superusuário).

**Etapa 4 — Segurança pendente, já aprovada.** SEC-01 (bloqueio de VISUALIZADOR em clusters), SEC-02/SEC-03 (logging de auditoria). Trivial, sem dependência, pode entrar em qualquer sprint.

**Etapa 5 — Integridade de importação.** IMP-01 (dedup por tenant), IMP-02 (chave Excel estável). Independente, mas priorizar antes de qualquer campanha de aquisição de clientes novos.

**Etapa 6 — Fundações de escala de dado.** BD-01 (Float→Numeric, o item de maior esforço da lista — quanto mais cedo, menor o volume histórico a migrar), BD-04 (migrations de IA), A-07/PF-02/BD-05 (índice composto em dev).

**Etapa 7 — Performance e concorrência.** A-06/PF-01 (agregação SQL de composição/OTIF), PF-08/BD-11 (revisão de pool/workers), PF-07 (mover relatórios/importação para Celery). *Depende de uma decisão de negócio*: quantos clientes-âncora e que volume são esperados nos próximos 12 meses — dimensiona o quanto investir aqui agora vs. depois.

**Etapa 8 — Frontend.** A-09/PF-04 (code-splitting), A-10/PF-05 (completar React Query). Mecanicamente extenso (toca ~40 arquivos) — melhor como janela dedicada única do que espalhado.

**Etapa 9 — UX comercial.** UX-01 (login), UX-08 (ocultar ações para VISUALIZADOR). Baixo esforço, pode correr em paralelo a qualquer etapa — priorizar antes de qualquer demonstração comercial relevante.

**Etapa 10 — Observabilidade e operação.** A-11 (Sentry), A-08 (Celery em produção), A-12/BD-07 (script de backup), A-20 (healthcheck). Importante antes de operar múltiplos clientes simultaneamente sem supervisão manual constante.

**Etapa 11 — Qualidade e testes, contínuo.** Q-01 (extrair sub-passos das 5 funções mais complexas), Q-09 (testes unitários de MCL/DLG/MBL/Score), Q-10 (Vitest no frontend). Não é um projeto isolado — deve acompanhar cada mudança feita nas Etapas 1, 2 e 7 (ex.: ao corrigir a fórmula do MCL na Etapa 2, já escrever o teste unitário que faltava).

**Etapa 12 — Preparação de longo prazo, decisão consciente de adiar implementação.** BD-08 (particionamento/retenção), BD-09 (RLS), PF-03/BD-06 (índice vetorial do RAG), avaliação de V5 (Benchmark Coletivo Anonimizado) como diferencial de rede.

## 9. Roadmap dos Próximos 24 Meses

### Curto prazo — 0 a 3 meses
- **Objetivo**: eliminar todo risco crítico já identificado antes de qualquer expansão comercial.
- **Entregas**: Etapas 1, 3, 4, 5 completas (CONS-01, EMPRESA-01/02, SEC-01/02/03, IMP-01/02) + UX-01 (quick win).
- **Benefícios**: números consistentes entre telas; onboarding comercialmente controlado; lacunas de segurança já aprovadas fechadas; importação segura para clientes novos.
- **Riscos mitigados**: inconsistência de dado percebida por cliente, perda/duplicação de dado fiscal, onboarding descontrolado.

### Curto/Médio — 3 a 6 meses
- **Objetivo**: fechar a confiabilidade do motor de decisão de BID e as fundações de reprodutibilidade de schema.
- **Entregas**: Etapa 2 completa (cluster MCL/BID); BD-04 (migrations de IA); início de A-11 (Sentry).
- **Benefícios**: "economia comprovada por BID" torna-se um número defensável de venda; qualquer novo ambiente de produção é reproduzível só via Alembic.
- **Riscos mitigados**: decisão de troca de transportadora baseada em número incorreto; deploy de cliente-âncora sem módulo de IA funcional.

### Médio — 6 a 12 meses
- **Objetivo**: fundações financeiras e de performance para volume crescente.
- **Entregas**: BD-01 (Float→Numeric, iniciado o quanto antes por ser o de maior esforço); A-06/PF-01 (agregação SQL); PF-08/BD-11 (revisão de pool/workers, condicionada à curva real de clientes).
- **Benefícios**: precisão financeira de centavo; elimina o único achado com risco de timeout perceptível; teto de concorrência revisado antes de virar incidente.
- **Riscos mitigados**: erro de arredondamento em relatório financeiro auditado por cliente; timeout do endpoint mais usado do sistema.

### Médio/Longo — 12 a 18 meses
- **Objetivo**: modernizar a experiência técnica do frontend e fechar a operação para múltiplos clientes simultâneos.
- **Entregas**: Etapa 8 completa (code-splitting + React Query); Etapa 10 completa (Celery em produção, backup versionado, healthcheck); PF-07 (fila para relatórios/importação).
- **Benefícios**: carregamento inicial proporcional ao uso real; operação resiliente sem depender de intervenção manual constante; um cliente com lote grande não afeta mais outro.
- **Riscos mitigados**: degradação de experiência a cada módulo novo; incidente silencioso em produção; efeito "vizinho barulhento" entre tenants.

### Longo — 18 a 24 meses
- **Objetivo**: preparação estrutural para escala SaaS de centenas/milhares de clientes.
- **Entregas**: decisão e execução de BD-08 (particionamento/retenção); BD-09 (RLS); PF-03/BD-06 (índice vetorial do RAG); reforço contínuo da Etapa 11 (qualidade/testes); reavaliação de V5 (Benchmark Coletivo) como diferencial de rede.
- **Benefícios**: base técnica pronta para operação SaaS de grande escala, não só "não vai quebrar hoje".
- **Riscos mitigados**: particionamento arriscado feito tarde demais; isolamento multi-tenant dependendo só de disciplina de aplicação, sem defesa em profundidade no banco.

## 10. Escalabilidade

| Cenário | Avaliação |
|---|---|
| **10 empresas** | Confortável em todas as dimensões técnicas hoje, sem nenhuma intervenção — é, na prática, o volume em que a plataforma já opera. |
| **50 empresas** | Ainda tecnicamente confortável; o primeiro sinal de atrito é operacional, não técnico — a ausência de modelo de plano (EMPRESA-01) começa a gerar carga administrativa manual perceptível a cada cliente novo. |
| **100 empresas** | Ponto de virada real: pool de conexão (PF-08/BD-11) e ausência de cache/code-splitting no frontend (A-09/A-10) começam a ser perceptíveis por usuário individual; a ausência de plano técnico deixa de ser incômodo e passa a ser um problema operacional sério. **Não recomendado sem completar as Etapas 1 a 7 do roadmap.** |
| **500 empresas** | Exige que as Etapas 1-7 já estejam concluídas — sem isso, risco concreto de incidente (timeout em picos de uso, contenção real nos workers compartilhados, inconsistência de dado percebida por múltiplos clientes na mesma janela de tempo). |
| **1.000 empresas** | Barreira dupla, técnica e de modelo de negócio. Tecnicamente exige adicionalmente RLS (BD-09) e particionamento/retenção (BD-08). Comercialmente exige que o onboarding tenha deixado de ser uma etapa manual da equipe (evolução de EMPRESA-01/02 para um fluxo real de self-service ou semi-automatizado). |

**Momento ideal para cada evolução**: revisar pool de conexão e frontend (cache/code-splitting) ao se aproximar de 50-70 clientes ativos, não esperar sentir o problema em produção; decidir a estratégia de particionamento/RLS com a base de clientes ainda pequena (decisão é barata agora, cara depois); tratar o modelo de plano/licenciamento como pré-requisito, não acompanhamento, de qualquer meta acima de 50 clientes.

## 11. Preparação Comercial

| Modalidade | Pronto hoje? | Justificativa |
|---|---|---|
| **Pilotos** | Sim | Plataforma funcional, navegável, com identidade visual coerente pós-login (Fase 6); modo simulado de IA permite demonstração completa sem custo de API. |
| **Projetos consultivos** | Sim | Onboarding técnico de dado é rápido (CNPJ auto-fill, importação validada); acompanhamento manual próximo cobre as lacunas de modelo comercial ainda inexistentes. |
| **Contratos recorrentes** | Sim, com ressalva | Só depois de corrigir CONS-01 e o cluster MCL/BID — não vender "economia comprovada" como número auditável antes disso. |
| **Dezenas de clientes** | Sim, é o modelo implícito de hoje | Nenhum achado técnico se manifesta nessa escala; atenção a EMPRESA-01/02 para não acumular exceção manual por cliente. |
| **Centenas de clientes** | Não ainda | Requer as Etapas 1 a 7 do roadmap concluídas (Seção 8) — sem isso, o crescimento expõe exatamente os achados já mapeados nesta auditoria. |
| **Operação SaaS completa (self-service, milhares de clientes)** | Não | Requer, além do técnico, a evolução de EMPRESA-01/02 para um modelo real de planos e onboarding automatizado — hoje inexistente por desenho, não por bug. |

## 12. Visão Estratégica do Produto

> **Nota de revisão (2026-07-08)**: esta seção substitui e amplia a formulação da versão anterior deste documento, reproduzida abaixo para rastreabilidade:
>
> *"O GD Frete Diagnóstico deve ser considerado uma plataforma SaaS de inteligência logística. Justificativa técnica: a Fase 7 confirmou, fórmula a fórmula, que os módulos centrais (DLG, MBL, MCL, Recomendações) vão além de consolidação de dado — detectam outlier estatisticamente, comparam contra referência de mercado segmentada, rankeiam propostas com score multi-critério e geram plano de ação priorizado. A Fase 8 confirmou que a arquitetura multi-tenant é real, não uma simulação de SaaS sobre um produto single-tenant."*
>
> Essa validação técnica **permanece integralmente correta e não é contestada aqui** — a arquitetura multi-tenant continua real (Fase 8), e o motor analítico continua determinístico e auditável (Fase 7). O que muda nesta revisão não é um fato técnico, é o **posicionamento estratégico oficial**: a definição de para quem, e como, o produto cria valor nesta fase. A formulação anterior descrevia corretamente a *capacidade técnica* da plataforma (ela é tecnicamente capaz de operar como SaaS multi-tenant); esta revisão define o *modelo de uso oficial* da fase atual, que é mais restrito por decisão de produto, não por limitação técnica.

### Definição oficial

**O GD Frete Diagnóstico é uma Plataforma de Inteligência para Governança de Fretes, utilizada pela equipe de analistas da GD Conecta para transformar dados logísticos em diagnósticos, benchmark, recomendações e apresentações executivas para seus clientes.**

Nesta fase do produto, a plataforma **não deve ser tratada como um SaaS tradicional voltado ao uso direto do cliente final**. O usuário prioritário é o analista da GD Conecta (Seção 13); o cliente é o consumidor das informações produzidas pelo motor analítico, não o operador da plataforma. A arquitetura permanece preparada — e deve continuar sendo mantida assim — para disponibilizar essas informações diretamente ao cliente no futuro (Seção 16), mas essa não é a prioridade da fase atual.

Esta redefinição também resolve, em termos de produto, a hesitação que a formulação anterior já registrava entre "SaaS" e "plataforma de governança logística": o termo "governança" nesta revisão qualifica o **domínio do produto** (governança de fretes, ver título oficial acima) e não uma alegação de maturidade de auditoria/consistência de dado — essa maturidade continua descrita, sem alteração, pelos achados técnicos das Seções 4, 6 e 7 (CONS-01, SEC-02/03 e correlatos).

### Missão
Dar à equipe de analistas da GD Conecta o motor analítico e a produtividade necessários para transformar dados fiscais de transporte em diagnóstico, benchmark e recomendação de frete auditáveis, entregues ao cliente como decisão executiva, não como planilha.

### Visão
Ser o motor analítico de referência por trás de toda entrega de diagnóstico de frete da GD Conecta — o padrão contra o qual qualquer indicador, benchmark ou recomendação apresentada a um cliente é calculado, validado e rastreável até a regra de negócio que o gerou.

### Proposta de valor
- **Para o analista da GD Conecta** (usuário primário, Seção 13): elimina o trabalho manual de consolidar CT-e/NF-e/planilha em indicador confiável, substitui a régua de comparação subjetiva por benchmark estatístico versionado, e converte a saída em apresentação executiva pronta em vez de dado bruto a ser formatado manualmente.
- **Para o cliente atendido pela GD Conecta** (consumidor da informação, Seção 13): recebe diagnóstico, benchmark e recomendação com rastreabilidade de cálculo (SQL determinístico, Seção 19), não uma opinião ou planilha ad hoc.

### Diferenciais competitivos
- Motor analítico determinístico e auditável (DLG, MBL, MCL, Score) — a IA interpreta, nunca calcula (princípio reforçado na Seção 14).
- Metodologia proprietária da GD Conecta operacionalizada em software, não uma ferramenta de BI genérica.
- Camada de apresentação executiva (Relatório Executivo HTML, Seção 18) tratada como parte integrante do produto, não como anexo separado do processo analítico.
- Arquitetura multi-tenant já validada tecnicamente (Fase 8), permitindo escalar o número de clientes atendidos pelos analistas sem custo de reengenharia — e mantendo, como opcionalidade futura, o caminho para o Portal do Cliente (Seção 16).

### Objetivos do produto (fase atual)
1. Maximizar a profundidade analítica e a produtividade do analista por cliente atendido.
2. Garantir que todo número apresentado a um cliente seja consistente entre módulos — pré-requisito já identificado como Item 1 da Seção 4 (CONS-01).
3. Consolidar o Relatório Executivo HTML como o artefato de entrega padrão ao cliente (Seção 18).
4. Preservar a arquitetura e o motor analítico como base reutilizável para uma futura camada de acesso direto do cliente (Seção 16), sem antecipar essa entrega no roadmap técnico aprovado (Seção 9).

## 13. Perfis de Usuários da Plataforma

Esta seção formaliza, em termos de produto, os perfis já implementados tecnicamente como papéis RBAC (`ADMIN`/`ANALISTA`/`VISUALIZADOR`, ver [`01_visao_geral.md`](01_visao_geral.md) e [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md)) e acrescenta a camada de perfis de negócio que ainda não tem representação direta no RBAC.

| Perfil | Papel no produto | Responsabilidade | Mapeamento técnico atual |
|---|---|---|---|
| **Usuário Primário** — Equipe de Analistas da GD Conecta | Opera a plataforma diariamente: importa dado, gera diagnóstico/benchmark/BID, interpreta o output da IA, monta o Relatório Executivo | Produzir diagnóstico correto e apresentável; validar o output antes de entregar ao cliente | Papel `ANALISTA` (ou `ADMIN` quando também administra usuários/empresa) |
| **Usuário Secundário** — Consultores da GD Conecta | Acompanha entregas, participa da decisão de BID e da apresentação executiva ao cliente, sem necessariamente operar todos os módulos do dia a dia | Validação de negócio e relacionamento com o cliente | Hoje sem papel RBAC dedicado — opera sob `ANALISTA` ou `VISUALIZADOR`, a depender do nível de acesso concedido |
| **Consumidor da Informação** — Clientes atendidos pela GD Conecta | Recebe diagnóstico, benchmark e recomendações via apresentação executiva e Relatório Executivo HTML/PDF | Consumir e decidir a partir da informação entregue; não acessa a plataforma diretamente hoje | Sem login hoje — consome o artefato exportado (Seção 18), não a aplicação |
| **Usuário Futuro** — Portal do Cliente | Evolução planejada (não priorizada nesta fase) para acesso direto e controlado do cliente a um subconjunto da informação | A definir no momento da priorização (Seção 16) | Não implementado; a arquitetura multi-tenant (Fase 8) já é compatível em princípio, sem desenho de escopo/permissão específico ainda |

**Implicação de produto**: decisões de UX e de priorização de funcionalidade devem otimizar primeiro para o Usuário Primário (analista) — é ele quem usa a plataforma todos os dias. O Consumidor da Informação é servido indiretamente, através da qualidade do artefato produzido pelo analista, não por acesso direto à aplicação nesta fase.

## 14. Princípios do Produto

1. **O motor analítico é o principal ativo da plataforma.** DLG, MBL, MCL, Score e Recomendações (Seção 3, [`06_regras_de_negocio.md`](06_regras_de_negocio.md)) são o que a plataforma vende — telas, relatórios e IA existem para tornar esse motor acessível e apresentável, não para substituí-lo.
2. **A plataforma operacionaliza a metodologia da GD Conecta.** Toda fórmula, peso e limiar implementados devem corresponder a uma decisão de metodologia já validada pela GD Conecta, não a uma escolha técnica arbitrária — daí a exigência de rastreabilidade `RN-xx` mantida desde a Fase 0.
3. **A IA interpreta resultados, nunca calcula indicadores.** Princípio já estabelecido tecnicamente (Fase 7) e confirmado na formulação anterior da Seção 12, agora elevado a princípio oficial de produto: qualquer funcionalidade nova de IA deve narrar ou priorizar sobre um número já calculado em SQL determinístico, nunca substituir o cálculo.
4. **Relatórios executivos são parte integrante do produto, não um extra.** O Relatório Executivo HTML (Seção 18) é entregável de primeira classe no roadmap, com o mesmo padrão de qualidade e revisão que qualquer módulo analítico.
5. **Priorizar profundidade analítica e produtividade do analista.** Ao decidir entre duas funcionalidades candidatas, prioriza-se a que aumenta a capacidade do analista de produzir um diagnóstico de maior valor, não a que apenas adiciona superfície de produto.
6. **Evitar funcionalidades que desviem do propósito principal.** Funcionalidades genéricas de BI, automações não relacionadas a frete, ou expansão de escopo para fora da cadeia Motor Analítico → Diagnóstico → Apresentação (Seção 15) devem ser questionadas antes de entrar no roadmap — ver checklist de governança (Seção 21).

## 15. Visão Arquitetural Conceitual

Esta seção descreve o fluxo conceitual de valor da plataforma — uma leitura de produto sobre a arquitetura técnica já documentada em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) — sem alterá-la. Não substitui a Clean Architecture, os fluxos de API ou o modelo de dados existentes; apenas explicita, em linguagem de produto, como as camadas técnicas se conectam ao valor entregue.

```
Motor Analítico (DLG · MBL · MCL · Score · Recomendações — SQL/Python determinístico)
        ↓
Plataforma do Analista (telas, importação, BID, administração — uso primário hoje)
        ↓
Diagnóstico
        ↓
Benchmark
        ↓
Recomendações
        ↓
IA Interpretativa (narra e prioriza, nunca calcula — Seção 14, princípio 3)
        ↓
Apresentação Executiva
        ↓
Relatório Executivo HTML (Seção 18 — artefato de entrega padrão)
        ↓
Exportação PDF (derivada do HTML, não um caminho de cálculo paralelo)
        ↓
Portal do Cliente (evolução futura — Seção 16, não priorizada nesta fase)
```

**Ponto central**: todas as camadas acima do Motor Analítico reutilizam o mesmo motor — não existe, e não deve existir, um segundo caminho de cálculo para o Portal do Cliente futuro, para a exportação em PDF, ou para qualquer apresentação executiva. Qualquer funcionalidade nova que introduza um cálculo paralelo ao motor analítico existente viola este princípio e deve ser reavaliada (Seção 21).

## 16. Estratégia de Evolução do Produto

### Fase Atual
**Fortalecimento da Plataforma do Analista.** Prioridade: profundidade analítica, consistência de dado entre módulos (CONS-01 e correlatos, Seção 4), produtividade do analista, e consolidação do Relatório Executivo HTML (Seção 18). O roadmap técnico já aprovado (Seção 9) reflete essa prioridade e não é alterado por esta revisão estratégica.

### Fase Posterior
**Disponibilização gradual de funcionalidades para um Portal do Cliente.** Sem data-alvo nesta revisão — depende de decisão comercial futura da GD Conecta sobre se e quando oferecer acesso direto ao cliente. Quando priorizada, deverá reutilizar o mesmo motor analítico (Seção 15) e reaproveitar componentes já existentes do Relatório Executivo HTML, em vez de construir um caminho de acesso paralelo.

### Regra de priorização
Toda decisão de produto — inclusive dentro das Etapas 1-12 já sequenciadas na Seção 8 — deve priorizar primeiro o uso interno pelos analistas. Uma funcionalidade que beneficia o Portal do Cliente futuro, mas não fortalece a Plataforma do Analista hoje, não deve furar a fila do roadmap técnico já aprovado.

### Atualização (2026-08-06) — decisão comercial tomada
A "decisão comercial futura" mencionada acima foi tomada: a GD Conecta decidiu iniciar a Fase Posterior, priorizando um primeiro recorte do Portal do Cliente. Ver Validação Estratégica e PRD em [`specs/v6.18.0/`](specs/v6.18.0/), avaliados contra o checklist de Governança do Produto (Seção 21). A Regra de priorização acima **não foi revogada**: o recorte aprovado é somente-leitura, reutiliza o motor analítico (Seção 15) e os componentes do Relatório Executivo HTML (Seção 18) já existentes, e não desvia capacidade de engenharia das Etapas 1-12 (Seção 8) já sequenciadas. A Especificação Técnica correspondente ainda está pendente (ver `specs/v6.18.0/`) e deve ser verificada contra o código real antes de qualquer implementação, conforme Seção 17.

## 17. Processo Oficial de Desenvolvimento

Esta seção insere uma etapa de validação estratégica antes do PRD, formalizando o processo oficial de evolução do sistema. Não altera o roadmap técnico aprovado (Seções 8-9), que descreve *o quê* será feito — esta seção descreve *como* qualquer novo item, técnico ou de produto, deve ser validado antes de entrar em desenvolvimento.

| # | Etapa | Objetivo | Critério de saída |
|---|---|---|---|
| 1 | **Validação Estratégica** | Confirmar que a proposta está alinhada à missão, aos princípios do produto (Seção 14) e à priorização Analista-primeiro (Seção 16) | Respostas positivas ao checklist de governança (Seção 21) |
| 2 | **PRD** | Documentar problema, usuário-alvo (Seção 13), critério de sucesso e escopo | PRD aprovado pelo responsável de produto |
| 3 | **Protótipo Funcional** | Validar a solução proposta com um protótipo navegável ou interativo, antes de comprometer esforço de engenharia | Protótipo demonstra o fluxo-chave para o usuário primário |
| 4 | **Revisão do Protótipo** | Coletar feedback do time de analistas (usuário primário) e de consultores (usuário secundário) | Protótipo aprovado, ou ajustado e reaprovado |
| 5 | **Especificação Técnica** | Detalhar impacto em arquitetura, dados, APIs e reuso do motor analítico (Seção 15) | Especificação não introduz cálculo paralelo ao motor existente nem duplica regra de negócio |
| 6 | **Revisão Técnica** | Validar a especificação contra os princípios arquiteturais (Seção 19) | Especificação aprovada tecnicamente, sem violar a Clean Architecture nem introduzir dívida não registrada |
| 7 | **Implementação Incremental** | Construir em fatias pequenas e testáveis, seguindo a lógica de dependência já usada no roadmap (Seção 8) | Cada incremento entregável e testável isoladamente |
| 8 | **Testes** | Cobrir a regra de negócio nova ou alterada com teste automatizado (consistente com a recomendação de Qualidade, Seção 22) | Suíte de testes cobre o caminho novo, sem regressão nos existentes |
| 9 | **Atualização da Documentação** | Atualizar o documento correspondente (`02`-`09`, `06_regras_de_negocio.md` quando aplicável) no mesmo ciclo, conforme a convenção já vigente desde a Fase 0 ([`00_README.md`](00_README.md)) | Documentação reflete o comportamento real antes do release |
| 10 | **Release** | Publicar a mudança com o nível de versão correto (Seção 20) e registro em [`11_changelog.md`](11_changelog.md) | Release registrado, versionado, e documentação sincronizada (critério da Etapa 9 já satisfeito) |

## 18. O Relatório Executivo HTML como Artefato Central

Esta seção formaliza o papel do Relatório Executivo HTML, já implementado como parte do módulo de Inteligência Logística com IA ([`01_visao_geral.md`](01_visao_geral.md), [`07_modulos_do_sistema.md`](07_modulos_do_sistema.md)):

- **O principal artefato entregue ao cliente é o Relatório Executivo HTML.** É a materialização direta da cadeia Motor Analítico → Diagnóstico → Benchmark → Recomendações → IA Interpretativa → Apresentação Executiva (Seção 15).
- **O PDF é uma exportação do Relatório Executivo HTML**, não um caminho de geração paralelo — qualquer divergência entre o conteúdo do HTML e do PDF exportado deve ser tratada como defeito, não como duas apresentações independentes.
- **Toda funcionalidade nova do motor analítico deve considerar sua apresentação dentro do Relatório Executivo, quando aplicável.** Um novo indicador, achado de benchmark ou recomendação que não tem representação clara no relatório está incompleto do ponto de vista de produto, mesmo que tecnicamente correto.
- **A plataforma deve reutilizar componentes existentes** (de tela e de geração de relatório) para compor o Relatório Executivo, em vez de construir uma camada de apresentação paralela por módulo — consistente com o princípio de não duplicação (Seção 19).

Esta formalização não introduz nenhuma mudança técnica: reforça, como exigência de produto, um comportamento que os módulos de IA e relatórios já implementam hoje.

## 19. Princípios Arquiteturais Reforçados

Esta seção confirma explicitamente, como decisão de produto e não apenas como constatação técnica, os princípios arquiteturais já documentados em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) e avaliados na Fase 1 ([`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md)):

- **Preservação da Clean Architecture** — nenhuma decisão de produto desta revisão exige ou sugere abandonar as camadas de domínio/aplicação/infraestrutura já em uso.
- **Reutilização de componentes** — telas, relatórios e, sobretudo, o motor analítico (Seção 15) devem ser reaproveitados por novas funcionalidades, não reimplementados.
- **Ausência de duplicação de regras de negócio** — toda fórmula tem um único lugar de origem, com código `RN-xx` (convenção de [`06_regras_de_negocio.md`](06_regras_de_negocio.md)); o achado CONS-01 (Seção 4, Item 1) é justamente o que acontece quando esse princípio falha na propagação, não na definição.
- **Documentação sincronizada com o código** — convenção "documentação viva, não retroativa" já vigente desde a Fase 0 ([`00_README.md`](00_README.md)), reafirmada como critério de saída do processo de desenvolvimento (Seção 17, Etapa 9).
- **Rastreabilidade entre requisitos, código e testes** — todo requisito de negócio deve ser localizável em `06_regras_de_negocio.md`, no código que o implementa e no teste que o cobre (reforça a recomendação de Qualidade já registrada na Seção 22).
- **Evolução incremental** — consistente com a ordem de implementação já sequenciada (Seção 8) e com a etapa "Implementação Incremental" do processo oficial (Seção 17, Etapa 7).

Nenhum destes princípios é novo; esta seção existe para que a visão estratégica do produto (Seção 12) e a arquitetura técnica (Seções 1-11 e [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md)) fiquem explicitamente ancoradas nos mesmos princípios, evitando que uma decisão de produto futura contrarie, sem perceber, um princípio arquitetural já estabelecido.

## 20. Política de Versionamento

Confirma oficialmente a política semver já em uso em [`11_changelog.md`](11_changelog.md) (de v1.0.0 a v6.6.0):

| Nível | Critério |
|---|---|
| **PATCH** | Correções que não alteram comportamento esperado nem contrato de API/dado (ex.: correção de bug, ajuste de cálculo para bater com a regra já documentada) |
| **MINOR** | Novas funcionalidades compatíveis com o comportamento existente (ex.: novo indicador, novo módulo, nova tela) |
| **MAJOR** | Mudanças estruturais incompatíveis (ex.: alteração de contrato de API, mudança de schema que quebra compatibilidade, redesenho de um módulo existente) |

**A definição do nível de versão é sempre uma decisão de engenharia**, baseada no impacto real da entrega — nunca uma decisão de marketing ou de expectativa comercial. Em caso de dúvida entre dois níveis, aplica-se o mais conservador (o de maior nível), seguindo a mesma disciplina já usada nas versões maiores registradas no histórico do produto.

## 21. Governança do Produto

Toda nova funcionalidade — técnica ou de produto — deve responder às perguntas abaixo **antes** do início do desenvolvimento (Etapa 1 do processo oficial, Seção 17):

1. Está alinhada ao propósito do produto (Seção 12)?
2. Aumenta a capacidade do analista de produzir diagnósticos de maior valor (Seção 13, Usuário Primário)?
3. Reutiliza o motor analítico existente (Seção 15), em vez de introduzir um caminho de cálculo paralelo?
4. Preserva a arquitetura (Seção 19)?
5. Evita retrabalho (consistente com a lógica de sequenciamento já usada na Seção 8)?
6. Mantém a documentação sincronizada (Seção 17, Etapa 9)?

**Caso qualquer resposta seja negativa, a implementação deve ser reavaliada** antes de prosseguir para o PRD (Seção 17, Etapa 2) — reavaliar não significa necessariamente descartar, significa ajustar o escopo até que todas as seis respostas sejam afirmativas.

## 22. Recomendações Estratégicas

**Arquitetura**: consolidar (não reverter) o padrão de "use case com SQL direto" como uma camada explícita de "read models" — é pragmatismo válido para agregação pesada, mas precisa parar de ser um desvio silencioso do padrão de repositório original.

**Produto**: tratar CONS-01 e o cluster MCL/BID como prioridade de produto, não só técnica — são os achados que mais diretamente afetam a percepção de confiabilidade do produto por um cliente pagante.

**Comercial**: construir EMPRESA-01/02 antes de qualquer meta de crescimento de base de clientes acima de 50 — é a única peça desta auditoria que não existe hoje nem parcialmente, ao contrário da maioria dos outros achados, que são correções sobre algo que já existe.

**Tecnologia**: tratar Celery (já disponível na stack) como a resposta padrão para todo processamento pesado disparado por usuário (relatórios, importação de lote, e a automação de IA em produção) — a infraestrutura já existe, falta usá-la de forma mais ampla.

**Governança**: fechar as lacunas de auditoria (SEC-02/03) como parte do mesmo esforço que corrige CONS-01 — ambas são, no fundo, a mesma disciplina (rastreabilidade e consistência) aplicada a domínios diferentes (log de ação vs. consistência de cálculo).

**Escalabilidade**: revisar pool de conexão/workers e frontend (cache/code-splitting) de forma proativa ao se aproximar de 50-70 clientes ativos — não reagir depois que o primeiro incidente de concorrência acontecer.

**Documentação**: manter a disciplina já estabelecida na Fase 0 ("documentação viva, não retroativa") — toda correção das Etapas 1-12 deve atualizar o documento correspondente (`02`-`09`, `06_regras_de_negocio.md` quando aplicável) no mesmo ciclo de mudança, e registrar em `11_changelog.md`.

**Qualidade**: tratar testes unitários das fórmulas críticas (MCL, DLG, MBL, Score) como parte do "custo de fazer a correção", não como item separado de backlog — cada etapa do roadmap que mexe numa fórmula deveria sair com o teste que faltava.

**Operação**: Sentry (captura de exceção) é a recomendação de menor esforço e maior retorno de toda a auditoria de 9 fases para reduzir o tempo de descoberta de incidente — priorizar isso independentemente de qualquer outra decisão de roadmap.

## 23. Conclusão Final

**1. Qual é a nota geral da plataforma?** 65/100 — "Em Evolução" (Seção 2).

**2. Quais são os 20 problemas mais importantes?** Listados e ordenados na Seção 4, liderados por CONS-01 (consistência de dado entre módulos analíticos) e EMPRESA-01/02 (ausência de modelo comercial).

**3. O que precisa ser corrigido antes de vender em maior escala?** CONS-01, EMPRESA-01/02, o cluster MCL/BID (4 itens), IMP-01/02, e os 3 achados de segurança já aprovados (SEC-01/02/03) — todos classificados como "Obrigatório" na Seção 5.

**4. O que pode esperar?** Débito arquitetural de longo prazo (A-01, BD-08, BD-09), observabilidade e automação de IA em produção (podem esperar meses, não anos, mas não são bloqueadores), e o `eval()` de regras de insight (IA-01) — desde que nenhuma tela de edição de regra seja construída antes da correção. Lista completa na Seção 6.

**5. Qual é o roadmap ideal dos próximos 24 meses?** Detalhado na Seção 9 — de "eliminar risco crítico" (0-3 meses) a "preparação estrutural para escala SaaS" (18-24 meses).

**6. Qual é o custo técnico da dívida atual?** Quase 100 achados distintos consolidados; 8 classificados como Crítico, ~13 como Alto, o restante Médio/Baixo — metodologia e critério detalhados na Seção 7.

**7. Qual é a ordem ideal das implementações?** As 12 etapas sequenciadas na Seção 8, com a Etapa 1 (consistência de dado) como pré-requisito técnico da Etapa 2 (motor de BID/MCL) — inverter essa ordem geraria retrabalho certo.

**8. Quando a plataforma estará preparada para operar com 10/50/100/500/1.000 empresas?** 10 e 50: hoje. 100: após as Etapas 1-7. 500: com as Etapas 1-7 obrigatoriamente concluídas. 1.000: adicionalmente RLS, particionamento e evolução do modelo comercial para semi-self-service (Seção 10).

**9. A plataforma está pronta para crescimento comercial?** Sim, para um modelo consultivo com dezenas de clientes bem acompanhados. Não, para expansão agressiva ou self-service sem antes executar as Etapas 1 a 5 do roadmap (Seção 11).

**10. Qual deve ser a prioridade estratégica da GD Conecta para os próximos dois anos?** Duas frentes em paralelo, não sequenciais: (a) fechar a consistência de dado entre módulos analíticos e a confiabilidade do motor de BID/MCL — porque é o que sustenta a credibilidade do produto perante qualquer cliente tecnicamente rigoroso; e (b) construir a peça de modelo comercial (plano/licenciamento e onboarding controlado) que hoje não existe — porque é a única lacuna desta auditoria de 9 fases que não é uma correção sobre algo já construído, é uma ausência completa. A tecnologia central já provou, em cinco gerações de módulo, que sabe crescer sem quebrar; o que falta não é mais capacidade técnica, é fechar essas duas frentes com a mesma disciplina que já produziu DLG, MBL e MCL.

### Adendo estratégico (2026-07-08)

As dez respostas acima permanecem válidas e não foram alteradas pela revisão estratégica. Duas leituras adicionais, decorrentes das Seções 12-21, complementam a conclusão original sem substituí-la:

**11. Para quem a plataforma deve ser otimizada nesta fase?** Para o analista da GD Conecta (Usuário Primário, Seção 13), não para o cliente final direto. As dez conclusões técnicas acima (notas, débito, roadmap, escalabilidade) continuam corretas e não mudam de valor — o que esta revisão acrescenta é o critério de para quem essas correções e essa escala existem: fortalecer a Plataforma do Analista primeiro (Seção 16), mantendo a arquitetura multi-tenant já validada (Fase 8) como caminho aberto, não como prioridade, para um futuro Portal do Cliente.

**12. Isso muda alguma prioridade técnica do roadmap?** Não. As Etapas 1-12 (Seção 8) e o roadmap de 24 meses (Seção 9) permanecem exatamente como sequenciados. A revisão estratégica formaliza o *porquê* e o *para quem* dessas etapas — em particular, reforça que CONS-01 e o cluster MCL/BID (Etapas 1-2) são ainda mais urgentes sob a nova definição oficial, pois são exatamente o que garante que o Relatório Executivo HTML (Seção 18) entregue ao cliente seja auditável e consistente.

## 24. Confirmação de Compatibilidade e Ajustes Futuros Recomendados

### Confirmação de compatibilidade

Esta revisão estratégica foi verificada contra o conteúdo técnico das Seções 1-11 (achados, notas, dívida técnica, roadmap, ordem de implementação, escalabilidade e preparação comercial) e contra [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md), [`10_roadmap.md`](10_roadmap.md) e [`11_changelog.md`](11_changelog.md). **Não foi identificado nenhum conflito**: nenhuma arquitetura, regra de negócio, API, schema, migration ou item do roadmap técnico aprovado foi alterado nesta atividade. A única mudança de conteúdo pré-existente é a reformulação da Seção 12 (posicionamento estratégico), e ela está documentada como tal, com o texto anterior preservado para rastreabilidade, sem impacto técnico.

### Ajustes futuros recomendados (não priorizados nesta revisão)

- Ao retomar **EMPRESA-01** (Seção 4, Item 2), considerar desde já um campo de "modalidade de acesso" (uso interno via analista vs. futuro acesso direto do cliente) na modelagem de plano/licenciamento, para evitar retrabalho quando o Portal do Cliente (Seção 16) for priorizado.
- Ao adotar o **Processo Oficial de Desenvolvimento** (Seção 17), avaliar se o formato de PRD hoje em uso já contempla a etapa de Validação Estratégica como pré-requisito formal, ou se precisa de um template novo.
- Ao priorizar novas funcionalidades de IA ou de relatório, aplicar o checklist de **Governança do Produto** (Seção 21) de forma explícita e documentada na Etapa 1 do processo (Seção 17), não apenas como critério informal.
- Nenhum ajuste técnico adicional (arquitetura, schema, API) foi identificado como necessário para acomodar esta revisão estratégica.

---

*Este documento é a referência técnica e estratégica oficial da plataforma GD Frete Diagnóstico. Consolida, nas Seções 1-11, as Fases 0 a 8 de auditoria técnica realizadas em 2026-07-07, e formaliza, nas Seções 12-21 e 24, a visão estratégica do produto, os perfis de usuário, os princípios do produto, a estratégia de evolução e a governança do produto, acrescentados em 2026-07-08 (ver [`00_README.md`](00_README.md) e o Histórico de Revisões no início deste documento). Nenhum código, banco de dados, arquitetura ou infraestrutura foi alterado na produção deste documento — toda ação recomendada permanece pendente de autorização explícita para implementação.*
