"""Caso de uso: importação de eventos de cancelamento de CT-e (MELHORIA 1).

Regras:
- Identificar o CT-e pela chave de acesso (escopo da empresa).
- Atualizar o status do CT-e para CANCELADO, gravando data, protocolo e nº do evento.
- Impedir duplicidade de importação (mesmo evento ou CT-e já cancelado).
- CT-e inexistente na base → registrar no log, sem erro fatal.
- Registrar TODAS as ocorrências (auditoria).
"""
from typing import List, Tuple

from app.application.dtos import OcorrenciaCancelamento, ResultadoCancelamento
from app.core.logging_config import get_logger
from app.domain.repositories import ICTeRepository
from app.infrastructure.parsers.evento_cancelamento_parser import (
    parse_evento_cancelamento_xml,
)

logger = get_logger(__name__)

# Guarda o XML do evento até este tamanho (auditoria) para não inflar a base.
_MAX_XML_ARMAZENADO = 200_000


class CancelamentoCteUseCase:
    def __init__(self, cte_repo: ICTeRepository):
        self.cte_repo = cte_repo

    def importar_eventos(
        self, empresa_id: int, arquivos: List[Tuple[str, bytes]]
    ) -> ResultadoCancelamento:
        resultado = ResultadoCancelamento(total_processados=len(arquivos))

        for nome, conteudo in arquivos:
            try:
                evento = parse_evento_cancelamento_xml(conteudo)
            except Exception as exc:  # noqa: BLE001
                self._registrar(
                    resultado, empresa_id, nome, chave="", numero_evento="",
                    resultado_tipo="ERRO", mensagem=str(exc)[:480],
                )
                continue

            if not evento.homologado:
                self._registrar(
                    resultado, empresa_id, nome, chave=evento.chave,
                    numero_evento=evento.numero_evento, resultado_tipo="ERRO",
                    mensagem=f"Evento não homologado pela SEFAZ (cStat={evento.c_stat}).",
                    tipo_evento=evento.tipo_evento,
                )
                continue

            cte = self.cte_repo.get_model_by_chave_empresa(evento.chave, empresa_id)

            if cte is None:
                self._registrar(
                    resultado, empresa_id, nome, chave=evento.chave,
                    numero_evento=evento.numero_evento,
                    resultado_tipo="CTE_NAO_ENCONTRADO",
                    mensagem="CT-e não localizado na base desta empresa.",
                    tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                    data_cancelamento=evento.data_evento,
                    xml=conteudo,
                )
                continue

            ja_cancelado = getattr(cte, "status", "ATIVO") == "CANCELADO"
            evento_repetido = self.cte_repo.existe_evento_cancelamento(
                empresa_id, evento.chave, evento.numero_evento
            )
            if ja_cancelado or evento_repetido:
                # Não persiste: a constraint uq_cte_cancelamento_evento
                # (empresa_id, chave, numero_evento) já garante uma única linha
                # de log por evento — a primeira importação (CANCELADO) já
                # cobre a auditoria. Inserir uma 2ª linha aqui violaria a
                # constraint e derrubaria o lote inteiro com IntegrityError.
                self._registrar(
                    resultado, empresa_id, nome, chave=evento.chave,
                    numero_evento=evento.numero_evento, cte_id=cte.id,
                    resultado_tipo="DUPLICADO",
                    mensagem="CT-e já cancelado ou evento já importado.",
                    tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                    data_cancelamento=evento.data_evento, persistir=False,
                )
                continue

            self.cte_repo.cancelar_cte(
                cte.id, evento.data_evento, evento.protocolo, evento.numero_evento
            )
            self._registrar(
                resultado, empresa_id, nome, chave=evento.chave,
                numero_evento=evento.numero_evento, cte_id=cte.id,
                resultado_tipo="CANCELADO",
                mensagem="CT-e cancelado com sucesso.",
                tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                data_cancelamento=evento.data_evento, xml=conteudo,
            )

        self.cte_repo.commit()
        logger.info(
            "Cancelamento empresa=%s: %s cancelados, %s duplicados, "
            "%s não encontrados, %s erros",
            empresa_id, resultado.cancelados, resultado.duplicados,
            resultado.nao_encontrados, resultado.erros,
        )
        return resultado

    # ── helpers ───────────────────────────────────────────────────────────────

    def _registrar(
        self, resultado: ResultadoCancelamento, empresa_id: int, arquivo: str, *,
        chave: str, numero_evento: str, resultado_tipo: str, mensagem: str,
        cte_id=None, tipo_evento: str = "", protocolo: str = "",
        data_cancelamento=None, xml: bytes | None = None, persistir: bool = True,
    ) -> None:
        if resultado_tipo == "CANCELADO":
            resultado.cancelados += 1
        elif resultado_tipo == "DUPLICADO":
            resultado.duplicados += 1
        elif resultado_tipo == "CTE_NAO_ENCONTRADO":
            resultado.nao_encontrados += 1
        else:
            resultado.erros += 1

        resultado.ocorrencias.append(OcorrenciaCancelamento(
            arquivo=arquivo, chave=chave,
            resultado=resultado_tipo, mensagem=mensagem,
        ))

        if not persistir:
            return

        xml_txt = None
        if xml is not None and len(xml) <= _MAX_XML_ARMAZENADO:
            try:
                xml_txt = xml.decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                xml_txt = None

        self.cte_repo.registrar_ocorrencia_cancelamento(
            empresa_id=empresa_id, cte_id=cte_id, chave=chave,
            protocolo=protocolo or "", numero_evento=numero_evento or "",
            tipo_evento=tipo_evento or "", data_cancelamento=data_cancelamento,
            resultado=resultado_tipo, mensagem=mensagem[:480],
            arquivo=arquivo[:250], xml_evento=xml_txt,
        )
