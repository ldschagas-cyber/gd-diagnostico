"""Caso de uso principal do módulo BID — gestão do processo de concorrência.

Responsável por: CRUD de BIDs, máquina de estados, registro automático
de auditoria em cada ação relevante.
"""
from datetime import date
from typing import Optional

from app.domain.entities import (
    Bid, BidAuditoria, BidStatusEnum, RoleEnum, User,
)
from app.domain.repositories import IBidAuditoriaRepository, IBidRepository


# Transições de status permitidas
_TRANSICOES = {
    BidStatusEnum.RASCUNHO:    {BidStatusEnum.ABERTO, BidStatusEnum.CANCELADO},
    BidStatusEnum.ABERTO:      {BidStatusEnum.EM_COTACAO, BidStatusEnum.CANCELADO},
    BidStatusEnum.EM_COTACAO:  {BidStatusEnum.ENCERRADO, BidStatusEnum.CANCELADO},
    BidStatusEnum.ENCERRADO:   set(),
    BidStatusEnum.CANCELADO:   set(),
}


class BidUseCase:
    def __init__(
        self,
        bid_repo: IBidRepository,
        auditoria_repo: IBidAuditoriaRepository,
    ):
        self.bid_repo = bid_repo
        self.audit = auditoria_repo

    def _log(self, bid_id: int, user_id: Optional[int], acao: str, detalhe: dict = {}):
        self.audit.registrar(BidAuditoria(bid_id=bid_id, user_id=user_id, acao=acao, detalhe=detalhe))

    def criar(self, bid: Bid, user: User) -> Bid:
        bid.created_by = user.id
        criado = self.bid_repo.create(bid)
        self._log(criado.id, user.id, "BID criado", {"nome": criado.nome})
        return criado

    def listar(self, empresa_id: int):
        return self.bid_repo.list_by_empresa(empresa_id)

    def obter(self, bid_id: int) -> Optional[Bid]:
        return self.bid_repo.get(bid_id)

    def atualizar(self, bid_id: int, dados: Bid, user: User) -> Optional[Bid]:
        atual = self.bid_repo.get(bid_id)
        if not atual:
            return None
        if atual.status == BidStatusEnum.ENCERRADO:
            raise ValueError("BID encerrado não pode ser editado.")
        dados.empresa_id = atual.empresa_id
        dados.status = atual.status
        dados.created_by = atual.created_by
        atualizado = self.bid_repo.update(bid_id, dados)
        self._log(bid_id, user.id, "BID atualizado", {"nome": dados.nome})
        return atualizado

    def alterar_status(
        self, bid_id: int, novo_status: BidStatusEnum, user: User
    ) -> Bid:
        bid = self.bid_repo.get(bid_id)
        if not bid:
            raise ValueError("BID não encontrado.")
        permitidos = _TRANSICOES.get(bid.status, set())
        if novo_status not in permitidos:
            raise ValueError(
                f"Transição inválida: {bid.status.value} → {novo_status.value}. "
                f"Permitido: {[s.value for s in permitidos] or 'nenhum'}"
            )
        atualizado = self.bid_repo.update_status(bid_id, novo_status)
        self._log(
            bid_id, user.id,
            f"Status alterado: {bid.status.value} → {novo_status.value}",
        )
        return atualizado

    def deletar(self, bid_id: int, user: User) -> bool:
        bid = self.bid_repo.get(bid_id)
        if not bid:
            return False
        if bid.status == BidStatusEnum.ENCERRADO:
            raise ValueError("BID encerrado não pode ser excluído.")
        ok = self.bid_repo.delete(bid_id)
        if ok:
            self._log(bid_id, user.id, "BID excluído", {"nome": bid.nome})
        return ok
