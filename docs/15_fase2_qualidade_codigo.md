# 15 · Fase 2 — Auditoria de Qualidade do Código

> **Escopo**: exclusivamente diagnóstico — nenhum arquivo de código, configuração ou banco de dados foi alterado nesta fase. Toda evidência abaixo foi coletada por leitura direta do código-fonte em 2026-07-07 (análise estática via AST, grep, leitura de trecho), não por inferência. Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) e [`14_fase1_auditoria_arquitetural.md`](14_fase1_auditoria_arquitetural.md) (Fase 1 — esta fase não reavalia arquitetura, foca em qualidade de código dentro da arquitetura já descrita).

---

## 1. Resumo Executivo

O código do GD Frete Diagnóstico é **legível e consistente na superfície** — nomenclatura em português coerente com o domínio, estrutura de pastas previsível, ausência de `print()` de depuração esquecido, zero teste marcado como `skip`/`xfail` (tudo que existe roda de verdade). Abaixo dessa superfície, a qualidade é **desigual entre módulos**: os módulos mais antigos (CT-e, Diagnóstico clássico, BID) têm funções menores e mais logging; os módulos analíticos mais recentes (DLG, MBL, MCL, Recomendações) concentram lógica de negócio em métodos longos e ramificados, com cobertura de log e de docstring visivelmente menor.

Não encontrei nenhum código genuinamente perigoso (sem `eval` fora do avaliador de regras já sandboxado, sem SQL montado por concatenação de string, sem segredo hardcoded). Os problemas são de **manutenibilidade acumulada**: funções que fazem demais, duplicação pontual (uma função de percentil, um par de formatadores de moeda), e uma divisão de estilo (`detail=` nomeado vs. posicional em `HTTPException`, uso de logging em 44% dos use cases) que não compromete o funcionamento mas dificulta consistência para quem entra agora.

O teste automatizado do backend é sólido para o que cobre (68 casos, estilo smoke/integração com banco real, boa densidade de assert) mas é **estilo integração, não unitário** — nenhum teste isola um use case do banco, então uma regra de negócio complexa (ex.: o score do MCL) só é validada de ponta a ponta, nunca isolada. O frontend tem **zero teste automatizado**, herdado como débito desde a auditoria original e nunca endereçado.

## 2. Nota de Qualidade do Código

# **67 / 100**

Código limpo e legível na maior parte da base, com bolsões concentrados de complexidade nos módulos analíticos mais novos e uma lacuna real de teste unitário/frontend.

## 3. Avaliação por Área

| Área | Nota | Leitura |
|---|---|---|
| Backend | 70/100 | Legível, mas com funções de 70-100+ linhas concentrando regra de negócio em módulos específicos |
| Frontend | 65/100 | Consistente em tratamento de erro; lógica de cálculo vazando para dentro de componentes em 16 de 44 páginas |
| Testes | 60/100 | Boa cobertura de fluxo crítico no backend (integração); zero unitário; zero frontend |
| Organização | 68/100 | Coerente com a Fase 1 — bem dividida por módulo, com pontos de arquivo monolítico já conhecidos |
| Padronização | 65/100 | Nomenclatura e idioma consistentes; convenção de `HTTPException` e uso de logging inconsistentes |
| Manutenibilidade | 70/100 | Alinhado à Fase 1; docstring/logging desiguais entre módulo antigo e novo puxam a nota para baixo |

## 4. Pontos Fortes

