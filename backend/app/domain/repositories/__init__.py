"""Interfaces de repositório (ports da Arquitetura Limpa).

A camada de aplicação depende destas abstrações, nunca da implementação
concreta. Isso permite trocar SQLite por PostgreSQL (RNF001) ou mockar em testes.
"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from app.domain.entities import (
    Benchmark,
    CTe,
    Cidade,
    ClientePortalUser,
    Empresa,
    FechamentoMensal,
    Filial,
    MetaNacional,
    MetaRegional,
    Regiao,
    Transportadora,
    User,
)

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Contrato CRUD genérico."""

    @abstractmethod
    def get(self, id: int) -> Optional[T]: ...

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100) -> List[T]: ...

    @abstractmethod
    def create(self, entity: T) -> T: ...

    @abstractmethod
    def update(self, id: int, entity: T) -> Optional[T]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IUserRepository(IRepository[User]):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...


class IClientePortalUserRepository(ABC):
    """Não estende `IRepository` genérico — o Portal do Cliente não expõe
    list/create/update/delete via API; usuário-cliente é provisionado por
    script de seed (v6.18.0), não por CRUD."""

    @abstractmethod
    def get(self, id: int) -> Optional[ClientePortalUser]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[ClientePortalUser]: ...

    @abstractmethod
    def atualizar_ultimo_acesso(self, id: int) -> None: ...


class IEmpresaRepository(IRepository[Empresa]):
    @abstractmethod
    def get_by_cnpj(self, cnpj: str) -> Optional[Empresa]: ...


class IFilialRepository(IRepository[Filial]):
    @abstractmethod
    def list_by_empresa(self, empresa_id: int) -> List[Filial]: ...

    @abstractmethod
    def list_cnpjs_da_empresa(self, empresa_id: int) -> List[str]:
        """Retorna CNPJ da matriz + de todas as filiais (RF008 — validação tomador)."""
        ...


class ITransportadoraRepository(IRepository[Transportadora]):
    @abstractmethod
    def get_by_cnpj(self, cnpj: str) -> Optional[Transportadora]: ...

    @abstractmethod
    def get_by_cnpj_empresa(self, cnpj: str, empresa_id: int) -> Optional[Transportadora]: ...

    @abstractmethod
    def list_by_empresa(self, empresa_id: int, limit: int = 1000) -> List[Transportadora]: ...


class IRegiaoRepository(IRepository[Regiao]):
    pass


class ICidadeRepository(IRepository[Cidade]):
    @abstractmethod
    def get_by_nome_uf(self, nome: str, uf: str) -> Optional[Cidade]: ...


class IMetaNacionalRepository(ABC):
    @abstractmethod
    def get(self, empresa_id: int) -> Optional[MetaNacional]: ...

    @abstractmethod
    def upsert(self, meta: MetaNacional) -> MetaNacional: ...


class IMetaRegionalRepository(ABC):
    @abstractmethod
    def list(self, empresa_id: int) -> List[MetaRegional]: ...

    @abstractmethod
    def upsert(self, meta: MetaRegional) -> MetaRegional: ...


class IFechamentoMensalRepository(ABC):
    @abstractmethod
    def get_by_competencia(self, empresa_id: int, competencia: str) -> Optional[FechamentoMensal]: ...

    @abstractmethod
    def list_historico(self, empresa_id: int, limite: int = 13) -> List[FechamentoMensal]: ...

    @abstractmethod
    def upsert(self, fechamento: FechamentoMensal) -> FechamentoMensal: ...

    @abstractmethod
    def fechar(self, empresa_id: int, competencia: str) -> Optional[FechamentoMensal]: ...

    @abstractmethod
    def reabrir(self, empresa_id: int, competencia: str) -> Optional[FechamentoMensal]: ...


class IBenchmarkRepository(ABC):
    @abstractmethod
    def list(self) -> List[Benchmark]: ...

    @abstractmethod
    def get_by_regiao(self, regiao: str) -> Optional[Benchmark]: ...

    @abstractmethod
    def upsert(self, benchmark: Benchmark) -> Benchmark: ...


# ══════════ Benchmark Logístico V2.1 — Modelo OD ══════════
from app.domain.entities import BenchmarkCorredor, ClusterCliente, HubLogistico


class IHubLogisticoRepository(ABC):
    @abstractmethod
    def list(self, empresa_id: int, apenas_ativos: bool = False) -> List[HubLogistico]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[HubLogistico]: ...
    @abstractmethod
    def get_by_codigo(self, empresa_id: int, codigo: str) -> Optional[HubLogistico]: ...
    @abstractmethod
    def create(self, hub: HubLogistico) -> HubLogistico: ...
    @abstractmethod
    def update(self, id: int, hub: HubLogistico) -> Optional[HubLogistico]: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IClusterClienteRepository(ABC):
    @abstractmethod
    def list_by_empresa(self, empresa_id: int) -> List[ClusterCliente]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[ClusterCliente]: ...
    @abstractmethod
    def create(self, cluster: ClusterCliente) -> ClusterCliente: ...
    @abstractmethod
    def update(self, id: int, cluster: ClusterCliente) -> Optional[ClusterCliente]: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IBenchmarkCorredorRepository(ABC):
    @abstractmethod
    def list(self, empresa_id: int) -> List[BenchmarkCorredor]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[BenchmarkCorredor]: ...
    @abstractmethod
    def get_by_corredor(
        self, empresa_id: int, hub_origem: str, hub_destino: str
    ) -> Optional[BenchmarkCorredor]: ...
    @abstractmethod
    def upsert(self, corredor: BenchmarkCorredor) -> BenchmarkCorredor: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...


