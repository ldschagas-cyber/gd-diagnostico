"""Backfill de destinatário/composição de frete — v6.7.0 (DT-27).

Corrige retroativamente CT-e importados ANTES do deploy da v6.7.0, que não
têm `destinatario_cnpj`/`destinatario_nome` (dimensão Cliente do DLG, RN-68)
nem a categorização granular de TDE/TDA/Estadia em `composicao_frete`
(RN-73) — ambos escritos pelo parser apenas no momento da importação.

Fora do fluxo normal de importação (RN-02 bloqueia reimportação do mesmo
arquivo como "duplicado", sem atualizar o registro existente): este use case
localiza o CT-e por chave DENTRO da empresa informada e faz UPDATE explícito
só de `destinatario_cnpj`/`destinatario_nome`/`composicao_frete` — nunca cria
CT-e novo, nunca altera peso/valor_frete/valor_mercadoria.

Uso: ver `backend/scripts/backfill_destinatario_v670.py` (CLI). Depois de
rodar, disparar `POST /dlg/{empresa_id}/processar` para o DLG recalcular a
dimensão Cliente com o dado corrigido.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

from app.core.logging_config import get_logger
from app.domain.repositories import ICTeRepository
from app.infrastructure.parsers.cte_parser import parse_cte_xml

logger = get_logger(__name__)


@dataclass
class ResultadoBackfill:
    total_arquivos: int = 0
    atualizados: int = 0
    sem_mudanca: int = 0
    nao_encontrados: int = 0
    erros: List[str] = field(default_factory=list)


class BackfillDestinatarioUseCase:
    def __init__(self, cte_repo: ICTeRepository):
        self.cte_repo = cte_repo

    def executar(self, empresa_id: int, arquivos: List[Tuple[str, bytes]]) -> ResultadoBackfill:
        """``arquivos``: lista de (nome, conteúdo) dos XML ORIGINAIS dos CT-e
        já importados (mesma chave de acesso) — não são arquivos novos."""
        resultado = ResultadoBackfill(total_arquivos=len(arquivos))

        for nome, conteudo in arquivos:
            try:
                parsed = parse_cte_xml(conteudo)
            except Exception as exc:  # noqa: BLE001
                resultado.erros.append(f"{nome}: {exc}")
                continue

            if not parsed.chave:
                resultado.erros.append(f"{nome}: chave do CT-e não encontrada.")
                continue

            mudou = self.cte_repo.atualizar_destinatario_e_composicao(
                empresa_id=empresa_id,
                chave=parsed.chave,
                destinatario_cnpj=parsed.destinatario_cnpj,
                destinatario_nome=parsed.destinatario_nome,
                composicao_frete=parsed.composicao,
            )
            if mudou is None:
                resultado.nao_encontrados += 1
                logger.info(
                    "Backfill destinatário: CT-e %s não encontrado na empresa %s (arquivo %s)",
                    parsed.chave, empresa_id, nome,
                )
            elif mudou:
                resultado.atualizados += 1
            else:
                resultado.sem_mudanca += 1

        logger.info(
            "Backfill destinatário/composição empresa=%s: %s atualizados, %s sem mudança, "
            "%s não encontrados, %s erros",
            empresa_id, resultado.atualizados, resultado.sem_mudanca,
            resultado.nao_encontrados, len(resultado.erros),
        )
        return resultado
