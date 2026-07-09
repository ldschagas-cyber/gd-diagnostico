# 19 · Fase 6 — Auditoria UX/UI e Experiência do Usuário

> **Escopo**: exclusivamente diagnóstico — nenhuma tela, componente ou estilo foi alterado nesta fase. Diferente das Fases 1-5 (só leitura de código), esta fase incluiu **navegação real na aplicação rodando** (login, criação de empresa, teste de responsividade em 3 resoluções), complementada por leitura de código para os pontos que exigiam confirmação textual (tooltips, subtítulos, rótulos). Ambiente restaurado ao estado original ao final — nenhum dado de teste, arquivo de configuração ou processo permaneceu.

---

## 1. Resumo Executivo

O GD Frete Diagnóstico entrega, **depois do login**, uma experiência coerente e profissionalmente organizada: identidade visual consistente (paleta Indigo/Amber/Ivory, logo "GD" no menu), boa tradução de jargão técnico para linguagem de negócio nos títulos de página (ex.: "Desempenho de prazo (SLA)" em vez de "OTIF" cru, subtítulos explicativos em toda página de sigla técnica como DLG/MBL/MCL), tratamento de erro uniforme, e um diferencial real testado nesta auditoria — **busca automática de dados de empresa por CNPJ** no cadastro, que reduz fricção de onboarding de forma tangível.

A **tela de login**, porém — o primeiro contato de qualquer usuário novo, e o momento mais importante para "vender" a plataforma antes mesmo de o usuário ver qualquer funcionalidade — não tem nenhuma identidade visual: nenhum logo, nenhum nome de produto, nenhuma frase de valor. É uma tela genérica de "Entrar", indistinguível de qualquer outro sistema interno. Isso pesa diretamente na pergunta que esta fase pede para responder: *"a experiência comunica que o produto é uma plataforma de inteligência logística?"* — a resposta é sim, mas só depois de já estar logado.

O segundo achado mais relevante é de navegação: o menu lateral tem 8 grupos e ~40 itens, com altura de conteúdo real medida em **2,5× a altura da viewport** — é colapsável por seção (confirmado funcionando), mas todos os grupos vêm expandidos por padrão e não há busca/filtro. E o papel VISUALIZADOR (leitura) hoje vê exatamente os mesmos botões de ação que ADMIN/ANALISTA — a restrição só aparece como erro ao tentar salvar, não como ausência da ação na tela, o que é confuso especificamente para o perfil que esta fase pede para avaliar à parte.

## 2. Nota UX/UI Geral

# **67 / 100**

Experiência sólida e coerente uma vez dentro do produto; primeira impressão (login) e navegação de um sistema com muitos módulos são os dois pontos que mais pesam contra a nota.

## 3. Avaliação por Área

| Área | Nota |
|---|---|
| Jornada do Usuário | 68/100 |
| Navegação | 62/100 |
| Dashboards | 72/100 |
| Indicadores | 75/100 |
| Design System | 76/100 |
| Responsividade | 58/100 |
| Acessibilidade | 65/100 *(observação visual, não auditoria automatizada — ver nota na seção 5)* |
| Feedback ao Usuário | 70/100 |
| Experiência Comercial | 60/100 |

## 4. Pontos Fortes

