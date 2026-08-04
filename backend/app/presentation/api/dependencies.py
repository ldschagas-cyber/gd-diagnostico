"""Dependências do FastAPI: injeção de repositórios, casos de uso e usuário atual."""
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ACCESS_COOKIE_NAME, decode_access_token
from app.domain.entities import User
from app.infrastructure.database.repositories import (
    BenchmarkRepository,
    CidadeRepository,
    CTeRepository,
    EmpresaRepository,
    FilialRepository,
    MatrizMercadoPctRepository,
    MetaNacionalRepository,
    MetaRegionalRepository,
    RegiaoRepository,
    TransportadoraRepository,
    UserRepository,
)
from app.infrastructure.database.repositories import (
    BenchmarkCorredorRepository,
    ClusterClienteRepository,
    HubLogisticoRepository,
)

# auto_error=False: a ausência do header não derruba a requisição aqui — o
# cookie httpOnly (fluxo do navegador) é tentado primeiro em get_current_user;
# o header Bearer (fluxo de API/testes) continua funcionando como alternativa.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


# ---- Repositórios ----
def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_empresa_repo(db: Session = Depends(get_db)) -> EmpresaRepository:
    return EmpresaRepository(db)


def get_filial_repo(db: Session = Depends(get_db)) -> FilialRepository:
    return FilialRepository(db)


def get_transportadora_repo(db: Session = Depends(get_db)) -> TransportadoraRepository:
    return TransportadoraRepository(db)


def get_regiao_repo(db: Session = Depends(get_db)) -> RegiaoRepository:
    return RegiaoRepository(db)


def get_cidade_repo(db: Session = Depends(get_db)) -> CidadeRepository:
    return CidadeRepository(db)


def get_meta_nacional_repo(db: Session = Depends(get_db)) -> MetaNacionalRepository:
    return MetaNacionalRepository(db)


def get_meta_regional_repo(db: Session = Depends(get_db)) -> MetaRegionalRepository:
    return MetaRegionalRepository(db)


def get_benchmark_repo(db: Session = Depends(get_db)) -> BenchmarkRepository:
    return BenchmarkRepository(db)


def get_referencia_mercado_pct_repo(db: Session = Depends(get_db)) -> MatrizMercadoPctRepository:
    return MatrizMercadoPctRepository(db)


def get_cte_repo(db: Session = Depends(get_db)) -> CTeRepository:
    return CTeRepository(db)


# ---- Repositórios e use case do Benchmark OD (V2.1) ----
def get_hub_repo(db: Session = Depends(get_db)) -> HubLogisticoRepository:
    return HubLogisticoRepository(db)


def get_cluster_repo(db: Session = Depends(get_db)) -> ClusterClienteRepository:
    return ClusterClienteRepository(db)


def get_benchmark_corredor_repo(db: Session = Depends(get_db)) -> BenchmarkCorredorRepository:
    return BenchmarkCorredorRepository(db)


def get_benchmark_od_uc(db: Session = Depends(get_db)):
    from app.application.use_cases.benchmark_od import BenchmarkODUseCase
    return BenchmarkODUseCase(
        CTeRepository(db),
        ClusterClienteRepository(db),
        BenchmarkCorredorRepository(db),
        HubLogisticoRepository(db),
    )


def get_simulador_hub_uc(db: Session = Depends(get_db)):
    from app.application.use_cases.simulador_hub import SimuladorHubUseCase
    return SimuladorHubUseCase(
        CTeRepository(db),
        ClusterClienteRepository(db),
        BenchmarkCorredorRepository(db),
        HubLogisticoRepository(db),
    )


# ---- Usuário atual (JWT: cookie httpOnly do navegador OU header Bearer) ----
def get_current_user(
    request: Request,
    token_header: str | None = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Um header Authorization explícito sempre vence o cookie ambiente
    # (ex.: chamadas de API/testes com identidade própria dentro de uma
    # mesma sessão de navegador/cliente HTTP que já carrega outro cookie).
    token = token_header or request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise cred_exc
    sub = decode_access_token(token)
    if sub is None:
        raise cred_exc
    user = user_repo.get(int(sub))
    if user is None or not user.is_active:
        raise cred_exc
    return user


# ---- Serviço-a-serviço (ex.: CRM chamando /internal) ----
def verify_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    """Fail-closed: sem INTERNAL_API_KEY configurada no servidor, os endpoints
    /internal ficam inacessíveis mesmo com qualquer header — não existe um
    'modo aberto' acidental."""
    if not settings.INTERNAL_API_KEY or x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais internas inválidas")


def get_current_superuser(user: User = Depends(get_current_user)) -> User:
    # Aceita is_superuser OU role=ADMIN (R-04: papel passa a ter efeito).
    role = getattr(user, "role", None)
    eh_admin = user.is_superuser or (getattr(role, "value", role) == "ADMIN")
    if not eh_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requer privilégios de administrador",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Alias semântico para exigir perfil administrador (R-04)."""
    return get_current_superuser(user)


# ---- Papel VISUALIZADOR: somente leitura (R-04) ----
def bloquear_visualizador(user: User = Depends(get_current_user)) -> User:
    """Dependency: bloqueia qualquer ação de escrita para o papel VISUALIZADOR.

    Use em endpoints POST/PUT/PATCH/DELETE que hoje só exigem
    `get_current_user`. ADMIN e ANALISTA continuam liberados; endpoints já
    restritos a `get_current_superuser`/`require_admin` não precisam disso
    (ADMIN nunca é VISUALIZADOR).
    """
    role = getattr(user, "role", None)
    role_val = getattr(role, "value", role)
    if role_val == "VISUALIZADOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu perfil é somente leitura (VISUALIZADOR) e não permite esta ação.",
        )
    return user


