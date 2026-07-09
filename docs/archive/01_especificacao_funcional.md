# Especificação Funcional — GD Frete Diagnóstico
**Versão:** 2.0.0 · **Data:** Junho 2026 · **GD Conecta**

---

## 1. Objetivo da Plataforma

O GD Frete Diagnóstico é uma plataforma web B2B de consultoria logística desenvolvida pela GD Conecta para apoiar empresas de pequeno e médio porte no diagnóstico, controle e otimização de seus custos de frete. A plataforma:

- Centraliza dados de CT-es (XML) e relatórios exportados de TMS (Excel).
- Calcula automaticamente indicadores de custo logístico (custo por kg, % frete sobre faturamento, OTIF).
- Compara os indicadores da empresa contra metas internas e benchmarks de mercado.
- Identifica oportunidades de economia e gera relatórios executivos e operacionais.

---

## 2. Escopo Atual (v2.0)

### Módulos Implementados

| Módulo | Descrição |
|--------|-----------|
| Autenticação | Login JWT, controle de acesso (admin/usuário) |
| Empresas | Cadastro multi-empresa (matriz + filiais) |
| Transportadoras | Cadastro de parceiros logísticos |
| Importação CT-e XML | Parser de XML do CT-e versão 3.00 |
| Importação Excel | Importação de relatórios TMS exportados |
| Dashboard Diagnóstico | Indicadores nacionais, regionais, por transportadora e prazo |
| Metas | Configuração de metas nacionais e regionais (R$/kg e %) |
| Benchmarks | Referências de mercado por macro-região |
| Benchmark Nacional | Comparativo empresa × mercado nacional |
| Benchmark Regional | Comparativo por região de entrega |
| Benchmark Transportadoras | Ranking de eficiência de transportadoras |
| Potencial de Economia | Cálculo e projeção de economia vs. mercado |
| Dashboard Executivo | Visão estratégica consolidada |
| Relatórios | PDF e Excel — diagnóstico e benchmark |
| Cadastros de Suporte | Regiões, Cidades, Usuários |

---

## 3. Fluxos de Negócio

### 3.1 Fluxo Principal de Diagnóstico

```
1. Cadastrar empresa (matriz + filiais)
2. Importar CT-es (XML ou Excel)
3. Configurar metas (nacionais e regionais)
4. Visualizar Dashboard Diagnóstico
5. Gerar Relatório PDF/Excel
```

### 3.2 Fluxo de Benchmark

```
1. Admin configura benchmarks de mercado (Configurações > Benchmarks)
2. Empresa importa dados de frete
3. Plataforma calcula desvio vs. mercado automaticamente
4. Usuário visualiza Benchmark Nacional/Regional/Transportadoras
5. Usuário visualiza Potencial de Economia + projeções
6. Usuário visualiza Dashboard Executivo (visão estratégica)
7. Geração de relatório consolidado de benchmark
```

### 3.3 Importação CT-e XML

```
1. Upload de 1 ou N arquivos XML (CT-e v3.00)
2. Parser extrai: chave, número, série, datas, CNPJ tomador/transportadora,
   peso (taxado = max entre bruto e cubado), valor frete, valor mercadoria,
   composição do frete (por componente Comp/xNome), UF origem/destino,
   chaves de NF-e vinculadas
3. Validação: CNPJ do tomador deve pertencer à empresa (matriz ou filial)
4. Deduplicação automática por chave de 44 dígitos
5. Importação em lote (até MAX_CTE_BATCH registros por vez)
6. Resultado: resumo de importados, duplicados e rejeitados
```

---

## 4. Regras de Negócio

### 4.1 Importação

- **RN01 — Validação de tomador:** O CNPJ do tomador do CT-e deve coincidir com o CNPJ da matriz ou de alguma filial cadastrada. CT-es com CNPJ desconhecido são rejeitados.
- **RN02 — Deduplicação:** CT-es com a mesma chave de 44 dígitos são ignorados na reimportação. Não há substituição de registros.
- **RN03 — Peso taxado:** O peso considerado é o maior entre peso bruto e peso cubado (exclui cUnid=03 Volumes e cUnid=00 Cubagem em m³). Reflete o critério das transportadoras.
- **RN04 — valor_mercadoria:** Extraído do campo `infCarga/vCarga` do CT-e (busca recursiva, pois o campo pode estar aninhado em `infCTeNorm`).
- **RN05 — Composição:** Componentes do frete (`Comp/xNome`) são categorizados em: Frete Peso, Frete Valor, Pedágio, GRIS, Seguro, Ademe, Despacho, Outros.

### 4.2 Indicadores

- **RN06 — Frete R$/kg:** `valor_total_frete / peso_total`. Zero se peso = 0.
- **RN07 — % Frete s/ mercadoria:** `valor_total_frete / valor_total_mercadoria × 100`. Zero se mercadoria = 0.
- **RN08 — OTIF:** `CT-es entregues no prazo / total com data de entrega × 100`.
- **RN09 — Macro-região:** A macro-região do destino é determinada pela UF de destino do CT-e (mapeamento `macro_regiao.py`).

### 4.3 Metas

