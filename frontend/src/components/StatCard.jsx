import { Card, CardContent, Typography, Stack, Box, Chip } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import RemoveIcon from "@mui/icons-material/Remove";

/**
 * Cartão de indicador. Quando `desvio` é informado, mostra um selo comparando
 * o resultado com a meta — verde quando dentro da meta, âmbar quando acima.
 * `desvioPositivoRuim` define se um desvio positivo é desfavorável (ex.: custo
 * acima da meta) — padrão true.
 */
export default function StatCard({
  rotulo,
  valor,
  legenda,
  cor = "primary.main",
  desvio,
  desvioPositivoRuim = true,
  icone,
  compacto = false,
}) {
  const temDesvio = desvio !== null && desvio !== undefined && !Number.isNaN(desvio);
  let corSelo = "default";
  let Icone = RemoveIcon;
  if (temDesvio) {
    const ruim = desvioPositivoRuim ? desvio > 0 : desvio < 0;
    if (Math.abs(desvio) < 0.0001) {
      corSelo = "default";
      Icone = RemoveIcon;
    } else if (ruim) {
      corSelo = "warning";
      Icone = TrendingUpIcon;
    } else {
      corSelo = "success";
      Icone = TrendingDownIcon;
    }
  }

  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={compacto ? { p: 1.75, "&:last-child": { pb: 1.75 } } : undefined}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ lineHeight: 1.3, fontSize: compacto ? 10.5 : undefined }}
          >
            {rotulo}
          </Typography>
          {icone && (
            <Box sx={{ color: cor, opacity: 0.8, "& svg": compacto ? { fontSize: 19 } : undefined }}>
              {icone}
            </Box>
          )}
        </Stack>
        <Typography
          variant={compacto ? "h5" : "h4"}
          sx={{ color: cor, fontWeight: 700, mt: 0.5, fontFamily: "'Sora', sans-serif" }}
        >
          {valor}
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1, flexWrap: "wrap" }}>
          {legenda && (
            <Typography variant="caption" color="text.secondary">
              {legenda}
            </Typography>
          )}
          {temDesvio && Math.abs(desvio) >= 0.0001 && (
            <Chip
              size="small"
              color={corSelo}
              icon={<Icone sx={{ fontSize: 16 }} />}
              label={`${desvio > 0 ? "+" : ""}${desvio.toLocaleString("pt-BR", {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
              })}`}
              variant="outlined"
            />
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
