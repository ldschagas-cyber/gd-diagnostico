# README para Agentes de IA

> Este documento é o guia oficial e permanente para qualquer agente de IA (ChatGPT, Claude Chat, Claude Code, ou qualquer ferramenta futura) que participe do desenvolvimento do GD Frete Diagnóstico. A partir desta versão, **a documentação versionada em `/docs` é a única fonte oficial de verdade do projeto — não a memória de conversas anteriores, de nenhuma ferramenta ou sessão específica**. Uma nova sessão de qualquer agente deve conseguir compreender o projeto e continuar o trabalho de forma consistente lendo apenas esta documentação.
>
> Este documento é exclusivamente de processo e governança. Não altera código, arquitetura, API, schema ou regra de negócio.

---

## Ordem Obrigatória de Leitura

Todo agente de IA deve ler, nesta ordem, antes de propor ou implementar qualquer mudança:

1. **[`00_contexto_oficial.md`](00_contexto_oficial.md)** — missão, visão, posicionamento, público-alvo, princípios permanentes, arquitetura conceitual, papel da IA, estratégia de evolução, diretrizes arquiteturais e política de versionamento. A referência principal do projeto.
2. **[`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md)** — Plano Diretor Técnico: nota geral da plataforma, os problemas mais importantes, dívida técnica consolidada, ordem ideal de implementação, roadmap de 24 meses e a elaboração detalhada da visão estratégica (Seções 12-21).
3. **[`11_changelog.md`](11_changelog.md)** — histórico real de versões, para saber o que já foi entregue e em que versão.
4. **[`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md)** — inventário técnico factual (rotas, tabelas, use cases, testes), para verificar o estado real do código antes de assumir qualquer coisa.
5. **[`10_roadmap.md`](10_roadmap.md)** — débitos técnicos e estado de roadmap por fase, para entender o que já está planejado e em que ordem.
6. **Documentação da versão em desenvolvimento** — PRD → Protótipo → Especificação Técnica da funcionalidade específica em curso, localizada em [`specs/`](specs/) (ex.: `specs/vX.Y.Z_PRD_<nome>.md`, `specs/vX.Y.Z_especificacao_tecnica_<nome>.md`). Se nenhum documento de versão em desenvolvimento existir para a tarefa solicitada, ver a regra de bloqueio abaixo.

Esta ordem não é apenas uma sugestão de leitura — é o que garante que a IA entenda, nesta sequência, **por que o produto existe → o que já foi diagnosticado e priorizado → o que já mudou → o que existe hoje de fato no código → o que está planejado → o que está sendo construído agora**.

---

## Processo Oficial

```
Validação Estratégica
        ↓
PRD
        ↓
Protótipo Funcional
        ↓
Revisão do Protótipo
        ↓
Especificação Técnica
        ↓
Revisão Técnica
        ↓
Implementação Incremental
        ↓
Testes
        ↓
Atualização Documental
        ↓
Release
```

| Etapa | Objetivo | Critério de saída |
|---|---|---|
| **Validação Estratégica** | Confirmar que a proposta está alinhada à missão e aos princípios permanentes ([`00_contexto_oficial.md`](00_contexto_oficial.md)) | Respostas positivas ao checklist de Governança do Produto ([`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md), Seção 21) |
| **PRD** | Documentar problema, usuário-alvo, critério de sucesso e escopo | PRD aprovado, salvo em `specs/` |
| **Protótipo Funcional** | Validar a solução com um protótipo navegável ou interativo antes de comprometer esforço de engenharia | Protótipo demonstra o fluxo-chave para o usuário primário (o analista) |
| **Revisão do Protótipo** | Coletar feedback do time de analistas e consultores | Protótipo aprovado, ou ajustado e reaprovado |
| **Especificação Técnica** | Detalhar impacto em arquitetura, dados, APIs e reuso do motor analítico, verificado contra o código real | Especificação não introduz cálculo paralelo ao motor existente nem duplica regra de negócio |
| **Revisão Técnica** | Validar a especificação contra as diretrizes arquiteturais ([`00_contexto_oficial.md`](00_contexto_oficial.md), Seção 10) | Especificação aprovada tecnicamente, sem violar a Clean Architecture nem introduzir dívida não registrada |
| **Implementação Incremental** | Construir em fatias pequenas e testáveis | Cada incremento entregável e testável isoladamente |
| **Testes** | Cobrir a regra de negócio nova ou alterada com teste automatizado | Suíte de testes cobre o caminho novo, sem regressão nos existentes |
| **Atualização Documental** | Atualizar o documento correspondente (`01`-`09`, `06_regras_de_negocio.md` quando aplicável) no mesmo ciclo | Documentação reflete o comportamento real antes do release |
| **Release** | Publicar a mudança com o nível de versão correto ([`00_contexto_oficial.md`](00_contexto_oficial.md), Seção 11) e registro em `11_changelog.md` | Release registrado, versionado, documentação sincronizada |

---

## Papéis das Ferramentas

| Ferramenta | Responsabilidades oficiais |
|---|---|
| **ChatGPT** | Análise estratégica; revisão; validação; apoio à tomada de decisão |
| **Claude Chat** | PRD; Protótipo Funcional; Especificação Técnica; documentação |
| **Claude Code** | Atualização documental; implementação; testes; migrations; versionamento |

Esta divisão é a referência oficial de quem produz o quê no processo. Um agente pode ser solicitado a apoiar uma etapa fora de sua responsabilidade primária em casos pontuais, mas a responsabilidade e o formato de saída de cada etapa do Processo Oficial seguem esta tabela por padrão.

---

## Regras

Antes de iniciar qualquer **implementação** (código, migration, endpoint, alteração de regra de negócio), o agente deve verificar previamente:

1. **Aderência ao Plano Diretor Técnico** ([`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md)) — a mudança está de acordo com a priorização e a ordem de implementação já aprovadas?
2. **Aderência ao Contexto Oficial** ([`00_contexto_oficial.md`](00_contexto_oficial.md)) — a mudança respeita a missão, os princípios permanentes e a estratégia de evolução (Analista-primeiro)?
3. **Existência de PRD aprovado** para a funcionalidade em questão.
4. **Existência de Protótipo aprovado**, quando a funcionalidade tiver superfície de UX relevante.
5. **Existência de Especificação Técnica aprovada**, verificada contra o código real.

