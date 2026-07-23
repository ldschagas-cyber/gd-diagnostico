"""Caso de uso: registro de Carta de Correção Eletrônica (CCe) de CT-e.

Diferente do cancelamento, a CCe **nunca é aplicada automaticamente** ao
CT-e já importado — apenas registrada no log de auditoria (mesma tabela do
cancelamento, reaproveitada) para que o analista decida manualmente se e como
atualizar o dado. Motivo: a CCe é disciplinada pelo Art. 58-B do Convênio
SINIEF 06/89 e não deveria, por regra, corrigir variáveis que determinam o
valor da prestação (ex.: quantidade/peso de carga) — na prática, porém,
emissores usam a CCe para isso, então o sistema precisa reconhecer o evento
sem confiar cegamente no valor corrigido.

Regras:
- Identificar o CT-e pela chave de acesso (escopo da empresa) — apenas para
  contexto do log (`cte_id`), sem alterar nenhum campo do CT-e.
- Impedir duplicidade de registro do mesmo evento (mesma chave + nº evento).
- CT-e inexistente na base → registrar no log, sem erro fatal.
- Registrar TODAS as ocorrências (auditoria).
"""
from typing import List, Tuple

from app.application.dtos import OcorrenciaCCe, ResultadoCCe
from app.core.logging_config import get_logger
from app.domain.repositories import ICTeRepository
from app.infrastructure.parsers.carta_correcao_parser import parse_carta_correcao_xml

logger = get_logger(__name__)

# Guarda o XML do evento até este tamanho (auditoria) para não inflar a base.
_MAX_XML_ARMAZENADO = 200_000


class CartaCorrecaoCteUseCase:
    def __init__(self, cte_repo: ICTeRepository):
        self.cte_repo = cte_repo

    def importar_eventos(
        self, empresa_id: int, arquivos: List[Tuple[str, bytes]]
    ) -> ResultadoCCe:
        resultado = ResultadoCCe(total_processados=len(arquivos))

        for nome, conteudo in arquivos:
            try:
                evento = parse_carta_correcao_xml(conteudo)
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
            cte_id = cte.id if cte else None

            if self.cte_repo.existe_cce_registrada(
                empresa_id, evento.chave, evento.numero_evento
            ):
                # Não persiste: a constraint uq_cte_cancelamento_evento
                # (empresa_id, chave, numero_evento) permite uma única linha
                # de log por evento — o primeiro registro (CCE_REGISTRADA) já
                # cobre a auditoria. Inserir uma 2ª linha aqui violaria a
                # constraint e derrubaria o lote inteiro com IntegrityError.
                self._registrar(
                    resultado, empresa_id, nome, chave=evento.chave,
                    numero_evento=evento.numero_evento, cte_id=cte_id,
                    resultado_tipo="DUPLICADO",
                    mensagem="Carta de Correção já registrada anteriormente.",
                    tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                    data_cancelamento=evento.data_evento, persistir=False,
                )
                continue

            mensagem_correcoes = "; ".join(str(c) for c in evento.correcoes) or (
                "Carta de Correção sem detalhamento de campo alterado."
            )
            mensagem = (
                "Correção proposta (NÃO aplicada automaticamente — revisão manual "
                f"necessária): {mensagem_correcoes}"
            )[:480]

            if cte is None:
                self._registrar(
                    resultado, empresa_id, nome, chave=evento.chave,
                    numero_evento=evento.numero_evento,
                    resultado_tipo="NAO_ENCONTRADO",
                    mensagem=f"CT-e não localizado na base desta empresa. {mensagem}"[:480],
                    tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                    data_cancelamento=evento.data_evento, xml=conteudo,
                )
                continue

            self._registrar(
                resultado, empresa_id, nome, chave=evento.chave,
                numero_evento=evento.numero_evento, cte_id=cte.id,
                resultado_tipo="REGISTRADA",
                mensagem=mensagem,
                tipo_evento=evento.tipo_evento, protocolo=evento.protocolo,
                data_cancelamento=evento.data_evento, xml=conteudo,
            )

        self.cte_repo.commit()
        logger.info(
            "Carta de Correção empresa=%s: %s registradas, %s duplicadas, "
            "%s não encontradas, %s erros",
            empresa_id, resultado.registradas, resultado.duplicados,
            resultado.nao_encontrados, resultado.erros,
        )
        return resultado

    # ── helpers ───────────────────────────────────────────────────────────────

    def _registrar(
        self, resultado: ResultadoCCe, empresa_id: int, arquivo: str, *,
        chave: str, numero_evento: str, resultado_tipo: str, mensagem: str,
        cte_id=None, tipo_evento: str = "", protocolo: str = "",
        data_cancelamento=None, xml: bytes | None = None, persistir: bool = True,
    ) -> None:
        if resultado_tipo == "REGISTRADA":
            resultado.registradas += 1
        elif resultado_tipo == "DUPLICADO":
            resultado.duplicados += 1
        elif resultado_tipo == "NAO_ENCONTRADO":
            resultado.nao_encontrados += 1
        else:
            resultado.erros += 1

        resultado.ocorrencias.append(OcorrenciaCCe(
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

        # Reaproveita o log de eventos de cancelamento (mesma tabela/estrutura):
        # resultado prefixado "CCE_" distingue as ocorrências de Carta de
        # Correção das de cancelamento na mesma auditoria, sem exigir migration.
        self.cte_repo.registrar_ocorrencia_cancelamento(
            empresa_id=empresa_id, cte_id=cte_id, chave=chave,
            protocolo=protocolo or "", numero_evento=numero_evento or "",
            tipo_evento=tipo_evento or "", data_cancelamento=data_cancelamento,
            resultado=f"CCE_{resultado_tipo}", mensagem=mensagem[:480],
            arquivo=arquivo[:250], xml_evento=xml_txt,
        )
