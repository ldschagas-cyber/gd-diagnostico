# Guia de Instalação V4 — Inteligência Logística com IA

Este guia cobre a infraestrutura adicional que a V4 precisa: **Redis** (para
Celery e cache) e como rodar tudo. O PostgreSQL com pgvector você já subiu no
passo anterior (Opção B).

---

## 1. Subir o Redis (Docker)

O Redis é necessário para o Celery (processamento assíncrono) e para o cache de
respostas de IA. Com o Docker Desktop rodando, no PowerShell:

```powershell
docker run -d --name gd-redis -p 6379:6379 redis:7-alpine
```

Pronto. Para verificar:

```powershell
docker ps
```

Deve listar `gd-redis` e `gd-postgres`.

### Comandos do dia a dia

| Ação | Comando |
|---|---|
| Iniciar Redis | `docker start gd-redis` |
| Parar Redis | `docker stop gd-redis` |
| Iniciar PostgreSQL | `docker start gd-postgres` |
| Ver containers | `docker ps` |

---

## 2. Instalar as novas dependências Python

No diretório do backend, com o ambiente ativado:

```powershell
cd C:\gdconecta\frete\backend
pip install -r requirements.txt
```

Isso instala: celery, redis, openai, anthropic, pgvector.

---

## 3. Configurar o .env

Copie `.env.example` para `.env` (se ainda não tiver) e confirme estas linhas:

```
DATABASE_URL=postgresql://postgres:gdconecta2026@localhost:5432/gd_frete
AI_SIMULATION_MODE=True
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Com `AI_SIMULATION_MODE=True`, a IA funciona em modo simulado (sem custo, sem
chaves). Quando obtiver as chaves da OpenAI e Anthropic, preencha
`OPENAI_API_KEY` e `ANTHROPIC_API_KEY` e mude para `AI_SIMULATION_MODE=False`.

---

## 4. Rodar o sistema

### Terminal 1 — Backend (API)
```powershell
cd C:\gdconecta\frete\backend
python -m uvicorn app.main:app --reload
```

### Terminal 2 — Celery Worker (processamento assíncrono)
```powershell
cd C:\gdconecta\frete\backend
celery -A app.infrastructure.celery_app worker --loglevel=info --pool=solo
```
> No Windows use `--pool=solo` (o pool padrão do Celery não funciona bem no Windows).

### Terminal 3 — Celery Beat (agendador de insights diários) — opcional
```powershell
cd C:\gdconecta\frete\backend
celery -A app.infrastructure.celery_app beat --loglevel=info
```

### Terminal 4 — Frontend
```powershell
cd C:\gdconecta\frete\frontend
npm install
npm run dev
```

Acesse a porta que aparecer (5173 ou seguinte). Faça login com
`admin@gdconecta.com.br` / `admin123` e abra o menu **Inteligência Logística - IA**.

---

## 5. Validar a infraestrutura (DT-09)

Para confirmar que o Celery + Redis estão operacionais, no terminal do backend:

```powershell
python -c "from app.infrastructure.celery_app import celery_disponivel; print('Celery/Redis OK:', celery_disponivel())"
```

Deve imprimir `Celery/Redis OK: True`. Se imprimir `False`, verifique se o
container `gd-redis` está rodando (`docker ps`).

---

## 6. Modo simulado vs. modo real

| | Modo Simulado (atual) | Modo Real |
|---|---|---|
| Chaves de API | Não precisa | OpenAI + Anthropic |
| Custo | Zero | Centavos por operação |
| Respostas de IA | Mock realista | Análise real |
| Números (score, economia) | **Reais (SQL)** | **Reais (SQL)** |

Importante: mesmo em modo simulado, **todos os números são reais** — vêm de
consultas SQL ao seu banco. Apenas o texto narrativo da IA é simulado. Isso
permite testar todo o fluxo antes de configurar as chaves.

---

## 7. Quando obter as chaves

1. **OpenAI:** https://platform.openai.com → API Keys → Create Key
2. **Anthropic:** https://console.anthropic.com → API Keys → Create Key
3. Adicione créditos em Billing nos dois (US$ 5-10 já dura bastante para testes)
4. No `.env`, preencha as chaves e mude `AI_SIMULATION_MODE=False`
5. Reinicie o backend. Pronto — agora a IA usa os modelos reais.

Nenhuma alteração de código é necessária.

---

## 8. RAG e Relatórios Executivos (Fases 7 e 8)

### RAG — Base de Conhecimento
O RAG (busca semântica) já funciona em modo simulado. Para usá-lo:

1. Abra **Inteligência → Base de Conhecimento**
2. Clique em **Indexar legislação ANTT** para carregar o conhecimento global
3. Indexe seus próprios documentos (benchmarks, relatórios, BIDs encerrados)
4. No **Assistente**, as perguntas passam a considerar esse contexto

Observação técnica: a busca usa similaridade de cosseno sobre embeddings
armazenados em JSON, o que funciona igual em SQLite e PostgreSQL. Para grandes
volumes de documentos, a otimização é trocar para uma coluna `vector` nativa do
pgvector com índice ivfflat — a extensão já está instalada no seu container
PostgreSQL (Opção B). Em modo simulado, os embeddings são determinísticos
(mesmo texto gera o mesmo vetor); com a chave da OpenAI, passam a ser
embeddings reais (`text-embedding-3-small`).

### Relatório Executivo IA
Na tela **Diagnóstico IA**, após gerar um diagnóstico, use o botão
**Baixar relatório** para exportar em **PDF**, **Word** ou **PowerPoint**.
O documento traz capa, KPIs, resumo executivo, oportunidades, plano de ação e
conclusões na identidade visual da GD Conecta.

### Quando a chave da Anthropic chegar
Você mencionou que vai providenciar a chave da Anthropic. Quando tiver:

1. No `.env`, preencha `ANTHROPIC_API_KEY=sk-ant-...`
2. Mude `AI_SIMULATION_MODE=False`
3. Reinicie o backend

A partir daí, o assistente e as tarefas de volume passam a usar o Claude Haiku
de verdade. Para o GPT-4.1 (diagnóstico/relatório) e os embeddings reais do RAG,
você também precisará da chave da OpenAI — mas pode rodar só com a Anthropic
configurando ambos os modelos para Claude, se preferir começar por ela. Me avise
quando tiver a chave que eu ajusto a configuração para o cenário que você quiser.