- **Zero `print()` de depuração** em todo o backend — onde há logging, é via `get_logger`, não debug esquecido.
- **Zero teste desabilitado** (`skip`/`xfail`) — os 68 casos realmente rodam a cada execução, não há teste "quebrado e ignorado".
- **Densidade de assert saudável**: média de 3 a 5 `assert` por teste nas suítes de fumaça — não são testes "vazios" que só checam status 200.
- **Idioma e nomenclatura de domínio 100% consistentes** — todo o backend e frontend usa português para nomes de negócio (`Transportadora`, `gerar_escopo`, `Frete R$/kg`), sem mistura com inglês a meio caminho, o que reduz a carga cognitiva de tradução mental.
- **Validação de CNPJ centralizada corretamente** — uma única implementação (`_validar_cnpj` em `schemas/__init__.py`), reusada por matriz e filial, sem duplicação.
- **Tratamento de erro do frontend 100% uniforme** — as 44 páginas usam `extrairErro()`, sem exceção.
- **Nenhum padrão inseguro clássico encontrado**: sem `eval()` fora do avaliador de regras já sandboxado (que roda sem `__builtins__`), sem concatenação de string formando SQL, sem segredo hardcoded em código (só em `.env`/exemplo, já tratado na auditoria de segurança anterior).

## 5. Pontos Fracos

- Concentração de regra de negócio em métodos longos e ramificados em módulos específicos (DLG, MBL, Recomendações, MCL).
- Cobertura de logging desigual: só 11 dos 25 use cases (44%) usam o logger da aplicação — os outros 14 não registram nada, mesmo em caminhos de erro tratado.
- Cobertura de docstring em métodos públicos de use case: 37% (36 de 98) — muito concentrada em poucos arquivos, quase ausente em outros.
- Duplicação pontual e evitável (função de percentil, formatadores de moeda/número).
- Inconsistência estilística no uso de `HTTPException` (61 ocorrências posicionais vs. uso nomeado `detail=` em outros lugares).
- 7 pontos onde a mensagem de uma exceção interna (`str(e)`) é repassada diretamente ao cliente da API.
- Testes de backend são só de integração — nenhuma regra de negócio complexa (ex.: cálculo de score) tem teste unitário isolado do banco.
- Zero teste de frontend.

## 6. Achados Técnicos

---

### Q-01 — Métodos com alta concentração de regra de negócio e ramificação

- **Prioridade**: P2 — Médio
- **Descrição**: análise estática (AST) do backend identificou os métodos mais longos/ramificados do sistema. Os cinco mais relevantes:

| Função | Arquivo:linha | Linhas | Ramos (if/for/while/bool) |
|---|---|---|---|
| `_agregar_transportadoras` | `dlg.py:372` | 99 | 16 |
| `consolidar` | `recomendacoes.py:58` | 106 | 11 |
| `_processar_periodo` | `mbl.py:149` | 87 | 14 |
| `_coletar_metricas` | `insights.py:115` | 68 | 11 |
| `_calcular_scores` | `mcl.py:189` | 67 | 8 |

- **Impacto**: são exatamente os motores de decisão mais críticos do produto (DLG, MBL, MCL, Recomendações, Insights) — os que mais precisarão de ajuste fino de regra de negócio ao longo do tempo, e são também os mais difíceis de modificar com segurança hoje, por concentrarem muita lógica numa única função.
- **Causa provável**: cada uma dessas funções nasceu implementando uma regra de negócio com várias exceções/casos (ex.: dedup de transportadora por identidade real, classificação por múltiplos limiares) — a lógica cresceu organicamente dentro do método original em vez de ser extraída incrementalmente.
- **Risco de não corrigir**: médio — o risco não é o código quebrar sozinho, é o próximo ajuste de regra de negócio (ex.: mudar o limiar de outlier do DLG) introduzir um efeito colateral não percebido por estar misturado com outras 15 ramificações na mesma função.
- **Solução recomendada**: extrair sub-passos nomeados (ex.: `_deduplicar_transportadoras`, `_classificar_desvio`) dentro do mesmo arquivo, sem mudar a interface pública do use case.
- **Esforço estimado**: Médio por função (meio dia cada, com teste de regressão).

---

### Q-02 — Cobertura de logging desigual entre use cases

