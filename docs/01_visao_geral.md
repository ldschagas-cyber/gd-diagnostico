# 01 · Visão Geral da Plataforma

> **Documentação oficial GD Frete Diagnóstico** · Versão do sistema: **6.5.1** · Documentação consolidada em: **2026-07-07**
> Este documento faz parte do conjunto de documentação oficial. Ver [`00_README.md`](00_README.md) para o índice completo.

## O que é

GD Frete Diagnóstico é a plataforma de **inteligência logística** da GD Conecta: uma consultoria/produto que ajuda empresas embarcadoras a entender, comparar e reduzir seus custos de frete a partir dos dados reais das suas operações (CT-e, NF-e, planilhas).

A plataforma evoluiu de um diagnóstico de custos simples (MVP) para uma suíte com cinco frentes principais:

1. **Diagnóstico Logístico** — indicadores nacionais, regionais, por transportadora e de prazo (OTIF), a partir da importação de CT-e/Excel.
2. **Benchmark Logístico** — comparação contra referências de mercado, em três gerações de modelo (regional legado → corredor Origem-Destino → matriz de mercado percentílica), mais um motor estatístico próprio (MBL) sobre a base do cliente.
3. **Concorrência Logística (BID de Frete)** — condução de processos de cotação eletrônica entre transportadoras, com um motor de decisão determinístico (MCL) que pondera custo, desempenho histórico (DLG/MBL), prazo e estabilidade.
4. **Inteligência Logística com IA** — camada de IA que narra e prioriza (nunca calcula) sobre os números vindos do SQL: insights automáticos, diagnóstico executivo, score logístico, detecção de oportunidades, assistente conversacional com tool-calling e busca semântica (RAG).
5. **Administração e Segurança** — multi-tenant real (isolamento por empresa cliente), papéis de acesso (ADMIN/ANALISTA/VISUALIZADOR) e autenticação via cookie `httpOnly`.

## Objetivo do projeto

Permitir que uma consultoria (GD Conecta) — ou, no modelo SaaS, cada empresa-cliente diretamente — importe seus documentos fiscais de transporte, veja onde está pagando mais frete do que deveria, compare-se com o mercado e com seu próprio histórico, conduza processos de cotação estruturados e receba recomendações e alertas gerados automaticamente, com a IA atuando como camada de interpretação sobre dados sempre calculados em SQL.

## Módulos implementados hoje (v6.5.1)

| Módulo | O que faz | Documentado em |
|---|---|---|
| Autenticação e Usuários | Login via cookie `httpOnly` + refresh; papéis ADMIN/ANALISTA/VISUALIZADOR | [`02`](02_especificacao_funcional.md), [`03`](03_arquitetura_tecnica.md) |
| Cadastros (Empresas, Filiais, Transportadoras, Regiões, Cidades) | Cadastro base multi-tenant | [`07`](07_modulos_do_sistema.md) |
| Importação (CT-e XML, Excel, Cancelamento) | Ingestão de dados fiscais com validação e deduplicação | [`06`](06_regras_de_negocio.md), [`07`](07_modulos_do_sistema.md) |
| Dashboard / Diagnóstico | Indicadores nacionais, regionais, por transportadora, prazos (OTIF) | [`06`](06_regras_de_negocio.md) |
| Metas e Benchmarks (legado) | Metas nacional/regional; benchmark por macrorregião (modelo original) | [`06`](06_regras_de_negocio.md) |
| Benchmark OD / Corredor (V2.1) | Benchmark por fluxo Origem→Destino via hubs logísticos e clusters de cliente | [`06`](06_regras_de_negocio.md), [`07`](07_modulos_do_sistema.md) |
| Benchmark V2 (Matriz de Mercado) | Matriz de mercado por região OD com percentis P10–P90; benchmark observado real do cliente | [`06`](06_regras_de_negocio.md) |
| DLG — Diagnóstico Logístico Analítico | KPIs e classificação de eficiência por Filial/Rota/Transportadora/Região; detecção de outliers | [`06`](06_regras_de_negocio.md) |
| MBL — Benchmark Estatístico | Percentis próprios do cliente, excluindo outliers do DLG | [`06`](06_regras_de_negocio.md) |
| Recomendações | Consolidação determinística de ações priorizadas a partir do diagnóstico/DLG | [`06`](06_regras_de_negocio.md) |
| Concorrência Logística (BID) | CRUD de BID, máquina de estados, escopo, propostas, comparativo, simulação, relatórios | [`07`](07_modulos_do_sistema.md) |
| MCL — Motor de Decisão de BID | Score ponderado (custo/DLG/MBL/SLA/estabilidade), decisão versionada, simulação de sensibilidade | [`06`](06_regras_de_negocio.md) |
| Inteligência Logística com IA | Insights, diagnóstico IA, score logístico, oportunidades, assistente, RAG, relatório executivo | [`06`](06_regras_de_negocio.md), [`07`](07_modulos_do_sistema.md) |
| Relatórios | Excel/PDF de diagnóstico, benchmark e BID; PDF/Word/PowerPoint de IA | [`07`](07_modulos_do_sistema.md) |

## Papéis de acesso

| Papel | O que pode fazer |
|---|---|
| **Superusuário global** (`is_superuser=True`, sem empresa) | Acessa e administra todas as empresas-cliente da plataforma |
| **ADMIN** (de uma empresa) | Administra usuários e dados da própria empresa; não pode acessar outra empresa nem conceder superusuário |
| **ANALISTA** | Acesso de leitura e escrita operacional (importar, gerar BID, gerar diagnóstico etc.) dentro da própria empresa |
| **VISUALIZADOR** | Somente leitura — qualquer ação de escrita retorna 403, exceto operações que não persistem dado (ex.: simulações de prévia) |

Ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) para o detalhamento técnico de autenticação e autorização, e [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md) para o histórico de correções de segurança que levaram a este modelo.

## Stack tecnológica (resumo)

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.x (síncrono) + Alembic, Clean Architecture |
| Banco de dados | PostgreSQL 16 (produção, com `pgvector`) / SQLite (dev local sem Docker) |
| Frontend | React 18 + Vite 6 + MUI 6 + TanStack Query + Recharts |
| IA | Abstração própria sobre OpenAI (GPT-4.1) e Anthropic (Claude Haiku), com modo simulado; Celery + Redis para processamento assíncrono |
| Infraestrutura | Docker Compose (dev e produção), Nginx como proxy reverso + servidor do SPA |

Detalhes completos em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md).

## Escala atual do sistema (números reais, auditados no código em 2026-07-07)

| Métrica | Valor |
|---|---|
| Routers de API | 19 |
| Endpoints de API | 148 |
| Tabelas no banco de dados | 44 |
| Migrations Alembic | 10 |
| Entidades de domínio (dataclasses) | 35 (+ 12 enums) |
| Use cases (regras de negócio) | 25 arquivos |
| Páginas React | ~50 |
| Testes automatizados | 68 casos em 7 arquivos |

## Como navegar esta documentação

Comece por este documento, depois siga para [`02_especificacao_funcional.md`](02_especificacao_funcional.md) (o quê o sistema faz) e [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) (como é construído). O índice completo, com a ordem de leitura recomendada por perfil (novo desenvolvedor, arquiteto, QA, gestor), está em [`00_README.md`](00_README.md).
