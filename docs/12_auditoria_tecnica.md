# 12 · Auditoria Técnica

> Consolida `archive/08_auditoria_arquitetural.md`, `archive/08_auditoria_arquitetural.docx` e `archive/09_relatorio_implementacao_v3.md` como registro histórico, e documenta a auditoria de segurança de 2026-07-07 sobre a v6.5.0/6.5.1.

## ⚠️ Aviso de validade

A auditoria original (seção 1 abaixo) foi feita sobre a **v2.0.0** do código — ~4× menos endpoints e tabelas do que a versão atual (v6.5.1). **Números de linha específicos citados na seção 1 (ex.: `main.py:147-149`) não correspondem mais ao código de hoje** e não devem ser usados para localizar algo no código atual. A seção 1 é preservada como retrato histórico e para entender a origem das decisões arquiteturais atuais (ex.: por que `defusedxml`, rate limiting e isolamento por `empresa_id` existem).

## 1. Auditoria Arquitetural v2.0.0 (histórica — Junho 2026)

### Notas por dimensão (na época)

| Dimensão | Nota (v2.0.0) |
|---|---|
| Arquitetura Geral | 76/100 |
| Segurança | 54/100 |
| Performance | 58/100 |
| Multi-empresa | 61/100 |
| Manutenibilidade | 82/100 |
| Cloud Readiness | 72/100 |
| Prontidão para IA | 28/100 |
| Escalabilidade | 55/100 |

### Principais achados (P-01 a P-25, S-01 a S-12)

Resumo dos achados mais relevantes que motivaram mudanças arquiteturais ainda vigentes hoje:

- **S-01** XML sem `defusedxml` (vulnerável a XML bomb) → corrigido na v3.0.0, ainda ativo.
- **S-02** upload sem limite de tamanho → corrigido na v3.0.0 (500/lote, 10-20MB), ainda ativo.
- **S-03** sem rate limiting no login → corrigido na v3.0.0 (`slowapi`), ainda ativo.
- **S-04** JWT em `localStorage` → **corrigido só na v6.5.1** (cookie httpOnly) — ficou pendente por 3 versões inteiras (V3.1, V4, v6.0-6.4) antes da correção.
- **S-05** Swagger sempre aberto → corrigido na v3.0.0, ainda ativo.
- **S-06** CORS `allow_methods=["*"]` → corrigido na v3.0.0, ainda ativo.
- **S-07** CNPJ sem dígito verificador → corrigido na v3.0.0, ainda ativo.
- **S-12 / P-25** autorização por empresa ausente, tabelas globais sem `empresa_id` → parcialmente corrigido na v3.0.0 (transportadoras) e **substancialmente ampliado na auditoria v6.5.0/6.5.1** (ver seção 3) — o padrão de correção existia desde v3.0.0 mas não foi retroaplicado aos módulos criados depois (BID, IA, MCL).
- **P-21** carga total de CT-es em memória → corrigido na v3.0.0 (agregação SQL).
- Demais achados (P-01 a P-04, monolíticos; P-14/P-19/P-20, paginação/testes de frontend) seguem sem confirmação de correção — ver débitos técnicos em [`10_roadmap.md`](10_roadmap.md).

O relatório completo, com blocos de código e referências de linha da época, está em `archive/08_auditoria_arquitetural.md`.

## 2. Relatório de Implementação v3.0.0 (histórico — remediação)

Documentou a correção de boa parte dos achados P0 de segurança da auditoria acima, com reavaliação de notas: Segurança 54→78, Multi-empresa 61→80, Performance 58→74. Também registrou 14 débitos técnicos (DT-01 a DT-14), a maioria endereçada nas versões seguintes — ver o rastreamento atualizado em [`10_roadmap.md`](10_roadmap.md). O relatório completo está em `archive/09_relatorio_implementacao_v3.md`.

**Este relatório nunca foi refeito para as versões V4 (IA), v6.0-6.4** — ou seja, entre a v3.0.0 e a auditoria de 2026-07-07 abaixo, não houve nenhuma reavaliação formal de segurança/arquitetura, apesar de 3 gerações de módulos novos (BID→MCL, IA completa, DLG/MBL/Recomendações) terem sido adicionadas.

## 3. Auditoria de Segurança 2026-07-07 (v6.5.0 → v6.5.1) — **atual**

### Contexto

Uma auditoria de segurança sob demanda revisou os módulos adicionados **depois** da auditoria v2.0.0/relatório v3.0.0 (BID, MCL, Inteligência IA, Transportadoras, Usuários) — módulos que nunca haviam sido auditados formalmente.

### Achados críticos confirmados

