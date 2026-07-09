import { useEffect, useState, useCallback } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, TextField, Button,
  LinearProgress, Alert,
} from "@mui/material";
import {
  ComposedChart, Bar, Line, BarChart, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtRsKg, fmtNumero, rotuloMacro } from "../utils/format";
import { GD } from "../theme";

export default function DashboardExecutivo() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    setErro("");
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      setDados(await benchmarkApi.executivo(empresaAtivaId, params));
    } catch (e) {
      setErro(extrairErro(e));
      setDados(null);
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, dataInicio, dataFim]);

  useEffect(() => {
    carregar();
  }, [empresaAtivaId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Dashboard Executivo" subtitulo="Visão estratégica de benchmark" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  const evolucao =
    dados?.evolucao?.map((p) => ({
      mes: p.mes,
      "R$/kg": Number(p.frete_rs_kg.toFixed(4)),
      "Benchmark nacional": Number((dados.benchmark_nacional_kg || 0).toFixed(4)),
    })) || [];

  const comparativo =
    dados?.regionais?.map((r) => ({
      nome: rotuloMacro(r.macro_regiao),
      "R$/kg": Number(r.frete_kg.valor.toFixed(4)),
      "Benchmark": Number(r.frete_kg.benchmark_medio.toFixed(4)),
    })) || [];

  const ranking =
    [...(dados?.transportadoras || [])]
      .sort((a, b) => b.frete_total - a.frete_total)
      .slice(0, 8)
      .map((t) => ({
        nome: t.nome.length > 16 ? t.nome.slice(0, 16) + "…" : t.nome,
        valor: Number(t.frete_total.toFixed(2)),
      }));

  return (
    <Box>
      <PageHeader
        titulo="Dashboard Executivo"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — visão estratégica de benchmark`}
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <TextField label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <Button variant="contained" onClick={carregar} disabled={carregando}>Aplicar</Button>
          </Stack>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && (
        <>
          {/* Cards estratégicos */}
          <Grid container spacing={2.5}>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Frete/kg atual" valor={fmtRsKg(dados.frete_kg_atual)} cor={GD.indigo} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Benchmark nacional" valor={fmtRsKg(dados.benchmark_nacional_kg)} cor={GD.blue} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Benchmark regional" valor={fmtRsKg(dados.benchmark_regional_kg)}
                legenda="ponderado por peso" cor={GD.blueDark} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Economia mensal" valor={fmtMoeda(dados.economia_mensal)}
                legenda="potencial vs. mercado" cor={GD.amberDark} />
            </Grid>
          </Grid>

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%", borderColor: GD.ok, borderWidth: 1.5 }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TrendingDownIcon sx={{ color: GD.ok }} />
                    <Typography variant="overline" color="text.secondary">Melhor transportadora (custo)</Typography>
                  </Stack>
                  <Typography variant="h6" sx={{ mt: 0.5 }}>{dados.melhor_transportadora || "—"}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {dados.melhor_transportadora ? fmtRsKg(dados.melhor_transportadora_kg) : ""}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%", borderColor: GD.danger, borderWidth: 1.5 }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TrendingUpIcon sx={{ color: GD.danger }} />
                    <Typography variant="overline" color="text.secondary">Pior transportadora (custo)</Typography>
                  </Stack>
                  <Typography variant="h6" sx={{ mt: 0.5 }}>{dados.pior_transportadora || "—"}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {dados.pior_transportadora ? fmtRsKg(dados.pior_transportadora_kg) : ""}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Evolução mensal */}
          <Card sx={{ mt: 2.5 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Evolução mensal do custo por kg</Typography>
              {evolucao.length ? (
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={evolucao}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <ReTooltip formatter={(v) => fmtRsKg(v)} />
                    <Legend />
                    <Bar dataKey="R$/kg" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={32} />
                    <Line dataKey="Benchmark nacional" stroke={GD.amber} strokeWidth={3} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                  Sem dados mensais no período.
                </Typography>
              )}
            </CardContent>
          </Card>

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Comparativo regional</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <ComposedChart data={comparativo}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <ReTooltip formatter={(v) => fmtRsKg(v)} />
                      <Legend />
                      <Bar dataKey="R$/kg" fill={GD.blue} radius={[4, 4, 0, 0]} />
                      <Line dataKey="Benchmark" stroke={GD.amber} strokeWidth={3} dot={{ r: 3 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Ranking de transportadoras (frete total)</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={ranking} layout="vertical" margin={{ left: 20 }}>
                      <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                      <YAxis type="category" dataKey="nome" tick={{ fontSize: 11 }} width={110} />
                      <ReTooltip formatter={(v) => fmtMoeda(v)} />
                      <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
                        {ranking.map((_, i) => (
                          <Cell key={i} fill={i === 0 ? GD.indigo : GD.blue} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}
