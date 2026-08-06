# 00 · Contexto Oficial do GD Frete Diagnóstico

> **Natureza e autoridade deste documento**: este é o **documento mestre e a principal referência oficial** do projeto GD Frete Diagnóstico. A partir desta versão, a documentação versionada em `/docs` — não a memória de conversas entre humano e IA, nem o histórico de nenhuma sessão específica — é a única fonte oficial de verdade sobre o que a plataforma é, para quem existe e como deve evoluir. Qualquer agente de IA (ChatGPT, Claude Chat, Claude Code, ou qualquer ferramenta futura) que inicie trabalho neste projeto deve ler este documento primeiro — ver ordem obrigatória de leitura em [`README_AI.md`](README_AI.md).
>
> Este documento consolida, de forma concisa e permanente, o conteúdo estratégico já elaborado e aprovado nas Seções 12-21 de [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) (Revisão Estratégica de 2026-07-07). Onde houver necessidade de aprofundamento — justificativa ligada a achado de auditoria, raciocínio completo, tabelas detalhadas — este documento aponta para a seção correspondente do Plano Diretor Técnico em vez de duplicar. Em caso de divergência futura entre os dois, **este documento prevalece como definição oficial**, e o Plano Diretor Técnico deve ser atualizado para refletir a mudança no mesmo ciclo (ver Seção 11 abaixo e a convenção de "documentação viva" em [`00_README.md`](00_README.md)).
>
> Nenhum código, schema, API ou regra de negócio foi alterado na criação deste documento. Atividade exclusivamente documental.

---

## 1. Missão

Dar à equipe de analistas da GD Conecta o motor analítico e a produtividade necessários para transformar dados fiscais de transporte (CT-e, NF-e, Excel) em diagnóstico, benchmark e recomendação de frete auditáveis, entregues ao cliente como decisão executiva — não como planilha.

## 2. Visão

Ser o motor analítico de referência por trás de toda entrega de diagnóstico de frete da GD Conecta — o padrão contra o qual qualquer indicador, benchmark ou recomendação apresentada a um cliente é calculado, validado e rastreável até a regra de negócio que o gerou.

## 3. Posicionamento

**O GD Frete Diagnóstico é uma Plataforma de Inteligência para Governança de Fretes, utilizada pela equipe de analistas da GD Conecta para transformar dados logísticos em diagnósticos, benchmark, recomendações e apresentações executivas para seus clientes.**

Nesta fase do produto, a plataforma **não deve ser tratada como um SaaS tradicional voltado ao uso direto do cliente final**. O usuário prioritário é o analista da GD Conecta; o cliente é o consumidor das informações produzidas pelo motor analítico, não o operador da plataforma. A arquitetura permanece preparada — e deve continuar sendo mantida assim — para disponibilizar essas informações diretamente ao cliente no futuro (Seção 9), mas essa não é a prioridade da fase atual.

A arquitetura multi-tenant real (uma instância, empresas-cliente como linhas isoladas, ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) e [`21_fase8_produto_saas.md`](21_fase8_produto_saas.md)) já valida a *capacidade técnica* de operar como SaaS multi-cliente. Este posicionamento define o *modelo de uso oficial* da fase atual — mais restrito por decisão de produto, não por limitação técnica.

## 4. Público-Alvo

| Perfil | Papel no produto | Mapeamento técnico atual |
|---|---|---|
| **Usuário Primário** — Equipe de Analistas da GD Conecta | Opera a plataforma diariamente: importa dado, gera diagnóstico/benchmark/BID, interpreta o output da IA, monta o Relatório Executivo | Papel RBAC `ANALISTA` (ou `ADMIN` quando também administra usuários/empresa) |
| **Usuário Secundário** — Consultores da GD Conecta | Acompanha entregas, participa da decisão de BID e da apresentação executiva ao cliente | Hoje sem papel RBAC dedicado — opera sob `ANALISTA` ou `VISUALIZADOR` |
| **Consumidor da Informação** — Clientes atendidos pela GD Conecta | Recebe diagnóstico, benchmark e recomendações via Relatório Executivo HTML/PDF | Sem login hoje — consome o artefato exportado, não a aplicação |
| **Usuário Futuro** — Portal do Cliente | Evolução planejada (não priorizada nesta fase) para acesso direto e controlado do cliente | Não implementado; arquitetura multi-tenant já compatível em princípio |