- **RN10 — Meta Nacional:** Única. Aplicada como linha de referência nos gráficos nacionais.
- **RN11 — Metas Regionais:** Uma por macro-região (NORTE, NORDESTE, CENTRO-OESTE, SUDESTE, SUL). Aplicadas como linhas de referência nos gráficos regionais.

### 4.4 Benchmarks de Mercado

- **RN12 — Benchmarks:** Valores globais de referência de mercado (mín/médio/máx de R$/kg e % frete) por macro-região + Nacional. Editáveis apenas por administrador.
- **RN13 — Benchmark Nacional vs. Regional:** Comparação nacional usa benchmark NACIONAL. Comparação regional usa o benchmark da própria região do destino. Transportadoras são comparadas ao benchmark NACIONAL.

### 4.5 Classificação Automática

- **RN14 — Frete % (faixas fixas):** ≤5% Excelente · 5–8% Muito Bom · 8–12% Atenção · 12–18% Crítico · >18% Muito Crítico.
- **RN15 — Frete R$/kg (relativo ao benchmark médio):** ≤ médio Excelente · até +10% Bom · até +20% Atenção · >+20% Crítico.
- **RN16 — Nível de custo da transportadora:** Excelente/Bom → Melhor custo · Atenção → Custo médio · Crítico → Pior custo.

### 4.6 Potencial de Economia

- **RN17 — Cálculo:** Economia por região = `max(0, frete_rs_kg − benchmark_médio) × peso_total`. Soma de todas as regiões.
- **RN18 — Projeção:** Base = ritmo mensal (`economia_total / n_meses`). Projeções: mensal ×1, trimestral ×3, semestral ×6, anual ×12.
- **RN19 — n_meses:** Número de meses cobertos pelos dados (`(data_max − data_min).days / 30`), mínimo 1.

---

## 5. Indicadores Calculados

| Indicador | Fórmula | Nível |
|-----------|---------|-------|
| Frete Total (R$) | Σ valor_frete | Nacional, Regional, Transp. |
| Peso Total (kg) | Σ peso_taxado | Nacional, Regional |
| Valor Mercadoria (R$) | Σ valor_mercadoria | Nacional, Regional |
| Frete R$/kg | frete_total / peso_total | Nacional, Regional, Transp. |
| % Frete s/ Merc. | frete_total / merc_total × 100 | Nacional, Regional, Transp. |
| Participação Transp. | frete_transp / frete_total × 100 | Por transportadora |
| OTIF | ctes_prazo / ctes_entregues × 100 | Nacional |
| Desvio vs. Meta | (valor − meta) / meta × 100 | Nacional, Regional |
| Desvio vs. Benchmark | (valor − bench_médio) / bench_médio × 100 | Nacional, Regional, Transp. |
| Economia Potencial (R$) | Σ max(0, rs_kg − bench) × peso | Por região |
| Projeção Anual | ritmo_mensal × 12 | Nacional |

---

## 6. Benchmarks de Referência (Valores Iniciais)

| Região | R$/kg Mín | R$/kg Méd | R$/kg Máx | % Mín | % Méd | % Máx |
|--------|-----------|-----------|-----------|-------|-------|-------|
| Nacional | 1,30 | 1,65 | 2,00 | 8 | 10 | 12 |
| Norte | 2,50 | 3,75 | 5,00 | 15 | 22 | 30 |
| Nordeste | 1,50 | 2,15 | 2,80 | 10 | 14 | 18 |
| Centro-Oeste | 1,20 | 1,60 | 2,00 | 7 | 9,5 | 12 |
| Sudeste | 0,70 | 0,95 | 1,20 | 4 | 6 | 8 |
| Sul | 0,80 | 1,10 | 1,40 | 5 | 7 | 9 |

*Editáveis pelo administrador em Configurações › Benchmarks.*

---

## 7. Relatórios

| Relatório | Formatos | Conteúdo |
|-----------|---------|---------|
| Diagnóstico | PDF, Excel | Nacional, Regional, Transportadoras, Prazos, Oportunidades |
| Benchmark | PDF, Excel | Nacional, Regional, Transportadoras, Potencial de Economia |

---

## 8. Controle de Acesso

| Perfil | Capacidades |
|--------|-------------|
| Administrador (superuser) | Tudo: cadastros, importação, dashboard, relatórios, metas, benchmarks, usuários |
| Usuário padrão | Visualização: dashboard, benchmark, relatórios. Sem acesso a metas, benchmarks, usuários |

---

## 9. Limitações Conhecidas da Versão Atual

- **Transportadoras globais:** A tabela de transportadoras é compartilhada (sem `empresa_id`). Para SaaS multi-tenant total, deve ser isolada por empresa em versão futura.
- **Metas e benchmarks globais:** Metas e benchmarks são configurações únicas globais. Versões futuras podem permitir configuração por empresa.
- **Sem vinculação NF-e:** O valor da mercadoria vem do CT-e (`infCarga/vCarga`). CT-es com esse campo vazio terão % frete = 0%. Futuro: importação de NF-es para cruzamento.
- **Execução local:** Versão atual testada em Windows com Python 3.14. Docker com PostgreSQL é a forma recomendada para ambientes compartilhados.
