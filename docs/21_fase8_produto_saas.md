# 21 · Fase 8 — Auditoria de Produto SaaS e Escalabilidade Comercial

> **Escopo**: exclusivamente diagnóstico — nenhum código, arquitetura, banco ou infraestrutura foi alterado nesta fase. Síntese construída sobre os relatórios das Fases 1-7 (já registrados como diagnóstico oficial) mais investigação direcionada e nova nesta fase: modelo de licenciamento/planos no código, controle de acesso à criação de empresa-cliente, e leitura por lente comercial dos achados técnicos já existentes. Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md), [`14`](14_fase1_auditoria_arquitetural.md)–[`20`](20_fase7_auditoria_funcional.md), [`10_roadmap.md`](10_roadmap.md).

---

## 1. Resumo Executivo

O GD Frete Diagnóstico tem uma base técnica genuinamente diferenciada — DLG, MBL, MCL e Recomendações formam um conjunto analítico que vai muito além de um dashboard de BI genérico, e a arquitetura multi-tenant é real (uma instância compartilhada, empresas como linhas isoladas por `empresa_id`, não uma instância por cliente). Isso é o oposto de um "MVP disfarçado de SaaS": a fundação (Clean Architecture, isolamento de aplicação, motor de decisão determinístico) suportaria crescimento se os débitos já identificados nas Fases 1-7 forem tratados com prioridade.

O achado mais crítico desta fase, porém, é novo e não havia sido nomeado explicitamente até aqui: **não existe nenhuma base técnica de plano/licenciamento**. `EmpresaModel` não tem campo de plano contratado, limite de usuários, limite de volume de CT-e ou módulos habilitados — confirmado por busca direta no schema. Todo limite hoje existente (`MAX_CTE_BATCH`, limites de upload) é uma configuração **global da plataforma**, não um parâmetro **por cliente**. Isso significa que, tecnicamente, todo cliente tem acesso a tudo, sem diferenciação comercial possível hoje além de negociação manual fora do sistema.

Agravando isso, **a criação de uma nova empresa-cliente não passa por nenhum controle comercial**: o endpoint `POST /empresas` exige apenas `require_admin`, que aceita qualquer usuário com papel ADMIN — inclusive o ADMIN de uma empresa-cliente já existente, não só a equipe da GD Conecta. Onboarding de cliente é, hoje, uma operação técnica aberta, não um processo de venda com aprovação, contrato ou vínculo de plano.

O terceiro eixo, já conhecido das Fases 3/4/5 mas relido aqui pela lente comercial: a **economia estimada do BID** — provavelmente o argumento de venda mais forte da plataforma ("pague menos frete, prove com números") — carrega hoje os achados P1 mais graves da Fase 7 (MCL-02, MCL-04/BID-07, BID-01, BID-04). Vender esse número como confiável antes de corrigi-los é o maior risco reputacional/comercial identificado nesta auditoria: é justamente o número que, se contestado por um cliente rigoroso, mina a credibilidade de todo o resto da plataforma.

Por fim, a plataforma é operada hoje como **uma instância única compartilhada por todos os tenants** — o que é bom para custo e simplicidade, mas significa que qualquer deploy, gargalo de banco (pool de 30 conexões) ou relatório pesado gerado por um cliente pode afetar **todos os outros clientes simultaneamente**. Isso é administrável com dezenas de clientes bem conhecidos e uma operação manual próxima; deixa de ser administrável sem intervenção prévia a partir de centenas.

## 2. Nota de Maturidade SaaS

# **60 / 100**

Fundação técnica e analítica sólida, com um produto genuinamente diferenciado; a lacuna que mais pesa não é de arquitetura, é de **modelo comercial ausente** (sem plano/licenciamento, sem processo controlado de onboarding) combinada aos achados funcionais já conhecidos que afetam justamente o módulo de maior potencial de venda (BID/MCL).

## 3. Avaliação por Área

