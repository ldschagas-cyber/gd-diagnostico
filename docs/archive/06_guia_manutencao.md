# Guia de Manutenção — GD Frete Diagnóstico
**Para desenvolvedores · v2.0.0 · GD Conecta**

---

## 1. Subir o Ambiente Local (Sem Docker)

### Pré-requisitos

- Python 3.12+ instalado
- Node.js 20+ instalado

### Backend

```bash
cd backend

# 1. Cria ambiente virtual
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# 2. Instala dependências
python -m pip install -r requirements.txt

# 3. Configura .env
cp .env.dev .env                   # já usa SQLite

# 4. Aplica migrations e sobe o servidor
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
# Acesse: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Acesse: http://localhost:5173
```

**Login padrão:** `admin@gdconecta.com.br` / `admin123`

---

## 2. Subir o Ambiente Local (Com Docker)

```bash
cp backend/.env.example backend/.env
# Ajuste as variáveis em backend/.env (PostgreSQL já configurado)

docker compose -f docker-compose.dev.yml up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# Banco:    localhost:5432 (gd_user/gd_pass/gd_frete)
```

---

## 3. Executar Testes

```bash
cd backend

# Instala dependências de teste (se não instaladas)
python -m pip install httpx pytest --break-system-packages

# Remove banco de testes e roda a suíte
rm -f gd_frete.db
PYTHONPATH=. python -m pytest tests/ -v
```

**Cobertura atual:** 9 testes de smoke (autenticação, importação, diagnóstico, benchmark, relatórios).

---

## 4. Executar Migrations

```bash
cd backend

# Ver status atual
python -m alembic current

# Aplicar migrations pendentes
python -m alembic upgrade head

# Criar nova migration (após alterar models)
python -m alembic revision --autogenerate -m "descricao_da_alteracao"

# Reverter última migration
python -m alembic downgrade -1

# Ver histórico
python -m alembic history --verbose
```

---

## 5. Publicar Nova Versão

```bash
# No servidor de produção:
cd /opt/gd-frete

# 1. Backup preventivo
/opt/gd-frete/scripts/backup.sh

# 2. Atualiza código
git pull origin main

# 3. Rebuild e restart
docker compose -f docker-compose.prod.yml up -d --build

# 4. Migrations são automáticas no startup
# Verifique:
docker compose -f docker-compose.prod.yml logs backend --tail=30

# 5. Confirma que tudo está healthy
docker compose -f docker-compose.prod.yml ps
```

---

## 6. Gerar Relatórios (Via API)

```bash
# Autenticar e salvar token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@gdconecta.com.br&password=admin123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Baixar relatório Excel de diagnóstico (empresa_id=1)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/relatorios/diagnostico/1/excel" \
  -o diagnostico.xlsx

# Baixar PDF de benchmark
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/relatorios/benchmark/1/pdf" \
  -o benchmark.pdf
```

---

## 7. Criar um Novo Módulo

Siga a Clean Architecture. O padrão de 6 passos:

### Passo 1 — Entidade de Domínio (`domain/entities/__init__.py`)

```python
@dataclass
class MeuModulo:
    id: Optional[int] = None
    nome: str = ""
    empresa_id: int = 0
```

### Passo 2 — Interface do Repositório (`domain/repositories/__init__.py`)

```python
class IMeuModuloRepository(ABC):
    @abstractmethod
    def list_by_empresa(self, empresa_id: int) -> List[MeuModulo]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[MeuModulo]: ...
    @abstractmethod
    def save(self, obj: MeuModulo) -> MeuModulo: ...
```

### Passo 3 — ORM Model (`infrastructure/database/models/__init__.py`)

```python
class MeuModuloModel(Base):
    __tablename__ = "meu_modulo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
```

### Passo 4 — Migration

```bash
python -m alembic revision --autogenerate -m "add_meu_modulo"
python -m alembic upgrade head
```

### Passo 5 — Repositório Concreto (`infrastructure/database/repositories/__init__.py`)

```python
class MeuModuloRepository(IMeuModuloRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_empresa(self, empresa_id: int):
        return [mapper(m) for m in self.db.scalars(
            select(MeuModuloModel).where(MeuModuloModel.empresa_id == empresa_id)
        ).all()]
```

### Passo 6 — Router + Schemas + Dependency + Registro

```python
# presentation/api/v1/meu_modulo.py
router = APIRouter(prefix="/meu-modulo", tags=["Meu Módulo"])

@router.get("/{empresa_id}", response_model=List[MeuModuloOut])
def listar(empresa_id: int, _=Depends(get_current_user), repo=Depends(get_meu_modulo_repo)):
    return repo.list_by_empresa(empresa_id)
```

Adicione `get_meu_modulo_repo` em `dependencies.py` e registre o router em `v1/__init__.py`.

---

## 8. Criar um Novo Endpoint

```python
# Em presentation/api/v1/meu_router.py
@router.get("/meu-endpoint/{empresa_id}", response_model=MeuOut)
def meu_endpoint(
    empresa_id: int,
    data_inicio: Optional[date] = Query(None),
    _=Depends(get_current_user),
    repo=Depends(get_meu_repo),
):
    # Chama o Use Case ou Repositório
    dados = repo.list_by_empresa(empresa_id)
    return dados
```

**Padrões a seguir:**
- Sempre use `Depends(get_current_user)` para autenticar.
- Adicione `Depends(get_current_superuser)` para rotas admin.
- Parâmetros de filtro (datas, IDs) via `Query()`.
- Retorno com `response_model` Pydantic.
- Erros: `raise HTTPException(status_code=..., detail="...")`.

---

## 9. Convenções de Código

### Python
- Tipagem explícita em todos os módulos públicos.
- Docstrings em `"""..."""` para classes e funções públicas.
- Constantes em UPPER_SNAKE_CASE.
- Funções auxiliares privadas com `_prefixo`.

### React
- Componentes de página: `PascalCase.jsx` em `pages/`.
- Componentes reutilizáveis: `PascalCase.jsx` em `components/`.
- Funções de API: agrupadas em `endpoints.js` por domínio (`empresasApi`, `benchmarkApi`, etc.).
- Cores sempre via `GD.indigo`, `GD.amber`, etc. — nunca hardcoded.

---

## 10. Comandos Úteis de Diagnóstico

```bash
# Ver todas as rotas registradas
python -c "
from app.main import app
for r in sorted(app.routes, key=lambda x: x.path):
    print(getattr(r, 'methods', {''}), r.path)
"

# Conectar ao banco PostgreSQL do container
docker exec -it gd_frete_db psql -U gd_user gd_frete

# Ver tabelas
\dt

# Contar CT-es por empresa
SELECT empresa_id, COUNT(*) FROM ctes GROUP BY empresa_id;

# Ver logs do backend em tempo real
docker compose -f docker-compose.prod.yml logs -f backend

# Reiniciar apenas o backend sem recriar
docker compose -f docker-compose.prod.yml restart backend

# Limpar banco de testes local
rm -f backend/gd_frete.db
```

---

## 11. Variáveis de Ambiente — Referência Rápida

| Variável | Dev | Prod |
|----------|-----|------|
| ENVIRONMENT | development | production |
| DEBUG | true | false |
| DATABASE_URL | sqlite:///./gd_frete.db | postgresql+psycopg2://... |
| SECRET_KEY | qualquer string | openssl rand -hex 32 |
| BACKEND_CORS_ORIGINS | localhost:5173 | https://app.gdconecta.com.br |
| FIRST_SUPERUSER_PASSWORD | admin123 | senha forte |
