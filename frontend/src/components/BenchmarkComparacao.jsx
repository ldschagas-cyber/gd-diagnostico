import { Card, CardContent, Typography, Stack, Box, Chip, LinearProgress } from "@mui/material";
import { corClassificacao, corDesvio, fmtDesvio } from "../utils/benchmark";

/**
 * Cartão que compara um indicador da empresa com a faixa de benchmark
 * (mínimo / médio / máximo), mostrando posição na faixa, desvio e classificação.
 */
export default function BenchmarkComparacao({ titulo, comp, formatar }) {
  const fmt = formatar || ((v) => v);
  const { valor, benchmark_min, benchmark_medio, benchmark_max, desvio_pct, classificacao } = comp;

  // posição do valor dentro da faixa [min, max] para a barra (0–100%)
  const span = benchmark_max - benchmark_min;
  const posicao =
    span > 0 ? Math.min(100, Math.max(0, ((valor - benchmark_min) / span) * 100)) : 50;

  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="overline" color="text.secondary">
            {titulo}
          </Typography>
          <Chip size="small" label={classificacao} color={corClassificacao(classificacao)} />
        </Stack>

        <Stack direction="row" alignItems="baseline" spacing={1.5}>
          <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: "'Sora', sans-serif" }}>
            {fmt(valor)}
          </Typography>
          <Typography variant="body2" sx={{ color: corDesvio(desvio_pct), fontWeight: 600 }}>
            {fmtDesvio(desvio_pct)} vs. mercado
          </Typography>
        </Stack>

        <Box sx={{ mt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={posicao}
            sx={{
              height: 8,
              borderRadius: 4,
              "& .MuiLinearProgress-bar": {
                backgroundColor:
                  valor <= benchmark_medio
                    ? "success.main"
                    : valor <= benchmark_max
                    ? "warning.main"
                    : "error.main",
              },
            }}
          />
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              mín {fmt(benchmark_min)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              médio {fmt(benchmark_medio)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              máx {fmt(benchmark_max)}
            </Typography>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}