- **Busca automática de CNPJ (BrasilAPI)** no cadastro de empresa — testada ao vivo nesta auditoria: preencher o CNPJ e clicar "Buscar CNPJ" preenche automaticamente razão social, nome fantasia e status. É um diferencial real de redução de fricção que muitos concorrentes B2B não têm.
- **Identidade visual consistente** dentro da aplicação — logo "GD" + "Frete Diagnóstico / GD Conecta" no topo do menu, paleta de marca aplicada de forma uniforme (Indigo `#2D3561`, Amber `#C9A84C`), item de menu ativo destacado.
- **Tradução consistente de jargão técnico**: toda página nomeada por sigla (DLG, MBL, MCL) tem um subtítulo em linguagem de negócio logo abaixo do título (ex.: MBL → "Referência estatística de custo logístico — percentis P10–P90, excluindo outliers do DLG"; MCL → "Motor de decisão de BID — score multi-critério..."), via um componente `PageHeader` padronizado.
- **Indicador de prazo traduzido para negócio**: o Dashboard chama o indicador de OTIF de "Desempenho de prazo (SLA)", não expõe a sigla técnica ao usuário final.
- **Empty states bem escritos** — a maioria das telas vazias tem texto claro do que fazer a seguir (ex.: "Selecione uma empresa para gerenciar suas filiais"); a tela de Empresas, especificamente, tem um botão de ação direto (`+ Nova Empresa`) bem posicionado.
- **Afomordância de formulário consistente**: botão de salvar/entrar fica desabilitado até os campos obrigatórios serem preenchidos, tanto no login quanto no cadastro de empresa.
- **Menu colapsável por seção** — confirmado funcionando ao clicar no cabeçalho de um grupo.
- **Tratamento de erro 100% uniforme** (já confirmado tecnicamente na Fase 2) — toda tela usa o mesmo padrão de exibição de erro, sem inconsistência de "algumas telas mostram, outras não".

## 5. Problemas Encontrados

---

### UX-01 — Tela de login sem nenhuma identidade visual do produto

- **Descrição**: a tela de login mostra só um card com título genérico "Entrar", subtítulo "Acesse o painel de diagnóstico de frete.", campos de e-mail/senha e botão. Não há logo, não há o nome "GD Frete Diagnóstico" ou "GD Conecta", não há nenhuma frase que comunique o que o produto faz ou seu valor.
- **Tela/módulo**: `frontend/src/pages/Login.jsx`
- **Evidência**: screenshot capturado nesta auditoria (2026-07-07) — card branco isolado, sem elemento de marca.
- **Impacto no usuário**: é o primeiro contato de qualquer pessoa com o produto — inclusive de um prospect que ganhou acesso a uma demonstração. Uma tela de login genérica não reforça a identidade nem comunica "isto é uma plataforma de inteligência logística", ao contrário do menu interno, que faz isso bem.
- **Prioridade**: **UX-P1** — prejudica a primeira impressão/percepção de valor do produto, especificamente relevante para venda/adoção.
- **Recomendação**: adicionar o logo e nome do produto ao card de login, e considerar uma frase curta de posicionamento (ex.: "Inteligência logística para reduzir seu custo de frete").
- **Esforço estimado**: Baixo.

---

### UX-02 — Credencial de acesso inicial exposta permanentemente na tela de login

- **Descrição**: o texto "Acesso inicial: admin@gdconecta.com.br" é renderizado sem nenhuma condição de ambiente (`import.meta.env.DEV` ou similar) — aparece sempre, inclusive em produção.
- **Tela/módulo**: `frontend/src/pages/Login.jsx:168`
- **Evidência**: confirmado no código-fonte — sem guard de ambiente ao redor dessa linha.
- **Impacto no usuário**: para um cliente pagante, ver um lembrete de "senha padrão" na tela de login do próprio produto passa a impressão de sistema ainda em desenvolvimento/não polido — além de ser uma pequena exposição de informação (formato do e-mail administrativo) desnecessária em produção.
- **Prioridade**: **UX-P2**
- **Recomendação**: mostrar essa dica só quando `ENVIRONMENT != production` (o mesmo padrão já usado no backend para Swagger/Redoc).
- **Esforço estimado**: Trivial.

---

### UX-03 — Empty state do Dashboard sem call-to-action direto