# ---- Autorização por empresa (multi-tenant, R-01) ----
def _usuario_pode_acessar_empresa(user: User, empresa_id: int) -> bool:
    """Regra de acesso multi-tenant.

    - Superusuário / admin global (sem empresa_id): acessa qualquer empresa.
    - Usuário comum: acessa qualquer empresa a que esteja vinculado
      (login baseado em empresa, v6.14) — checagem contra `empresas_ids`
      (tabela usuario_empresas), não mais contra um único `empresa_id`.
    """
    role = getattr(user, "role", None)
    eh_admin = user.is_superuser or (getattr(role, "value", role) == "ADMIN")
    if eh_admin and user.empresa_id is None:
        return True
    return empresa_id in (getattr(user, "empresas_ids", None) or [])


def verificar_acesso_empresa(
    empresa_id: int,
    user: User = Depends(get_current_user),
    empresa_repo: "EmpresaRepository" = Depends(get_empresa_repo),
):
    """Dependency: valida existência da empresa E acesso do usuário a ela (R-01).

    O parâmetro `empresa_id` é resolvido automaticamente do path da rota.
    Use em qualquer endpoint que receba empresa_id no caminho:
        _=Depends(verificar_acesso_empresa)
    ou para já obter a empresa:
        empresa=Depends(verificar_acesso_empresa)
    """
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, f"Empresa {empresa_id} não encontrada")
    if not _usuario_pode_acessar_empresa(user, empresa_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso aos dados desta empresa.",
        )
    return empresa


def _get_empresa_or_404(empresa_id: int, empresa_repo: "EmpresaRepository"):
    """Mantido por compatibilidade. Apenas valida existência (sem acesso).

    Prefira `verificar_acesso_empresa` como dependency nos endpoints.
    """
    empresa = empresa_repo.get(empresa_id)
    if not empresa:
        raise HTTPException(404, f"Empresa {empresa_id} não encontrada")
    return empresa


# ══════════ Dependências BID (V3.1) ══════════
from app.infrastructure.database.repositories import (
    BidRepository, BidEscopoRepository, BidTransportadoraRepository,
    BidPropostaRepository, BidSimulacaoRepository, BidAuditoriaRepository,
)


def get_bid_repo(db: Session = Depends(get_db)) -> BidRepository:
    return BidRepository(db)

def get_bid_escopo_repo(db: Session = Depends(get_db)) -> BidEscopoRepository:
    return BidEscopoRepository(db)

def get_bid_transportadora_repo(db: Session = Depends(get_db)) -> BidTransportadoraRepository:
    return BidTransportadoraRepository(db)

def get_bid_proposta_repo(db: Session = Depends(get_db)) -> BidPropostaRepository:
    return BidPropostaRepository(db)

def get_bid_simulacao_repo(db: Session = Depends(get_db)) -> BidSimulacaoRepository:
    return BidSimulacaoRepository(db)

def get_bid_auditoria_repo(db: Session = Depends(get_db)) -> BidAuditoriaRepository:
    return BidAuditoriaRepository(db)


# ---- Autorização por BID e por Transportadora (multi-tenant, R-01) ----
def get_bid_com_acesso(
    bid_id: int,
    user: User = Depends(get_current_user),
    bid_repo: BidRepository = Depends(get_bid_repo),
):
    """Dependency: carrega o BID pelo `bid_id` do path e garante que o usuário
    logado tem acesso à empresa dona dele. Use em qualquer endpoint de
    `/bid/{bid_id}/...` ou `/mcl/{bid_id}/...` no lugar de só `get_current_user`.
    """
    bid = bid_repo.get(bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail=f"BID {bid_id} não encontrado")
    if not _usuario_pode_acessar_empresa(user, bid.empresa_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este BID.",
        )
    return bid


def get_transportadora_com_acesso(
    tid: int,
    user: User = Depends(get_current_user),
    repo: TransportadoraRepository = Depends(get_transportadora_repo),
):
    """Dependency: carrega a transportadora pelo `tid` do path e garante que o
    usuário logado tem acesso à empresa dona dela (R-01)."""
    t = repo.get(tid)
    if not t:
        raise HTTPException(status_code=404, detail="Transportadora não encontrada")
    if not _usuario_pode_acessar_empresa(user, t.empresa_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta transportadora.",
        )
    return t