1. **IDOR / quebra de isolamento multi-tenant em BID, MCL, Transportadoras e Inteligência IA.** A dependency `verificar_acesso_empresa` já existia e estava corretamente aplicada em `empresas.py`, `dashboard.py`, `dlg.py`, `mbl.py`, `importacao.py` desde a v3.0.0 — mas **nunca foi retroaplicada** aos módulos adicionados depois. Resultado prático: um usuário autenticado de uma empresa cliente conseguia ler/alterar dados de concorrência (BID), decisões de MCL, cadastro de transportadoras e insights de IA de **outras empresas clientes**, só trocando um parâmetro na URL — o mesmo risco que a auditoria original já havia classificado como "Alto (SaaS)" em 2026-06, mas presumia corrigido de forma abrangente.
2. **Escalonamento de privilégio entre empresas no módulo de Usuários.** `GET /usuarios` retornava a lista de usuários de **toda a plataforma** para qualquer usuário autenticado, sem filtro de empresa. `get_current_superuser` tratava `role=ADMIN` (papel pensado como *por empresa*) como equivalente a superusuário *global* — permitindo que um ADMIN de uma única empresa-cliente criasse/editasse usuários de outras empresas e concedesse `is_superuser=True` a si mesmo, obtendo controle da plataforma inteira a partir de uma única conta comprometida.
3. **Bug funcional correlato**: `PUT /usuarios/{id}` sem o campo `senha` zerava o hash de senha existente, invalidando o login do usuário editado.

### Correções aplicadas

- Nova dependency `get_bid_com_acesso` (carrega o BID pelo `bid_id` do path e valida a empresa dona dele — o `empresa_id` efetivo de qualquer operação subsequente passa a vir do próprio registro, nunca de um parâmetro de query do cliente) e `get_transportadora_com_acesso` (equivalente para transportadora).
- `verificar_acesso_empresa` retroaplicada a todos os ~60 endpoints de BID, MCL, Inteligência IA e Transportadoras que não a tinham.
- `usuarios.py`: `GET` passa a filtrar por empresa (exceto para superusuário global); `PUT`/`POST`/`DELETE` passam a impedir que um ADMIN de empresa opere fora da própria empresa ou conceda `is_superuser`.
- Correção do bug de zeramento de senha.
- **RBAC de VISUALIZADOR**: nova dependency `bloquear_visualizador`, retroaplicada a todo endpoint de escrita do sistema (exceto os já admin-only e as ~3 ações que só calculam sem persistir).
- **Migração de JWT para cookie `httpOnly`**: fecha definitivamente o risco S-04 (pendente desde a auditoria v2.0.0) — ver [`03_arquitetura_tecnica.md`](03_arquitetura_tecnica.md#5-autenticação-e-autorização).

### Verificação

- 68 testes automatizados (suíte completa) passam sem regressão.
- Dois novos arquivos de teste dedicados: `test_isolamento_v6_5_1.py` (prova, com dois tenants simulados, que o cross-tenant IDOR e o escalonamento de privilégio deixaram de funcionar, e que VISUALIZADOR é bloqueado enquanto ANALISTA continua liberado) e `test_cookie_auth_v6_5_1.py` (prova o ciclo completo de cookie: login grava, chamada autenticada funciona só com cookie, refresh lê do cookie, logout revoga).
- Fluxo de login/navegação/logout validado manualmente em navegador real (não só em teste automatizado): cookie confirmado `httpOnly` (`document.cookie` vazio após login), dashboard renderiza via cookie sem qualquer token em `localStorage`, logout efetivamente revoga a sessão no servidor.

### O que ficou fora desta rodada (ver [`10_roadmap.md`](10_roadmap.md) para o registro completo)

- Frontend não esconde botões de escrita para o papel VISUALIZADOR (só o backend bloqueia).
- Sem token CSRF complementar ao `SameSite=Lax`.
- `benchmark_v2_api.py`/`benchmarks.py`/`metas.py` — mutações em dados globais (matriz de mercado, metas) foram corrigidas para exigir admin, mas não foram objeto de um novo isolamento por empresa (são, por design, dados globais — ver RN-60).

## 4. Recomendação para a próxima auditoria técnica (Fase 1)

1. Revalidar pontualmente os débitos técnicos marcados "não revalidado" em [`10_roadmap.md`](10_roadmap.md) (composição de frete em Python, acesso a métodos privados entre use cases, ausência de cache Redis no dashboard, relatórios síncronos).
2. Gerar as migrations Alembic faltantes (tabelas de IA, mudanças de segurança v6.5.x) antes de qualquer deploy de produção que dependa só de `alembic upgrade head`.
3. Revisar `benchmark_v2_api.py`, `benchmarks.py`, `metas.py`, `regioes.py`/`cidades` quanto à consistência de quem pode escrever em cadastros globais (hoje: alguns exigem admin, outros só bloqueiam VISUALIZADOR — ver [`05_apis.md`](05_apis.md) coluna Auth).
4. Considerar testes de carga/performance reais (a auditoria v3.0.0 usou apenas estimativas, nunca medições).
