# Catálogo de APIs — GD Frete Diagnóstico
**Versão:** 2.0.0 · **Base URL:** `/api/v1` · **Autenticação:** Bearer JWT

---

## Convenções

- Todos os endpoints (exceto `POST /auth/login`) exigem header `Authorization: Bearer <token>`.
- Endpoints marcados com `[ADMIN]` exigem `is_superuser = true`.
- Datas no formato `YYYY-MM-DD`. Valores monetários em R$ (float).
- Respostas de erro seguem: `{"detail": "mensagem de erro"}`.

---

## Módulo: Autenticação

### `POST /auth/login`
Autentica usuário e retorna token JWT.

**Request** (`application/x-www-form-urlencoded`):
```
username=admin@gdconecta.com.br&password=admin123
```

**Response 200:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```
**Erros:** 401 — credenciais inválidas.

---

## Módulo: Usuários `[ADMIN]`

### `GET /usuarios`
Lista todos os usuários.

### `POST /usuarios`
Cria novo usuário.
```json
{ "nome": "string", "email": "string", "password": "string", "is_superuser": false }
```

### `PUT /usuarios/{id}`
Atualiza usuário (nome, email, senha, status).

### `DELETE /usuarios/{id}`
Remove usuário.

---

## Módulo: Empresas

### `GET /empresas`
Lista todas as empresas.

### `POST /empresas` `[ADMIN]`
Cria nova empresa.
```json
{ "razao_social": "string", "nome_fantasia": "string", "cnpj_matriz": "string" }
```

### `GET /empresas/{id}`
Retorna empresa por ID.

### `PUT /empresas/{id}` `[ADMIN]`
Atualiza empresa.

### `DELETE /empresas/{id}` `[ADMIN]`
Remove empresa (cascade: filiais, CT-es, NF-es).

### `GET /empresas/{id}/filiais`
Lista filiais da empresa.

### `POST /empresas/{id}/filiais` `[ADMIN]`
Adiciona filial.
```json
{ "razao_social": "string", "cnpj": "string", "cidade": "string", "uf": "string" }
```

### `PUT /empresas/{empresa_id}/filiais/{filial_id}` `[ADMIN]`
Atualiza filial.

### `DELETE /empresas/{empresa_id}/filiais/{filial_id}` `[ADMIN]`
Remove filial.

---

## Módulo: Transportadoras

### `GET /transportadoras`
Lista todas as transportadoras.

### `POST /transportadoras` `[ADMIN]`
Cria transportadora.
```json
{
  "razao_social": "string", "nome_fantasia": "string", "cnpj": "string",
  "cidade": "string", "uf": "string", "contato": "string", "email": "string"
}
```

### `GET /transportadoras/{id}`
Retorna por ID.

### `PUT /transportadoras/{id}` `[ADMIN]`
Atualiza.

### `DELETE /transportadoras/{id}` `[ADMIN]`
Remove.

---

## Módulo: Regiões e Cidades

### `GET /regioes`
Lista regiões personalizadas.

### `POST /regioes` `[ADMIN]`
Cria região.

### `GET /regioes/{id}/cidades`
Lista cidades da região.

### `POST /regioes/{id}/cidades`
Vincula cidade à região.

---

## Módulo: Metas `[ADMIN]`

### `GET /metas/nacional`
Retorna a meta nacional.

### `PUT /metas/nacional`
Define meta nacional.
```json
{ "meta_rs_kg": 1.50, "meta_pct_frete": 10.0 }
```

### `GET /metas/regionais`
Lista metas regionais.

### `PUT /metas/regionais/{macro_regiao}`
Define meta regional. `macro_regiao` ∈ `NORTE|NORDESTE|CENTRO_OESTE|SUDESTE|SUL`.

---

## Módulo: Benchmarks

### `GET /benchmarks`
Lista benchmarks de mercado (todos os usuários).

### `PUT /benchmarks/{regiao}` `[ADMIN]`
Atualiza benchmark. `regiao` ∈ `NACIONAL|NORTE|NORDESTE|CENTRO_OESTE|SUDESTE|SUL`.
```json
{
  "regiao": "SUDESTE",
  "frete_kg_min": 0.70, "frete_kg_medio": 0.95, "frete_kg_max": 1.20,
  "frete_pct_min": 4.0, "frete_pct_medio": 6.0, "frete_pct_max": 8.0
}
```

---

## Módulo: Importação

### `POST /importacao/cte/{empresa_id}`
Importa CT-es via XML.

**Request** (`multipart/form-data`):
- `arquivos`: um ou mais arquivos `.xml`

**Response 200:**
```json
{
  "importados": 42,
  "duplicados": 3,
  "rejeitados": 1,
  "detalhes_rejeitados": ["CT-e XXX: tomador 12345678000199 não é da empresa"]
}
```

**Regras:** Valida CNPJ tomador, deduplica por chave, extrai peso taxado.

### `POST /importacao/excel/{empresa_id}`
Importa CT-es via planilha Excel.

**Request** (`multipart/form-data`):
- `arquivo`: arquivo `.xlsx`

---

## Módulo: Dashboard (Diagnóstico)

### `GET /dashboard/{empresa_id}`
Retorna todos os indicadores de diagnóstico.

**Query params:**
- `data_inicio` (date, opcional)
- `data_fim` (date, opcional)

**Response 200:**
```json
{
  "empresa_id": 1,
  "empresa_nome": "string",
  "periodo_inicio": "2025-01-01",
  "periodo_fim": "2025-12-31",
  "nacional": {
    "valor_total_frete": 120000.0,
    "valor_total_mercadoria": 1200000.0,
    "peso_total": 80000.0,
    "frete_rs_kg": 1.50,
    "frete_pct": 10.0,
    "meta_rs_kg": 1.20,
    "meta_pct": 8.0,
    "desvio_rs_kg": 0.30,
    "desvio_pct": 25.0,
    "qtd_ctes": 500
  },
  "regionais": [ { "macro_regiao": "SUDESTE", "frete_total": 80000.0, ... } ],
  "transportadoras": [ { "nome": "TRANSP X", "participacao_pct": 60.0, ... } ],
  "prazos": [ { "transportadora": "TRANSP X", "otif": 92.5, ... } ],
  "composicao_frete": { "Frete Peso": 80000.0, "Pedágio": 12000.0 },
  "oportunidades": [ "Custo acima da meta em SUDESTE (+25%)" ]
}
```

---

## Módulo: Benchmark — Análise

### `GET /benchmark/nacional/{empresa_id}`
Comparativo nacional da empresa vs. benchmark de mercado.

**Query params:** `data_inicio`, `data_fim`, `transportadora_id` (todos opcionais)

**Response 200:**
```json
{
  "empresa_nome": "string",
  "valor_total_frete": 120000.0,
  "frete_kg": {
    "valor": 1.50,
    "benchmark_min": 1.30, "benchmark_medio": 1.65, "benchmark_max": 2.00,
    "desvio_pct": -9.1,
    "classificacao": "Excelente",
    "dentro_faixa": true
  },
  "frete_pct": { "valor": 10.0, "classificacao": "Atenção", ... }
}
```

### `GET /benchmark/regional/{empresa_id}`
Lista de comparativos por região de entrega.

**Response 200:** `[ { "macro_regiao": "SUDESTE", "frete_kg": {...}, "frete_pct": {...} } ]`

### `GET /benchmark/transportadoras/{empresa_id}`
Ranking de transportadoras por eficiência de custo vs. benchmark nacional.

**Response 200:**
```json
[{
  "nome": "TRANSP X", "frete_total": 80000.0, "participacao_pct": 60.0,
  "nivel_custo": "Melhor custo",
  "frete_kg": { "valor": 1.20, "desvio_pct": -27.3, "classificacao": "Excelente" }
}]
```

### `GET /benchmark/economia/{empresa_id}`
Potencial de economia e projeções.

**Response 200:**
```json
{
  "economia_total": 11000.0,
  "economia_pct": 9.2,
  "frete_total": 120000.0,
  "meses_periodo": 3.0,
  "economia_mensal": 3666.67,
  "proj_mensal": 3666.67,
  "proj_trimestral": 11000.0,
  "proj_semestral": 22000.0,
  "proj_anual": 44000.0,
  "por_regiao": [{ "macro_regiao": "SUDESTE", "economia": 9000.0, ... }]
}
```

### `GET /benchmark/executivo/{empresa_id}`
Dashboard executivo consolidado.

---

## Módulo: Relatórios

### `GET /relatorios/diagnostico/{empresa_id}/excel`
Baixa relatório de diagnóstico em Excel (`.xlsx`).

**Query params:** `data_inicio`, `data_fim`

**Response 200:** `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### `GET /relatorios/diagnostico/{empresa_id}/pdf`
Baixa relatório de diagnóstico em PDF.

**Response 200:** `Content-Type: application/pdf`

### `GET /relatorios/benchmark/{empresa_id}/excel`
Relatório consolidado de benchmark em Excel.

### `GET /relatorios/benchmark/{empresa_id}/pdf`
Relatório consolidado de benchmark em PDF.
