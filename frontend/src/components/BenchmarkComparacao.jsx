import { Card, CardContent, Typography, Stack, Box, Chip, LinearProgress } from "@mui/material";
import { corClassificacao, corDesvio } from "../utils/benchmark";

// Rótulo estendido do desvio, específico deste cartão (as tabelas de outras
// telas de Benchmark usam o formato compacto `fmtDesvio`, que não é alterado).
function rotuloDesvio(desvio_pct) {
  const abs = Math.abs(desvio_pct ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  if (Math.abs(desvio_pct ?? 0) < 0.05) return "Na média nacional";
  return `${abs}% ${desvio_pct > 0 ? "acima" : "abaixo"} da média nacional`;
}

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
            {rotuloDesvio(desvio_pct)}
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
              Mercado: Mínimo {fmt(benchmark_min)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Mercado: Média {fmt(benchmark_medio)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Mercado: Máximo {fmt(benchmark_max)}
            </Typography>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}
