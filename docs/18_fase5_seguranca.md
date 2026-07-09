# 18 · Fase 5 — Auditoria de Segurança

> **Escopo**: exclusivamente diagnóstico — nenhuma vulnerabilidade foi corrigida, nenhum código/configuração/permissão foi alterado nesta fase. Toda evidência foi coletada por leitura direta do código-fonte em 2026-07-07, mais uma consulta pontual à web para o histórico de CVEs de uma dependência crítica (JWT). Base oficial: [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) e relatórios das Fases 1-4. Esta fase **consolida** os achados de segurança já identificados nas fases anteriores e na auditoria de segurança já realizada e corrigida em 2026-07-07 (documentada em [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md)) — não repete a descoberta, referencia-os com código `SEC-xx` e foca em achados **novos**, não cobertos antes.

---

## 1. Resumo Executivo

A plataforma já passou por uma correção de segurança real e verificada em 2026-07-07 (antes desta auditoria formal em fases): as falhas mais graves que existiam — quebra de isolamento multi-tenant em BID/MCL/Transportadoras/Inteligência IA, escalonamento de privilégio entre empresas no módulo de Usuários, e JWT em `localStorage` — foram identificadas, corrigidas e verificadas com teste automatizado e navegador real. Essa base está sólida e é o motivo pelo qual a nota desta fase não é baixa.

Ainda assim, esta auditoria formal encontrou **uma regressão real e concreta** que a correção anterior não cobriu: os endpoints de **clusters do cliente** (`benchmark_od_config.py`) — que gerenciam o mapeamento UF/município→hub logístico de cada empresa — nunca receberam a dependency `bloquear_visualizador`, ao contrário de praticamente todo o resto do sistema. Um usuário com papel VISUALIZADOR (deveria ser só leitura) hoje consegue criar, editar e excluir clusters da própria empresa.

Além disso, encontrei uma lacuna de **auditoria/rastreabilidade** significativa: as duas ações mais sensíveis do sistema do ponto de vista de governança — gestão de usuários (criação, edição, concessão de privilégio, exclusão) e exclusão em massa de dados importados — **não geram nenhum log**, ao contrário do módulo de BID, que tem uma tabela de auditoria dedicada (`bid_auditorias`) para ações de risco muito menor.

Não encontrei nenhuma injeção de SQL, nenhum XSS via `dangerouslySetInnerHTML`, nenhum SSRF, nenhum segredo hardcoded, e a proteção contra XML Bomb está corretamente aplicada nos dois parsers de XML do sistema. A infraestrutura, porém, não envia nenhum header de segurança HTTP (`CSP`, `X-Frame-Options`, `HSTS`) — uma lacuna padrão de baixo esforço e alto retorno.

## 2. Nota de Segurança

# **71 / 100**

Fundação de autenticação/autorização sólida e já corrigida uma vez com sucesso; uma regressão pontual real encontrada (clusters); lacunas de auditoria/rastreabilidade e de headers HTTP que são de baixo esforço para fechar.

## 3. Avaliação por Área

| Área | Nota |
|---|---|
| Autenticação | 78/100 |
| Autorização | 72/100 |
| Multi-tenancy | 75/100 |
| APIs | 68/100 |
| Banco de Dados | 75/100 |
| Frontend | 78/100 |
| Infraestrutura | 58/100 |
| Uploads | 82/100 |
| Logs e Auditoria | 55/100 |
| Proteção de Dados | 72/100 |

## 4. Pontos Fortes

