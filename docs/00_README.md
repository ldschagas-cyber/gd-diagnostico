# GD Frete Diagnóstico — Documentação Oficial

**Versão do sistema documentada: 6.6.0** · **Documentação consolidada em: 2026-07-07** · Este é o ponto de entrada oficial da documentação do projeto.

## Baseline Oficial da Documentação

Esta estrutura (`/docs`, 13 documentos numerados + `archive/`) foi aprovada como a **documentação oficial (Single Source of Truth)** do projeto GD Frete Diagnóstico.

| Campo | Valor |
|---|---|
| **Data da consolidação** | 2026-07-07 |
| **Versão da plataforma na consolidação** | 6.5.1 |
| **Versão da documentação** | 1.0.0 (primeira baseline oficial) |
| **Responsável pela aprovação** | Responsável do projeto GD Conecta (ldschagas@gmail.com) |
| **Executor técnico da consolidação** | Assistente de IA Claude (Sonnet 5, Anthropic), em sessão assistida |
| **Escopo** | Auditoria e reescrita de toda a documentação funcional/técnica em `/docs`, comparada linha a linha com o código-fonte da v6.5.1; nenhum arquivo de código foi alterado nesta fase |

**Regra vigente a partir desta baseline**: toda alteração futura no sistema (código, schema, endpoint, regra de negócio, infraestrutura) deve ser refletida na documentação correspondente no mesmo ciclo de mudança — não como tarefa avulsa posterior. Ver convenções de manutenção da documentação abaixo.

## O que é a plataforma

GD Frete Diagnóstico é a plataforma de inteligência logística da GD Conecta: importa dados fiscais de transporte (CT-e, NF-e, Excel), calcula indicadores de custo de frete, compara com benchmarks de mercado em múltiplos modelos, conduz processos de cotação eletrônica entre transportadoras (BID) e narra tudo isso através de uma camada de IA que interpreta — mas nunca calcula — os números, que vêm sempre de SQL determinístico.

Ver [`01_visao_geral.md`](01_visao_geral.md) para a descrição completa e [`00_contexto_oficial.md`](00_contexto_oficial.md) para a missão, visão, posicionamento e princípios permanentes do produto.

## Camada de Governança do Projeto (leitura obrigatória para qualquer agente de IA)

A partir de 2026-07-08, o projeto passou a ter uma **camada oficial de governança**, permanente e versionada, que elimina a dependência da memória de conversas entre humano e IA:

- **[`00_contexto_oficial.md`](00_contexto_oficial.md)** — documento mestre: missão, visão, posicionamento, público-alvo, princípios permanentes, arquitetura conceitual, papel da IA no produto, estratégia de evolução, diretrizes arquiteturais e política de versionamento. **A principal referência oficial do projeto.**
- **[`README_AI.md`](README_AI.md)** — guia exclusivo para agentes de IA (ChatGPT, Claude Chat, Claude Code): ordem obrigatória de leitura, processo oficial de desenvolvimento (Validação Estratégica → PRD → Protótipo → Especificação Técnica → Implementação → Release), papéis de cada ferramenta, e regras de bloqueio quando falta PRD/Protótipo/Especificação aprovados.

Qualquer IA que inicie trabalho neste projeto deve ler `00_contexto_oficial.md` e `README_AI.md` antes de propor ou implementar qualquer mudança — ver a ordem completa dentro de `README_AI.md`.

## Índice completo

