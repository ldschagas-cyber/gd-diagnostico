import { useEffect, useState, useCallback } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button,
  LinearProgress, Chip, Divider,
} from "@mui/material";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
} from "recharts";
import SpeedIcon from "@mui/icons-material/Speed";
import RefreshIcon from "@mui/icons-material/Refresh";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { inteligenciaApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

const COR_CLASSIFICACAO = {
  "Excelente": "#2E7D32", "Muito Bom": "#558B2F", "Regular": GD.amber,
  "Crítico": "#E65100", "Muito Crítico": "#C62828",
};

const COMPONENTES = [
  { chave: "benchmark_nacional", rotulo: "Benchmark Nacional", peso: "30%" },
  { chave: "benchmark_regional", rotulo: "Benchmark Regional", peso: "20%" },
  { chave: "transportadoras", rotulo: "Transportadoras", peso: "20%" },
  { chave: "filiais", rotulo: "Filiais", peso: "15%" },
  { chave: "economia", rotulo: "Economia", peso: "15%" },
];

export default function ScoreLogistico() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [status, setStatus] = useState(null);
  const [score, setScore] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [setorial, setSetorial] = useState(null);
  const [carregando, setCarregando] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const [st, sc, hist, set] = await Promise.all([
        inteligenciaApi.status(),
        inteligenciaApi.obterScore(empresaAtivaId),
        inteligenciaApi.historicoScore(empresaAtivaId),
        inteligenciaApi.benchmarkSetorial(empresaAtivaId),
      ]);
      setStatus(st);
      setScore(sc);
      setHistorico(hist.reverse());
      setSetorial(set);
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, fb]);

  useEffect(() => { carregar(); }, [carregar]);

  const recalcular = async () => {
    setCarregando(true);
    try {
      await inteligenciaApi.calcularScore(empresaAtivaId);
      fb.sucesso("Score recalculado.");
      carregar();
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Score Logístico" icone={<SpeedIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  const corClass = score?.classificacao ? COR_CLASSIFICACAO[score.classificacao] : GD.indigo;
  const radarData = score
    ? COMPONENTES.map((c) => ({
        eixo: c.rotulo,
        valor: score.componentes?.[c.chave] ?? 0,
      }))
    : [];
  const histData = historico.map((h) => ({
    data: new Date(h.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
    score: h.score_total,
  }));

  return (
    <Box>
      <PageHeader
        titulo="Score Logístico"
        subtitulo="Nota de 0 a 100 da saúde da operação"
        icone={<SpeedIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={recalcular} disabled={carregando}>
            Recalcular
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />
      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Grid container spacing={3}>
        {/* Score grande */}
        <Grid item xs={12} md={4}>
          <Card sx={{ bgcolor: GD.indigo, color: "#fff", height: "100%" }}>
            <CardContent sx={{ textAlign: "center", py: 4 }}>
              <Typography variant="overline" sx={{ opacity: 0.8 }}>Score Geral</Typography>
              <Typography variant="h1" fontWeight={800} sx={{ my: 1 }}>
                {score?.score_total ?? "—"}
              </Typography>
              {score?.classificacao && (
                <Chip label={score.classificacao}
                      sx={{ bgcolor: corClass, color: "#fff", fontWeight: 700, fontSize: "1rem", py: 2, px: 1 }} />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Radar dos componentes */}
        <Grid item xs={12} md={8}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                Composição do Score
              </Typography>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="eixo" tick={{ fontSize: 12 }} />
                  <Radar name="Score" dataKey="valor" stroke={GD.indigo} fill={GD.indigo} fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Detalhamento dos componentes */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                Detalhamento por componente
              </Typography>
              <Stack spacing={2}>
                {COMPONENTES.map((c) => {
                  const v = score?.componentes?.[c.chave] ?? 0;
                  return (
                    <Box key={c.chave}>
                      <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                        <Typography variant="body2">
                          {c.rotulo} <Typography component="span" variant="caption" color="text.secondary">(peso {c.peso})</Typography>
                        </Typography>
                        <Typography variant="body2" fontWeight={700}>{v}/100</Typography>
                      </Stack>
                      <LinearProgress
                        variant="determinate" value={Math.min(100, v)}
                        sx={{ height: 8, borderRadius: 4,
                          "& .MuiLinearProgress-bar": { bgcolor: v >= 75 ? "#2E7D32" : v >= 50 ? GD.amber : "#C62828" } }}
                      />
                    </Box>
                  );
                })}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Histórico */}
        {histData.length > 1 && (
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                  Evolução do Score
                </Typography>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={histData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="data" />
                    <YAxis domain={[0, 100]} />
                    <ReTooltip />
                    <Line type="monotone" dataKey="score" stroke={GD.blue} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        )}
        {/* Benchmark Setorial */}
        {setorial?.comparativo?.length > 0 && (
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                  Benchmark Setorial
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Seu frete de R$ {setorial.frete_kg_empresa}/kg comparado às referências de mercado.
                  {setorial.segmento_mais_aderente && (
                    <> Segmento mais aderente: <strong>
                      {setorial.comparativo.find((c) => c.segmento === setorial.segmento_mais_aderente)?.segmento_rotulo}
                    </strong>.</>
                  )}
                </Typography>
                <Stack spacing={1.5}>
                  {setorial.comparativo.map((c) => {
                    const corPos = c.posicao === "abaixo" ? "#2E7D32"
                      : c.posicao === "acima" ? "#C62828" : GD.amber;
                    const rotuloPos = c.posicao === "abaixo" ? "abaixo do setor"
                      : c.posicao === "acima" ? "acima do setor"
                      : c.posicao === "alinhado" ? "alinhado" : "—";
                    return (
                      <Stack key={c.segmento} direction="row" justifyContent="space-between" alignItems="center"
                             sx={{ py: 0.5, borderBottom: "1px solid", borderColor: "divider" }}>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>{c.segmento_rotulo}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            Mercado: R$ {c.frete_kg_medio}/kg
                          </Typography>
                        </Box>
                        <Stack direction="row" spacing={1} alignItems="center">
                          {c.diferenca_pct !== null && (
                            <Typography variant="body2" sx={{ color: corPos, fontWeight: 700 }}>
                              {c.diferenca_pct > 0 ? "+" : ""}{c.diferenca_pct}%
                            </Typography>
                          )}
                          <Chip label={rotuloPos} size="small"
                                sx={{ bgcolor: corPos, color: "#fff", minWidth: 110 }} />
                        </Stack>
                      </Stack>
                    );
                  })}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