- **Prioridade**: P2 — Médio
- **Descrição**: apenas 11 dos 25 use cases (44%) importam/usam `get_logger`. Os 14 restantes — incluindo módulos que fazem chamada a serviços externos (IA) ou processamento em lote (importação, cancelamento) — não registram log algum em seus próprios métodos.
- **Impacto**: quando algo dá errado num desses 14 use cases sem gerar exceção HTTP (ex.: uma condição de borda silenciosamente ignorada), não sobra rastro nenhum para investigação posterior.
- **Causa provável**: logging foi adicionado pontualmente onde parecia necessário no momento, não como convenção aplicada a todo use case novo.
- **Localização**: `app/application/use_cases/*.py` (14 arquivos sem `get_logger`)
- **Risco de não corrigir**: médio — cresce junto com o achado A-11 da Fase 1 (zero observabilidade); sem log nem observabilidade, um incidente silencioso é praticamente invisível.
- **Solução recomendada**: adicionar logging nos pontos de decisão relevantes (early return, fallback, dado inconsistente) dos 14 use cases, priorizando os que lidam com dinheiro/decisão (BID, MCL) e com IA (custo de API).
- **Esforço estimado**: Baixo-Médio (mecânico, mas em 14 arquivos).

---

### Q-03 — Cobertura de docstring baixa e desigual em métodos públicos de use case

- **Prioridade**: P3 — Baixo
- **Descrição**: 37% (36/98) dos métodos públicos de use case têm docstring. A distribuição não é uniforme — alguns arquivos (ex.: `dlg.py`, cujo cabeçalho de módulo é bem documentado) têm boa cobertura; outros não têm nenhuma docstring de método, só o docstring de módulo no topo do arquivo.
- **Impacto**: para regras com fórmula/peso específico (ex.: `RN-34` a `RN-48`, já catalogadas em [`06_regras_de_negocio.md`](06_regras_de_negocio.md)), a única fonte de verdade acaba sendo o próprio código sem explicação inline de por que aquele peso/limiar foi escolhido.
- **Causa provável**: convenção de "comentário só quando não-óbvio" aplicada de forma inconsistente — alguns autores documentaram o "porquê" da fórmula, outros deixaram só o código.
- **Localização**: `app/application/use_cases/*.py`, distribuído
- **Risco de não corrigir**: baixo — a documentação de regras de negócio já foi centralizada em `06_regras_de_negocio.md` (Fase 0), o que mitiga parte do problema; falta o "porquê" de escolhas específicas de constante (ex.: por que 1,75 no fator de suavização logarítmica do benchmark OD).
- **Solução recomendada**: docstring nos métodos que implementam fórmula com constante "mágica", explicando a origem/motivação do valor, não o que o código já deixa claro.
- **Esforço estimado**: Baixo, incremental.

---

### Q-04 — Duplicação da função de cálculo de percentil (já registrado na Fase 1 como A-03, reclassificado aqui como achado de qualidade de código)

- **Prioridade**: P2 — Médio
- **Descrição**: `_percentil` (interpolação linear) existe de forma idêntica em `benchmark_observado.py:30` e `mbl.py:46`, mesmo docstring.
- **Localização**: `app/application/use_cases/benchmark_observado.py:30`, `app/application/use_cases/mbl.py:46`
- **Classificação de duplicação**: **gera risco** (não é aceitável nem crítica) — uma correção futura no método de interpolação, se aplicada só em um dos dois lugares, faz os dois benchmarks (V2 e MBL) divergirem silenciosamente no mesmo cálculo.
- **Solução recomendada**: mesma do achado A-03 da Fase 1 — extrair para um módulo utilitário compartilhado.
- **Esforço estimado**: Baixo.

---

### Q-05 — Formatadores de moeda/número reimplementados fora de `utils/format.js`