- **Autenticação via cookie `httpOnly`**, com `SameSite=Lax`, `Secure` em produção, e `path` restrito no cookie de refresh — verificado em navegador real, não só em teste automatizado.
- **Algoritmo JWT pinado explicitamente** na validação (`jwt.decode(..., algorithms=[settings.ALGORITHM])`) — mitigação correta contra ataques de confusão de algoritmo, independente da versão exata da biblioteca instalada.
- **Zero SQL montado por concatenação/f-string** em toda a base — confirmado por busca exaustiva; todo acesso a dado passa pelo ORM parametrizado.
- **Zero uso de `dangerouslySetInnerHTML`** no frontend — não há vetor óbvio de XSS via renderização de HTML não sanitizado.
- **Zero chamada HTTP de saída controlada por dado do usuário** — sem risco de SSRF (as únicas chamadas externas são a OpenAI/Anthropic, com endpoint fixo do SDK).
- **Proteção contra XML Bomb correta e confirmada em ambos os parsers de XML** (CT-e e evento de cancelamento) — os dois usam `defusedxml.ElementTree`, não a biblioteca padrão vulnerável.
- **Limites de upload e validação de assinatura (magic bytes)** aplicados de forma consistente.
- **Mascaramento de CNPJ** já implementado e usado em 13 pontos do frontend.
- **Isolamento multi-tenant hoje consistente** nos 19 routers (após a correção de 2026-07-07), verificado com teste dedicado simulando dois tenants.
- **Rate limiting no login** (10/min/IP) e global (200/min) — proteção real contra força bruta.

## 5. Vulnerabilidades e Riscos

---

### SEC-01 — Endpoints de Clusters do Cliente sem bloqueio de VISUALIZADOR (regressão não coberta pela correção anterior)

- **Descrição**: `criar_cluster`, `atualizar_cluster` e `remover_cluster` em `benchmark_od_config.py` exigem `verificar_acesso_empresa` (correto — confirma que o usuário pertence à empresa), mas **não** exigem `bloquear_visualizador`. Todo o resto do sistema recebeu esse bloqueio na correção de 2026-07-07; este módulo específico não foi incluído no escopo daquela correção.
- **Evidência**: `backend/app/presentation/api/v1/benchmark_od_config.py:84,214,232` — nenhum dos três tem `bloquear_visualizador` entre as dependencies.
- **Localização**: `POST/PUT/DELETE /empresas/{empresa_id}/clusters[/{cluster_id}]`
- **Impacto**: um usuário com papel VISUALIZADOR (que deveria ter só leitura) da própria empresa consegue criar, editar e excluir o mapeamento de clusters (UF/município → hub logístico) — uma configuração que afeta diretamente o cálculo de benchmark por corredor (OD) de toda a empresa.
- **Prioridade**: P1 — Alto
- **Risco**: baixo-médio no imediato (exige que a empresa já tenha um usuário VISUALIZADOR ativo e mal-intencionado ou com credencial comprometida), mas é uma quebra direta da garantia de RBAC que o sistema afirma ter, e o tipo de achado que mina a confiança no restante da cobertura se não corrigido.
- **Recomendação**: adicionar `bloquear_visualizador` aos três endpoints, seguindo o padrão já aplicado em todo o resto do sistema.
- **Esforço estimado**: Trivial (3 linhas).

---

### SEC-02 — Gestão de usuários sem nenhum registro de auditoria

- **Descrição**: `usuarios.py` não tem uma única chamada de `logger.*` em todo o arquivo. Criação de usuário, edição, concessão/remoção de `is_superuser`, mudança de papel e exclusão de usuário — nenhuma dessas ações fica registrada em log ou em tabela de auditoria.
- **Evidência**: `grep -c "logger\." backend/app/presentation/api/v1/usuarios.py` → 0.
- **Localização**: `app/presentation/api/v1/usuarios.py` (todos os endpoints)
- **Impacto**: se uma conta ADMIN for comprometida (ou um ADMIN legítimo agir de má-fé), não há como reconstruir depois quem criou/editou/promoveu qual usuário e quando — justamente a superfície que a correção de escalonamento de privilégio de 2026-07-07 tratou como a mais sensível do sistema.
- **Prioridade**: P1 — Alto
- **Risco**: cresce com o número de administradores de empresa na plataforma — hoje, com poucos clientes, o "raio de explosão" de uma conta comprometida é pequeno e mais fácil de investigar manualmente; isso deixa de ser verdade conforme a base de clientes cresce.
- **Recomendação**: registrar log estruturado (ou, melhor, uma tabela de auditoria dedicada, no mesmo padrão de `bid_auditorias`) para toda mutação em `usuarios.py`, com especial atenção a mudanças de `is_superuser`/`role`.
- **Esforço estimado**: Baixo (logging) a Médio (tabela de auditoria dedicada).