- **Descrição**: ao logar sem nenhuma empresa cadastrada, o Dashboard mostra "Selecione uma empresa" / "Cadastre e selecione uma empresa ativa para visualizar o diagnóstico." — só texto, sem um botão que leve direto ao cadastro de empresa.
- **Tela/módulo**: `frontend/src/pages/Dashboard.jsx` (estado vazio)
- **Evidência**: screenshot capturado nesta auditoria — comparado diretamente com a tela de Empresas, que **tem** um botão `+ Nova Empresa` bem posicionado no mesmo cenário de "lista vazia".
- **Impacto no usuário**: um usuário novo, no momento mais crítico da jornada (primeiro login), precisa descobrir sozinho que "cadastre uma empresa" significa "abra o menu, ache Cadastros, ache Empresas, ache o botão lá" — múltiplos passos que um botão direto no próprio Dashboard eliminaria.
- **Prioridade**: **UX-P2**
- **Recomendação**: adicionar um botão "Cadastrar empresa" diretamente no empty state do Dashboard, levando à tela de Empresas com o modal já aberto.
- **Esforço estimado**: Baixo.

---

### UX-04 — Menu lateral extenso, sem busca, com todos os grupos expandidos por padrão

- **Descrição**: o menu tem 8 grupos (Acesso e Segurança, Cadastros, Configuração, Importação, Diagnóstico Logístico, Benchmark Logístico, Concorrência Logística - BID, Inteligência Logística - IA) e cerca de 40 itens de navegação no total. Medição real nesta auditoria: o conteúdo do menu ocupa **1.571px de altura contra 609px de viewport visível** (≈2,6×) na resolução testada (800×812). O menu **é** colapsável por grupo (confirmado clicando no cabeçalho), mas todos os grupos aparecem expandidos no estado inicial, e não há campo de busca/filtro.
- **Tela/módulo**: `frontend/src/layouts/AppLayout.jsx`
- **Evidência**: medição via inspeção de `scrollHeight`/`clientHeight` do container do menu, nesta auditoria.
- **Impacto no usuário**: para achar um item específico (ex.: "Recomendações", perto do fim do grupo Diagnóstico Logístico), o usuário precisa rolar por boa parte do menu, mesmo sabendo exatamente o que procura — não há atalho.
- **Prioridade**: **UX-P2**
- **Recomendação**: (1) considerar persistir o estado colapsado/expandido de cada grupo entre sessões (se ainda não fizer isso); (2) avaliar um campo de busca rápida no topo do menu para usuários que já sabem o nome da tela que procuram — comum em produtos com esse volume de módulos.
- **Esforço estimado**: Baixo (persistência de estado) a Médio (busca).

---

### UX-05 — Validação de formulário aparece antes de qualquer interação do usuário

- **Descrição**: no modal "Nova Empresa", o campo "Setor" já mostra o texto de erro "Selecione o setor (obrigatório)" em vermelho **assim que o modal abre**, antes de o usuário tocar em qualquer campo ou tentar salvar.
- **Tela/módulo**: modal de criação de empresa, `frontend/src/pages/Empresas.jsx`
- **Evidência**: screenshot capturado nesta auditoria, logo após abrir o modal.
- **Impacto no usuário**: validação "eager" (mostrada antes de qualquer tentativa) é uma prática de UX geralmente evitada — o padrão recomendado é validar ao perder o foco do campo (`blur`) ou ao tentar submeter, não no carregamento inicial do formulário. Aqui, o efeito prático é pequeno (é só um campo), mas destoa do resto do formulário, que não mostra erro em nenhum outro campo vazio no mesmo momento.
- **Prioridade**: **UX-P3**
- **Recomendação**: mostrar a validação do campo Setor só após o usuário interagir com ele ou tentar salvar, no mesmo padrão dos demais campos do formulário.
- **Esforço estimado**: Baixo.

---

### UX-06 — Layout não aproveita o espaço disponível em resolução de tablet