Decisões de UX e de priorização de funcionalidade devem otimizar primeiro para o Usuário Primário (analista). Detalhamento completo em [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 13.

## 5. Princípios Permanentes

1. **O motor analítico é o principal ativo da plataforma.** DLG, MBL, MCL, Score e Recomendações ([`06_regras_de_negocio.md`](06_regras_de_negocio.md)) são o que a plataforma vende — telas, relatórios e IA existem para tornar esse motor acessível e apresentável, não para substituí-lo.
2. **A plataforma operacionaliza a metodologia da GD Conecta.** Toda fórmula, peso e limiar implementados devem corresponder a uma decisão de metodologia já validada pela GD Conecta, não a uma escolha técnica arbitrária — daí a rastreabilidade `RN-xx` mantida desde a Fase 0 de auditoria.
3. **A IA interpreta resultados, nunca calcula indicadores.** Ver Seção 8.
4. **Relatórios executivos são parte integrante do produto, não um extra.** O Relatório Executivo HTML (Seção 6) é entregável de primeira classe, com o mesmo padrão de qualidade e revisão que qualquer módulo analítico.
5. **Priorizar profundidade analítica e produtividade do analista.** Entre duas funcionalidades candidatas, prioriza-se a que aumenta a capacidade do analista de produzir um diagnóstico de maior valor, não a que apenas adiciona superfície de produto.
6. **Evitar funcionalidades que desviem do propósito principal.** Funcionalidades genéricas de BI, automações não relacionadas a frete, ou expansão de escopo para fora da cadeia da Seção 6 devem ser questionadas antes de entrar no roadmap — ver checklist de governança em [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 21.

## 6. Arquitetura Conceitual

Leitura de produto sobre a arquitetura técnica já documentada em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) — não a substitui nem a altera:

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
IA Interpretativa (narra e prioriza, nunca calcula — Seção 8)
        ↓
Apresentação Executiva
        ↓
Relatório Executivo HTML (artefato de entrega padrão ao cliente)
        ↓
Exportação PDF (derivada do HTML, não um caminho de cálculo paralelo)
        ↓
Portal do Cliente (evolução futura — Seção 9, não priorizada nesta fase)
```

**Ponto central**: todas as camadas acima do Motor Analítico reutilizam o mesmo motor. Não existe, e não deve existir, um segundo caminho de cálculo para o Portal do Cliente futuro, para a exportação em PDF, ou para qualquer apresentação executiva.

## 7. O Relatório Executivo HTML

- O principal artefato entregue ao cliente é o **Relatório Executivo HTML** — materialização direta da cadeia da Seção 6.
- O **PDF é uma exportação** do Relatório Executivo HTML, não um caminho de geração paralelo.
- Toda funcionalidade nova do motor analítico deve considerar sua apresentação dentro do Relatório Executivo, quando aplicável.
- A plataforma deve **reutilizar componentes existentes** para compor o Relatório Executivo, em vez de construir uma camada de apresentação paralela por módulo.

Detalhamento em [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 18.

## 8. Papel da IA no Produto

A camada de IA do produto (insights automáticos, diagnóstico executivo, score logístico, detecção de oportunidades, assistente conversacional, RAG — ver [`01_visao_geral.md`](01_visao_geral.md)) **interpreta e prioriza, nunca calcula**. Todo número que a IA apresenta vem de SQL/Python determinístico já executado pelo motor analítico (Seção 6); a IA nunca é a origem de um indicador, benchmark ou recomendação.

Este princípio de produto é distinto do papel das *ferramentas de IA usadas no processo de desenvolvimento* (ChatGPT, Claude Chat, Claude Code) — esse segundo tema é tratado em [`README_AI.md`](README_AI.md), não aqui.

## 9. Estratégia de Evolução

**Fase Atual — Fortalecimento da Plataforma do Analista.** Prioridade: profundidade analítica, consistência de dado entre módulos (achado CONS-01, [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) Seção 4), produtividade do analista, e consolidação do Relatório Executivo HTML (Seção 7).

**Fase Posterior — Disponibilização gradual de funcionalidades para um Portal do Cliente.** Sem data-alvo definida — depende de decisão comercial futura da GD Conecta. Quando priorizada, deve reutilizar o mesmo motor analítico (Seção 6) e reaproveitar componentes já existentes do Relatório Executivo HTML.

**Regra de priorização**: toda decisão de produto deve priorizar primeiro o uso interno pelos analistas. Uma funcionalidade que beneficia o Portal do Cliente futuro, mas não fortalece a Plataforma do Analista hoje, não deve furar a fila do roadmap técnico aprovado ([`10_roadmap.md`](10_roadmap.md), [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) Seção 9).

**Atualização (2026-08-06) — decisão comercial tomada.** A "decisão comercial futura" referida acima foi tomada: a GD Conecta decidiu iniciar a Fase Posterior e priorizar um primeiro recorte do Portal do Cliente (ver Validação Estratégica e PRD em [`specs/v6.18.0/`](specs/v6.18.0/)). Isto **destrava a fase, não revoga a Regra de priorização**: o primeiro recorte do Portal do Cliente foi desenhado como uma camada de acesso somente-leitura sobre indicadores, gráficos e recomendações que o motor analítico já produz para o analista hoje — reutilizando o mesmo motor (Seção 6) e os mesmos componentes do Relatório Executivo HTML, sem introduzir cálculo paralelo nem desviar capacidade de engenharia do roadmap técnico já aprovado. Detalhamento completo da avaliação contra o checklist de Governança do Produto (Seção 21 do Plano Diretor) na Validação Estratégica de `specs/v6.18.0/`.

## 10. Diretrizes Arquiteturais

Confirmação explícita, como decisão de produto, dos princípios arquiteturais já documentados em [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) e avaliados na Fase 1 de auditoria ([`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md)):