| # | Documento | Conteúdo |
|---|---|---|
| 00 | [`README.md`](00_README.md) | Este documento — índice e ponto de entrada |
| 00 | [`contexto_oficial.md`](00_contexto_oficial.md) | **Contexto Oficial** — documento mestre de governança: missão, visão, posicionamento, público-alvo, princípios permanentes, arquitetura conceitual, papel da IA, estratégia de evolução, diretrizes arquiteturais, política de versionamento. A principal referência estratégica do projeto |
| — | [`README_AI.md`](README_AI.md) | Guia oficial para agentes de IA (ChatGPT, Claude Chat, Claude Code): ordem obrigatória de leitura, processo oficial de desenvolvimento, papéis das ferramentas, regras de bloqueio por ausência de PRD/Protótipo/Especificação Técnica aprovados |
| 01 | [`visao_geral.md`](01_visao_geral.md) | O que é a plataforma, módulos, papéis de acesso, stack resumida, escala do sistema |
| 02 | [`especificacao_funcional.md`](02_especificacao_funcional.md) | O que cada módulo faz, fluxos de negócio, o que é global vs. isolado por empresa, limitações conhecidas |
| 03 | [`arquitetura_tecnica.md`](03_arquitetura_tecnica.md) | Clean Architecture, stack completa, autenticação/autorização, segurança, infraestrutura, IA |
| 04 | [`modelo_de_dados.md`](04_modelo_de_dados.md) | As 44 tabelas do banco, organizadas por módulo, e as 10 migrations Alembic |
| 05 | [`apis.md`](05_apis.md) | Catálogo completo dos 148 endpoints, com autorização exigida por rota |
| 06 | [`regras_de_negocio.md`](06_regras_de_negocio.md) | Todas as fórmulas, pesos, limiares e classificações, com código `RN-xx` estável para referência |
| 07 | [`modulos_do_sistema.md`](07_modulos_do_sistema.md) | Cruzamento tela ↔ endpoint ↔ entidade ↔ regra, por módulo funcional |
| 08 | [`instalacao_deploy.md`](08_instalacao_deploy.md) | Ambiente local (com/sem Docker), infraestrutura de IA, deploy em produção, variáveis de ambiente |
| 09 | [`manutencao.md`](09_manutencao.md) | Testes, migrations, criar novo módulo/endpoint, convenções de código |
| 10 | [`roadmap.md`](10_roadmap.md) | O que falta (V5/V6), débitos técnicos consolidados e atualizados |
| 11 | [`changelog.md`](11_changelog.md) | Histórico de versões, reordenado cronologicamente, de v1.0.0 a v6.5.1 |
| 12 | [`auditoria_tecnica.md`](12_auditoria_tecnica.md) | Auditorias de segurança/arquitetura — histórica (v2.0.0) e atual (v6.5.0→v6.5.1) |
| 13 | [`inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) | Inventário técnico completo (Technical Baseline) — linha de base oficial para a Fase 1 — Auditoria Técnica |
| 14 | [`fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md) | Relatório da Fase 1 — Auditoria Técnica da Arquitetura: nota geral, achados classificados (P0-P3), dívida técnica, roadmap arquitetural |
| 15 | [`fase2_qualidade_codigo.md`](15_fase2_qualidade_codigo.md) | Relatório da Fase 2 — Auditoria de Qualidade do Código: complexidade, duplicação, padronização, qualidade de testes, dívida técnica de código |
| 16 | [`fase3_performance.md`](16_fase3_performance.md) | Relatório da Fase 3 — Auditoria de Performance: gargalos atuais e futuros, cenários de crescimento, roadmap de performance |
| 17 | [`fase4_banco_de_dados.md`](17_fase4_banco_de_dados.md) | Relatório da Fase 4 — Auditoria de Banco de Dados: modelagem, integridade, índices, migrations, escalabilidade, multi-tenancy, governança |
| 18 | [`fase5_seguranca.md`](18_fase5_seguranca.md) | Relatório da Fase 5 — Auditoria de Segurança: autenticação, autorização, multi-tenancy, APIs, uploads, dependências, matriz de risco |
| 19 | [`fase6_ux_ui.md`](19_fase6_ux_ui.md) | Relatório da Fase 6 — Auditoria UX/UI e Experiência do Usuário: jornada por perfil, navegação, dashboards, indicadores, design system, responsividade, acessibilidade, achados UX-01 a UX-10 |
| 20 | [`fase7_auditoria_funcional.md`](20_fase7_auditoria_funcional.md) | Relatório da Fase 7 — Auditoria Funcional e Regras de Negócio: validação de RN-01 a RN-57 contra o código real, achados FUNC-P1 a FUNC-P3 por módulo (Importação, Indicadores, DLG, Benchmark, MBL, MCL, BID, Recomendações, IA) |
| 21 | [`fase8_produto_saas.md`](21_fase8_produto_saas.md) | Relatório da Fase 8 — Auditoria de Produto SaaS e Escalabilidade Comercial: maturidade de produto, multi-tenancy, escalabilidade técnica, modelo de licenciamento, onboarding, diferenciação competitiva, achados SAAS-P1 a P3 |
| 22 | [`plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) | **Plano Diretor Técnico** — consolidação executiva das Fases 0 a 8 (nota geral 65/100, os 20 problemas mais importantes, o que corrigir antes da expansão comercial, dívida técnica consolidada, ordem ideal de implementação, roadmap de 24 meses) **+ visão estratégica do produto** (missão, perfis de usuário, princípios do produto, visão arquitetural conceitual, estratégia de evolução, processo oficial de desenvolvimento, papel do Relatório Executivo HTML, política de versionamento e governança do produto, acrescentados em 2026-07-08). Referência técnica **e estratégica** oficial da plataforma |
| — | [`archive/`](archive/) | Todos os documentos originais, preservados, com nota de por que foram substituídos |

## Ordem de leitura recomendada

**Se você é um agente de IA (ChatGPT, Claude Chat, Claude Code) iniciando qualquer trabalho neste projeto**: siga a ordem obrigatória definida em [`README_AI.md`](README_AI.md) — `00_contexto_oficial.md` → `22_plano_diretor_tecnico.md` → `11_changelog.md` → `13_inventario_tecnico_baseline.md` → `10_roadmap.md` → documentação da versão em desenvolvimento (`specs/`).

**Se você é novo no projeto**: 01 → 02 → 03 → 07 → 05.

**Se você vai mexer em regra de negócio/cálculo**: 06 diretamente, depois 07 para achar a tela/endpoint correspondente.

**Se você vai fazer deploy ou subir ambiente local**: 08 → 09.

**Se você vai auditar segurança ou decidir uma próxima frente de arquitetura**: 12 → 10 → 03.

**Se você quer entender por que algo é do jeito que é**: 11 (changelog) e 12 (auditoria) juntos contam a história.

## Convenções adotadas

- **Fonte da verdade**: o código-fonte. Sempre que um documento antigo divergia do código, o código venceu — a divergência foi registrada em [`archive/README.md`](archive/README.md) e corrigida na documentação nova.
- **Numeração de regras de negócio**: `RN-01` a `RN-66`, estável — ao alterar uma regra, atualize o texto em [`06_regras_de_negocio.md`](06_regras_de_negocio.md) sem reciclar o número de uma regra removida (marque como "removida" em vez de reaproveitar o código).
- **Nada foi excluído**: todo documento anterior está em `archive/`, com uma nota explicando o que mudou e para onde a informação foi.
- **Versão semver vs. nome de produto**: até a v6.0.0 os documentos antigos usavam nomes de produto ("V3.1", "V4") que não batiam com o semver do changelog — a partir daqui, use só o semver. Ver a nota em [`11_changelog.md`](11_changelog.md#nota-sobre-nomenclatura-de-versão).
- **Documentação viva, não retroativa**: a partir da Baseline Oficial (v1.0.0 desta documentação), qualquer mudança de código que afete comportamento, schema, endpoint, regra de negócio ou infraestrutura deve atualizar o documento correspondente (`02`–`09`) no mesmo ciclo de trabalho, e registrar a mudança em `11_changelog.md`. Deixar a documentação decair novamente é o problema que a Fase 0 existiu para resolver.
- **Documentação como única fonte oficial de verdade**: desde 2026-07-08 ([`00_contexto_oficial.md`](00_contexto_oficial.md), [`README_AI.md`](README_AI.md)), a memória de conversas entre humano e IA deixou de ser considerada referência do projeto. Toda decisão estratégica, de produto ou técnica que precise sobreviver além de uma única sessão deve estar registrada em `/docs` — se não está documentada, não é oficial.

## Histórico de versões desta documentação

| Data | O que mudou |
|---|---|
| 2026-07-07 | **Consolidação completa (Fase 0)**: 13 documentos originais (cobrindo só até v2.0.0/v3.0.0/v5.0.0, com contradições internas entre si) foram auditados, comparados linha a linha com o código real da v6.5.1, e substituídos por este conjunto de 12 documentos + arquivo histórico. Ver o relatório completo desta consolidação nas notas da sessão de auditoria de 2026-07-07 (registrado em [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md), seção 3). **Aprovada como Baseline Oficial da Documentação (v1.0.0)** — ver seção acima. |
| 2026-07-07 | Adicionado `13_inventario_tecnico_baseline.md` como Linha de Base Oficial (Technical Baseline) para a Fase 1 — Auditoria Técnica. |
| 2026-07-07 | Adicionado `14_fase1_auditoria_arquitetural.md` — relatório da Fase 1 concluída, aguardando aprovação para a Fase 2 (Auditoria de Qualidade do Código). |
| 2026-07-07 | Fase 1 aprovada. Adicionado `15_fase2_qualidade_codigo.md` — relatório da Fase 2 concluído, aguardando aprovação para a próxima fase. |
| 2026-07-07 | Fase 2 aprovada. Adicionado `16_fase3_performance.md` — relatório da Fase 3 concluído, aguardando aprovação para a próxima fase. |
| 2026-07-07 | Fase 3 aprovada. Adicionado `17_fase4_banco_de_dados.md` — relatório da Fase 4 concluído, aguardando aprovação para a próxima fase. |
| 2026-07-07 | Fase 4 aprovada. Adicionado `18_fase5_seguranca.md` — relatório da Fase 5 concluído, aguardando aprovação para a próxima fase. |
| 2026-07-07 | Fase 5 aprovada como diagnóstico oficial (nenhuma correção implementada nesta fase — achados SEC-01 a SEC-11 incorporados ao roadmap consolidado). Adicionado `19_fase6_ux_ui.md` — relatório da Fase 6 concluído, aguardando aprovação para a próxima fase. |
| 2026-07-07 | Fase 6 aprovada como diagnóstico oficial (nenhuma alteração de tela/componente nesta fase — achados UX-01 a UX-10 incorporados ao roadmap consolidado). Iniciada Fase 7 — Auditoria Funcional e Regras de Negócio. |
| 2026-07-07 | Fase 7 aprovada como diagnóstico oficial (nenhum código/regra/cálculo alterado nesta fase — achados FUNC-P1 a FUNC-P3 incorporados ao roadmap consolidado, com destaque para CONS-01, o motor MCL/BID e a governança de dados analíticos). Adicionado `20_fase7_auditoria_funcional.md`. Aguardando autorização para iniciar a Fase 8 — Auditoria de Produto SaaS e Escalabilidade Comercial. |
| 2026-07-07 | Fase 8 aprovada como diagnóstico oficial (nenhum código/arquitetura/infraestrutura alterado nesta fase — achados SAAS-P1 a P3 incorporados ao diagnóstico consolidado, com destaque para a ausência de modelo técnico de plano/licenciamento e o controle de criação de empresa-cliente). Adicionado `21_fase8_produto_saas.md`. Iniciada Fase 9 — Consolidação Final e Plano Diretor Técnico da Plataforma (não é uma nova auditoria; consolida as Fases 0-8 num único documento executivo, `22_plano_diretor_tecnico.md`). |
| 2026-07-07 | **Fase 9 concluída — Plano Diretor Técnico consolidado.** Adicionado `22_plano_diretor_tecnico.md`, sintetizando as Fases 0 a 8 (nota geral 65/100, classificação "Em Evolução"; 20 problemas mais importantes priorizados; roadmap de 24 meses; ordem ideal de implementação em 12 etapas). Este documento passa a ser a **referência técnica oficial** para toda evolução futura da plataforma, encerrando o programa de auditoria de 9 fases iniciado em 2026-07-07. |
| 2026-07-07 | **Primeira implementação pós-auditoria: CONS-01 (v6.6.0), Etapa 1 do Plano Diretor Técnico.** RN-09 (exclusão de CT-e cancelado dos totais analíticos) propagada aos 9 módulos do achado original + Benchmark Setorial (achado adicional, mesma causa raiz). `06_regras_de_negocio.md`, `10_roadmap.md` (DT-19 resolvido) e `22_plano_diretor_tecnico.md` (Etapa 1 concluída) atualizados no mesmo ciclo. Ver `11_changelog.md` [6.6.0]. |
| 2026-07-08 | **Revisão estratégica do Plano Diretor Técnico (v1.1 do documento).** Adicionadas as Seções 12-21 e 24 a `22_plano_diretor_tecnico.md`: visão estratégica do produto (reformulando a antiga Seção 12), perfis de usuário (analista como usuário primário, cliente como consumidor da informação), princípios do produto, visão arquitetural conceitual, estratégia de evolução (Plataforma do Analista hoje, Portal do Cliente como evolução futura), processo oficial de desenvolvimento (10 etapas, com Validação Estratégica antes do PRD), papel do Relatório Executivo HTML, princípios arquiteturais reforçados, política de versionamento e governança do produto. **Atividade exclusivamente documental** — nenhum código, arquitetura, schema, API ou item do roadmap técnico aprovado (Seções 1-11) foi alterado; ver histórico de revisões e confirmação de compatibilidade dentro do próprio `22_plano_diretor_tecnico.md`. |
| 2026-07-08 | **Criação da camada oficial de governança do projeto.** Adicionados `00_contexto_oficial.md` (documento mestre: missão, visão, posicionamento, público-alvo, princípios permanentes, arquitetura conceitual, papel da IA, estratégia de evolução, diretrizes arquiteturais, política de versionamento) e `README_AI.md` (guia para agentes de IA: ordem obrigatória de leitura, processo oficial de desenvolvimento, papéis de ChatGPT/Claude Chat/Claude Code, e regras de bloqueio por ausência de PRD/Protótipo/Especificação Técnica aprovados). A partir desta consolidação, a documentação versionada em `/docs` — não a memória de conversas — passa a ser a única fonte oficial de verdade do projeto. **Atividade exclusivamente documental** — nenhum código, API, schema ou regra de negócio foi alterado. |

## Relacionamento entre os documentos

```
contexto_oficial (governança — missão, visão, princípios, estratégia)
 └─→ README_AI (guia de processo para agentes de IA)
      └─→ 22 (plano diretor técnico) ←→ 10 (roadmap) ←→ 11 (changelog)
                                                          └─→ 13 (inventário técnico — baseline da Fase 1)

01 (visão geral)
 ├─→ 02 (o quê o sistema faz) ──→ 06 (regras/fórmulas) ──→ 07 (tela↔endpoint↔regra)
 ├─→ 03 (como é construído)   ──→ 04 (dados) + 05 (APIs)
 ├─→ 08 (instalar/deploy)     ──→ 09 (manter no dia a dia)
 └─→ 10 (o que falta)         ←→ 11 (histórico) ←→ 12 (auditorias de segurança)
                                                    └─→ 13 (inventário técnico — baseline da Fase 1)
```
