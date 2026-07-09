"""Mapeia UF para macro-região do IBGE (RF006/RF012)."""
from app.domain.entities import MacroRegiaoEnum

UF_PARA_MACRO: dict[str, MacroRegiaoEnum] = {
    # Norte
    "AC": MacroRegiaoEnum.NORTE, "AP": MacroRegiaoEnum.NORTE,
    "AM": MacroRegiaoEnum.NORTE, "PA": MacroRegiaoEnum.NORTE,
    "RO": MacroRegiaoEnum.NORTE, "RR": MacroRegiaoEnum.NORTE,
    "TO": MacroRegiaoEnum.NORTE,
    # Nordeste
    "AL": MacroRegiaoEnum.NORDESTE, "BA": MacroRegiaoEnum.NORDESTE,
    "CE": MacroRegiaoEnum.NORDESTE, "MA": MacroRegiaoEnum.NORDESTE,
    "PB": MacroRegiaoEnum.NORDESTE, "PE": MacroRegiaoEnum.NORDESTE,
    "PI": MacroRegiaoEnum.NORDESTE, "RN": MacroRegiaoEnum.NORDESTE,
    "SE": MacroRegiaoEnum.NORDESTE,
    # Centro-Oeste
    "DF": MacroRegiaoEnum.CENTRO_OESTE, "GO": MacroRegiaoEnum.CENTRO_OESTE,
    "MT": MacroRegiaoEnum.CENTRO_OESTE, "MS": MacroRegiaoEnum.CENTRO_OESTE,
    # Sudeste
    "ES": MacroRegiaoEnum.SUDESTE, "MG": MacroRegiaoEnum.SUDESTE,
    "RJ": MacroRegiaoEnum.SUDESTE, "SP": MacroRegiaoEnum.SUDESTE,
    # Sul
    "PR": MacroRegiaoEnum.SUL, "RS": MacroRegiaoEnum.SUL,
    "SC": MacroRegiaoEnum.SUL,
}


def macro_por_uf(uf: str) -> MacroRegiaoEnum | None:
    if not uf:
        return None
    return UF_PARA_MACRO.get(uf.strip().upper())