- **Preservação da Clean Architecture** — nenhuma decisão de produto exige ou sugere abandonar as camadas de domínio/aplicação/infraestrutura já em uso.
- **Reutilização de componentes** — telas, relatórios e, sobretudo, o motor analítico (Seção 6) devem ser reaproveitados por novas funcionalidades, não reimplementados.
- **Ausência de duplicação de regras de negócio** — toda fórmula tem um único lugar de origem, com código `RN-xx` ([`06_regras_de_negocio.md`](06_regras_de_negocio.md)).
- **Documentação sincronizada com o código** — convenção "documentação viva, não retroativa" vigente desde a Fase 0 de auditoria ([`00_README.md`](00_README.md)).
- **Rastreabilidade entre requisitos, código e testes** — todo requisito de negócio deve ser localizável em `06_regras_de_negocio.md`, no código que o implementa e no teste que o cobre.
- **Evolução incremental** — consistente com a ordem de implementação já sequenciada em [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 8.

## 11. Política de Versionamento

| Nível | Critério |
|---|---|
| **PATCH** | Correções que não alteram comportamento esperado nem contrato de API/dado |
| **MINOR** | Novas funcionalidades compatíveis com o comportamento existente |
| **MAJOR** | Mudanças estruturais incompatíveis (contrato de API, schema que quebra compatibilidade, redesenho de módulo existente) |

A definição do nível de versão é sempre uma decisão de engenharia, baseada no impacto real da entrega — nunca uma decisão de marketing ou de expectativa comercial. Em caso de dúvida entre dois níveis, aplica-se o mais conservador. Ver histórico real de versões em [`11_changelog.md`](11_changelog.md).

## 12. Relação com os Demais Documentos

| Documento | Relação com este documento |
|---|---|
| [`README_AI.md`](README_AI.md) | Operacionaliza este contexto para agentes de IA: ordem de leitura, processo oficial, papéis das ferramentas, regras de bloqueio |
| [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) | Elaboração detalhada e ligada à auditoria técnica do conteúdo estratégico resumido aqui (Seções 12-21 do Plano Diretor) |
| [`10_roadmap.md`](10_roadmap.md) | Débitos técnicos e estado de roadmap por fase — a Estratégia de Evolução (Seção 9) prioriza o que este roadmap sequencia |
| [`11_changelog.md`](11_changelog.md) | Histórico real de versões — referência para aplicar a Política de Versionamento (Seção 11) |
| [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) | Levantamento factual do estado técnico — base para qualquer nova Especificação Técnica verificar o código real antes de propor mudança |
| [`06_regras_de_negocio.md`](06_regras_de_negocio.md) | Fonte de verdade das fórmulas do motor analítico (Seção 1, Seção 5, princípio 1 e 2) |
| [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md) | Fonte de verdade da arquitetura técnica (Seção 6, Seção 10) |

---

*Documento criado em 2026-07-08 como parte da camada oficial de governança do projeto. Versão deste documento: 1.1.0 (atualização de 2026-08-06 na Seção 9 — registro da decisão comercial de iniciar a Fase Posterior do Portal do Cliente; texto original da Seção 9 preservado acima, sem remoção). Nenhum código, banco de dados, API ou infraestrutura foi alterado na sua produção. Ver [`00_README.md`](00_README.md) para o índice completo da documentação e [`README_AI.md`](README_AI.md) para o guia de uso desta documentação por agentes de IA.*