---

### SEC-03 — Exclusão de dados importados sem log de auditoria

- **Descrição**: `DELETE /importacao/dados/{empresa_id}` — que apaga em massa os CT-e importados de uma empresa (mesmo exigindo confirmação exata da quantidade e `require_admin`) — não gera nenhum registro de log.
- **Evidência**: `grep -c "logger\." backend/app/presentation/api/v1/importacao.py` → 0.
- **Localização**: `app/presentation/api/v1/importacao.py` (endpoint de exclusão)
- **Impacto**: é a operação mais destrutiva e irreversível de todo o sistema (apaga dado fiscal histórico do cliente) e é também a única de igual severidade sem nenhum rastro de quem a executou.
- **Prioridade**: P1 — Alto
- **Risco**: baixo em frequência (ação rara, deliberada, já protegida por confirmação e por exigir admin), mas alto em impacto se precisar ser investigada depois de já ter acontecido.
- **Recomendação**: registrar log estruturado com `empresa_id`, usuário executor, quantidade confirmada e origem (`XML`/`Excel`/todos) antes de executar a exclusão.
- **Esforço estimado**: Trivial.

---

### SEC-04 — Nenhum header de segurança HTTP configurado no Nginx

- **Descrição**: `frontend/nginx.conf` não define `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`, `X-Content-Type-Options` nem `Referrer-Policy`.
- **Evidência**: busca por `add_header` em `nginx.conf` só retorna os dois usos existentes (`Content-Type` do healthcheck e `Cache-Control` de assets estáticos) — nenhum header de segurança.
- **Localização**: `frontend/nginx.conf`
- **Impacto**: sem `X-Frame-Options`/CSP com `frame-ancestors`, a aplicação pode em tese ser embutida em um `<iframe>` de terceiros (clickjacking); sem `X-Content-Type-Options: nosniff`, navegadores antigos podem tentar adivinhar o tipo de conteúdo de forma insegura; sem HSTS, a primeira conexão de um usuário pode não forçar HTTPS.
- **Prioridade**: P2 — Médio
- **Risco**: baixo isoladamente (nenhum dos achados desta auditoria depende de um desses headers para ser explorado), mas é uma camada de defesa em profundidade padrão da indústria, de custo muito baixo para adicionar.
- **Recomendação**: adicionar os 4-5 headers padrão de segurança ao bloco `server` do `nginx.conf`.
- **Esforço estimado**: Trivial.

---

### SEC-05 — Dependências com versão mínima flutuante; biblioteca JWT com histórico relevante de CVEs

- **Descrição**: `requirements.txt` declara toda dependência com `>=`, nunca com versão travada (`==`) nem lockfile (`requirements-lock.txt`/`poetry.lock` inexistente). Para `python-jose[cryptography]>=3.3.0` especificamente, há histórico relevante: **CVE-2024-33663** (confusão de algoritmo, corrigida após 3.3.0), uma **DoS por "JWT bomb"** via compressão (corrigida na 3.4.0) e um relato mais recente de bypass de assinatura via `alg=none` (corrigido em versão posterior à 3.3.0). Como a instalação usa `pip install -r requirements.txt` sem lockfile, a versão exata em produção depende do momento da última reconstrução da imagem Docker, não é garantida por controle de versão.
- **Evidência**: `backend/requirements.txt` (todas as 22 linhas usam `>=`); pesquisa web confirmando o histórico de CVEs do `python-jose`.
- **Localização**: `backend/requirements.txt`
- **Impacto mitigado**: o próprio código da aplicação já pina `algorithms=[settings.ALGORITHM]` na validação (`app/core/security.py`), o que neutraliza a classe de vulnerabilidade "confusão de algoritmo"/`alg=none` independentemente da versão da biblioteca — essa é uma mitigação de código correta e já presente. O ataque de "JWT bomb" via JWE comprimido exigiria que a aplicação decodificasse um JWE arbitrário fornecido por um atacante, o que não é o padrão de uso aqui (a aplicação só decodifica tokens que ela mesma emitiu).
- **Prioridade**: P2 — Médio (rebaixado de P1 porque a mitigação de código já existe; o risco remanescente é de reprodutibilidade/gestão de dependência, não de exploração ativa)
- **Recomendação**: (1) travar versões exatas em produção (gerar lockfile via `pip freeze`/`pip-tools`), (2) adotar `pip-audit` ou `safety` como parte do processo de build/CI para checar CVEs conhecidas automaticamente a cada deploy, em vez de depender de auditoria manual pontual como esta.
- **Esforço estimado**: Baixo (lockfile) a Médio (integrar scanner de dependência ao pipeline).