| Área | Nota | Leitura |
|---|---|---|
| Produto | 75/100 | Suíte analítica real, não só consolidação de dados (confirmado na Fase 7) |
| Proposta de valor | 72/100 | Clara e diferenciada, mas depende de corrigir CONS-01 (Fase 7) para ser 100% defensável em auditoria de cliente |
| Multi-tenancy | 68/100 | Isolamento de aplicação correto (Fase 5); sem RLS (BD-09), sem gating por plano, criação de empresa sem controle comercial |
| Escalabilidade técnica | 58/100 | Consistente com a nota de Performance (Fase 3) e Banco (Fase 4) — confortável até ~100 clientes, requer intervenção antes de 1.000 |
| Operação SaaS | 50/100 | Deploy manual único afeta todos os tenants simultaneamente; sem observabilidade (Sentry/OpenTelemetry); monitoramento é `docker stats` manual |
| Onboarding | 65/100 | Tecnicamente rápido (CNPJ auto-fill, importação direta), mas primeira impressão fraca (UX-01/UX-03, Fase 6) e sem controle de quem pode criar uma empresa |
| Comercialização | 45/100 | **Achado central desta fase**: zero base técnica de plano/licenciamento — nota mais baixa de toda a auditoria de 8 fases |
| Diferenciação competitiva | 78/100 | Forte no papel (DLG/MBL/MCL como motor de decisão determinístico é raro no mercado), parcialmente comprometida pelos P1 funcionais da Fase 7 |

## 4. Pontos Fortes do Produto

- **Suíte analítica real, não dashboard passivo**: DLG detecta outlier estatístico, MBL compara contra referência própria do cliente, MCL rankeia propostas de transportadora com score multi-critério, Recomendações converte tudo isso em plano de ação priorizado — confirmado formula-a-formula na Fase 7.
- **Multi-tenancy é arquitetura real de SaaS**, não gambiarra: uma instância, um banco, empresas como linhas isoladas por `empresa_id` — não é preciso implantar uma cópia da aplicação por cliente.
- **Onboarding técnico de dado é rápido**: busca automática de CNPJ (BrasilAPI, testada ao vivo na Fase 6) reduz fricção de cadastro; importação de CT-e/Excel com validação e deduplicação está pronta para uso real desde o primeiro dia.
- **Camada de IA é estruturalmente honesta**: não calcula, só narra números que já vêm de SQL determinístico (confirmado na Fase 7) — isso é um diferencial de confiança defensável perante um cliente técnico cético sobre "IA que inventa números".
- **Modo simulado de IA sem custo** (`AI_SIMULATION_MODE=True` por padrão) permite demonstração completa da experiência de IA sem gastar créditos de API — bom para ciclo de vendas/piloto.
- **RBAC de três papéis (ADMIN/ANALISTA/VISUALIZADOR) já existe e é aplicado no backend** (Fase 5) — base necessária para vender acesso diferenciado dentro da mesma empresa-cliente (ex.: diretoria como VISUALIZADOR, operação como ANALISTA).

## 5. Riscos para Escala

| Risco | Origem | Manifesta-se a partir de |
|---|---|---|
| Pool de conexão ao banco (30 no total, compartilhado por todos os tenants) | PF-08/BD-11 (Fases 3/4) | ~100 empresas com uso simultâneo |
| Relatórios e importação síncronos competem pelos mesmos 2 workers **entre todos os tenants** — um cliente com lote grande pode atrasar outro | PF-07 (Fase 3) | Uso simultâneo de múltiplos clientes, não depende do número total |
| Zero code-splitting + cache cobrindo ~7% das telas — piora a cada módulo novo, para todo usuário | PF-04/PF-05 (Fase 3) | Cresce com o número de módulos e usuários, não com o número de empresas |
| Sem particionamento/retenção de `ctes`, `documentos_vetoriais` | BD-08 (Fase 4) | Anos de operação acumulada, não número de clientes |
| Sem Row-Level Security como defesa em profundidade do isolamento multi-tenant | BD-09/SEC-06 (Fases 4/5) | Antes de qualquer acesso direto ao banco por ferramenta externa (BI, analytics) ou crescimento de equipe |
| Deploy é `docker compose up --build` de uma instância única — toda atualização de versão afeta **todos** os tenants ao mesmo tempo, sem janela de manutenção segmentada nem staging documentado | Observação nova desta fase | Já existe hoje; risco cresce com o número de clientes ativos simultaneamente durante um deploy |
| RAG (busca semântica) cresce sem limite natural de contenção, mais lento com o tempo de uso por empresa, não com volume de CT-e | PF-03/BD-06 (Fases 3/4) | Anos de uso intenso por uma mesma empresa |

