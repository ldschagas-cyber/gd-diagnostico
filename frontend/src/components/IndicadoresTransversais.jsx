import { Card, CardContent, Typography, Stack, Chip, Box, LinearProgress, Tooltip } from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import DonutLargeIcon from "@mui/icons-material/DonutLarge";
import { useIndicadoresMercado } from "../api/queries";
import { GD } from "../theme";

const COR_NIVEL = { Alta: "success", Média: "warning", Baixa: "error" };

/**
 * Índice de Confiabilidade + Cobertura do Benchmark — indicadores
 * transversais reutilizáveis em qualquer tela que consuma a Matriz
 * Benchmark (OD). Busca `GET /benchmark/indicadores-mercado/{empresaId}`
 * via React Query (cache compartilhado entre as telas que o consomem).
 */
export default function IndicadoresTransversais({ empresaId, dataInicio, dataFim }) {
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: dados } = useIndicadoresMercado(empresaId, params);

  if (!dados) return null;

  const { confiabilidade, cobertura } = dados;

  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={2.5} sx={{ mb: 2.5 }}>
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <VerifiedIcon sx={{ color: COR_NIVEL[confiabilidade.nivel] ? undefined : GD.indigo }} color={COR_NIVEL[confiabilidade.nivel] || "default"} />
            <Typography variant="subtitle2" color="text.secondary">Índice de Confiabilidade</Typography>
          </Stack>
          <Stack direction="row" spacing={1.5} alignItems="baseline">
            <Chip label={confiabilidade.nivel} color={COR_NIVEL[confiabilidade.nivel] || "default"} sx={{ fontWeight: 700 }} />
            <Typography variant="body2" color="text.secondary">
              {confiabilidade.qtd_ctes.toLocaleString("pt-BR")} CT-es
            </Typography>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
            {confiabilidade.mensagem}
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ flex: 2 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
            <DonutLargeIcon sx={{ color: GD.indigo }} />
            <Typography variant="subtitle2" color="text.secondary">Cobertura do Benchmark</Typography>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={3}>
            <BarraCobertura rotulo="CT-es cobertos" valor={cobertura.pct_ctes_cobertos}
              legenda={`${cobertura.qtd_ctes_cobertos} de ${cobertura.qtd_ctes_total}`} />
            <BarraCobertura rotulo="Peso coberto" valor={cobertura.pct_peso_coberto} />
            <BarraCobertura rotulo="Corredores cobertos" valor={cobertura.pct_corredores_cobertos}
              legenda={`${cobertura.qtd_corredores_cobertos} de ${cobertura.qtd_corredores_operados}`} />
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

function BarraCobertura({ rotulo, valor, legenda }) {
  return (
    <Box sx={{ flex: 1, minWidth: 140 }}>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="caption" color="text.secondary">{rotulo}</Typography>
        <Typography variant="caption" fontWeight={700}>{valor.toFixed(0)}%</Typography>
      </Stack>
      <Tooltip title={legenda || ""}>
        <LinearProgress variant="determinate" value={Math.min(100, valor)} sx={{ height: 8, borderRadius: 4, mt: 0.5 }} />
      </Tooltip>
      {legenda && <Typography variant="caption" color="text.secondary">{legenda}</Typography>}
    </Box>
  );
}