- **Descrição**: testado ao vivo nesta auditoria em 768×1024 (preset tablet): o conteúdo da tela permanece confinado a uma coluna de largura fixa (~558px), deixando aproximadamente 200px de espaço vazio à direita, sem nenhum reflow para aproveitar a largura disponível (ex.: grid de 2 colunas para os cards "Empresas"/"Filiais").
- **Tela/módulo**: observado em `Empresas.jsx`, mas é um padrão de layout (`AppLayout`), não específico dessa página.
- **Evidência**: screenshot capturado nesta auditoria em viewport 768×1024.
- **Impacto no usuário**: em tablets (cada vez mais comuns como dispositivo de consulta rápida para gestores em campo), a tela desperdiça espaço de forma visível, sem necessariamente quebrar a usabilidade — é uma questão de aproveitamento, não de funcionalidade.
- **Prioridade**: **UX-P2**
- **Recomendação**: revisar breakpoints do layout para que conteúdo em grade (cards, listagens) use 2 colunas a partir da largura de tablet, em vez de manter a largura de mobile até o desktop.
- **Esforço estimado**: Médio (depende de quantas páginas usam grid fixo em vez de responsivo).

---

### UX-07 — Pequeno resíduo de ajuste em viewport mobile

- **Descrição**: em 375×812 (preset mobile), o conteúdo é utilizável e legível, mas há um espaço vazio residual na margem direita/inferior sugerindo que o container principal não se ajusta 100% ao viewport mobile mais estreito.
- **Tela/módulo**: `AppLayout` (geral)
- **Evidência**: screenshot capturado nesta auditoria em viewport 375×812.
- **Impacto no usuário**: baixo — a aplicação continua funcional e legível, é um resíduo visual, não uma quebra de layout.
- **Prioridade**: **UX-P3**
- **Recomendação**: revisar o container raiz para ocupar 100% da largura em viewports abaixo de ~400px.
- **Esforço estimado**: Baixo.

---

### UX-08 — Papel VISUALIZADOR vê os mesmos botões de ação que ADMIN/ANALISTA

- **Descrição**: o frontend não esconde nem desabilita visualmente botões de criar/editar/excluir para o papel VISUALIZADOR — a restrição existe só no backend (confirmado nas Fases 0 e 5: retorna 403). Um usuário VISUALIZADOR vê o mesmo botão "+ Nova Empresa", os mesmos botões de salvar em todo formulário, e só descobre que não pode agir ao tentar e receber um erro.
- **Tela/módulo**: toda a aplicação (padrão transversal, não uma tela específica)
- **Evidência**: confirmado no código (nenhuma checagem de `role` encontrada nos componentes de botão de ação durante a Fase 0/1) e coerente com o débito já registrado em [`10_roadmap.md`](10_roadmap.md) (DT-15).
- **Impacto no usuário**: é a experiência mais diretamente prejudicada entre os quatro perfis que esta fase pediu para avaliar — um VISUALIZADOR (ex.: um diretor financeiro com acesso de consulta) tenta uma ação, vê a interface reagir como se fosse permitida, e só no final recebe um erro — uma experiência de "por que isso não funciona?" em vez de simplesmente não ver a opção.
- **Prioridade**: **UX-P1**
- **Recomendação**: esconder ou desabilitar (com tooltip explicativo "Seu perfil é somente leitura") os botões de ação quando `usuario.role === "VISUALIZADOR"`, usando a mesma informação de sessão que `AuthContext` já expõe.
- **Esforço estimado**: Médio (toca múltiplas telas, mas é um padrão mecânico repetido).

---

### UX-09 — Indicador de prazo/SLA parcialmente desabilitado no Dashboard, com comentário de desenvolvimento visível no código

- **Descrição**: o código do Dashboard tem o comentário `{/* Desempenho de prazo (SLA) — fora do mock, desabilitado (apagar depois). */}` associado à seção de prazo — sugerindo que esse indicador pode estar parcialmente mockado/desabilitado em algum cenário, com uma nota de "apagar depois" nunca removida.
- **Tela/módulo**: `frontend/src/pages/Dashboard.jsx:449`
- **Evidência**: comentário encontrado no código-fonte durante esta auditoria.
- **Impacto no usuário**: não verificado se afeta a experiência real hoje (o comentário pode já estar obsoleto) — sinalizado por precaução, já que é exatamente o tipo de comentário que indica uma condição especial não documentada em nenhum outro lugar.
- **Prioridade**: **UX-P3**
- **Recomendação**: confirmar se a condição ainda se aplica; se não, remover o comentário órfão; se sim, documentar por quê em vez de um lembrete informal de "apagar depois".
- **Esforço estimado**: Trivial (investigação) a Baixo (limpeza).