## 6. Barreiras Comerciais Identificadas

---

**EMPRESA-01 — Ausência total de modelo técnico de plano/licenciamento**
- **Evidência**: `EmpresaModel` (`app/infrastructure/database/models/__init__.py:44-64`) não tem nenhum campo de plano, limite de usuário, limite de volume de CT-e ou módulo habilitado. Busca por `plano`/`licença`/`quota`/`assinatura` no backend só retorna `plano_acao` (plano de ação da Recomendação/IA — conceito de negócio diferente, não plano comercial).
- **Impacto**: hoje é tecnicamente impossível vender "SaaS Básico" vs. "SaaS Premium" ou cobrar por módulo adicional (BID, IA) sem controle algum no sistema — qualquer diferenciação comercial depende de acordo verbal/contratual fora do produto, sem nenhuma trava técnica que a sustente. Isso não escala além de um número pequeno de clientes acompanhados manualmente.
- **Prioridade**: **SAAS-P1 — Crítico**.
- **Recomendação**: adicionar um campo `plano` (enum) e limites associados (`limite_usuarios`, `limite_ctes_mes`, `modulos_habilitados`) em `EmpresaModel`, com enforcement nos pontos de entrada relevantes (criação de usuário, importação, acesso a router de módulo).

---

**EMPRESA-02 — Criação de nova empresa-cliente não passa por controle comercial**
- **Evidência**: `POST /empresas` (`app/presentation/api/v1/empresas.py:42`) exige só `Depends(require_admin)`; `require_admin` (`dependencies.py:138-140`) é alias de `get_current_superuser`, que aceita **qualquer usuário com `role=ADMIN`**, não apenas superusuário global (`dependencies.py:126-135`).
- **Impacto**: um ADMIN de uma empresa-cliente já existente pode, tecnicamente, criar uma nova empresa no sistema — o onboarding de cliente não é uma etapa controlada de um processo de venda (aprovação, vínculo de contrato/plano), é uma chamada de API aberta a qualquer ADMIN.
- **Prioridade**: **SAAS-P1 — Crítico** (também tem leitura de segurança, mas o ângulo relevante aqui é de processo comercial/governança, não de vulnerabilidade técnica isolada).
- **Recomendação**: restringir `POST /empresas` a superusuário global (`is_superuser=True`), e tratar criação de empresa como etapa de um fluxo interno de onboarding vinculado a um plano/contrato, não uma ação disponível a qualquer administrador de empresa-cliente.

---

**BID/MCL — economia estimada, o argumento de venda mais forte, carrega os achados P1 mais graves de toda a Fase 7**
- **Evidência**: MCL-02 (referência de custo nacional desconectada do corredor real), MCL-04/BID-07 (dupla contagem de peso/frete), BID-01 (escopo sem filtro de CT-e ativo), BID-04 (BID editável após encerrado) — ver [`20_fase7_auditoria_funcional.md`](20_fase7_auditoria_funcional.md).
- **Impacto comercial**: "quanto vamos economizar trocando de transportadora" é o número mais fácil de vender e o mais fácil de um cliente rigoroso conferir de forma independente — um erro descoberto aqui, depois da venda, é o tipo de problema que gera cancelamento de contrato e dano de reputação, não só um bug técnico.
- **Prioridade**: **SAAS-P1 — Crítico** (herdado da Fase 7, elevado aqui por causa do impacto comercial direto).
- **Recomendação**: tratar os 4 achados P1 do cluster MCL/BID como pré-requisito antes de usar "economia comprovada por BID" como argumento central de venda — não é preciso esperar a evolução completa do produto, só esses quatro pontos.

