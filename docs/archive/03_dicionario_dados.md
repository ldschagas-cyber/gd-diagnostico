# Dicionário de Dados — GD Frete Diagnóstico
**Versão:** 2.0.0 · **Data:** Junho 2026 · **GD Conecta**

---

## Convenções

- `PK` = Primary Key · `FK` = Foreign Key · `UQ` = Unique · `IX` = Index
- Tipos mapeados do SQLAlchemy para PostgreSQL: `Integer → INTEGER`, `String(n) → VARCHAR(n)`, `Float → DOUBLE PRECISION`, `Boolean → BOOLEAN`, `Date → DATE`, `DateTime → TIMESTAMP`, `JSON → JSONB`
- Campos `created_at` usam `server_default=func.now()` — preenchidos automaticamente pelo banco.

---

## Tabela: `users`

Usuários da plataforma. Globais (sem isolamento por empresa no MVP).

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| nome | VARCHAR(150) | NOT NULL | Nome completo do usuário |
| email | VARCHAR(150) | NOT NULL, UQ, IX | E-mail (login) |
| hashed_password | VARCHAR(255) | NOT NULL | Senha hasheada com bcrypt |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Usuário ativo/inativo |
| is_superuser | BOOLEAN | NOT NULL, DEFAULT false | Administrador da plataforma |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Data/hora de criação |

**Índices:** `ix_users_email` (unique)

---

## Tabela: `empresas`

Empresas-cliente (matriz). Entidade raiz do isolamento multi-tenant.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| razao_social | VARCHAR(200) | NOT NULL | Razão social |
| nome_fantasia | VARCHAR(200) | NOT NULL, DEFAULT '' | Nome fantasia |
| cnpj_matriz | VARCHAR(20) | NOT NULL, UQ, IX | CNPJ da matriz (formato: XX.XXX.XXX/XXXX-XX ou só dígitos) |
| status | VARCHAR(10) | NOT NULL, DEFAULT 'ATIVO' | ATIVO \| INATIVO |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Data/hora de criação |

**Índices:** `ix_empresas_cnpj_matriz` (unique)
**Relacionamentos:** 1:N com `filiais`, 1:N com `ctes`

---

## Tabela: `filiais`

Filiais das empresas. Usadas para validar o CNPJ tomador na importação de CT-es.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| empresa_id | INTEGER | FK(empresas.id), NOT NULL, IX | Empresa à qual a filial pertence |
| razao_social | VARCHAR(200) | NOT NULL | Razão social da filial |
| cnpj | VARCHAR(20) | NOT NULL, IX | CNPJ da filial |
| cidade | VARCHAR(120) | DEFAULT '' | Cidade da filial |
| uf | VARCHAR(2) | DEFAULT '' | UF da filial |

**Índices:** `ix_filiais_empresa_id`, `ix_filiais_cnpj`
**FK:** `filiais.empresa_id → empresas.id` (CASCADE DELETE)

---

## Tabela: `transportadoras`

Cadastro de transportadoras. Global (compartilhado entre todas as empresas no MVP).

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| razao_social | VARCHAR(200) | NOT NULL | Razão social |
| nome_fantasia | VARCHAR(200) | DEFAULT '' | Nome fantasia / apelido |
| cnpj | VARCHAR(20) | NOT NULL, UQ, IX | CNPJ da transportadora |
| endereco | VARCHAR(200) | DEFAULT '' | Endereço completo |
| cidade | VARCHAR(120) | DEFAULT '' | Cidade |
| uf | VARCHAR(2) | DEFAULT '' | UF |
| cep | VARCHAR(10) | DEFAULT '' | CEP |
| contato | VARCHAR(120) | DEFAULT '' | Nome do contato |
| telefone | VARCHAR(30) | DEFAULT '' | Telefone |
| email | VARCHAR(150) | DEFAULT '' | E-mail |
| status | VARCHAR(10) | DEFAULT 'ATIVO' | ATIVO \| INATIVO |

**Índices:** `ix_transportadoras_cnpj` (unique)

---

## Tabela: `regioes`

Regiões de entrega personalizadas (cadastro de suporte).

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| nome | VARCHAR(120) | NOT NULL, UQ | Nome da região |
| descricao | VARCHAR(255) | DEFAULT '' | Descrição livre |

---

## Tabela: `cidades`

Mapeamento de cidades para macro-regiões.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| nome | VARCHAR(120) | NOT NULL, IX | Nome da cidade |
| uf | VARCHAR(2) | NOT NULL, IX | UF (sigla) |
| regiao_id | INTEGER | FK(regioes.id), NULL | Região personalizada (opcional) |
| macro_regiao | VARCHAR(15) | NULL | Macro-região: NORTE\|NORDESTE\|CENTRO_OESTE\|SUDESTE\|SUL |

**Índices:** `ix_cidades_nome`, `ix_cidades_uf`

---

## Tabela: `meta_nacional`