class ICTeRepository(IRepository[CTe]):
    @abstractmethod
    def get_by_chave(self, chave: str) -> Optional[CTe]: ...

    @abstractmethod
    def get_chaves_existentes(self, chaves: List[str]) -> set:
        """Retorna, dentre as chaves informadas, as que já existem no banco (qualquer empresa).

        Usado para checar duplicidade em lote (uma query) em vez de uma query por CT-e.
        """
        ...

    @abstractmethod
    def list_by_empresa(
        self,
        empresa_id: int,
        data_inicio=None,
        data_fim=None,
        apenas_ativos: bool = False,
    ) -> List[CTe]: ...

    @abstractmethod
    def bulk_create(self, ctes: List[CTe]) -> int: ...

    @abstractmethod
    def agregar_nacional(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> dict: ...

    @abstractmethod
    def agregar_por_regiao(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> list: ...

    @abstractmethod
    def intervalo_datas(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> tuple:
        """Retorna (MIN, MAX) de data_emissao dos CT-es que atendem ao filtro."""
        ...

    @abstractmethod
    def agregar_por_transportadora(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> list: ...

    @abstractmethod
    def agregar_por_uf_od(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> list:
        """Agrega via SQL por par (uf_origem, uf_destino) — base do modelo OD."""
        ...

    @abstractmethod
    def listar_prazos(
        self, empresa_id: int, data_inicio=None, data_fim=None, apenas_ativos: bool = True
    ) -> List[CTe]: ...


# ══════════ Módulo BID (V3.1) ══════════
from app.domain.entities import (
    Bid, BidAuditoria, BidEscopo, BidProposta, BidSimulacao, BidTransportadora,
    BidStatusEnum, BidTransportadoraStatusEnum,
)


class IBidRepository(ABC):
    @abstractmethod
    def get(self, id: int) -> Optional[Bid]: ...
    @abstractmethod
    def list_by_empresa(self, empresa_id: int) -> List[Bid]: ...
    @abstractmethod
    def create(self, bid: Bid) -> Bid: ...
    @abstractmethod
    def update(self, id: int, bid: Bid) -> Optional[Bid]: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...
    @abstractmethod
    def update_status(self, id: int, status: BidStatusEnum) -> Optional[Bid]: ...


class IBidEscopoRepository(ABC):
    @abstractmethod
    def list_by_bid(self, bid_id: int) -> List[BidEscopo]: ...
    @abstractmethod
    def create(self, escopo: BidEscopo) -> BidEscopo: ...
    @abstractmethod
    def update(self, id: int, escopo: BidEscopo) -> Optional[BidEscopo]: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...
    @abstractmethod
    def delete_by_bid(self, bid_id: int) -> int: ...


class IBidTransportadoraRepository(ABC):
    @abstractmethod
    def list_by_bid(self, bid_id: int) -> List[BidTransportadora]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[BidTransportadora]: ...
    @abstractmethod
    def create(self, bt: BidTransportadora) -> BidTransportadora: ...
    @abstractmethod
    def update(self, id: int, bt: BidTransportadora) -> Optional[BidTransportadora]: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...
    @abstractmethod
    def update_status(self, id: int, status: BidTransportadoraStatusEnum) -> Optional[BidTransportadora]: ...


class IBidPropostaRepository(ABC):
    @abstractmethod
    def list_by_bid(self, bid_id: int) -> List[BidProposta]: ...
    @abstractmethod
    def list_by_bid_transportadora(self, bid_transportadora_id: int) -> List[BidProposta]: ...
    @abstractmethod
    def create(self, proposta: BidProposta) -> BidProposta: ...
    @abstractmethod
    def bulk_create(self, propostas: List[BidProposta]) -> int: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...
    @abstractmethod
    def delete_by_bid(self, bid_id: int) -> int: ...


class IBidSimulacaoRepository(ABC):
    @abstractmethod
    def list_by_bid(self, bid_id: int) -> List[BidSimulacao]: ...
    @abstractmethod
    def get(self, id: int) -> Optional[BidSimulacao]: ...
    @abstractmethod
    def create(self, sim: BidSimulacao) -> BidSimulacao: ...
    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IBidAuditoriaRepository(ABC):
    @abstractmethod
    def list_by_bid(self, bid_id: int) -> List[BidAuditoria]: ...
    @abstractmethod
    def registrar(self, audit: BidAuditoria) -> BidAuditoria: ...
