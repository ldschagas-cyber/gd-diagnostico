// Funções utilitárias de formatação no padrão brasileiro.

export const fmtMoeda = (v) =>
  (v ?? 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  });

export const fmtNumero = (v, casas = 2) =>
  (v ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });

export const fmtPct = (v, casas = 2) => `${fmtNumero(v, casas)}%`;

export const fmtRsKg = (v) => `R$ ${fmtNumero(v, 2)}/kg`;

// Máscara visual de CNPJ: 00.000.000/0000-00
export function mascararCnpj(valor) {
  const d = String(valor || "").replace(/\D/g, "").slice(0, 14);
  return d
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

export const soDigitos = (v) => String(v || "").replace(/\D/g, "");

export const UFS = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
  "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
  "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

export const MACRO_REGIOES = [
  { valor: "NORTE", rotulo: "Norte" },
  { valor: "NORDESTE", rotulo: "Nordeste" },
  { valor: "CENTRO_OESTE", rotulo: "Centro-Oeste" },
  { valor: "SUDESTE", rotulo: "Sudeste" },
  { valor: "SUL", rotulo: "Sul" },
];

export const rotuloMacro = (v) =>
  MACRO_REGIOES.find((m) => m.valor === v)?.rotulo || v || "—";
