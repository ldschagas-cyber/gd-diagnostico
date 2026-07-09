---
name: archive-readme
---

# Arquivo Histórico da Documentação

Esta pasta preserva **todos** os documentos originais da pasta `/docs`, encontrados durante a auditoria e consolidação documental de **2026-07-07** (Fase 0). Nenhum conteúdo foi excluído — tudo aqui permanece disponível para consulta histórica, auditoria de proveniência ou recuperação de detalhes que não foram trazidos para a documentação oficial nova.

**A documentação oficial vigente está em `/docs` (fora desta pasta).** Os arquivos abaixo são histórico e **não devem ser usados como referência técnica atual** — eles descrevem o sistema em versões anteriores (principalmente v2.0.0 e v3.0.0), e o próprio código já avançou até v6.5.1.

## Conteúdo arquivado

| Arquivo | O que era | Por que foi arquivado | Onde a informação foi incorporada |
|---|---|---|---|
| `01_especificacao_funcional.md` | Especificação funcional v2.0.0 (RN01–RN19, indicadores, benchmark regional legado) | Cobre só até o benchmark regional "legado"; não menciona Benchmark OD (V2.1), BID, IA, DLG/MBL/MCL, Recomendações | `02_especificacao_funcional.md` (novo) |
| `especificacao_funcional.docx` | Versão Word resumida do documento acima, mesma versão 2.0.0 | Subconjunto do `.md` acima, mesmas lacunas | `02_especificacao_funcional.md` (novo) |
| `especificacao_funcional_benchmark_od_v2.1.docx` | Especificação da correção do modelo de Benchmark para fluxo Origem→Destino (V2.1) — nome original do arquivo estava corrompido por problema de encoding, corrigido aqui | Documento pontual de uma mudança específica, nunca integrado à numeração oficial nem referenciado pelos demais docs | `02_especificacao_funcional.md` e `06_regras_de_negocio.md` (novo) |
| `02_arquitetura_tecnica.md` | Arquitetura técnica v2.0.0 (11 routers, 1 migration) | Cobre ~58% dos routers reais (19 hoje) e cita só 1 de 10 migrations | `03_arquitetura_tecnica.md` (novo) |
| `03_dicionario_dados.md` | Dicionário de dados do schema inicial (11 tabelas) | O schema real tem 44 tabelas — cobre ~25% | `04_modelo_de_dados.md` (novo) |
| `04_catalogo_apis.md` | Catálogo de API v2.0.0 (~50 endpoints estimados) | O sistema real tem 148 endpoints em 19 routers | `05_apis.md` (novo) |
| `05_guia_deploy_ubuntu.md` | Guia de deploy em produção (Ubuntu 24.04) | Não menciona Redis/Celery (necessários desde a v5.0.0); `client_max_body_size` divergente do `nginx.conf` real | `08_instalacao_deploy.md` (novo) |
| `06_guia_manutencao.md` | Guia de manutenção para desenvolvedores | Número de testes desatualizado ("9 testes"); não cobre variáveis de ambiente de IA | `09_manutencao.md` (novo) |
| `07_changelog.md` | Changelog v1.0.0 → v5.0.0/v4.0.0 | Entradas fora de ordem cronológica; sem nenhum registro de v6.0.0 a v6.5.1 | `11_changelog.md` (novo, reordenado e estendido) |
| `08_auditoria_arquitetural.md` | Auditoria arquitetural completa da v2.0.0 (25 problemas P-01 a P-25, 12 riscos de segurança S-01 a S-12) | Audita uma versão de código com ~4× menos endpoints/tabelas que a atual; números de linha citados não correspondem mais ao código | `12_auditoria_tecnica.md` (novo, como registro histórico) |
| `08_auditoria_arquitetural.docx` | Versão resumida/apresentação do documento acima | Mesma limitação, e ainda diverge do `.md` na numeração de problemas (P-26/27/28 só existem aqui) | `12_auditoria_tecnica.md` (novo) |
| `09_relatorio_implementacao_v3.md` | Relatório de remediação das correções da v3.0.0 (antes/depois, reavaliação de notas, débitos técnicos DT-01 a DT-14) | Nunca foi refeito para as versões v4, v5, v6.x | `12_auditoria_tecnica.md` (novo) |
| `10_guia_instalacao_v4_ia.md` | Guia de instalação do módulo de IA (Redis, Celery, chaves de API) | Tom conversacional dirigido a uma sessão de suporte específica; não cobre v6.x | `08_instalacao_deploy.md` (novo) |

