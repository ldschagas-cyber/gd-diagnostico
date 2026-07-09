"""Parser de CT-e (Conhecimento de Transporte eletrônico) a partir do XML SEFAZ.

Extrai os campos exigidos pelo RF008. Tolerante a variações de namespace e
à presença (ou não) do envelope de protocolo (cteProc).
"""
from datetime import date, datetime
from typing import List, Optional
# defusedxml previne XML Bomb, Billion Laughs e Entity Expansion attacks.
# Substituição do stdlib ElementTree é a única mudança necessária — API idêntica.
import defusedxml.ElementTree as ET

from app.core.logging_config import get_logger

logger = get_logger(__name__)

NS = {"cte": "http://www.portalfiscal.inf.br/cte"}


class CTeParseResult:
    def __init__(self):
        self.chave: str = ""
        self.numero: str = ""
        self.serie: str = ""
        self.data_emissao: Optional[date] = None
        self.tomador_cnpj: str = ""
        self.destinatario_cnpj: str = ""
        self.destinatario_nome: str = ""
        self.transportadora_cnpj: str = ""
        self.transportadora_nome: str = ""
        self.peso: float = 0.0
        self.valor_frete: float = 0.0
        self.valor_mercadoria: float = 0.0
        self.composicao: dict = {}
        self.municipio_origem: str = ""
        self.uf_origem: str = ""
        self.municipio_destino: str = ""
        self.uf_destino: str = ""
        self.chaves_nfe: List[str] = []


def _find(el, path: str):
    return el.find(path, NS)


def _text(el, path: str, default: str = "") -> str:
    node = el.find(path, NS) if el is not None else None
    return node.text.strip() if node is not None and node.text else default


def _float(el, path: str, default: float = 0.0) -> float:
    raw = _text(el, path)
    if not raw:
        return default
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return default


def _parse_data(raw: str) -> Optional[date]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19] if "T" in raw else raw, fmt).date()
        except ValueError:
            continue
    # ISO com timezone (ex: 2024-01-15T10:00:00-03:00)
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def parse_cte_xml(xml_bytes: bytes) -> CTeParseResult:
    """Recebe o conteúdo bruto de um XML de CT-e e devolve os campos extraídos."""
    root = ET.fromstring(xml_bytes)

    # Localiza o nó <infCte> independentemente de envelope (cteProc/CTe).
    inf = root.find(".//cte:infCte", NS)
    if inf is None:
        raise ValueError("XML não contém infCte — não parece um CT-e válido.")

    result = CTeParseResult()

    # Chave: atributo Id do infCte (formato 'CTe' + 44 dígitos)
    raw_id = inf.get("Id", "")
    result.chave = "".join(c for c in raw_id if c.isdigit())

    ide = _find(inf, "cte:ide")
    if ide is not None:
        result.numero = _text(ide, "cte:nCT")
        result.serie = _text(ide, "cte:serie")
        result.data_emissao = _parse_data(_text(ide, "cte:dhEmi"))
        result.municipio_origem = _text(ide, "cte:xMunIni")
        result.uf_origem = _text(ide, "cte:UFIni")
        result.municipio_destino = _text(ide, "cte:xMunFim")
        result.uf_destino = _text(ide, "cte:UFFim")

    # Emitente = transportadora
    emit = _find(inf, "cte:emit")
    if emit is not None:
        result.transportadora_cnpj = _so_digitos(_text(emit, "cte:CNPJ"))
        result.transportadora_nome = _text(emit, "cte:xNome") or _text(emit, "cte:xFant")

    # Tomador do serviço (RF008): pode estar em toma3/toma4
    result.tomador_cnpj = _extrair_tomador(inf)

    # Destinatário da mercadoria (v6.7.0 — dimensão CLIENTE_FINAL do DLG).
    # Independente do tomador: o destinatário é sempre <dest>, mesmo quando
    # o tomador do serviço é outro participante (rem/exped/receb).
    result.destinatario_cnpj, result.destinatario_nome = _extrair_destinatario(inf)

    # Valor do frete (vTPrest = valor total da prestação)
    vprest = _find(inf, "cte:vPrest")
    if vprest is not None:
        result.valor_frete = _float(vprest, "cte:vTPrest")
        # Composição do frete: componentes <Comp><xNome>..</xNome><vComp>..</vComp></Comp>
        result.composicao = _extrair_composicao(vprest)

    # Peso: infCarga/infQ com cUnid=01(KG)/tpMed peso
    result.peso = _extrair_peso(inf)

    # Valor da carga/mercadoria (faturamento) — infCarga/vCarga.
    # Busca recursiva: em CT-es reais o infCarga fica dentro de infCTeNorm.
    infcarga = _find(inf, ".//cte:infCarga")
    if infcarga is not None:
        result.valor_mercadoria = _float(infcarga, "cte:vCarga")

    # Chaves das NF-es vinculadas (infCTeNorm/infDoc/infNFe/chave)
    for chave_node in inf.findall(".//cte:infNFe/cte:chave", NS):
        if chave_node.text:
            result.chaves_nfe.append(chave_node.text.strip())

    return result


