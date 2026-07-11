import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button,
  LinearProgress, Divider, Chip,
} from "@mui/material";
import PsychologyIcon from "@mui/icons-material/Psychology";
import SpeedIcon from "@mui/icons-material/Speed";
import SavingsIcon from "@mui/icons-material/Savings";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { useIaStatus, useIaDashboard } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

const COR_CLASSIFICACAO = {
  "Excelente": "#2E7D32",
  "Muito Bom": "#558B2F",
  "Regular": GD.amber,
  "Crítico": "#E65100",
  "Muito Crítico": "#C62828",
};

function KPICard({ titulo, valor, subtitulo, icone, color }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {titulo}
            </Typography>
            <Typography variant="h5" fontWeight={700} sx={{ color: color || GD.indigo }}>
              {valor}
            </Typography>
            {subtitulo && (
              <Typography variant="caption" color="text.secondary">
                {subtitulo}
              </Typography>
            )}
          </Box>
          <Box sx={{ color: color || GD.indigo, opacity: 0.7 }}>{icone}</Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function InteligenciaDashboard() {
  const { empresaAtivaId } = useEmpresa();
  const nav = useNavigate();
  const fb = useFeedback();

  const statusQ = useIaStatus();
  const dashQ = useIaDashboard(empresaAtivaId);

  const status = statusQ.data ?? null;
  const dash = dashQ.data ?? null;
  const carregando = statusQ.isFetching || dashQ.isFetching;
  const erro = dashQ.error ? extrairErro(dashQ.error) : "";

  useEffect(() => {
    if (statusQ.error) fb.erro(extrairErro(statusQ.error));
  }, [statusQ.error]); // eslint-disable-line react-hooks/exhaustive-deps

  const carregar = () => {
    statusQ.refetch();
    dashQ.refetch();
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Inteligência Logística" icone={<PsychologyIcon />} />
        <VazioEstado mensagem="Selecione uma empresa para ver a inteligência logística." />
      </Box>
    );
  }

  const corClass = dash?.classificacao ? COR_CLASSIFICACAO[dash.classificacao] : GD.indigo;

  return (
    <Box>
      <PageHeader
        titulo="Inteligência Logística"
        subtitulo="Visão consolidada da análise por IA"
        icone={<PsychologyIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="outlined" onClick={carregar} disabled={carregando}>
            Atualizar
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Typography color="error" sx={{ mb: 2 }}>{erro}</Typography>}

      {/* Score em destaque */}
      <Card sx={{ mb: 3, bgcolor: GD.indigo, color: "#fff" }}>
        <CardContent>
          <Grid container alignItems="center" spacing={2}>
            <Grid item xs={12} sm={3} textAlign="center">
              <Typography variant="overline" sx={{ opacity: 0.8 }}>
                Score Logístico
              </Typography>
              <Typography variant="h2" fontWeight={800}>
                {dash?.score_logistico ?? "—"}
              </Typography>
              {dash?.classificacao && (
                <Chip
                  label={dash.classificacao}
                  sx={{ bgcolor: corClass, color: "#fff", fontWeight: 700 }}
                />
              )}
            </Grid>
            <Grid item xs={12} sm={9}>
              <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                O Score Logístico resume a saúde da sua operação numa nota de 0 a 100,
                combinando benchmark nacional, regional, transportadoras, filiais e
                potencial de economia.
              </Typography>
              <Button
                variant="contained" color="secondary" size="small"
                onClick={() => nav("/inteligencia/score")}
              >
                Ver detalhamento do score
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* KPIs */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            titulo="Economia Potencial"
            valor={fmtMoeda(dash?.economia_potencial)}
            subtitulo="por ano (estimado)"
            icone={<SavingsIcon fontSize="large" />}
            color={GD.blue}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            titulo="Economia Capturada"
            valor={fmtMoeda(dash?.economia_capturada)}
            subtitulo="via BIDs encerrados"
            icone={<TrendingUpIcon fontSize="large" />}
            color="#2E7D32"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            titulo="Oportunidades Abertas"
            valor={dash?.oportunidades_abertas ?? 0}
            subtitulo="aguardando ação"
            icone={<TrendingUpIcon fontSize="large" />}
            color={GD.amber}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            titulo="Insights Gerados"
            valor={dash?.insights_gerados ?? 0}
            subtitulo="alertas automáticos"
            icone={<LightbulbIcon fontSize="large" />}
            color={GD.indigo}
          />
        </Grid>
      </Grid>

      {/* Atalhos */}
      <Typography variant="h6" sx={{ mb: 2 }}>Explorar</Typography>
      <Grid container spacing={2}>
        {[
          { t: "Diagnóstico IA", d: "Análise executiva automática da operação", ic: <AutoAwesomeIcon />, r: "/inteligencia/diagnostico" },
          { t: "Insights Automáticos", d: "Alertas diários sobre custo e desempenho", ic: <LightbulbIcon />, r: "/inteligencia/insights" },
          { t: "Oportunidades", d: "Economias identificadas automaticamente", ic: <SavingsIcon />, r: "/inteligencia/oportunidades" },
          { t: "Assistente Logístico", d: "Pergunte sobre seus dados em linguagem natural", ic: <PsychologyIcon />, r: "/inteligencia/assistente" },
          { t: "Score & Benchmark", d: "Detalhamento do score e comparação setorial", ic: <SpeedIcon />, r: "/inteligencia/score" },
        ].map((card) => (
          <Grid item xs={12} sm={6} md={4} key={card.r}>
            <Card
              variant="outlined"
              sx={{ height: "100%", cursor: "pointer", "&:hover": { borderColor: GD.indigo } }}
              onClick={() => nav(card.r)}
            >
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                  <Box sx={{ color: GD.indigo }}>{card.ic}</Box>
                  <Typography variant="subtitle1" fontWeight={700}>{card.t}</Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary">{card.d}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
