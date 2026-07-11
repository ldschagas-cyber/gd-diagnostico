import {
  Box, Grid, Card, CardContent, Typography, Stack, TextField, Button,
  LinearProgress, Alert, Chip,
} from "@mui/material";
import {
  ComposedChart, Bar, Line, BarChart, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import IndicadoresTransversais from "../components/IndicadoresTransversais";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import {
  useBenchmarkExecutivo, useBenchmarkNacional, useIaScore,
  useComparativoMercado, useSimuladorEconomia,
} from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtRsKg, fmtNumero, fmtPct, rotuloMacro } from "../utils/format";
import { GD } from "../theme";

const CLASSIFICACOES_CRITICAS = new Set(["ACIMA_P75"]);
const CORES_HEATMAP = { ABAIXO_P50: GD.ok, ENTRE_P50_P75: GD.amber, ACIMA_P75: GD.danger, SEM_REFERENCIA: "#CBD2DA" };

export default function DashboardExecutivo() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [tela, , patch] = useTelaEstado("benchmark-executivo", { dataInicio: "", dataFim: "" });
  const { dataInicio, dataFim } = tela;
  const setDataInicio = (v) => patch({ dataInicio: v });
  const setDataFim = (v) => patch({ dataFim: v });

  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;

  const executivoQ = useBenchmarkExecutivo(empresaAtivaId, params);
  const nacionalQ = useBenchmarkNacional(empresaAtivaId, params);
  const scoreQ = useIaScore(empresaAtivaId);
  const nacMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "NACIONAL" });
  const regMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "REGIAO" });
  const corMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "CORREDOR" });
  const ecoP50Q = useSimuladorEconomia(empresaAtivaId, { ...params, cenario: "P50" });
  const ecoP25Q = useSimuladorEconomia(empresaAtivaId, { ...params, cenario: "P25" });

  const dados = executivoQ.data;
  const nacional = nacionalQ.data;
  const score = scoreQ.data;
  const nacionalMercado = nacMercQ.data?.[0] || null;
  const porRegiaoMercado = regMercQ.data || [];
  const porCorredorMercado = corMercQ.data || [];
  const economiaP50 = ecoP50Q.data;
  const economiaP25 = ecoP25Q.data;

  const carregando =
    executivoQ.isFetching || nacionalQ.isFetching || scoreQ.isFetching ||
    nacMercQ.isFetching || regMercQ.isFetching || corMercQ.isFetching ||
    ecoP50Q.isFetching || ecoP25Q.isFetching;
  const erro = executivoQ.error ? extrairErro(executivoQ.error) : "";

  const aplicar = () => {
    executivoQ.refetch();
    nacionalQ.refetch();
    scoreQ.refetch();
    nacMercQ.refetch();
    regMercQ.refetch();
    corMercQ.refetch();
    ecoP50Q.refetch();
    ecoP25Q.refetch();
  };

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

  const regioesCriticas = porRegiaoMercado.filter((r) => CLASSIFICACOES_CRITICAS.has(r.classificacao));
  const corredoresCriticos = porCorredorMercado.filter((c) => CLASSIFICACOES_CRITICAS.has(c.classificacao));

  const BUCKETS = ["≤P10", "P10-P25", "P25-P50", "P50-P75", "P75-P90", ">P90"];
  const distribuicao = BUCKETS.map((b) => ({
    faixa: b,
    corredores: porCorredorMercado.filter((c) => c.percentil === b).length,
  }));

  const tendencia = (() => {
    const serie = dados?.evolucao || [];
    if (serie.length < 2) return null;
    const delta = serie[serie.length - 1].frete_rs_kg - serie[serie.length - 2].frete_rs_kg;
    if (Math.abs(delta) < 0.001) return { rotulo: "Estável", cor: "default" };
    return delta > 0 ? { rotulo: "Em alta", cor: "error" } : { rotulo: "Em queda", cor: "success" };
  })();

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
            <Button variant="contained" onClick={aplicar} disabled={carregando}>Aplicar</Button>
          </Stack>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && (
        <>
          <IndicadoresTransversais empresaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />

          {/* Performance */}
          <Typography variant="overline" color="text.secondary">Performance</Typography>
          <Grid container spacing={2.5} sx={{ mt: 0, mb: 2 }}>
            <Grid item xs={6} md={2.4}>
              <StatCard rotulo="Frete Total" valor={nacional ? fmtMoeda(nacional.valor_total_frete) : "—"} cor={GD.indigo} />
            </Grid>
            <Grid item xs={6} md={2.4}>
              <StatCard rotulo="Peso" valor={nacional ? `${fmtNumero(nacional.peso_total, 0)} kg` : "—"} cor={GD.blue} />
            </Grid>
            <Grid item xs={6} md={2.4}>
              <StatCard rotulo="Nº CT-es" valor={nacional ? String(nacional.qtd_ctes) : "—"} cor={GD.blueDark} />
            </Grid>
            <Grid item xs={6} md={2.4}>
              <StatCard rotulo="R$/kg" valor={fmtRsKg(dados.frete_kg_atual)} cor={GD.ok} />
            </Grid>
            <Grid item xs={6} md={2.4}>
              <StatCard rotulo="% Frete/Faturamento" valor={nacional ? fmtPct(nacional.frete_pct.valor) : "—"} cor={GD.amberDark} />
            </Grid>
          </Grid>

          {/* Benchmark */}
          <Typography variant="overline" color="text.secondary">Benchmark</Typography>
          <Grid container spacing={2.5} sx={{ mt: 0, mb: 2 }}>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Score Benchmark" valor={score ? fmtNumero(score.score_total, 0) : "—"}
                legenda={score?.classificacao} cor={GD.indigo} />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Percentil Atual" valor={nacionalMercado?.percentil || "—"}
                legenda="posição do R$/kg vs. Matriz Benchmark (OD)" cor={GD.blue} />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="% acima do Mercado" valor={nacionalMercado?.diferenca_pct != null ? fmtPct(nacionalMercado.diferenca_pct) : "—"}
                legenda="vs. mediana (P50) da Matriz Benchmark (OD)" cor={nacionalMercado?.diferenca_pct > 0 ? GD.danger : GD.ok} />
            </Grid>
          </Grid>

          {/* Economia */}
          <Typography variant="overline" color="text.secondary">Economia</Typography>
          <Grid container spacing={2.5} sx={{ mt: 0, mb: 2 }}>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Potencial de Economia" valor={fmtMoeda(dados.economia_total)} legenda="no período" cor={GD.amberDark} />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Economia no P50" valor={economiaP50 ? fmtMoeda(economiaP50.economia_total) : "—"}
                legenda="se atingir a mediana de mercado" cor={GD.amber} />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Economia no P25" valor={economiaP25 ? fmtMoeda(economiaP25.economia_total) : "—"}
                legenda="se atingir o quartil mais competitivo" cor={GD.amber} />
            </Grid>
          </Grid>

          {/* Risco */}
          <Typography variant="overline" color="text.secondary">Risco</Typography>
          <Grid container spacing={2.5} sx={{ mt: 0, mb: 0.5 }}>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Corredores Críticos" valor={String(corredoresCriticos.length)}
                legenda="acima do P75 de mercado" cor={corredoresCriticos.length ? GD.danger : GD.ok}
                icone={corredoresCriticos.length ? <WarningAmberIcon /> : undefined} />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatCard rotulo="Regiões Críticas" valor={String(regioesCriticas.length)}
                legenda="acima do P75 de mercado" cor={regioesCriticas.length ? GD.danger : GD.ok}
                icone={regioesCriticas.length ? <WarningAmberIcon /> : undefined} />
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">Tendência (R$/kg, últimos meses)</Typography>
                  <Box sx={{ mt: 0.5 }}>
                    {tendencia
                      ? <Chip label={tendencia.rotulo} color={tendencia.cor} sx={{ fontWeight: 700 }} />
                      : <Typography variant="body2" color="text.secondary">Histórico insuficiente</Typography>}
                  </Box>
                </CardContent>
              </Card>
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

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Distribuição percentílica dos corredores</Typography>
                  {porCorredorMercado.length ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={distribuicao}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="faixa" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                        <ReTooltip formatter={(v) => `${v} corredor(es)`} />
                        <Bar dataKey="corredores" radius={[4, 4, 0, 0]}>
                          {distribuicao.map((d, i) => (
                            <Cell key={i} fill={d.faixa === ">P90" || d.faixa === "P75-P90" ? GD.danger : d.faixa === "≤P10" || d.faixa === "P10-P25" ? GD.ok : GD.blue} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                      Sem Benchmark Observado gerado para o período.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Heatmap nacional — custo × Matriz Benchmark (OD)</Typography>
                  {porRegiaoMercado.length ? (
                    <Grid container spacing={1.5}>
                      {porRegiaoMercado.map((r) => (
                        <Grid item xs={6} sm={4} key={r.destino_regiao}>
                          <Box sx={{
                            p: 1.5, borderRadius: 2, textAlign: "center",
                            bgcolor: CORES_HEATMAP[r.classificacao] || "#CBD2DA", color: "#fff",
                          }}>
                            <Typography variant="caption" sx={{ opacity: 0.9, display: "block" }}>
                              {rotuloMacro(r.destino_regiao)}
                            </Typography>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                              {fmtNumero(r.cliente_p50, 2)}
                            </Typography>
                            <Typography variant="caption" sx={{ opacity: 0.85 }}>R$/kg</Typography>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  ) : (
                    <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                      Sem dados regionais de mercado no período.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}