---

### SEC-06 — Isolamento multi-tenant sem Row-Level Security como defesa em profundidade (retomado — já é BD-09 da Fase 4)

- **Descrição**: sem alteração da análise da Fase 4 — o isolamento por `empresa_id` é garantido só pela aplicação, sem imposição a nível de banco.
- **Prioridade**: P2 — Médio (mantida)

---

### SEC-07 — Sem token CSRF complementar ao `SameSite=Lax` (retomado — já é A-16/DT-16 da Fase 1)

- **Descrição**: sem alteração — `SameSite=Lax` já mitiga a maior parte do risco prático de CSRF para chamadas via fetch/XHR (não anexa o cookie em requisições cross-site de subrecurso), mas não há um token de dupla submissão como camada adicional.
- **Prioridade**: P3 — Baixo (mantida — risco residual já é pequeno com `SameSite=Lax`)

---

### SEC-08 — Ausência de fluxo de recuperação de senha (observação, não vulnerabilidade)

- **Descrição**: não existe endpoint de "esqueci minha senha" — hoje, só um ADMIN pode resetar a senha de outro usuário via `PUT /usuarios/{id}`.
- **Impacto**: a ausência em si **não é** uma falha de segurança (evita, inclusive, toda uma classe de vulnerabilidade de fluxos de reset mal implementados — tokens previsíveis, e-mails não verificados etc.) — é uma lacuna funcional/operacional: um usuário travado depende de um administrador disponível.
- **Prioridade**: P3 — Baixo
- **Recomendação**: se implementado no futuro, seguir prática segura (token de uso único, expiração curta, sem enumeração de e-mail existente na resposta).
- **Esforço estimado**: N/A (não é uma correção, é uma feature futura).

---

### SEC-09 — Módulo de Inteligência IA sem contrato de resposta tipado (retomado — já é A-05 da Fase 1, pela lente OWASP API3)

- **Descrição**: sem alteração — os 26 endpoints de `inteligencia.py` retornam `dict` cru, sem `response_model`.
- **Leitura de segurança adicional (OWASP API3:2023 — Broken Object Property Level Authorization)**: sem um contrato de resposta explícito, o risco de um campo sensível ser incluído no retorno "sem querer" (ex.: um campo de debug, um custo interno de IA que não deveria ir ao cliente) não tem uma rede de segurança de schema — depende só de quem escreve o endpoint prestar atenção manualmente a cada retorno.
- **Prioridade**: P2 — Médio
- **Recomendação**: mesma da Fase 1 — declarar `response_model` para as ~10 famílias de resposta do módulo.

---

### SEC-10 — Mensagem de exceção interna repassada ao cliente em 7 pontos (retomado — já é Q-08 da Fase 2)

- **Descrição**: sem alteração — `str(e)`/`str(exc)` usado como `detail` do `HTTPException` em 7 pontos, hoje controlado (só `ValueError` de negócio), mas sem garantia estrutural contra vazamento futuro de detalhe de infraestrutura.
- **Prioridade**: P3 — Baixo (mantida)

---

### SEC-11 — Ausência de resource limits e HEALTHCHECK no backend de produção (retomado — já é A-20 da Fase 1, pela lente de disponibilidade)