- **Prioridade**: P3 — Baixo
- **Descrição**: `utils/format.js` já exporta `fmtMoeda` e `fmtNumero`, prontos para uso. Ainda assim, `BidVisaoGeral.jsx:70-71` declara localmente `fmtNum`/`fmtRS` reimplementando `toLocaleString("pt-BR", ...)` na mão, e `IndicadorBaseCte.jsx`, `StatCard.jsx`, `DiagnosticoIA.jsx` chamam `toLocaleString` diretamente em vez de importar o utilitário.
- **Impacto**: qualquer ajuste de formatação (ex.: trocar de 0 para 2 casas decimais em algum lugar, ou padronizar o símbolo de milhar) precisa ser replicado manualmente em cada arquivo que não usa o utilitário compartilhado.
- **Classificação de duplicação**: **aceitável a gera risco** (formatação visual, não regra de negócio — o pior caso é inconsistência visual, não erro de cálculo).
- **Localização**: `frontend/src/pages/BidVisaoGeral.jsx:70-71`, `frontend/src/components/IndicadorBaseCte.jsx`, `frontend/src/components/StatCard.jsx`, `frontend/src/pages/DiagnosticoIA.jsx`
- **Solução recomendada**: substituir as chamadas locais por `fmtMoeda`/`fmtNumero` de `utils/format.js`.
- **Esforço estimado**: Baixo (busca e substituição pontual).

---

### Q-06 — Lógica de cálculo dentro de componentes de página (16 de 44 páginas)

- **Prioridade**: P2 — Médio
- **Descrição**: 16 páginas (`Dashboard.jsx`, `DashboardExecutivo.jsx`, `BidDashboard.jsx`, `BidComparativo.jsx`, `BidEscopo.jsx`, `BidSimulacao.jsx`, `BidVisaoGeral.jsx`, `ConcorrenciaMCL.jsx`, `ScoreLogistico.jsx`, `Oportunidades.jsx`, `MatrizOD.jsx`, `BenchmarkMBL.jsx`, `BenchmarkRegional.jsx`, `BaseConhecimento.jsx`, `ImportacaoCte.jsx`, `ImportacaoExcel.jsx`) fazem cálculo (`toFixed`, `Math.*`, `reduce`) diretamente no corpo do componente, misturado com JSX de apresentação.
- **Impacto**: a maior parte desse cálculo é de exibição (arredondamento, formatação), não regra de negócio duplicada do backend — mas nos casos onde é agregação (ex.: soma de itens de uma simulação em `BidSimulacao.jsx`), fica mais difícil de testar isoladamente (precisaria montar o componente inteiro para validar a soma) e mais fácil de divergir do cálculo equivalente que o backend já faz.
- **Causa provável**: ausência de uma camada de "view model"/hook de transformação entre o dado cru da API e o que a tela exibe.
- **Localização**: as 16 páginas citadas, em `frontend/src/pages/`
- **Risco de não corrigir**: médio — cresce proporcionalmente ao número de telas que fazem agregação client-side de um dado que o backend já deveria entregar pronto.
- **Solução recomendada**: para os casos de agregação (não só formatação), mover o cálculo para um hook (`useBidSimulacaoTotais`, por exemplo) ou, preferencialmente, para o backend, mantendo o frontend só como apresentação.
- **Esforço estimado**: Médio, caso a caso.

---

### Q-07 — Inconsistência de estilo em `HTTPException` (posicional vs. nomeado)

- **Prioridade**: P3 — Baixo
- **Descrição**: 61 ocorrências de `HTTPException(codigo, "mensagem")` (argumentos posicionais) convivem com outras que usam `HTTPException(status_code=..., detail="...")` nomeado, no mesmo arquivo em alguns casos.
- **Impacto**: nenhum funcional (o resultado é idêntico) — é puramente estilístico, mas dificulta a leitura em diff/revisão quando os dois estilos aparecem lado a lado.
- **Localização**: `app/presentation/api/v1/*.py`, amplamente distribuído
- **Solução recomendada**: padronizar em um estilo (recomendo nomeado, mais explícito) e aplicar via lint/convenção de PR.
- **Esforço estimado**: Baixo, mecânico.

---

### Q-08 — Mensagem de exceção interna repassada diretamente ao cliente da API