# Normalização dos nomes de componentes do frete para as categorias do diagnóstico.
_CATEGORIAS_COMP = {
    "FRETE PESO": "Frete Peso",
    "FRETE-PESO": "Frete Peso",
    "PESO": "Frete Peso",
    "FRETE VALOR": "Frete Valor",
    "FRETE-VALOR": "Frete Valor",
    "AD VALOREM": "Frete Valor",
    "ADVALOREM": "Frete Valor",
    "PEDAGIO": "Pedágio",
    "PEDÁGIO": "Pedágio",
    "GRIS": "GRIS",
    "SEGURO": "Seguro",
    "ADEME": "Ademe",
    "DESPACHO": "Despacho",
    "SEC/CAT": "Outros",
    "TDA/TDE": "Outros",   # item combinado — não decomponível sem premissa arbitrária (RN-73)
    "TDA": "TDA",
    "TDE": "TDE",
    "ESTADIA": "Estadia",
    "ADICIONAL": "Outros",
}


def _categoria_componente(nome: str) -> str:
    chave = (nome or "").upper().strip()
    if chave in _CATEGORIAS_COMP:
        return _CATEGORIAS_COMP[chave]
    # Heurística para variações ("FRETE PESO ...", "PEDAGIO ...")
    for termo, categoria in _CATEGORIAS_COMP.items():
        if termo in chave:
            return categoria
    return "Outros"


def _extrair_composicao(vprest) -> dict:
    """Soma os componentes do frete (<Comp>) agrupados por categoria."""
    comp: dict = {}
    for node in vprest.findall("cte:Comp", NS):
        nome = _text(node, "cte:xNome")
        try:
            valor = float(_text(node, "cte:vComp") or 0)
        except (TypeError, ValueError):
            valor = 0.0
        if valor <= 0:
            continue
        categoria = _categoria_componente(nome)
        comp[categoria] = round(comp.get(categoria, 0.0) + valor, 2)
    return comp


def _extrair_tomador(inf) -> str:
    """O tomador pode ser identificado em toma3 (indicador) ou toma4 (CNPJ explícito)."""
    # toma4: contém CNPJ/CPF do tomador diretamente
    toma4 = inf.find(".//cte:toma4", NS)
    if toma4 is None:
        toma4 = inf.find(".//cte:toma04", NS)
    if toma4 is not None:
        cnpj = _text(toma4, "cte:CNPJ") or _text(toma4, "cte:CPF")
        if cnpj:
            return _so_digitos(cnpj)

    # toma3: indica qual participante é o tomador (0=rem,1=exp,2=rec,3=dest,4=outros)
    toma3 = inf.find(".//cte:toma3", NS)
    if toma3 is None:
        toma3 = inf.find(".//cte:ide/cte:toma3", NS)
    if toma3 is not None:
        ind = _text(toma3, "cte:toma")
        mapa = {"0": "cte:rem", "1": "cte:exped", "2": "cte:receb", "3": "cte:dest"}
        tag = mapa.get(ind)
        if tag:
            participante = inf.find(f"cte:{tag.split(':')[1]}", NS)
            if participante is not None:
                cnpj = _text(participante, "cte:CNPJ") or _text(participante, "cte:CPF")
                if cnpj:
                    return _so_digitos(cnpj)

    # fallback: tenta o destinatário
    dest = _find(inf, "cte:dest")
    if dest is not None:
        return _so_digitos(_text(dest, "cte:CNPJ") or _text(dest, "cte:CPF"))
    return ""


def _extrair_destinatario(inf) -> tuple[str, str]:
    """RN-68 (insumo): CNPJ/CPF e nome do destinatário (<dest>) da carga.

    Não existe hoje CT-e sem o nó <dest> na prática (é campo obrigatório do
    leiaute), mas o parser é tolerante: retorna ("", "") quando ausente —
    esses CT-e caem em "Cliente não identificado" na agregação (RN-68).
    """
    dest = _find(inf, "cte:dest")
    if dest is None:
        return "", ""
    cnpj = _so_digitos(_text(dest, "cte:CNPJ") or _text(dest, "cte:CPF"))
    nome = _text(dest, "cte:xNome")
    return cnpj, nome


def _extrair_peso(inf) -> float:
    """Peso considerado para o frete = maior entre os pesos informados
    (peso bruto x peso cubado). A transportadora taxa o frete pelo maior
    peso ('peso taxado'), então é ele que reflete o custo real por kg.

    Considera apenas medidas de peso em KG; ignora VOLUMES (cUnid 03) e
    CUBAGEM em m³ (cUnid 00).
    """
    pesos = []
    for infq in inf.findall(".//cte:infCarga/cte:infQ", NS):
        tp = (_text(infq, "cte:tpMed") or "").upper()
        unid = _text(infq, "cte:cUnid")
        qtd = _float(infq, "cte:qCarga")
        if ("PESO" in tp or unid == "01" or "KG" in tp) and qtd > 0:
            pesos.append(qtd)
    return max(pesos) if pesos else 0.0


def _so_digitos(valor: str) -> str:
    return "".join(c for c in (valor or "") if c.isdigit())