- **Descrição**: sem alteração — sem limite de CPU/memória por container, sem `HEALTHCHECK` no `backend/Dockerfile`.
- **Leitura de segurança adicional**: sem limite de recurso, um endpoint com uso intensivo de CPU/memória (ex.: um relatório muito grande, ou a varredura RAG do achado PF-03/BD-06 crescendo) tem potencial de se comportar como uma negação de serviço não-intencional contra os outros tenants no mesmo host — não é um ataque, mas o efeito prático (indisponibilidade para outros clientes) é o mesmo.
- **Prioridade**: P2 — Médio
- **Recomendação**: mesma da Fase 1.

---

## 6. Matriz de Risco

| Achado | Probabilidade | Impacto | Criticidade |
|---|---|---|---|
| SEC-01 (clusters sem bloqueio VISUALIZADOR) | Baixa | Médio | 🟡 Médio |
| SEC-02 (usuários sem auditoria) | Baixa | Alto | 🟡 Médio-Alto |
| SEC-03 (exclusão de dados sem auditoria) | Muito baixa | Alto | 🟡 Médio |
| SEC-04 (sem headers HTTP) | Baixa | Baixo | 🟢 Baixo |
| SEC-05 (dependência JWT não travada) | Baixa (mitigado em código) | Médio | 🟡 Médio |
| SEC-06 (sem RLS) | Muito baixa hoje | Alto em escala | 🟢 Baixo (hoje) |
| SEC-07 (sem CSRF token) | Muito baixa (`SameSite=Lax` já mitiga) | Baixo | 🟢 Baixo |
| SEC-08 (sem recuperação de senha) | N/A | N/A | ⚪ Não é risco |
| SEC-09 (IA sem response_model) | Baixa | Médio | 🟡 Médio |
| SEC-10 (exceção interna exposta) | Muito baixa | Baixo | 🟢 Baixo |
| SEC-11 (sem resource limits) | Baixa | Médio | 🟢 Baixo-Médio |

Nenhum achado desta fase atingiu classificação **P0 — Crítico**. A base de autenticação/autorização já recebeu sua correção crítica antes desta fase formal (documentada em [`12_auditoria_tecnica.md`](12_auditoria_tecnica.md)).

## 7. Plano de Evolução de Segurança

### Curto prazo (correções críticas e alto impacto)

- SEC-01: adicionar `bloquear_visualizador` aos 3 endpoints de clusters — trivial, deveria ser tratado como uma extensão direta da correção de 2026-07-07.
- SEC-02, SEC-03: logging estruturado para gestão de usuários e exclusão de dados importados.
- SEC-04: headers de segurança HTTP padrão no Nginx.
- SEC-05 (parcial): gerar lockfile de dependências Python.

### Médio prazo (melhorias estruturais)

- SEC-02 (evolução): considerar tabela de auditoria dedicada para `usuarios.py`, no padrão de `bid_auditorias`.
- SEC-05: integrar `pip-audit`/`safety` ao pipeline de build.
- SEC-09: `response_model` no módulo de Inteligência IA.
- SEC-11: resource limits e healthcheck no backend de produção.

### Longo prazo (maturidade SaaS enterprise)

- SEC-06: avaliar Row-Level Security como defesa em profundidade antes de qualquer acesso direto de terceiros ao banco (BI/analytics).
- SEC-07: avaliar token CSRF de dupla submissão se o modelo de ameaça mudar (ex.: se surgir necessidade de suportar clientes que desabilitam `SameSite`).
- Considerar um processo formal de revisão de segurança recorrente (não só reativo), dado que a correção mais crítica encontrada nesta linha de auditorias (isolamento multi-tenant) já havia sido *parcialmente* corrigida antes e ainda assim teve uma lacuna (SEC-01) — o processo de "corrigir e nunca mais revisitar" é, em si, um risco.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma vulnerabilidade foi corrigida durante esta auditoria — a correção de SEC-01, SEC-02 e SEC-03 fica pendente de autorização explícita para implementação em fase futura.*