---

### UX-10 — Versão exibida no rodapé do menu desatualizada

- **Descrição**: o rodapé do menu lateral mostra "v6.3 · GD Frete Diagnóstico", enquanto a versão real declarada em `app/core/config.py` é `6.5.0` (e o sistema já está, na prática, em 6.5.1 após as correções de segurança).
- **Tela/módulo**: `frontend/src/layouts/AppLayout.jsx` (rodapé do menu)
- **Evidência**: screenshot capturado nesta auditoria, comparado com `VERSION` em `backend/app/core/config.py`.
- **Impacto no usuário**: baixo diretamente (a maioria dos usuários não presta atenção ao número de versão), mas é um sinal de inconsistência entre frontend e backend que pode confundir suporte técnico ao diagnosticar um problema relatado por um cliente ("qual versão você está usando?").
- **Prioridade**: **UX-P3**
- **Recomendação**: derivar essa string de uma única fonte (ex.: variável de build injetada a partir do mesmo `VERSION` do backend, ou de `package.json`), não hardcoded separadamente no frontend.
- **Esforço estimado**: Trivial.

---

## Nota sobre Acessibilidade (seção 65/100)

Esta auditoria avaliou acessibilidade por **observação visual direta** (contraste aparente de texto sobre fundo, presença de rótulos em campos de formulário, navegação por teclado não testada formalmente) — não foi rodada nenhuma ferramenta automatizada de auditoria de acessibilidade (axe-core, Lighthouse, WAVE) nesta sessão. O que foi observado: contraste de texto aparenta ser adequado (texto escuro sobre fundo claro, botões com bom contraste visual), campos de formulário têm rótulos associados (`LabelText` presente na árvore de acessibilidade capturada). **Recomenda-se uma auditoria de acessibilidade dedicada com ferramenta automatizada antes de tratar a nota desta seção como definitiva** — 65/100 aqui reflete ausência de problema óbvio observado, não uma auditoria completa (ex.: não foi testada navegação 100% por teclado, nem leitor de tela).

## 6. Quick Wins (alto impacto, baixo esforço)

- UX-02: esconder a dica de "Acesso inicial" em produção — uma linha de condição.
- UX-03: botão de CTA no empty state do Dashboard.
- UX-05: corrigir o momento de exibição da validação do campo Setor.
- UX-10: derivar a string de versão de uma única fonte.
- UX-01 (parcial): adicionar ao menos o nome do produto à tela de login, mesmo antes de um trabalho visual mais completo de marca.

## 7. Roadmap UX

### Curto prazo

- UX-02, UX-03, UX-05, UX-10 (quick wins acima).
- UX-01: adicionar identidade visual básica à tela de login.

### Médio prazo

- UX-08: ocultar/desabilitar ações de escrita para o papel VISUALIZADOR na interface — fecha a lacuna mais relevante desta fase do ponto de vista de experiência por perfil de usuário.
- UX-04: avaliar persistência do estado de colapso do menu e/ou campo de busca rápida.
- UX-06: revisar breakpoints de layout para aproveitar melhor a largura em tablets.

### Longo prazo

- Auditoria de acessibilidade dedicada com ferramenta automatizada (axe-core/Lighthouse), incluindo teste de navegação por teclado e leitor de tela — não coberta com profundidade suficiente nesta fase.
- Revisão de identidade visual da tela de login como parte de uma frente maior de "primeira impressão comercial" (relevante se a plataforma for usada em demonstrações de venda a novos clientes).
- UX-07: polimento fino de responsividade mobile.

---

*Este relatório é parte da documentação oficial do projeto (ver [`00_README.md`](00_README.md)). Nenhuma tela, componente ou estilo foi alterado durante esta auditoria.*