---

**Sem diferenciação de módulo por contrato — todo cliente vê tudo**
- **Evidência**: consequência direta de EMPRESA-01 — não há checagem de "módulo contratado" em nenhum router.
- **Impacto**: impede um modelo de precificação por módulo (ex.: Diagnóstico + Benchmark no plano básico, BID/IA como add-on premium) sem construir isso do zero — hoje seria um esforço de desenvolvimento, não uma configuração.
- **Prioridade**: SAAS-P2 — Importante.
- **Recomendação**: consequência natural da correção de EMPRESA-01 (o campo `modulos_habilitados` já cobriria isso).

---

**Objeções de compra prováveis num ciclo de vendas técnico**
- "Os números batem entre as telas de Diagnóstico, Benchmark e Dashboard Executivo?" → hoje, não sempre (CONS-01, Fase 7) — objeção real se o prospect for tecnicamente rigoroso e comparar telas lado a lado, o que é um comportamento esperado de um comprador de ferramenta de auditoria de custo.
- "A economia do BID é garantida?" → tecnicamente não deveria ser vendida como número auditável ainda (ver acima).
- "Meus dados ficam isolados de outros clientes?" → sim na aplicação (Fase 5), mas sem RLS como camada extra no banco — resposta defensável para a maioria dos clientes, potencialmente insuficiente para um cliente enterprise com exigência de auditoria de segurança formal (SOC2-like).
- "Quanto custa por usuário/módulo?" → sem resposta técnica pronta hoje (EMPRESA-01) — força negociação manual em cada novo cliente.
- Primeira tela que um prospect em demonstração vê (login) não comunica identidade de produto nenhuma (UX-01, Fase 6) — detalhe pequeno, mas é literalmente a primeira impressão de qualquer demonstração comercial.

## 7. Capacidade Estimada de Crescimento

| Cenário | Avaliação |
|---|---|
| **10 clientes** | Confortável em todas as dimensões técnicas (Fases 3/4 já confirmam isso) — o modelo de operação manual/consultiva (sem plano técnico, onboarding acompanhado de perto pela equipe) funciona bem nessa escala; é, na prática, o modelo implícito que a plataforma já opera hoje. |
| **100 clientes** | Tecnicamente ainda administrável **se o uso simultâneo for baixo**, mas é o ponto em que a ausência de modelo de plano/licenciamento (EMPRESA-01) deixa de ser uma lacuna teórica e passa a ser um problema operacional real — cada cliente novo negociado manualmente, sem trava de limite, sem diferenciação de módulo, é uma carga administrativa que cresce linearmente com o número de clientes, não com processo. É também o ponto de revisar o pool de conexão (PF-08/BD-11) antes que vire incidente. |
| **1.000 clientes** | Barreira dupla — técnica **e** de modelo de negócio. Tecnicamente: pool de conexão, ausência de particionamento/retenção e ausência de RLS deixam de ser "boas práticas futuras" (Fases 3/4). Comercialmente: é operacionalmente inviável vender/onboardar 1.000 clientes sem nenhuma base de self-service, plano técnico ou automação de onboarding — o gargalo nesse volume não é só o banco de dados, é o processo humano por trás de cada cliente novo. |

## 8. Roadmap SaaS Recomendado