**Caso qualquer um destes esteja ausente, a implementação deve ser interrompida e comunicada** — não presumida, não inferida da conversa, não construída "a partir do contexto que parece razoável". A ausência de um desses documentos é motivo suficiente para parar e sinalizar ao usuário, mesmo que a tarefa pedida pareça pequena ou óbvia.

Esta regra existe precisamente para eliminar a dependência da memória de conversas: se a justificativa de uma mudança só existe na cabeça de quem pediu ou no histórico de uma sessão anterior, ela ainda não está pronta para ser implementada — precisa primeiro virar documento, seguindo o Processo Oficial acima.

---

## Referências Cruzadas

Para navegação rápida entre a camada de governança e o restante da documentação:

| A partir de... | ...vá para |
|---|---|
| [`00_contexto_oficial.md`](00_contexto_oficial.md) | Seção 12 (Relação com os Demais Documentos) lista todos os documentos relacionados e o motivo de cada relação |
| [`22_plano_diretor_tecnico.md`](22_plano_diretor_tecnico.md) | Histórico de Revisões (início do documento) e Seção 24 (Confirmação de Compatibilidade) explicam como o Plano Diretor se relaciona com o Contexto Oficial |
| [`10_roadmap.md`](10_roadmap.md) | Cada débito técnico referencia o achado de origem (Fases 1-8) e, quando aplicável, a etapa do Plano Diretor Técnico que o endereça |
| [`11_changelog.md`](11_changelog.md) | Cada versão relevante ao Plano Diretor já traz nota cruzada (ex.: "Etapa 1 do Plano Diretor Técnico") |
| [`13_inventario_tecnico_baseline.md`](13_inventario_tecnico_baseline.md) | Aponta para o documento dedicado (`01`-`12`) sempre que um item já está descrito em outro lugar, em vez de duplicar |
| [`00_README.md`](00_README.md) | Índice completo dos 24+ documentos oficiais e ordem de leitura recomendada por perfil (novo desenvolvedor, arquiteto, QA, gestor) |

---

## Critérios de Aceite desta Camada de Governança

- Esta documentação é **permanente** e **versionada** — vive em `/docs`, não em memória de conversa.
- Qualquer IA futura, em uma sessão nova, sem nenhum contexto prévio, deve conseguir seguir a Ordem Obrigatória de Leitura acima e compreender imediatamente o que o projeto é, o que já foi decidido e como propor a próxima mudança.
- Nenhuma implementação deve depender de uma justificativa que exista apenas em uma conversa passada — se a justificativa importa, ela deve estar em um PRD, uma Especificação Técnica, o Plano Diretor Técnico ou o Contexto Oficial.

---

*Documento criado em 2026-07-08 como parte da camada oficial de governança do projeto. Nenhum código, banco de dados, API ou infraestrutura foi alterado na sua produção. Ver [`00_contexto_oficial.md`](00_contexto_oficial.md) para a referência estratégica principal e [`00_README.md`](00_README.md) para o índice completo da documentação técnica.*