- **Prioridade**: P3 — Baixo (qualidade de código; não é a auditoria de segurança dedicada)
- **Descrição**: em 7 pontos, o `detail` do `HTTPException` é `str(e)`/`str(exc)` — a mensagem literal de uma exceção Python capturada.
- **Impacto**: hoje, essas exceções são `ValueError` levantadas deliberadamente pelos próprios use cases com mensagens de negócio (ex.: "BID já está encerrado") — não vazam stack trace nem detalhe de infraestrutura. O risco é que, se uma dessas capturas um dia envolver uma exceção de uma biblioteca de nível mais baixo (ex.: uma violação de constraint do banco), o texto interno (nome de tabela/coluna) vazaria para a resposta HTTP sem essa intenção.
- **Localização**: `app/presentation/api/v1/bid.py:167,183,197`, `dashboard.py:46`, `importacao.py:133,230`, `relatorios.py:36`
- **Risco de não corrigir**: baixo hoje, dado o uso atual controlado; vale como item de vigilância para revisão de código futura (novo `except` não deve repassar `str(e)` de biblioteca externa direto).
- **Solução recomendada**: manter para `ValueError` de negócio (é o padrão certo aqui), mas documentar como convenção em [`09_manutencao.md`](09_manutencao.md) para não virar hábito de repassar qualquer exceção.
- **Esforço estimado**: Trivial (documentação de convenção).

---

### Q-09 — Testes do backend são só de integração — nenhuma regra complexa tem teste unitário isolado

- **Prioridade**: P2 — Médio
- **Descrição**: os 68 testes rodam contra um banco SQLite real (temporário), passando pela pilha HTTP inteira (`TestClient`). Não há nenhum teste que instancie um use case isoladamente (ex.: `McLUseCase` com repositórios fake/mock) para validar só a fórmula de score sem precisar de HTTP+banco.
- **Impacto**: para validar uma mudança pontual na fórmula do MCL (ex.: ajustar `LIMITE_ACIMA_MBL_PCT` de 20% para 15%), o único teste disponível é de ponta a ponta — mais lento de rodar, mais difícil de isolar exatamente qual componente do cálculo quebrou se o teste falhar.
- **Causa provável**: a estratégia de teste adotada desde o MVP é "smoke test" (validar que o fluxo funciona), nunca evoluiu para incluir uma camada de teste unitário para as regras de negócio mais complexas que vieram depois (MCL, DLG, MBL).
- **Localização**: `backend/tests/*.py` (ausência, não presença)
- **Risco de não corrigir**: médio — cresce com a complexidade das fórmulas (achado Q-01); hoje ainda é gerenciável porque o volume de regras é conhecido, mas cada fórmula nova sem teste unitário aumenta o tempo de investigação quando um teste de integração falha.
- **Solução recomendada**: adicionar testes unitários (sem HTTP, sem banco — usando repositórios fake in-memory) para as fórmulas de `mcl.py`, `dlg.py`, `mbl.py`, `score_logistico.py`, complementando (não substituindo) os testes de integração existentes.
- **Esforço estimado**: Médio-Alto (requer criar fakes de repositório, mas paga-se rápido em velocidade de execução).

---

### Q-10 — Zero teste automatizado de frontend (reafirma achado já conhecido, com foco em qualidade de código)

- **Prioridade**: P1 — Alto
- **Descrição**: nenhuma página, componente, hook ou função de `utils/` tem teste automatizado. Não há Vitest/Jest/Testing Library configurado no projeto.
- **Impacto**: qualquer mudança em `utils/format.js`, `client.js` (interceptor de refresh de cookie) ou em uma página com cálculo embutido (achado Q-06) não tem rede de segurança automatizada — só validação manual.
- **Localização**: `frontend/` (ausência de infraestrutura de teste)
- **Risco de não corrigir**: alto e crescente — é o único item desta lista onde o risco sobe diretamente com o tempo (mais páginas, mais lógica embutida, zero cobertura acumulando).
- **Solução recomendada**: começar pelo que é mais barato e mais valioso: testes unitários de `utils/format.js` e `utils/benchmark.js` (funções puras, fáceis de testar) e do interceptor de refresh em `client.js` (lógica de fila/retry não-trivial); testes de página vêm depois.
- **Esforço estimado**: Médio para começar (setup de Vitest + primeiros testes de utils), Alto para cobertura ampla.

---

## 7. Dívida Técnica de Código

