"""Parser do XML de evento de cancelamento de CT-e (MELHORIA 1).

Extrai os campos necessários para efetivar o cancelamento de um CT-e a partir
do XML oficial do evento (tpEvento 110111). Tolerante às variações de namespace
e à presença (ou não) do envelope de processamento (procEventoCTe) e do retorno
da SEFAZ (retEventoCTe).

Estrutura típica:
    <procEventoCTe>
      <eventoCTe>
        <infEvento Id="ID110111...">
          <chCTe>...44 dígitos...</chCTe>
          <dhEvento>2025-03-15T10:00:00-03:00</dhEvento>
          <tpEvento>110111</tpEvento>
          <nSeqEvento>1</nSeqEvento>
          <detEvento><evCancCTe><nProt>...</nProt></evCancCTe></detEvento>
        </infEvento>
      </eventoCTe>
      <retEventoCTe><infEvento>
          <nProt>...</nProt><dhRegEvento>...</dhRegEvento><cStat>135</cStat>
      </infEvento></retEventoCTe>
    </procEventoCTe>
"""
from datetime import date
from typing import Optional

import defusedxml.ElementTree as ET

from app.core.logging_config import get_logger
from app.infrastructure.parsers.cte_parser import _parse_data

logger = get_logger(__name__)

NS = {"cte": "http://www.portalfiscal.inf.br/cte"}

# tpEvento de cancelamento de CT-e (Manual de Eventos do CT-e).
TP_EVENTO_CANCELAMENTO = "110111"

# cStat de homologação de cancelamento consideradas "efetivadas".
CSTAT_CANCELAMENTO_OK = {"101", "135", "155"}


class EventoCancelamentoResult:
    def __init__(self):
        self.chave: str = ""
        self.tipo_evento: str = ""
        self.numero_evento: str = ""
        self.protocolo: str = ""
        self.data_evento: Optional[date] = None
        self.c_stat: str = ""
        self.homologado: bool = True  # True se não houver retorno OU cStat de sucesso


def _text(el, path: str, default: str = "") -> str:
    node = el.find(path, NS) if el is not None else None
    return node.text.strip() if node is not None and node.text else default


def parse_evento_cancelamento_xml(xml_bytes: bytes) -> EventoCancelamentoResult:
    """Recebe o XML bruto de um evento de cancelamento e devolve os campos.

    Levanta ValueError quando o XML não é um evento de cancelamento de CT-e.
    """
    root = ET.fromstring(xml_bytes)

    inf = root.find(".//cte:eventoCTe/cte:infEvento", NS)
    if inf is None:
        inf = root.find(".//cte:infEvento", NS)
    if inf is None:
        raise ValueError("XML não contém infEvento — não é um evento de CT-e válido.")

    result = EventoCancelamentoResult()
    result.tipo_evento = _text(inf, "cte:tpEvento")
    if result.tipo_evento and result.tipo_evento != TP_EVENTO_CANCELAMENTO:
        raise ValueError(
            f"Evento tpEvento={result.tipo_evento} não é cancelamento "
            f"(esperado {TP_EVENTO_CANCELAMENTO})."
        )

    result.chave = "".join(c for c in _text(inf, "cte:chCTe") if c.isdigit())
    result.numero_evento = _text(inf, "cte:nSeqEvento") or "1"
    result.data_evento = _parse_data(_text(inf, "cte:dhEvento"))

    # Protocolo do cancelamento: preferir o nProt de dentro do evento (evCancCTe).
    prot = inf.find(".//cte:detEvento//cte:nProt", NS)
    if prot is not None and prot.text:
        result.protocolo = prot.text.strip()

    # Retorno da SEFAZ (quando presente): protocolo/data/homologação oficiais.
    ret = root.find(".//cte:retEventoCTe/cte:infEvento", NS)
    if ret is not None:
        ret_prot = _text(ret, "cte:nProt")
        if ret_prot:
            result.protocolo = ret_prot
        result.c_stat = _text(ret, "cte:cStat")
        data_reg = _parse_data(_text(ret, "cte:dhRegEvento"))
        if data_reg:
            result.data_evento = data_reg
        if result.c_stat:
            result.homologado = result.c_stat in CSTAT_CANCELAMENTO_OK

    if not result.chave:
        raise ValueError("Evento de cancelamento sem chave de acesso do CT-e (chCTe).")

    return result
