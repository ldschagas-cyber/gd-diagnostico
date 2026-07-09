// Mapeamento de classificações de benchmark para cores do MUI (chips).
// Segue a Especificação Funcional do Módulo Benchmark Logístico (seção 12).

export const CORES_CLASSIFICACAO = {
  Excelente: "success",
  "Muito Bom": "success",
  Bom: "info",
  Atenção: "warning",
  Crítico: "error",
  "Muito Crítico": "error",
  "Sem referência": "default",
  "Sem dados": "default",
};

export const corClassificacao = (c) => CORES_CLASSIFICACAO[c] || "default";

// Nível de custo da transportadora (seção 10).
export const CORES_NIVEL_CUSTO = {
  "Melhor custo": "success",
  "Custo médio": "warning",
  "Pior custo": "error",
};

export const corNivelCusto = (n) => CORES_NIVEL_CUSTO[n] || "default";

// Cor do desvio: negativo (abaixo do benchmark) é bom; positivo é ruim.
export const corDesvio = (desvio) =>
  desvio > 0 ? "error.main" : desvio < 0 ? "success.main" : "text.secondary";

export const fmtDesvio = (d) =>
  `${d > 0 ? "+" : ""}${(d ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
