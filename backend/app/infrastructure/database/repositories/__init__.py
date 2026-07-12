"""Implementações concretas dos repositórios usando SQLAlchemy (adapters)."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    Benchmark,
    CTe,
    CTE_STATUS_ATIVO,
    CTE_STATUS_CANCELADO,
    Cidade,
    Empresa,
    Filial,
    MetaNacional,
    MetaRegional,
    Regiao,
    Transportadora,
    User,
)
from app.domain.repositories import (
    IBenchmarkRepository,
    ICidadeRepository,
    ICTeRepository,
    IEmpresaRepository,
    IFilialRepository,
    IMetaNacionalRepository,
    IMetaRegionalRepository,
    IRegiaoRepository,
    ITransportadoraRepository,
    IUserRepository,
)
from app.infrastructure.database.models import (
    BenchmarkModel,
    CidadeModel,
    CTeModel,
    CteCancelamentoModel,
    EmpresaModel,
    FilialModel,
    MetaNacionalModel,
    MetaRegionalModel,
    NFeModel,
    RegiaoModel,
    TransportadoraModel,
    UserModel,
)
from app.infrastructure.database.repositories import mappers as mp


class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[User]:
        m = self.db.get(UserModel, id)
        return mp.user_to_domain(m) if m else None

    def get_by_email(self, email: str) -> Optional[User]:
        m = self.db.scalar(select(UserModel).where(UserModel.email == email))
        return mp.user_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        rows = self.db.scalars(select(UserModel).offset(skip).limit(limit)).all()
        return [mp.user_to_domain(m) for m in rows]

    def create(self, e: User) -> User:
        m = UserModel(
            nome=e.nome, email=e.email, hashed_password=e.hashed_password,
            is_active=e.is_active, is_superuser=e.is_superuser,
            role=(e.role.value if hasattr(e.role, "value") else (e.role or "ANALISTA")),
            empresa_id=e.empresa_id,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.user_to_domain(m)

    def update(self, id: int, e: User) -> Optional[User]:
        m = self.db.get(UserModel, id)
        if not m:
            return None
        m.nome = e.nome; m.email = e.email; m.is_active = e.is_active
        m.is_superuser = e.is_superuser
        m.empresa_id = e.empresa_id
        if getattr(e, "role", None):
            m.role = e.role.value if hasattr(e.role, "value") else e.role
        if e.hashed_password:
            m.hashed_password = e.hashed_password
        self.db.commit(); self.db.refresh(m)
        return mp.user_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(UserModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class EmpresaRepository(IEmpresaRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[Empresa]:
        m = self.db.get(EmpresaModel, id)
        return mp.empresa_to_domain(m) if m else None

    def get_by_cnpj(self, cnpj: str) -> Optional[Empresa]:
        m = self.db.scalar(select(EmpresaModel).where(EmpresaModel.cnpj_matriz == cnpj))
        return mp.empresa_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[Empresa]:
        rows = self.db.scalars(select(EmpresaModel).offset(skip).limit(limit)).all()
        return [mp.empresa_to_domain(m) for m in rows]

    def create(self, e: Empresa) -> Empresa:
        m = EmpresaModel(
            razao_social=e.razao_social, nome_fantasia=e.nome_fantasia,
            cnpj_matriz=e.cnpj_matriz, status=e.status.value,
            setor=e.setor.value if hasattr(e.setor, "value") else e.setor,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.empresa_to_domain(m)

    def update(self, id: int, e: Empresa) -> Optional[Empresa]:
        m = self.db.get(EmpresaModel, id)
        if not m:
            return None
        m.razao_social = e.razao_social; m.nome_fantasia = e.nome_fantasia
        m.cnpj_matriz = e.cnpj_matriz; m.status = e.status.value
        m.setor = e.setor.value if hasattr(e.setor, "value") else e.setor
        self.db.commit(); self.db.refresh(m)
        return mp.empresa_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(EmpresaModel, id)
        if not m:
            return False
        # Inativação lógica (RF002 — "Inativar embarcadores")
        m.status = "INATIVO"
        self.db.commit()
        return True


class FilialRepository(IFilialRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[Filial]:
        m = self.db.get(FilialModel, id)
        return mp.filial_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[Filial]:
        rows = self.db.scalars(select(FilialModel).offset(skip).limit(limit)).all()
        return [mp.filial_to_domain(m) for m in rows]

    def list_by_empresa(self, empresa_id: int) -> List[Filial]:
        rows = self.db.scalars(
            select(FilialModel).where(FilialModel.empresa_id == empresa_id)
        ).all()
        return [mp.filial_to_domain(m) for m in rows]

    def list_cnpjs_da_empresa(self, empresa_id: int) -> List[str]:
        cnpjs: List[str] = []
        empresa = self.db.get(EmpresaModel, empresa_id)
        if empresa:
            cnpjs.append(_so_digitos(empresa.cnpj_matriz))
        filiais = self.db.scalars(
            select(FilialModel).where(FilialModel.empresa_id == empresa_id)
        ).all()
        cnpjs.extend(_so_digitos(f.cnpj) for f in filiais)
        return [c for c in cnpjs if c]

    def create(self, e: Filial) -> Filial:
        m = FilialModel(
            empresa_id=e.empresa_id, razao_social=e.razao_social,
            cnpj=e.cnpj, cidade=e.cidade, uf=e.uf,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.filial_to_domain(m)

    def update(self, id: int, e: Filial) -> Optional[Filial]:
        m = self.db.get(FilialModel, id)
        if not m:
            return None
        m.empresa_id = e.empresa_id; m.razao_social = e.razao_social
        m.cnpj = e.cnpj; m.cidade = e.cidade; m.uf = e.uf
        self.db.commit(); self.db.refresh(m)
        return mp.filial_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(FilialModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class TransportadoraRepository(ITransportadoraRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[Transportadora]:
        m = self.db.get(TransportadoraModel, id)
        return mp.transportadora_to_domain(m) if m else None

    def get_by_cnpj(self, cnpj: str) -> Optional[Transportadora]:
        """Busca global por CNPJ — usada apenas para compatibilidade."""
        m = self.db.scalar(
            select(TransportadoraModel).where(TransportadoraModel.cnpj == cnpj)
        )
        return mp.transportadora_to_domain(m) if m else None

    def get_by_cnpj_empresa(self, cnpj: str, empresa_id: int) -> Optional[Transportadora]:
        """Busca transportadora por CNPJ dentro do escopo da empresa."""
        m = self.db.scalar(
            select(TransportadoraModel).where(
                TransportadoraModel.cnpj == cnpj,
                TransportadoraModel.empresa_id == empresa_id,
            )
        )
        return mp.transportadora_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[Transportadora]:
        """Lista global (legado) — preferir list_by_empresa."""
        rows = self.db.scalars(
            select(TransportadoraModel).offset(skip).limit(limit)
        ).all()
        return [mp.transportadora_to_domain(m) for m in rows]

    def list_by_empresa(self, empresa_id: int, limit: int = 1000) -> List[Transportadora]:
        """Lista transportadoras da empresa (isolamento multi-tenant)."""
        rows = self.db.scalars(
            select(TransportadoraModel)
            .where(TransportadoraModel.empresa_id == empresa_id)
            .limit(limit)
        ).all()
        return [mp.transportadora_to_domain(m) for m in rows]

    def create(self, e: Transportadora) -> Transportadora:
        m = TransportadoraModel(
            empresa_id=e.empresa_id,
            razao_social=e.razao_social, nome_fantasia=e.nome_fantasia, cnpj=e.cnpj,
            endereco=e.endereco, cidade=e.cidade, uf=e.uf, cep=e.cep,
            contato=e.contato, telefone=e.telefone, email=e.email, status=e.status.value,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.transportadora_to_domain(m)

    def update(self, id: int, e: Transportadora) -> Optional[Transportadora]:
        m = self.db.get(TransportadoraModel, id)
        if not m:
            return None
        for attr in ("razao_social", "nome_fantasia", "cnpj", "endereco", "cidade",
                     "uf", "cep", "contato", "telefone", "email"):
            setattr(m, attr, getattr(e, attr))
        m.status = e.status.value
        self.db.commit(); self.db.refresh(m)
        return mp.transportadora_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(TransportadoraModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class RegiaoRepository(IRegiaoRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[Regiao]:
        m = self.db.get(RegiaoModel, id)
        return mp.regiao_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[Regiao]:
        rows = self.db.scalars(select(RegiaoModel).offset(skip).limit(limit)).all()
        return [mp.regiao_to_domain(m) for m in rows]

    def create(self, e: Regiao) -> Regiao:
        m = RegiaoModel(nome=e.nome, descricao=e.descricao)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.regiao_to_domain(m)

    def update(self, id: int, e: Regiao) -> Optional[Regiao]:
        m = self.db.get(RegiaoModel, id)
        if not m:
            return None
        m.nome = e.nome; m.descricao = e.descricao
        self.db.commit(); self.db.refresh(m)
        return mp.regiao_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(RegiaoModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class CidadeRepository(ICidadeRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[Cidade]:
        m = self.db.get(CidadeModel, id)
        return mp.cidade_to_domain(m) if m else None

    def get_by_nome_uf(self, nome: str, uf: str) -> Optional[Cidade]:
        m = self.db.scalar(
            select(CidadeModel).where(
                CidadeModel.nome.ilike(nome.strip()),
                CidadeModel.uf == uf.strip().upper(),
            )
        )
        return mp.cidade_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 1000) -> List[Cidade]:
        rows = self.db.scalars(select(CidadeModel).offset(skip).limit(limit)).all()
        return [mp.cidade_to_domain(m) for m in rows]

    def create(self, e: Cidade) -> Cidade:
        m = CidadeModel(
            nome=e.nome, uf=e.uf, regiao_id=e.regiao_id,
            macro_regiao=e.macro_regiao.value if e.macro_regiao else None,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.cidade_to_domain(m)

    def update(self, id: int, e: Cidade) -> Optional[Cidade]:
        m = self.db.get(CidadeModel, id)
        if not m:
            return None
        m.nome = e.nome; m.uf = e.uf; m.regiao_id = e.regiao_id
        m.macro_regiao = e.macro_regiao.value if e.macro_regiao else None
        self.db.commit(); self.db.refresh(m)
        return mp.cidade_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(CidadeModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class MetaNacionalRepository(IMetaNacionalRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Optional[MetaNacional]:
        m = self.db.scalar(select(MetaNacionalModel).limit(1))
        return mp.meta_nacional_to_domain(m) if m else None

    def upsert(self, meta: MetaNacional) -> MetaNacional:
        m = self.db.scalar(select(MetaNacionalModel).limit(1))
        if not m:
            m = MetaNacionalModel()
            self.db.add(m)
        m.meta_rs_kg = meta.meta_rs_kg
        m.meta_pct_frete = meta.meta_pct_frete
        self.db.commit(); self.db.refresh(m)
        return mp.meta_nacional_to_domain(m)


class MetaRegionalRepository(IMetaRegionalRepository):
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[MetaRegional]:
        rows = self.db.scalars(select(MetaRegionalModel)).all()
        return [mp.meta_regional_to_domain(m) for m in rows]

    def upsert(self, meta: MetaRegional) -> MetaRegional:
        m = self.db.scalar(
            select(MetaRegionalModel).where(
                MetaRegionalModel.macro_regiao == meta.macro_regiao.value
            )
        )
        if not m:
            m = MetaRegionalModel(macro_regiao=meta.macro_regiao.value)
            self.db.add(m)
        m.meta_rs_kg = meta.meta_rs_kg
        m.meta_pct_frete = meta.meta_pct_frete
        m.prazo_medio_meta = meta.prazo_medio_meta
        self.db.commit(); self.db.refresh(m)
        return mp.meta_regional_to_domain(m)


class CTeRepository(ICTeRepository):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[CTe]:
        m = self.db.get(CTeModel, id)
        return mp.cte_to_domain(m) if m else None

    def get_by_chave(self, chave: str) -> Optional[CTe]:
        m = self.db.scalar(select(CTeModel).where(CTeModel.chave == chave))
        return mp.cte_to_domain(m) if m else None

    def list(self, skip: int = 0, limit: int = 100) -> List[CTe]:
        rows = self.db.scalars(select(CTeModel).offset(skip).limit(limit)).all()
        return [mp.cte_to_domain(m) for m in rows]

    def list_by_empresa(
        self, empresa_id: int, data_inicio: date | None = None,
        data_fim: date | None = None, apenas_ativos: bool = False,
    ) -> List[CTe]:
        stmt = select(CTeModel).where(CTeModel.empresa_id == empresa_id)
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        rows = self.db.scalars(stmt).all()
        return [mp.cte_to_domain(m) for m in rows]

    def create(self, e: CTe) -> CTe:
        m = self._to_model(e)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.cte_to_domain(m)

    def bulk_create(self, ctes: List[CTe]) -> int:
        """Insere CT-es em lote com um único commit."""
        count = 0
        for e in ctes:
            m = self._to_model(e)
            self.db.add(m)
            count += 1
        self.db.commit()
        return count

    # ── Agregações SQL (performance: evita carregar todos os CT-es em Python) ──

    def agregar_nacional(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
        apenas_ativos: bool = True,
    ) -> dict:
        """Retorna totais nacionais via SQL (SUM/COUNT) — sem materializar objetos CTe.

        Por padrão considera apenas CT-es ATIVOS (MELHORIA — cancelamentos são
        excluídos dos indicadores financeiros).
        """
        from sqlalchemy import func

        stmt = (
            select(
                func.sum(CTeModel.valor_frete).label("valor_total_frete"),
                func.sum(CTeModel.valor_mercadoria).label("valor_total_mercadoria"),
                func.sum(CTeModel.peso).label("peso_total"),
                func.count(CTeModel.id).label("qtd_ctes"),
            )
            .where(CTeModel.empresa_id == empresa_id)
        )
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        row = self.db.execute(stmt).one()
        return {
            "valor_total_frete": float(row.valor_total_frete or 0),
            "valor_total_mercadoria": float(row.valor_total_mercadoria or 0),
            "peso_total": float(row.peso_total or 0),
            "qtd_ctes": int(row.qtd_ctes or 0),
        }

    def contar_situacao_nacional(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
    ) -> dict:
        """Conta CT-es emitidos, ativos e cancelados (MELHORIAS 3 e 4)."""
        from sqlalchemy import case, func

        stmt = (
            select(
                func.count(CTeModel.id).label("emitidos"),
                func.sum(
                    case((CTeModel.status == CTE_STATUS_CANCELADO, 1), else_=0)
                ).label("cancelados"),
            )
            .where(CTeModel.empresa_id == empresa_id)
        )
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        row = self.db.execute(stmt).one()
        emitidos = int(row.emitidos or 0)
        cancelados = int(row.cancelados or 0)
        return {
            "emitidos": emitidos,
            "cancelados": cancelados,
            "ativos": emitidos - cancelados,
        }

    def agregar_por_regiao(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
        apenas_ativos: bool = True,
    ) -> list[dict]:
        """Retorna totais agrupados por macro_regiao_destino via SQL GROUP BY.

        Por padrão considera apenas CT-es ATIVOS.
        """
        from sqlalchemy import func

        stmt = (
            select(
                CTeModel.macro_regiao_destino.label("macro_regiao"),
                func.sum(CTeModel.valor_frete).label("frete_total"),
                func.sum(CTeModel.valor_mercadoria).label("mercadoria_total"),
                func.sum(CTeModel.peso).label("peso_total"),
                func.count(CTeModel.id).label("qtd_ctes"),
            )
            .where(CTeModel.empresa_id == empresa_id)
            .group_by(CTeModel.macro_regiao_destino)
        )
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        rows = self.db.execute(stmt).all()
        return [
            {
                "macro_regiao": r.macro_regiao or "INDEFINIDA",
                "frete_total": float(r.frete_total or 0),
                "mercadoria_total": float(r.mercadoria_total or 0),
                "peso_total": float(r.peso_total or 0),
                "qtd_ctes": int(r.qtd_ctes or 0),
            }
            for r in rows
        ]

    def agregar_por_transportadora(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
        apenas_ativos: bool = True,
    ) -> list[dict]:
        """Retorna totais agrupados por transportadora_id via SQL GROUP BY.

        Por padrão considera apenas CT-es ATIVOS.
        """
        from sqlalchemy import func

        stmt = (
            select(
                CTeModel.transportadora_id.label("transportadora_id"),
                func.sum(CTeModel.valor_frete).label("frete_total"),
                func.sum(CTeModel.valor_mercadoria).label("mercadoria_total"),
                func.sum(CTeModel.peso).label("peso_total"),
                func.count(CTeModel.id).label("qtd_ctes"),
            )
            .where(CTeModel.empresa_id == empresa_id)
            .group_by(CTeModel.transportadora_id)
        )
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        rows = self.db.execute(stmt).all()
        return [
            {
                "transportadora_id": r.transportadora_id,
                "frete_total": float(r.frete_total or 0),
                "mercadoria_total": float(r.mercadoria_total or 0),
                "peso_total": float(r.peso_total or 0),
                "qtd_ctes": int(r.qtd_ctes or 0),
            }
            for r in rows
        ]

    def agregar_por_uf_od(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
        apenas_ativos: bool = True,
    ) -> list[dict]:
        """Agrega via SQL por par (uf_origem, uf_destino) — base do modelo OD.

        Devolve uma linha por corredor UF→UF. A consolidação em Hub→Hub
        é feita na camada de aplicação, que conhece o mapa de clusters
        da empresa. Por padrão considera apenas CT-es ATIVOS (RN-09).
        """
        from sqlalchemy import func

        stmt = (
            select(
                CTeModel.uf_origem.label("uf_origem"),
                CTeModel.municipio_origem.label("municipio_origem"),
                CTeModel.uf_destino.label("uf_destino"),
                CTeModel.municipio_destino.label("municipio_destino"),
                func.sum(CTeModel.valor_frete).label("frete_total"),
                func.sum(CTeModel.valor_mercadoria).label("mercadoria_total"),
                func.sum(CTeModel.peso).label("peso_total"),
                func.count(CTeModel.id).label("qtd_ctes"),
            )
            .where(CTeModel.empresa_id == empresa_id)
            .group_by(
                CTeModel.uf_origem, CTeModel.municipio_origem,
                CTeModel.uf_destino, CTeModel.municipio_destino,
            )
        )
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        rows = self.db.execute(stmt).all()
        return [
            {
                "uf_origem": (r.uf_origem or "").upper(),
                "municipio_origem": r.municipio_origem or "",
                "uf_destino": (r.uf_destino or "").upper(),
                "municipio_destino": r.municipio_destino or "",
                "frete_total": float(r.frete_total or 0),
                "mercadoria_total": float(r.mercadoria_total or 0),
                "peso_total": float(r.peso_total or 0),
                "qtd_ctes": int(r.qtd_ctes or 0),
            }
            for r in rows
        ]

    def listar_prazos(
        self,
        empresa_id: int,
        data_inicio: "date | None" = None,
        data_fim: "date | None" = None,
        apenas_ativos: bool = True,
    ) -> "List[CTe]":
        """Carrega apenas CT-es com datas de prazo preenchidas (subconjunto menor).

        Por padrão considera apenas CT-es ATIVOS.
        """
        stmt = (
            select(CTeModel)
            .where(
                CTeModel.empresa_id == empresa_id,
                CTeModel.data_saida.is_not(None),
                CTeModel.data_entrega.is_not(None),
            )
        )
        if apenas_ativos:
            stmt = stmt.where(CTeModel.status == CTE_STATUS_ATIVO)
        if data_inicio:
            stmt = stmt.where(CTeModel.data_emissao >= data_inicio)
        if data_fim:
            stmt = stmt.where(CTeModel.data_emissao <= data_fim)
        rows = self.db.scalars(stmt).all()
        return [mp.cte_to_domain(m) for m in rows]

    def update(self, id: int, e: CTe) -> Optional[CTe]:
        m = self.db.get(CTeModel, id)
        if not m:
            return None
        m.transportadora_id = e.transportadora_id
        m.data_saida = e.data_saida
        m.data_entrega = e.data_entrega
        self.db.commit(); self.db.refresh(m)
        return mp.cte_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(CTeModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True

    def _to_model(self, e: CTe) -> CTeModel:
        return CTeModel(
            empresa_id=e.empresa_id, transportadora_id=e.transportadora_id,
            chave=e.chave, numero=e.numero, serie=e.serie,
            data_emissao=e.data_emissao, tomador_cnpj=e.tomador_cnpj,
            destinatario_cnpj=e.destinatario_cnpj or None,
            destinatario_nome=e.destinatario_nome or None,
            peso=e.peso, valor_frete=e.valor_frete, valor_mercadoria=e.valor_mercadoria,
            municipio_origem=e.municipio_origem, uf_origem=e.uf_origem,
            municipio_destino=e.municipio_destino, uf_destino=e.uf_destino,
            macro_regiao_destino=e.macro_regiao_destino.value
            if e.macro_regiao_destino else None,
            data_saida=e.data_saida, data_entrega=e.data_entrega,
            origem_importacao=e.origem_importacao,
            composicao_frete=e.composicao_frete or {},
            nfes=[
                NFeModel(
                    chave=n.chave, numero=n.numero, data_emissao=n.data_emissao,
                    valor_mercadoria=n.valor_mercadoria, peso=n.peso,
                    municipio_destino=n.municipio_destino,
                )
                for n in e.nfes
            ],
        )

    # ── Suporte à importação Excel: upsert por chave natural (RF010 — evolução) ──

    def buscar_excel_existente(
        self, empresa_id: int, nota_fiscal: str, cte: str = ""
    ) -> Optional[int]:
        """Localiza um CT-e importado via Excel pela chave natural do negócio.

        Independe da `chave` sintética (que inclui o índice da linha), para
        encontrar também registros importados em execuções anteriores:
          - Se houver número de CT-e, casa por CTeModel.numero == cte.
          - Caso contrário, casa pela NF gravada no registro-filho NFeModel.numero.
        Retorna o id do CT-e existente ou None. Restrito a origem EXCEL para não
        afetar registros vindos de XML.
        """
        base = select(CTeModel.id).where(
            CTeModel.empresa_id == empresa_id,
            CTeModel.origem_importacao == "EXCEL",
        )
        cte = (cte or "").strip()
        if cte:
            stmt = base.where(CTeModel.numero == cte)
        else:
            nf = (nota_fiscal or "").strip()
            if not nf:
                return None
            sub = select(NFeModel.cte_id).where(NFeModel.numero == nf)
            stmt = base.where(CTeModel.id.in_(sub))
        return self.db.scalar(stmt.limit(1))

    def atualizar_importacao_excel(self, cte_id: int, e: CTe) -> bool:
        """Atualiza um CT-e de origem Excel SOMENTE com os campos importados,
        preservando o que não vem na planilha. Sincroniza o NF-e filho principal.

        Não altera a `chave` (identidade), nem `origem_importacao`. Distinto do
        método `update` genérico (que cobre apenas transportadora/datas) para não
        interferir em outros fluxos.
        """
        m = self.db.get(CTeModel, cte_id)
        if not m:
            return False
        m.transportadora_id = e.transportadora_id
        m.numero = e.numero
        m.data_emissao = e.data_emissao
        m.peso = e.peso
        m.valor_frete = e.valor_frete
        m.valor_mercadoria = e.valor_mercadoria
        m.municipio_origem = e.municipio_origem
        m.uf_origem = e.uf_origem
        m.municipio_destino = e.municipio_destino
        m.uf_destino = e.uf_destino
        m.macro_regiao_destino = (
            e.macro_regiao_destino.value if e.macro_regiao_destino else None
        )
        m.data_saida = e.data_saida
        m.data_entrega = e.data_entrega
        # Só sobrescreve a composição quando a planilha trouxe componentes,
        # evitando apagar uma composição já existente numa reimportação sem eles.
        if e.composicao_frete:
            m.composicao_frete = e.composicao_frete
        # Sincroniza o NF-e principal (primeiro filho) com os dados da linha.
        nfe_nova = e.nfes[0] if e.nfes else None
        if nfe_nova is not None:
            if m.nfes:
                filho = m.nfes[0]
                filho.numero = nfe_nova.numero
                filho.valor_mercadoria = nfe_nova.valor_mercadoria
                filho.peso = nfe_nova.peso
                filho.municipio_destino = nfe_nova.municipio_destino
            else:
                m.nfes.append(NFeModel(
                    chave=nfe_nova.chave, numero=nfe_nova.numero,
                    valor_mercadoria=nfe_nova.valor_mercadoria, peso=nfe_nova.peso,
                    municipio_destino=nfe_nova.municipio_destino,
                ))
        self.db.commit()
        return True

    # ── Backfill de destinatário/composição (v6.7.0 — DT-27) ──────────────────

    def atualizar_destinatario_e_composicao(
        self,
        empresa_id: int,
        chave: str,
        destinatario_cnpj: str,
        destinatario_nome: str,
        composicao_frete: dict,
    ) -> Optional[bool]:
        """Corrige retroativamente `destinatario_cnpj`/`destinatario_nome` e a
        categorização de `composicao_frete` (RN-68/RN-73) de um CT-e já
        importado ANTES da v6.7.0, sem passar pelo fluxo normal de importação
        (que bloqueia como duplicado por chave, RN-02) e sem criar registro
        novo. Nunca altera peso/valor_frete/valor_mercadoria — só os dois
        campos acima.

        Isolamento multi-tenant: busca por (empresa_id, chave) — um CT-e de
        outra empresa nunca é alcançado, mesmo que a chave (globalmente
        única) exista em outro tenant.

        Retorna ``None`` se o CT-e não existe nessa empresa (nada a corrigir),
        ``True``/``False`` conforme algo tenha mudado — idempotente, pode
        rodar quantas vezes for preciso sobre o mesmo arquivo.
        """
        m = self.db.scalar(
            select(CTeModel).where(
                CTeModel.empresa_id == empresa_id,
                CTeModel.chave == chave,
            )
        )
        if not m:
            return None

        mudou = False
        if destinatario_cnpj and m.destinatario_cnpj != destinatario_cnpj:
            m.destinatario_cnpj = destinatario_cnpj
            mudou = True
        if destinatario_nome and m.destinatario_nome != destinatario_nome:
            m.destinatario_nome = destinatario_nome
            mudou = True
        if composicao_frete and m.composicao_frete != composicao_frete:
            m.composicao_frete = composicao_frete
            mudou = True

        if mudou:
            self.db.commit()
        return mudou

    # ── Gestão de dados importados (RF008/RF010 — exclusão administrativa) ──

    def contar_por_origem(self, empresa_id: int) -> dict:
        """Conta CT-es da empresa separados por origem (XML / EXCEL)."""
        from sqlalchemy import func
        rows = self.db.execute(
            select(CTeModel.origem_importacao, func.count(CTeModel.id))
            .where(CTeModel.empresa_id == empresa_id)
            .group_by(CTeModel.origem_importacao)
        ).all()
        por_origem = {origem: int(qtd) for origem, qtd in rows}
        xml = por_origem.get("XML", 0)
        excel = por_origem.get("EXCEL", 0)
        return {"total": xml + excel + sum(
            v for k, v in por_origem.items() if k not in ("XML", "EXCEL")
        ), "xml": xml, "excel": excel}

    # ── Cancelamento de CT-e (MELHORIA 1) ────────────────────────────────────

    def get_model_by_chave_empresa(self, chave: str, empresa_id: int):
        """Retorna o CTeModel (não a entidade) pela chave, no escopo da empresa."""
        return self.db.scalar(
            select(CTeModel).where(
                CTeModel.chave == chave,
                CTeModel.empresa_id == empresa_id,
            )
        )

    def cancelar_cte(
        self, cte_id: int, data_cancelamento, protocolo: str, numero_evento: str
    ) -> bool:
        """Marca um CT-e como CANCELADO e grava os dados do evento.

        Idempotente na perspectiva de status: chamar novamente apenas atualiza
        os metadados do cancelamento. Não faz commit — o caller controla a
        transação (permite processar um lote com um único commit).
        """
        m = self.db.get(CTeModel, cte_id)
        if not m:
            return False
        m.status = CTE_STATUS_CANCELADO
        m.cancelado_em = data_cancelamento
        m.protocolo_cancelamento = protocolo or ""
        m.numero_evento_cancelamento = numero_evento or ""
        return True

    def registrar_ocorrencia_cancelamento(self, **kwargs) -> None:
        """Insere uma linha no log de eventos de cancelamento (sem commit)."""
        self.db.add(CteCancelamentoModel(**kwargs))

    def existe_evento_cancelamento(
        self, empresa_id: int, chave: str, numero_evento: str
    ) -> bool:
        """True se o evento (empresa+chave+nSeqEvento) já foi importado."""
        return self.db.scalar(
            select(CteCancelamentoModel.id).where(
                CteCancelamentoModel.empresa_id == empresa_id,
                CteCancelamentoModel.chave == chave,
                CteCancelamentoModel.numero_evento == numero_evento,
                CteCancelamentoModel.resultado == "CANCELADO",
            ).limit(1)
        ) is not None

    def commit(self) -> None:
        self.db.commit()

    def listar_ocorrencias_cancelamento(
        self, empresa_id: int, limit: int = 500
    ) -> list["CteCancelamentoModel"]:
        return list(self.db.scalars(
            select(CteCancelamentoModel)
            .where(CteCancelamentoModel.empresa_id == empresa_id)
            .order_by(CteCancelamentoModel.created_at.desc())
            .limit(limit)
        ).all())

    def contar_por_competencia(self, empresa_id: int) -> list[dict]:
        """Conta CT-es da empresa agrupados por competência (mês/ano) da emissão.

        Base do indicador de histórico da tela de importação. Usa agregação
        no banco (GROUP BY por ano/mês da data de emissão), ordenada do mês
        mais recente para o mais antigo. CT-es sem data de emissão são
        ignorados. O ``extract`` do SQLAlchemy é compatível com PostgreSQL
        (EXTRACT nativo) e com SQLite (via strftime), mantendo o mesmo
        comportamento em produção e nos testes.
        """
        from sqlalchemy import case, extract, func

        ano = extract("year", CTeModel.data_emissao)
        mes = extract("month", CTeModel.data_emissao)
        # Cancelados/ativos por competência (MELHORIA 2). Contagem condicional
        # no próprio GROUP BY para não exigir uma segunda consulta.
        cancelados_expr = func.sum(
            case((CTeModel.status == CTE_STATUS_CANCELADO, 1), else_=0)
        )
        rows = self.db.execute(
            select(
                ano.label("ano"), mes.label("mes"),
                func.count(CTeModel.id).label("emitidos"),
                cancelados_expr.label("cancelados"),
            )
            .where(
                CTeModel.empresa_id == empresa_id,
                CTeModel.data_emissao.is_not(None),
            )
            .group_by(ano, mes)
            .order_by(ano.desc(), mes.desc())
        ).all()
        saida = []
        for a, m, emitidos, cancelados in rows:
            emitidos = int(emitidos or 0)
            cancelados = int(cancelados or 0)
            ativos = emitidos - cancelados
            saida.append({
                "ano": int(a),
                "mes": int(m),
                "competencia": f"{int(a):04d}-{int(m):02d}",
                "rotulo": f"{int(m):02d}/{int(a):04d}",
                "quantidade": emitidos,   # compatibilidade: emitidos
                "emitidos": emitidos,
                "ativos": ativos,
                "cancelados": cancelados,
            })
        return saida

    def frete_mensal_ativos(self, empresa_id: int, meses: int = 6) -> list[dict]:
        """Soma o frete e a mercadoria (apenas CT-es ATIVOS) por competência (mês/ano).

        Base das evoluções mensais do dashboard (Frete Total e % Frete/Mercadoria).
        Retorna os últimos ``meses`` em ordem cronológica (mais antigo → mais
        recente). Agregação no banco (GROUP BY ano/mês da emissão), compatível
        com PostgreSQL (EXTRACT nativo) e SQLite (strftime), no mesmo padrão de
        ``contar_por_competencia``. CT-es sem data de emissão são ignorados.
        """
        from sqlalchemy import extract, func

        ano = extract("year", CTeModel.data_emissao)
        mes = extract("month", CTeModel.data_emissao)
        rows = self.db.execute(
            select(
                ano.label("ano"), mes.label("mes"),
                func.sum(CTeModel.valor_frete).label("frete"),
                func.sum(CTeModel.valor_mercadoria).label("mercadoria"),
            )
            .where(
                CTeModel.empresa_id == empresa_id,
                CTeModel.data_emissao.is_not(None),
                CTeModel.status != CTE_STATUS_CANCELADO,
            )
            .group_by(ano, mes)
            .order_by(ano.desc(), mes.desc())
            .limit(meses)
        ).all()
        saida = [
            {
                "competencia": f"{int(a):04d}-{int(m):02d}",
                "frete_total": float(frete or 0.0),
                "frete_pct": float(frete or 0.0) / float(mercadoria) * 100 if mercadoria else 0.0,
            }
            for a, m, frete, mercadoria in rows
        ]
        saida.reverse()  # cronológico: mais antigo → mais recente
        return saida

    def excluir_por_empresa(
        self, empresa_id: int, origem: Optional[str] = None
    ) -> int:
        """Exclui CT-es importados da empresa (e seus NF-es filhos).

        - origem=None  -> exclui todos os CT-es da empresa.
        - origem="XML" -> exclui apenas os importados por XML.
        - origem="EXCEL" -> exclui apenas os importados por planilha.

        Remove explicitamente os NF-es filhos antes (sem deixar órfãos).
        Retorna a quantidade de CT-es excluídos.
        """
        from sqlalchemy import delete as sa_delete

        filtro = [CTeModel.empresa_id == empresa_id]
        if origem:
            filtro.append(CTeModel.origem_importacao == origem)

        ids = [row[0] for row in self.db.execute(
            select(CTeModel.id).where(*filtro)
        ).all()]
        if not ids:
            return 0

        self.db.execute(sa_delete(NFeModel).where(NFeModel.cte_id.in_(ids)))
        self.db.execute(sa_delete(CTeModel).where(CTeModel.id.in_(ids)))
        self.db.commit()
        return len(ids)


def _so_digitos(valor: str) -> str:
    return "".join(c for c in (valor or "") if c.isdigit())


class BenchmarkRepository(IBenchmarkRepository):
    def __init__(self, db: Session):
        self.db = db

    def _kg_do_mercado(self, regiao: str):
        """Benchmark V2 — R$/kg da referência regional vem da matriz de MERCADO
        (benchmark_mercado), agregada por região de destino. NACIONAL agrega todas.
        Retorna (min, medio, max) ou None quando não há dados de mercado (fallback
        para a tabela legada)."""
        from app.infrastructure.database.models import BenchmarkMercadoModel
        stmt = select(BenchmarkMercadoModel)
        r = (regiao or "").strip().upper()
        if r and r != "NACIONAL":
            stmt = stmt.where(BenchmarkMercadoModel.destino_regiao == r)
        rows = self.db.scalars(stmt).all()
        if not rows:
            return None
        def media(attr):
            vals = [getattr(x, attr) for x in rows if getattr(x, attr)]
            return round(sum(vals) / len(vals), 4) if vals else 0.0
        p10, p50, p90 = media("rs_kg_p10"), media("rs_kg_p50"), media("rs_kg_p90")
        if not p50:
            return None
        return (p10 or p50, p50, p90 or p50)

    def _overlay_kg(self, b: Benchmark) -> Benchmark:
        kg = self._kg_do_mercado(b.regiao.value)
        if kg:
            b.frete_kg_min, b.frete_kg_medio, b.frete_kg_max = kg
        return b

    def list(self) -> List[Benchmark]:
        rows = self.db.scalars(select(BenchmarkModel)).all()
        return [self._overlay_kg(mp.benchmark_to_domain(m)) for m in rows]

    def get_by_regiao(self, regiao: str) -> Optional[Benchmark]:
        m = self.db.scalar(
            select(BenchmarkModel).where(BenchmarkModel.regiao == regiao)
        )
        return self._overlay_kg(mp.benchmark_to_domain(m)) if m else None

    def upsert(self, benchmark: Benchmark) -> Benchmark:
        regiao = benchmark.regiao.value
        m = self.db.scalar(
            select(BenchmarkModel).where(BenchmarkModel.regiao == regiao)
        )
        if not m:
            m = BenchmarkModel(regiao=regiao)
            self.db.add(m)
        m.frete_kg_min = benchmark.frete_kg_min
        m.frete_kg_medio = benchmark.frete_kg_medio
        m.frete_kg_max = benchmark.frete_kg_max
        m.frete_pct_min = benchmark.frete_pct_min
        m.frete_pct_medio = benchmark.frete_pct_medio
        m.frete_pct_max = benchmark.frete_pct_max
        self.db.commit(); self.db.refresh(m)
        return mp.benchmark_to_domain(m)


# ══════════ Repositórios Benchmark OD (V2.1) ══════════
from app.domain.entities import BenchmarkCorredor, ClusterCliente, HubLogistico
from app.domain.repositories import (
    IBenchmarkCorredorRepository, IClusterClienteRepository, IHubLogisticoRepository,
)
from app.infrastructure.database.models import (
    BenchmarkCorredorModel, ClusterClienteModel, HubLogisticoModel,
)


class HubLogisticoRepository(IHubLogisticoRepository):
    def __init__(self, db: Session):
        self.db = db

    def list(self, apenas_ativos: bool = False) -> List[HubLogistico]:
        stmt = select(HubLogisticoModel).order_by(HubLogisticoModel.nome)
        if apenas_ativos:
            stmt = stmt.where(HubLogisticoModel.ativo.is_(True))
        return [mp.hub_to_domain(m) for m in self.db.scalars(stmt).all()]

    def get(self, id: int) -> Optional[HubLogistico]:
        m = self.db.get(HubLogisticoModel, id)
        return mp.hub_to_domain(m) if m else None

    def get_by_codigo(self, codigo: str) -> Optional[HubLogistico]:
        m = self.db.scalar(select(HubLogisticoModel).where(HubLogisticoModel.codigo == codigo))
        return mp.hub_to_domain(m) if m else None

    def create(self, hub: HubLogistico) -> HubLogistico:
        m = HubLogisticoModel(
            codigo=hub.codigo, nome=hub.nome, descricao=hub.descricao, ativo=hub.ativo,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.hub_to_domain(m)

    def update(self, id: int, hub: HubLogistico) -> Optional[HubLogistico]:
        m = self.db.get(HubLogisticoModel, id)
        if not m:
            return None
        m.codigo = hub.codigo; m.nome = hub.nome
        m.descricao = hub.descricao; m.ativo = hub.ativo
        self.db.commit(); self.db.refresh(m)
        return mp.hub_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(HubLogisticoModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class ClusterClienteRepository(IClusterClienteRepository):
    def __init__(self, db: Session):
        self.db = db

    def _hub(self, hub_id: int) -> Optional[HubLogisticoModel]:
        return self.db.get(HubLogisticoModel, hub_id)

    def list_by_empresa(self, empresa_id: int) -> List[ClusterCliente]:
        rows = self.db.scalars(
            select(ClusterClienteModel)
            .where(ClusterClienteModel.empresa_id == empresa_id)
            .order_by(ClusterClienteModel.uf, ClusterClienteModel.municipio)
        ).all()
        return [mp.cluster_to_domain(m, self._hub(m.hub_id)) for m in rows]

    def get(self, id: int) -> Optional[ClusterCliente]:
        m = self.db.get(ClusterClienteModel, id)
        return mp.cluster_to_domain(m, self._hub(m.hub_id)) if m else None

    def create(self, cluster: ClusterCliente) -> ClusterCliente:
        m = ClusterClienteModel(
            empresa_id=cluster.empresa_id, uf=(cluster.uf or "").upper(),
            municipio=cluster.municipio or "", hub_id=cluster.hub_id,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp.cluster_to_domain(m, self._hub(m.hub_id))

    def update(self, id: int, cluster: ClusterCliente) -> Optional[ClusterCliente]:
        m = self.db.get(ClusterClienteModel, id)
        if not m:
            return None
        m.uf = (cluster.uf or "").upper()
        m.municipio = cluster.municipio or ""
        m.hub_id = cluster.hub_id
        self.db.commit(); self.db.refresh(m)
        return mp.cluster_to_domain(m, self._hub(m.hub_id))

    def delete(self, id: int) -> bool:
        m = self.db.get(ClusterClienteModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


class BenchmarkCorredorRepository(IBenchmarkCorredorRepository):
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[BenchmarkCorredor]:
        rows = self.db.scalars(select(BenchmarkCorredorModel)).all()
        return [mp.benchmark_corredor_to_domain(m) for m in rows]

    def get(self, id: int) -> Optional[BenchmarkCorredor]:
        m = self.db.get(BenchmarkCorredorModel, id)
        return mp.benchmark_corredor_to_domain(m) if m else None

    def get_by_corredor(self, hub_origem: str, hub_destino: str) -> Optional[BenchmarkCorredor]:
        m = self.db.scalar(
            select(BenchmarkCorredorModel).where(
                BenchmarkCorredorModel.hub_origem_codigo == hub_origem,
                BenchmarkCorredorModel.hub_destino_codigo == hub_destino,
            )
        )
        return mp.benchmark_corredor_to_domain(m) if m else None

    def upsert(self, corredor: BenchmarkCorredor) -> BenchmarkCorredor:
        m = self.db.scalar(
            select(BenchmarkCorredorModel).where(
                BenchmarkCorredorModel.hub_origem_codigo == corredor.hub_origem_codigo,
                BenchmarkCorredorModel.hub_destino_codigo == corredor.hub_destino_codigo,
            )
        )
        if not m:
            m = BenchmarkCorredorModel(
                hub_origem_codigo=corredor.hub_origem_codigo,
                hub_destino_codigo=corredor.hub_destino_codigo,
            )
            self.db.add(m)
        m.frete_kg_min = corredor.frete_kg_min
        m.frete_kg_medio = corredor.frete_kg_medio
        m.frete_kg_max = corredor.frete_kg_max
        m.frete_pct_min = corredor.frete_pct_min
        m.frete_pct_medio = corredor.frete_pct_medio
        m.frete_pct_max = corredor.frete_pct_max
        m.volume_referencia = corredor.volume_referencia
        m.dispersao_kg = corredor.dispersao_kg
        m.observacoes = corredor.observacoes
        self.db.commit(); self.db.refresh(m)
        return mp.benchmark_corredor_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(BenchmarkCorredorModel, id)
        if not m:
            return False
        self.db.delete(m); self.db.commit()
        return True


# ══════════ Repositórios BID (V3.1) ══════════
from app.domain.entities import (
    Bid, BidAuditoria, BidEscopo, BidProposta, BidSimulacao, BidTransportadora,
    BidStatusEnum, BidTransportadoraStatusEnum,
)
from app.domain.repositories import (
    IBidAuditoriaRepository, IBidEscopoRepository, IBidPropostaRepository,
    IBidRepository, IBidSimulacaoRepository, IBidTransportadoraRepository,
)
from app.infrastructure.database.models import (
    BidAuditoriaModel, BidEscopoModel, BidModel,
    BidPropostaModel, BidSimulacaoModel, BidTransportadoraModel,
)
import app.infrastructure.database.repositories.mappers as mp_bid


class BidRepository(IBidRepository):
    def __init__(self, db: Session): self.db = db

    def get(self, id: int) -> Optional[Bid]:
        m = self.db.get(BidModel, id)
        return mp_bid.bid_to_domain(m) if m else None

    def list_by_empresa(self, empresa_id: int) -> List[Bid]:
        rows = self.db.scalars(
            select(BidModel).where(BidModel.empresa_id == empresa_id)
            .order_by(BidModel.created_at.desc())
        ).all()
        return [mp_bid.bid_to_domain(m) for m in rows]

    def create(self, bid: Bid) -> Bid:
        m = BidModel(
            empresa_id=bid.empresa_id, nome=bid.nome, descricao=bid.descricao,
            objetivo=bid.objetivo, observacoes=bid.observacoes,
            status=bid.status.value, data_inicio=bid.data_inicio,
            segmentacao_tipo=bid.segmentacao_tipo or "GERAL",
            segmentacao_valor=bid.segmentacao_valor or "",
            data_encerramento=bid.data_encerramento,
            periodo_analise_inicio=bid.periodo_analise_inicio,
            periodo_analise_fim=bid.periodo_analise_fim,
            created_by=bid.created_by,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_to_domain(m)

    def update(self, id: int, bid: Bid) -> Optional[Bid]:
        m = self.db.get(BidModel, id)
        if not m: return None
        for attr in ("nome", "descricao", "objetivo", "observacoes",
                     "segmentacao_tipo", "segmentacao_valor",
                     "data_inicio", "data_encerramento",
                     "periodo_analise_inicio", "periodo_analise_fim"):
            setattr(m, attr, getattr(bid, attr))
        self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(BidModel, id)
        if not m: return False
        self.db.delete(m); self.db.commit()
        return True

    def update_status(self, id: int, status: BidStatusEnum) -> Optional[Bid]:
        m = self.db.get(BidModel, id)
        if not m: return None
        m.status = status.value
        self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_to_domain(m)


class BidEscopoRepository(IBidEscopoRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_bid(self, bid_id: int) -> List[BidEscopo]:
        rows = self.db.scalars(select(BidEscopoModel).where(BidEscopoModel.bid_id == bid_id)).all()
        return [mp_bid.bid_escopo_to_domain(m) for m in rows]

    def create(self, e: BidEscopo) -> BidEscopo:
        m = BidEscopoModel(
            bid_id=e.bid_id, tipo_agrupamento=e.tipo_agrupamento.value,
            valor_grupo=e.valor_grupo, peso_total=e.peso_total,
            valor_frete_total=e.valor_frete_total, valor_mercadoria_total=e.valor_mercadoria_total,
            qtd_embarques=e.qtd_embarques, frete_rs_kg=e.frete_rs_kg, frete_pct=e.frete_pct,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_escopo_to_domain(m)

    def update(self, id: int, e: BidEscopo) -> Optional[BidEscopo]:
        m = self.db.get(BidEscopoModel, id)
        if not m: return None
        for attr in ("peso_total", "valor_frete_total", "valor_mercadoria_total",
                     "qtd_embarques", "frete_rs_kg", "frete_pct"):
            setattr(m, attr, getattr(e, attr))
        self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_escopo_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(BidEscopoModel, id)
        if not m: return False
        self.db.delete(m); self.db.commit()
        return True

    def delete_by_bid(self, bid_id: int) -> int:
        rows = self.db.scalars(select(BidEscopoModel).where(BidEscopoModel.bid_id == bid_id)).all()
        count = len(rows)
        for r in rows: self.db.delete(r)
        self.db.commit()
        return count


class BidTransportadoraRepository(IBidTransportadoraRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_bid(self, bid_id: int) -> List[BidTransportadora]:
        rows = self.db.scalars(select(BidTransportadoraModel).where(BidTransportadoraModel.bid_id == bid_id)).all()
        return [mp_bid.bid_transportadora_to_domain(m) for m in rows]

    def get(self, id: int) -> Optional[BidTransportadora]:
        m = self.db.get(BidTransportadoraModel, id)
        return mp_bid.bid_transportadora_to_domain(m) if m else None

    def create(self, bt: BidTransportadora) -> BidTransportadora:
        m = BidTransportadoraModel(
            bid_id=bt.bid_id, transportadora_id=bt.transportadora_id,
            status=bt.status.value, observacoes=bt.observacoes or "",
            avaliacao_usuario=bt.avaliacao_usuario,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_transportadora_to_domain(m)

    def update(self, id: int, bt: BidTransportadora) -> Optional[BidTransportadora]:
        m = self.db.get(BidTransportadoraModel, id)
        if not m: return None
        m.observacoes = bt.observacoes or ""
        m.avaliacao_usuario = bt.avaliacao_usuario
        self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_transportadora_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(BidTransportadoraModel, id)
        if not m: return False
        self.db.delete(m); self.db.commit()
        return True

    def update_status(self, id: int, status: BidTransportadoraStatusEnum) -> Optional[BidTransportadora]:
        m = self.db.get(BidTransportadoraModel, id)
        if not m: return None
        m.status = status.value
        self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_transportadora_to_domain(m)


class BidPropostaRepository(IBidPropostaRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_bid(self, bid_id: int) -> List[BidProposta]:
        rows = self.db.scalars(select(BidPropostaModel).where(
            BidPropostaModel.bid_id == bid_id,
            BidPropostaModel.deleted.is_(False),
        )).all()
        return [mp_bid.bid_proposta_to_domain(m) for m in rows]

    def list_by_bid_transportadora(self, bid_transportadora_id: int) -> List[BidProposta]:
        rows = self.db.scalars(
            select(BidPropostaModel).where(
                BidPropostaModel.bid_transportadora_id == bid_transportadora_id,
                BidPropostaModel.deleted.is_(False),
            )
        ).all()
        return [mp_bid.bid_proposta_to_domain(m) for m in rows]

    def create(self, p: BidProposta) -> BidProposta:
        m = BidPropostaModel(
            bid_id=p.bid_id, bid_transportadora_id=p.bid_transportadora_id,
            tipo_agrupamento=p.tipo_agrupamento.value, valor_grupo=p.valor_grupo,
            valor_rs_kg=p.valor_rs_kg, valor_minimo=p.valor_minimo,
            prazo_dias=p.prazo_dias, cobertura_pct=p.cobertura_pct,
            observacoes=p.observacoes or "", origem=p.origem.value,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_proposta_to_domain(m)

    def bulk_create(self, propostas: List[BidProposta]) -> int:
        for p in propostas:
            m = BidPropostaModel(
                bid_id=p.bid_id, bid_transportadora_id=p.bid_transportadora_id,
                tipo_agrupamento=p.tipo_agrupamento.value, valor_grupo=p.valor_grupo,
                valor_rs_kg=p.valor_rs_kg, valor_minimo=p.valor_minimo,
                prazo_dias=p.prazo_dias, cobertura_pct=p.cobertura_pct,
                observacoes=p.observacoes or "", origem=p.origem.value,
            )
            self.db.add(m)
        self.db.commit()
        return len(propostas)

    def delete(self, id: int) -> bool:
        m = self.db.get(BidPropostaModel, id)
        if not m or m.deleted:
            return False
        m.deleted = True  # soft delete — preserva histórico/auditoria
        self.db.commit()
        return True

    def delete_by_bid(self, bid_id: int) -> int:
        rows = self.db.scalars(select(BidPropostaModel).where(BidPropostaModel.bid_id == bid_id)).all()
        count = len(rows)
        for r in rows: self.db.delete(r)
        self.db.commit()
        return count


class BidSimulacaoRepository(IBidSimulacaoRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_bid(self, bid_id: int) -> List[BidSimulacao]:
        rows = self.db.scalars(select(BidSimulacaoModel).where(BidSimulacaoModel.bid_id == bid_id)).all()
        return [mp_bid.bid_simulacao_to_domain(m) for m in rows]

    def get(self, id: int) -> Optional[BidSimulacao]:
        m = self.db.get(BidSimulacaoModel, id)
        return mp_bid.bid_simulacao_to_domain(m) if m else None

    def create(self, s: BidSimulacao) -> BidSimulacao:
        m = BidSimulacaoModel(
            bid_id=s.bid_id, nome=s.nome, descricao=s.descricao or "",
            itens=s.itens, custo_atual=s.custo_atual, custo_proposto=s.custo_proposto,
            economia_total=s.economia_total, reducao_pct=s.reducao_pct,
        )
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_simulacao_to_domain(m)

    def delete(self, id: int) -> bool:
        m = self.db.get(BidSimulacaoModel, id)
        if not m: return False
        self.db.delete(m); self.db.commit()
        return True


class BidAuditoriaRepository(IBidAuditoriaRepository):
    def __init__(self, db: Session): self.db = db

    def list_by_bid(self, bid_id: int) -> List[BidAuditoria]:
        rows = self.db.scalars(
            select(BidAuditoriaModel).where(BidAuditoriaModel.bid_id == bid_id)
            .order_by(BidAuditoriaModel.created_at.desc())
        ).all()
        return [mp_bid.bid_auditoria_to_domain(m) for m in rows]

    def registrar(self, a: BidAuditoria) -> BidAuditoria:
        m = BidAuditoriaModel(bid_id=a.bid_id, user_id=a.user_id, acao=a.acao, detalhe=a.detalhe)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return mp_bid.bid_auditoria_to_domain(m)


# ════════════════════════════════════════════════════════════════
# MELHORIA 8 — Repositório de Recomendações consolidadas
# ════════════════════════════════════════════════════════════════

class RecomendacaoRepository:
    """Persistência das recomendações consolidadas dos indicadores.

    Trabalha diretamente com o RecomendacaoModel (não há entidade de domínio
    dedicada — o modelo já é simples e estável). O upsert é feito pela chave
    natural (empresa_id, indicador, chave_origem), preservando o `status`
    definido pelo usuário quando a recomendação é reconsolidada.
    """

    def __init__(self, db: Session):
        self.db = db

    def listar(self, empresa_id: int, prioridade: Optional[str] = None,
               status: Optional[str] = None) -> List["RecomendacaoModel"]:
        from sqlalchemy import case
        from app.infrastructure.database.models import RecomendacaoModel
        # Ordena por severidade da prioridade e depois pela economia estimada.
        ordem = case(
            (RecomendacaoModel.prioridade == "CRITICA", 0),
            (RecomendacaoModel.prioridade == "ALTA", 1),
            (RecomendacaoModel.prioridade == "MEDIA", 2),
            (RecomendacaoModel.prioridade == "BAIXA", 3),
            else_=4,
        )
        stmt = select(RecomendacaoModel).where(
            RecomendacaoModel.empresa_id == empresa_id
        )
        if prioridade:
            stmt = stmt.where(RecomendacaoModel.prioridade == prioridade.upper())
        if status:
            stmt = stmt.where(RecomendacaoModel.status == status.upper())
        stmt = stmt.order_by(ordem, RecomendacaoModel.economia_estimada.desc())
        return list(self.db.scalars(stmt).all())

    def upsert(self, empresa_id: int, indicador: str, chave_origem: str,
               **campos) -> "RecomendacaoModel":
        """Cria ou atualiza uma recomendação pela chave natural. Preserva o
        `status` já existente (não sobrescreve decisão do usuário)."""
        from app.infrastructure.database.models import RecomendacaoModel
        m = self.db.scalar(
            select(RecomendacaoModel).where(
                RecomendacaoModel.empresa_id == empresa_id,
                RecomendacaoModel.indicador == indicador,
                RecomendacaoModel.chave_origem == chave_origem,
            )
        )
        if m is None:
            m = RecomendacaoModel(
                empresa_id=empresa_id, indicador=indicador, chave_origem=chave_origem
            )
            self.db.add(m)
        for k, v in campos.items():
            setattr(m, k, v)
        return m

    def atualizar_status(self, rec_id: int, empresa_id: int, status: str) -> bool:
        from app.infrastructure.database.models import RecomendacaoModel
        m = self.db.scalar(
            select(RecomendacaoModel).where(
                RecomendacaoModel.id == rec_id,
                RecomendacaoModel.empresa_id == empresa_id,
            )
        )
        if not m:
            return False
        m.status = status.upper()
        self.db.commit()
        return True

    def remover_orfas(self, empresa_id: int, origem: str,
                      chaves_vigentes: set) -> int:
        """Remove recomendações de REGRA que não foram reconfirmadas na última
        consolidação (deixaram de existir). Não toca em recomendações de IA nem
        nas que o usuário marcou como concluídas/descartadas."""
        from app.infrastructure.database.models import RecomendacaoModel
        alvo = self.db.scalars(
            select(RecomendacaoModel).where(
                RecomendacaoModel.empresa_id == empresa_id,
                RecomendacaoModel.origem == origem,
                RecomendacaoModel.status == "ABERTA",
            )
        ).all()
        removidas = 0
        for m in alvo:
            if (m.indicador, m.chave_origem) not in chaves_vigentes:
                self.db.delete(m)
                removidas += 1
        return removidas

    def commit(self) -> None:
        self.db.commit()