### Curto prazo (0-6 meses)
- **EMPRESA-01**: adicionar campo de plano/licenciamento e limites por empresa em `EmpresaModel`, mesmo que o enforcement inicial seja simples.
- **EMPRESA-02**: restringir criação de empresa a superusuário global.
- Corrigir os achados P1 já conhecidos que afetam diretamente a credibilidade comercial: **CONS-01** (Fase 7, consistência de dados entre telas) e o cluster **MCL/BID** (MCL-02, MCL-04/BID-07, BID-01, BID-04).
- **UX-01** (identidade visual do login) — baixo esforço, alto impacto na primeira impressão comercial (já recomendado na Fase 6).
- Corrigir **SEC-01/02/03** (Fase 5, já aprovados como pendentes de implementação).
- Gerar as migrations Alembic faltantes (**BD-04**) antes de qualquer deploy dedicado a um cliente-âncora que exija instância própria.

### Médio prazo (6-18 meses)
- Resolver os débitos de escalabilidade antes que se tornem urgentes: pool de conexão (PF-08/BD-11), mover relatórios/importação de lote para Celery (PF-07), completar code-splitting e cache no frontend (PF-04/PF-05).
- Implementar RLS como camada adicional de defesa em profundidade (BD-09), especialmente se surgir demanda de acesso direto ao banco por ferramenta de BI de algum cliente maior.
- Observabilidade (Sentry/OpenTelemetry) e um processo de deploy com staging e janela de impacto reduzida — hoje um deploy afeta todos os tenants simultaneamente sem aviso.
- Automatizar mais do fluxo de onboarding (auto-provisionamento de empresa vinculado a um plano já definido, reduzindo a etapa manual da equipe).

### Longo prazo (18-36 meses)
- Migração de `Float` para `Numeric`/`Decimal` nos campos monetários (BD-01) — relevante conforme a base de clientes e o rigor de auditoria financeira crescem.
- Estratégia de particionamento/retenção de `ctes` e tabelas de IA (BD-08) antes que o volume torne a migração arriscada.
- Avaliar V5 (Benchmark Coletivo Anonimizado, já no roadmap) como diferencial de rede — quanto mais clientes, melhor o benchmark de todos, um efeito de rede que nenhum concorrente pontual (BI genérico, planilha, consultoria pontual) replica facilmente.
- Se o modelo comercial evoluir para self-service (PLG), completar a base iniciada em EMPRESA-01/02 com um fluxo de signup e provisionamento automático real.

## 9. Conclusão

**O GD Frete Diagnóstico está pronto para ser vendido como plataforma SaaS — com um modelo de venda consultivo e acompanhado, a um número pequeno-médio de clientes (dezenas), não para uma operação self-service em escala.**

A tecnologia central (DLG/MBL/MCL/Recomendações, multi-tenancy real, RBAC) é diferenciada e sólida o suficiente para sustentar esse modelo hoje. O que falta não é uma reconstrução — é fechar uma lista objetiva e majoritariamente já conhecida:

1. **Modelo técnico de plano/licenciamento** (EMPRESA-01) — hoje inexistente; é o único achado desta fase que não vem de nenhuma auditoria anterior.
2. **Controle de acesso à criação de empresa-cliente** (EMPRESA-02) — onboarding hoje é uma chamada de API aberta, não um processo comercial.
3. **Os achados P1 de segurança (Fase 5)** e **funcionais (Fase 7)** já aprovados como diagnóstico oficial, com destaque para **CONS-01** e o cluster **MCL/BID** — porque afetam diretamente o argumento de venda mais forte da plataforma (economia comprovada por dado).
4. **Os débitos de escalabilidade já quantificados (Fases 3/4)** — não urgentes para o volume atual, mas devem ser tratados antes de qualquer campanha comercial agressiva que mire dezenas de clientes novos em pouco tempo, não depois que o incidente já tiver acontecido.

Nenhum desses quatro pontos exige descobrir algo novo — a auditoria de 8 fases já identificou todos eles. O que resta é a decisão de priorizar a correção antes da expansão comercial, não durante ou depois dela.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhum código, arquitetura, banco de dados ou infraestrutura foi alterado durante esta auditoria.*
