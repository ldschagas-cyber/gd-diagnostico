"""Parser do XML de Carta de Correção Eletrônica de CT-e (CCe, tpEvento 110110).

Extrai os campos da CCe para fins de **registro em log/auditoria** — este
parser não decide nem executa nenhuma alteração no CT-e já importado. A CCe é
disciplinada pelo Art. 58-B do Convênio SINIEF 06/89 e não pode, por regra,
corrigir variáveis que determinam o valor do imposto/prestação (base de
cálculo, alíquota, quantidade, valor da prestação) nem dados cadastrais de
emitente/tomador/remetente/destinatário — por isso as correções propostas são
apenas registradas para revisão manual do analista, nunca aplicadas
automaticamente (ver `CartaCorrecaoCteUseCase`).

Estrutura típica:
    <procEventoCTe>
      <eventoCTe>
        <infEvento Id="ID11011026250121612496000124570000001174851036952142001">
          <chCTe>...44 dígitos...</chCTe>
          <dhEvento>2025-01-31T20:47:25-03:00</dhEvento>
          <tpEvento>110110</tpEvento>
          <nSeqEvento>1</nSeqEvento>
          <detEvento>
            <evCCeCTe>
              <infCorrecao>
                <grupoAlterado>infQ</grupoAlterado>
                <campoAlterado>qCarga</campoAlterado>
                <valorAlterado>3.0000</valorAlterado>
                <nroItemAlterado>02</nroItemAlterado>
              </infCorrecao>
              <!-- pode haver mais de um infCorrecao no mesmo evento -->
            </evCCeCTe>
          </detEvento>
        </infEvento>
      </eventoCTe>
      <retEventoCTe><infEvento>
          <nProt>...</nProt><dhRegEvento>...</dhRegEvento><cStat>135</cStat>
      </infEvento></retEventoCTe>
    </procEventoCTe>
"""
from datetime import date
from typing import List, Optional

import defusedxml.ElementTree as ET

from app.core.logging_config import get_logger
from app.infrastructure.parsers.cte_parser import _parse_data

logger = get_logger(__name__)

NS = {"cte": "http://www.portalfiscal.inf.br/cte"}

# tpEvento de Carta de Correção de CT-e (Manual de Eventos do CT-e).
TP_EVENTO_CCE = "110110"

# cStat de homologação de CCe consideradas "efetivadas" (mesmos códigos do cancelamento).
CSTAT_CCE_OK = {"101", "135", "155"}


class CorrecaoCCe:
    def __init__(self, grupo: str, campo: str, valor: str, item: str = ""):
        self.grupo = grupo
        self.campo = campo
        self.valor = valor
        self.item = item

    def __str__(self) -> str:
        alvo = f"{self.grupo}.{self.campo}"
        if self.item:
            alvo += f" (item {self.item})"
        return f"{alvo}: {self.valor}"


class CartaCorrecaoResult:
    def __init__(self):
        self.chave: str = ""
        self.tipo_evento: str = ""
        self.numero_evento: str = ""
        self.protocolo: str = ""
        self.data_evento: Optional[date] = None
        self.c_stat: str = ""
        self.homologado: bool = True  # True se não houver retorno OU cStat de sucesso
        self.correcoes: List[CorrecaoCCe] = []


def _text(el, path: str, default: str = "") -> str:
    node = el.find(path, NS) if el is not None else None
    return node.text.strip() if node is not None and node.text else default


def parse_carta_correcao_xml(xml_bytes: bytes) -> CartaCorrecaoResult:
    """Recebe o XML bruto de uma CCe e devolve os campos para registro em log.

    Levanta ValueError quando o XML não é uma Carta de Correção de CT-e.
    """
    root = ET.fromstring(xml_bytes)

    inf = root.find(".//cte:eventoCTe/cte:infEvento", NS)
    if inf is None:
        inf = root.find(".//cte:infEvento", NS)
    if inf is None:
        raise ValueError("XML não contém infEvento — não é um evento de CT-e válido.")

    result = CartaCorrecaoResult()
    result.tipo_evento = _text(inf, "cte:tpEvento")
    if result.tipo_evento and result.tipo_evento != TP_EVENTO_CCE:
        raise ValueError(
            f"Evento tpEvento={result.tipo_evento} não é Carta de Correção "
            f"(esperado {TP_EVENTO_CCE})."
        )

    result.chave = "".join(c for c in _text(inf, "cte:chCTe") if c.isdigit())
    result.numero_evento = _text(inf, "cte:nSeqEvento") or "1"
    result.data_evento = _parse_data(_text(inf, "cte:dhEvento"))

    for correcao in inf.findall(".//cte:infCorrecao", NS):
        grupo = _text(correcao, "cte:grupoAlterado")
        campo = _text(correcao, "cte:campoAlterado")
        valor = _text(correcao, "cte:valorAlterado")
        item = _text(correcao, "cte:nroItemAlterado")
        if grupo or campo:
            result.correcoes.append(CorrecaoCCe(grupo, campo, valor, item))

    # Retorno da SEFAZ (quando presente): protocolo/data/homologação oficiais.
    ret = root.find(".//cte:retEventoCTe/cte:infEvento", NS)
    if ret is not None:
        prot = _text(ret, "cte:nProt")
        if prot:
            result.protocolo = prot
        result.c_stat = _text(ret, "cte:cStat")
        data_reg = _parse_data(_text(ret, "cte:dhRegEvento"))
        if data_reg:
            result.data_evento = data_reg
        if result.c_stat:
            result.homologado = result.c_stat in CSTAT_CCE_OK

    if not result.chave:
        raise ValueError("Carta de Correção sem chave de acesso do CT-e (chCTe).")

    return result