## Divergências e contradições identificadas nesta auditoria (registro)

Estas inconsistências foram encontradas comparando os documentos arquivados entre si e com o código-fonte. Ficam registradas aqui para rastreabilidade; a documentação nova já reflete o estado real do código, não estes valores:

1. **Banco de dados principal**: `backend/README.md` (fora de `/docs`, não arquivado) afirmava "SQLite, preparado para migração a PostgreSQL"; `02_arquitetura_tecnica.md` e o changelog `[2.0.0]` já tratavam PostgreSQL como banco de produção. **Código real**: PostgreSQL em produção (`docker-compose.prod.yml`), SQLite só em dev local sem Docker. *(Corrigido em `backend/README.md` em 2026-07-07, junto desta consolidação — ver nota abaixo.)*
2. **Biblioteca de hash de senha**: `backend/README.md` citava "passlib"; `02_arquitetura_tecnica.md` dizia explicitamente "não usa passlib — compatibilidade Python 3.14". **Código real**: `bcrypt` direto, sem passlib (`app/core/security.py`). *(Corrigido em `backend/README.md`.)*
3. **Limite de lote de importação de CT-e**: `backend/README.md` citava 10.000; o changelog `[3.0.0]` (P0 de segurança) fala em 500/lote. **Código real**: `MAX_XML_BATCH = 500` em `importacao.py` (upload físico); `MAX_CTE_BATCH = 10000` em `config.py` é um limite diferente — agora ambos distinguidos em `backend/README.md` e em [`../08_instalacao_deploy.md`](../08_instalacao_deploy.md).
4. **`client_max_body_size` do Nginx**: `05_guia_deploy_ubuntu.md` cita 50M; auditoria/relatório v3 citam 25M. **Código real** (`frontend/nginx.conf`): 25M no bloco raiz, 50M no bloco `/api/` — ambos os documentos antigos citavam só um dos dois valores, sem indicar que são blocos diferentes.
5. **Número de testes automatizados**: `06_guia_manutencao.md`/`09_relatorio_implementacao_v3.md` citam "9 testes"; `07_changelog.md [4.0.0]` já falava em 45. **Código real hoje**: 7 arquivos de teste, 68 casos no total.
6. **"Transportadoras globais"**: `01_especificacao_funcional.md`, `02_arquitetura_tecnica.md` e `03_dicionario_dados.md` apresentam transportadoras como cadastro global compartilhado. **Código real**: `transportadoras.empresa_id` existe desde a migração `a2f8c1e4b9d3` (v3.0.0) — isolado por empresa desde então.
7. **Numeração de problemas da auditoria**: `08_auditoria_arquitetural.md` numera P-01 a P-25; a versão `.docx` do mesmo relatório cita adicionalmente P-26, P-27, P-28, que não existem no `.md`.

## Nota sobre `backend/README.md`

Esse arquivo fica fora de `/docs` (é o README do módulo `backend/`, não parte do conjunto de documentação numerado) e por isso não foi movido para este arquivo — mas continha as três contradições acima (itens 1–3), todas herdadas de uma versão anterior à v2.0.0 e nunca corrigidas. Em 2026-07-07, junto desta consolidação, `backend/README.md` foi **reescrito integralmente** para refletir o estado real do código (v6.5.1) e agora aponta para `../docs/00_README.md` como referência completa, mantendo-se como um guia rápido de desenvolvimento local.

## Convenção de nomenclatura de versão (esclarecimento)

Os documentos antigos misturam **nome de versão de produto** ("V3.1 — BID de Frete", "V4 — Inteligência com IA") com **número semver do changelog** (`4.0.0`, `5.0.0`), de forma não correspondente (produto "V3.1" = changelog `4.0.0`; produto "V4" = changelog `5.0.0`). A documentação nova (`11_changelog.md`) mantém ambas as referências lado a lado para evitar essa confusão daqui em diante.