| Dívida | Origem | Impacto | Recomendação |
|---|---|---|---|
| Regra de negócio concentrada em métodos longos (Q-01) | Crescimento orgânico das fórmulas de DLG/MBL/MCL/Recomendações sem refatoração incremental | Dificulta ajuste seguro de regra de negócio | Extrair sub-passos nomeados, sem mudar interface pública |
| Logging inconsistente entre use cases (Q-02) | Adicionado pontualmente, nunca como convenção | Incidentes silenciosos em 56% dos use cases | Aplicar como checklist de PR para use case novo |
| Docstring desigual (Q-03) | Convenção "comentar só o não-óbvio" aplicada sem critério uniforme | Conhecimento tácito sobre constantes/fórmulas | Documentar o "porquê" de constantes mágicas |
| Duplicação de percentil e formatadores (Q-04, Q-05) | Dois módulos desenvolvidos em paralelo sem checagem de reuso | Risco de divergência silenciosa | Extrair utilitário compartilhado |
| Testes só de integração (Q-09) | Estratégia de smoke-test nunca evoluiu para unitário | Investigação lenta quando fórmula complexa quebra | Adicionar unitário para MCL/DLG/MBL/Score |
| Zero teste de frontend (Q-10) | Nunca priorizado desde o MVP | Risco crescente sem rede de segurança | Começar por `utils/` e `client.js` |

## 8. Plano de Melhoria

### Curto prazo (correções simples, alto impacto)

- Q-04: extrair `_percentil` compartilhado (backend).
- Q-05: substituir formatadores locais pelos de `utils/format.js` (frontend).
- Q-07: padronizar `HTTPException` para uso nomeado (`detail=`).
- Q-08: documentar em [`09_manutencao.md`](09_manutencao.md) a convenção de não repassar `str(e)` de exceções que não sejam `ValueError` de negócio.
- Q-02 (parcial): adicionar logging nos use cases de BID/MCL primeiro (maior criticidade financeira).

### Médio prazo (refatorações estruturais)

- Q-01: extrair sub-passos das 5 funções mais complexas identificadas (`_agregar_transportadoras`, `consolidar`, `_processar_periodo`, `_coletar_metricas`, `_calcular_scores`).
- Q-06: mover cálculos de agregação (não formatação) das páginas de BID/Score para hooks dedicados ou para o backend.
- Q-09: iniciar suíte de testes unitários para as fórmulas de MCL/DLG/MBL/Score Logístico, com repositórios fake.
- Q-10 (início): configurar Vitest e cobrir `utils/format.js`, `utils/benchmark.js`, e o interceptor de `client.js`.

### Longo prazo (melhorias arquiteturais)

- Q-10 (cobertura ampla): expandir teste de frontend para páginas críticas (Dashboard, BID, Importação).
- Consolidar convenção de logging e docstring como parte de um guia de estilo formal, referenciado em [`09_manutencao.md`](09_manutencao.md), e aplicado retroativamente aos 14 use cases sem log e aos métodos sem docstring que implementam fórmula.
- Reavaliar, junto com o achado A-01 da Fase 1 (use cases com SQL direto), se a extração de sub-passos (Q-01) deve migrar para a camada de "read models" recomendada na Fase 1 — as duas dívidas se tocam na mesma região do código.

---

## Resposta à pergunta do escopo

**O código atual possui qualidade suficiente para suportar a evolução da plataforma?**

Sim, com ressalvas conhecidas e endereçáveis. Não há débito que bloqueie evolução — é debito que **acumula custo de manutenção** se não for tratado antes do próximo ciclo de módulos novos (V5/V6, já sinalizado na Fase 1). O ponto que mais preocupa nesta fase especificamente é a ausência total de teste de frontend (Q-10) e a natureza só-integração dos testes de backend (Q-09) para as fórmulas mais complexas do produto (MCL, DLG, MBL) — são os dois itens desta auditoria com risco crescente ao longo do tempo, ao contrário dos demais achados, que são estáveis (não pioram sozinhos).

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma alteração de código foi feita durante esta auditoria.*