Meta única de custo logístico nacional.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Sempre = 1 (singleton) |
| meta_rs_kg | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | Meta de custo por kg (R$) |
| meta_pct_frete | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | Meta de % frete sobre mercadoria |

---

## Tabela: `meta_regional`

Meta de custo por macro-região.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| macro_regiao | VARCHAR(15) | NOT NULL, UQ, IX | NORTE\|NORDESTE\|CENTRO_OESTE\|SUDESTE\|SUL |
| meta_rs_kg | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | Meta de custo por kg (R$) |
| meta_pct_frete | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | Meta de % frete |
| prazo_medio_meta | INTEGER | NOT NULL, DEFAULT 0 | Prazo médio meta (dias) |

**Índices:** `ix_meta_regional_macro_regiao` (unique)

---

## Tabela: `benchmarks`

Valores de referência de mercado por região. Editáveis pelo administrador.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| regiao | VARCHAR(15) | NOT NULL, UQ, IX | NACIONAL\|NORTE\|NORDESTE\|CENTRO_OESTE\|SUDESTE\|SUL |
| frete_kg_min | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | R$/kg mínimo de mercado |
| frete_kg_medio | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | R$/kg médio de mercado |
| frete_kg_max | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | R$/kg máximo de mercado |
| frete_pct_min | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | % frete mínimo de mercado |
| frete_pct_medio | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | % frete médio de mercado |
| frete_pct_max | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | % frete máximo de mercado |

**Índices:** `ix_benchmarks_regiao` (unique)

---

## Tabela: `ctes`

Conhecimentos de Transporte Eletrônico. Principal tabela operacional.

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| empresa_id | INTEGER | FK(empresas.id), NOT NULL, IX | Empresa tomadora |
| transportadora_id | INTEGER | FK(transportadoras.id), NULL | Transportadora emissora |
| chave | VARCHAR(50) | NOT NULL, UQ, IX | Chave de acesso 44 dígitos |
| numero | VARCHAR(20) | DEFAULT '' | Número do CT-e |
| serie | VARCHAR(10) | DEFAULT '' | Série do CT-e |
| data_emissao | DATE | NULL | Data de emissão |
| tomador_cnpj | VARCHAR(20) | DEFAULT '' | CNPJ do tomador (matriz ou filial) |
| peso | DOUBLE PRECISION | DEFAULT 0 | Peso taxado (kg) = max(bruto, cubado) |
| valor_frete | DOUBLE PRECISION | DEFAULT 0 | Valor total do frete (R$) |
| valor_mercadoria | DOUBLE PRECISION | DEFAULT 0 | Valor da mercadoria / vCarga (R$) |
| municipio_origem | VARCHAR(120) | DEFAULT '' | Município de origem |
| uf_origem | VARCHAR(2) | DEFAULT '' | UF de origem |
| municipio_destino | VARCHAR(120) | DEFAULT '' | Município de destino |
| uf_destino | VARCHAR(2) | DEFAULT '' | UF de destino |
| macro_regiao_destino | VARCHAR(15) | NULL | Macro-região do destino (calculada) |
| data_saida | DATE | NULL | Data de saída/coleta |
| data_entrega | DATE | NULL | Data de entrega efetiva |
| origem_importacao | VARCHAR(10) | DEFAULT 'XML' | XML \| EXCEL |
| composicao_frete | JSONB | NULL | Composição por componente: `{"Frete Peso": 100.0, "Pedágio": 15.0, ...}` |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Data/hora de importação |

**Índices:** `ix_ctes_empresa_id`, `ix_ctes_chave` (unique)
**FK:** `ctes.empresa_id → empresas.id`, `ctes.transportadora_id → transportadoras.id`

---

## Tabela: `nfes`

Notas Fiscais vinculadas aos CT-es (chaves extraídas do XML).

| Campo | Tipo | Constraints | Descrição |
|-------|------|-------------|-----------|
| id | INTEGER | PK | Identificador sequencial |
| cte_id | INTEGER | FK(ctes.id), NULL, IX | CT-e ao qual a NF-e está vinculada |
| chave | VARCHAR(50) | NOT NULL, IX | Chave de acesso 44 dígitos da NF-e |
| numero | VARCHAR(20) | DEFAULT '' | Número da NF-e |
| data_emissao | DATE | NULL | Data de emissão |
| valor_mercadoria | DOUBLE PRECISION | DEFAULT 0 | Valor da NF-e (R$) |
| peso | DOUBLE PRECISION | DEFAULT 0 | Peso da NF-e (kg) |
| municipio_destino | VARCHAR(120) | DEFAULT '' | Município de destino |

**Índices:** `ix_nfes_cte_id`, `ix_nfes_chave`
**FK:** `nfes.cte_id → ctes.id` (CASCADE DELETE)

---

## Diagrama de Relacionamentos (Resumido)

```
empresas ──1:N── filiais
    │
    └──1:N── ctes ──N:1── transportadoras
                 │
                 └──1:N── nfes

regioes ──1:N── cidades

[Tabelas globais sem FK de empresa]
meta_nacional, meta_regional, benchmarks, users
```
