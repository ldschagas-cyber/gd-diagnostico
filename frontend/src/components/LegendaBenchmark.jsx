import { Stack, Chip, Typography } from "@mui/material";
import { rotuloFonte, corFonte } from "../utils/benchmark";

/**
 * Barra de legenda reutilizável do módulo Benchmark Mercado — mostra a fonte
 * do dado da tela (mercado externo / histórico interno / regra
 * determinística) e, opcionalmente, a escala de classificação percentílica.
 * Reduz a confusão entre telas que comparam contra fontes diferentes.
 */
export default function LegendaBenchmark({ fonte, mostrarClassificacao = false }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
        Fonte:
      </Typography>
      <Chip size="small" label={rotuloFonte(fonte)} color={corFonte(fonte)} variant="outlined" />

      {mostrarClassificacao && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1.5, fontWeight: 700 }}>
            Classificação:
          </Typography>
          <Chip size="small" label="Abaixo do mercado" color="success" variant="outlined" />
          <Chip size="small" label="Dentro do mercado" color="info" variant="outlined" />
          <Chip size="small" label="Acima do mercado" color="error" variant="outlined" />
          <Chip size="small" label="Sem referência" color="default" variant="outlined" />
        </>
      )}
    </Stack>
  );
}
