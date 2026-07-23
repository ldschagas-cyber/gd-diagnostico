import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box, Grid, Card, CardContent, Typography, Stack, TextField, Button,
  LinearProgress, Alert, Chip, ToggleButton, ToggleButtonGroup,
} from "@mui/material";
import {
  ComposedChart, Bar, Line, BarChart, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from "recharts";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import RefreshIcon from "@mui/icons-material/Refresh";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import {
  useBenchmarkExecutivo, useBenchmarkNacional, useIaScore,
  useComparativoMercado,
  useIaStatus, useIaScoreHistorico, useIaBenchmarkSetorial, useCalcularScore,
} from "../api/queries";
import { useBenchmarkPeriodo } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtRsKg, fmtNumero, fmtPct } from "../utils/format";
import { GD } from "../theme";

const CLASSIFICACOES_CRITICAS = new Set(["ACIMA_P75"]);

const COR_CLASSIFICACAO_SCORE = {
  "Excelente": "#2E7D32", "Muito Bom": "#558B2F", "Regular": GD.amber,
  "Crítico": "#E65100", "Muito Crítico": "#C62828",
};
const COMPONENTES_SCORE = [
  { chave: "benchmark_nacional", rotulo: "Benchmark Nacional", peso: "30%" },
  { chave: "benchmark_regional", rotulo: "Benchmark Regional", peso: "20%" },
  { chave: "transportadoras", rotulo: "Transportadoras", peso: "20%" },
  { chave: "filiais", rotulo: "Filiais", peso: "15%" },
  { chave: "economia", rotulo: "Economia", peso: "15%" },
];

// Card de KPI com botão de ação — variante de StatCard para os 3 cards que
// levam pra outra tela (StatCard não tem slot de ação).
function CardAcao({ rotulo, valor, legenda, cor, tint, acaoRotulo, onAcao }) {
  return (
    <Card sx={{ height: "100%", ...(tint && { borderLeft: `3px solid ${tint}` }) }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">{rotulo}</Typography>
        <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: "'Sora', sans-serif", color: cor || GD.indigo, mt: 0.5 }}>
          {valor}
        </Typography>
        {legenda && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{legenda}</Typography>}
        {onAcao && (
          <Button size="small" sx={{ mt: 1, ml: -1 }} onClick={onAcao}>{acaoRotulo}</Button>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardExecutivo() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fb = useFeedback();

  const [aba, setAba] = useState(() => (searchParams.get("aba") === "score" ? "score" : "geral"));

  const [periodo, , patchPeriodo] = useBenchmarkPeriodo();
  const { dataInicio, dataFim } = periodo;
  const setDataInicio = (v) => patchPeriodo({ dataInicio: v });
  const setDataFim = (v) => patchPeriodo({ dataFim: v });

  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;

  // ── Visão Geral ──
  const executivoQ = useBenchmarkExecutivo(empresaAtivaId, params);
  const nacionalQ = useBenchmarkNacional(empresaAtivaId, params);
  const scoreQ = useIaScore(empresaAtivaId);
  const nacMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "NACIONAL" });
  const regMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "REGIAO" });
  const corMercQ = useComparativoMercado(empresaAtivaId, { ...params, escopo: "CORREDOR" });

  // ── Score Logístico (só busca quando essa visão está ativa) ──
  const scoreAtivo = aba === "score";
  const statusQ = useIaStatus({ enabled: scoreAtivo });
  const historicoQ = useIaScoreHistorico(empresaAtivaId, { enabled: !!empresaAtivaId && scoreAtivo });
  const setorialQ = useIaBenchmarkSetorial(empresaAtivaId, { enabled: !!empresaAtivaId && scoreAtivo });
  const calcularMut = useCalcularScore(empresaAtivaId);

  const dados = executivoQ.data;
  const nacional = nacionalQ.data;
  const score = scoreQ.data;
  const nacionalMercado = nacMercQ.data?.[0] || null;
  const porRegiaoMercado = regMercQ.data || [];
  const porCorredorMercado = corMercQ.data || [];
  const status = statusQ.data ?? null;
  const historico = historicoQ.data ?? [];
  const setorial = setorialQ.data ?? null;

  const carregando =
    executivoQ.isFetching || nacionalQ.isFetching || scoreQ.isFetching ||
    nacMercQ.isFetching || regMercQ.isFetching || corMercQ.isFetching ||
    statusQ.isFetching || historicoQ.isFetching || setorialQ.isFetching || calcularMut.isPending;
  const erro = executivoQ.error ? extrairErro(executivoQ.error) : "";

  useEffect(() => {
    const e = scoreQ.error || historicoQ.error || setorialQ.error;
    if (e && scoreAtivo) fb.erro(extrairErro(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoreQ.error, historicoQ.error, setorialQ.error, scoreAtivo]);

  const aplicar = () => {
    executivoQ.refetch();
    nacionalQ.refetch();
    scoreQ.refetch();
    nacMercQ.refetch();
    regMercQ.refetch();
    corMercQ.refetch();
  };

  const recalcularScore = async () => {
    try {
      await calcularMut.mutateAsync();
      fb.sucesso("Score recalculado.");
      // A invalidação da mutação recarrega score e histórico automaticamente.
    } catch (e) {
      fb.erro(extrairErro(e));
    }
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
  const totalCriticos = regioesCriticas.length + corredoresCriticos.length;

  const tendencia = (() => {
    const serie = dados?.evolucao || [];
    if (serie.length < 2) return null;
    const delta = serie[serie.length - 1].frete_rs_kg - serie[serie.length - 2].frete_rs_kg;
    if (Math.abs(delta) < 0.001) return { rotulo: "Estável", cor: "default" };
    return delta > 0 ? { rotulo: "Em alta", cor: "error" } : { rotulo: "Em queda", cor: "success" };
  })();

  const irParaComparacao = (escopo) => {
    navigate(`/benchmark/comparativo-mercado?escopo=${escopo}`);
  };

  return (
    <Box>
      <PageHeader
        titulo="Dashboard Executivo"
        subtitulo={
          aba === "geral"
            ? `${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — visão estratégica de benchmark`
            : "Nota de 0 a 100 da saúde da operação"
        }
        acoes={
          aba === "geral" ? (
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
              <TextField label="De" type="date" size="small" value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
              <TextField label="Até" type="date" size="small" value={dataFim}
                onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
              <Button variant="contained" onClick={aplicar} disabled={carregando}>Aplicar</Button>
            </Stack>
          ) : (
            <Button variant="contained" startIcon={<RefreshIcon />} onClick={recalcularScore} disabled={carregando}>
              Recalcular
            </Button>
          )
        }
      />

      <Box sx={{ mb: 2.5 }}>
        <ToggleButtonGroup exclusive value={aba} onChange={(_, v) => v && setAba(v)} size="small">
          <ToggleButton value="geral">Visão Geral</ToggleButton>
          <ToggleButton value="score">Score Logístico</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {aba === "geral" && erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {aba === "score" ? (
        <>
          <ModoSimuladoBanner status={status} />

          <Alert
            severity="info" variant="outlined" sx={{ mb: 2 }}
            action={
              <Button size="small" onClick={() => irParaComparacao("CORREDOR")}>
                Ver Índice do Corredor
              </Button>
            }
          >
            Este é o <strong>Score Logístico Geral</strong> — soma 5 componentes ponderados da
            operação inteira (30/20/20/15/15). Não confundir com o <strong>Índice de
            Competitividade do Corredor</strong>, na tela Comparação com o Mercado (aba Hubs),
            que usa só R$/kg e %Frete de um corredor específico (60%/40%).
          </Alert>

          <ScoreLogisticoView score={score} historico={historico} setorial={setorial} />
        </>
      ) : dados && (
        <>
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

          {/* Benchmark, Economia e Risco — cards de ação que levam à tela de detalhe */}
          <Typography variant="overline" color="text.secondary">Benchmark, Economia e Risco</Typography>
          <Grid container spacing={2.5} sx={{ mt: 0, mb: 2 }}>
            <Grid item xs={12} sm={6} md={3}>
              <CardAcao
                rotulo="Score Benchmark" valor={score ? fmtNumero(score.score_total, 0) : "—"}
                legenda={score?.classificacao} cor={GD.indigo}
                acaoRotulo="Ver composição →" onAcao={() => setAba("score")}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Percentil Atual" valor={nacionalMercado?.percentil || "—"}
                legenda="posição do R$/kg vs. Matriz Benchmark" cor={GD.blue} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="% acima do Mercado" valor={nacionalMercado?.diferenca_pct != null ? fmtPct(nacionalMercado.diferenca_pct) : "—"}
                legenda="vs. mediana (P50) da Matriz Benchmark" cor={nacionalMercado?.diferenca_pct > 0 ? GD.danger : GD.ok} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <CardAcao
                rotulo="Potencial de Economia" valor={fmtMoeda(dados.economia_total)} legenda="no período"
                cor={GD.amberDark} acaoRotulo="Ver simulador →" onAcao={() => navigate("/benchmark/economia")}
              />
            </Grid>
          </Grid>

          <Grid container spacing={2.5} sx={{ mt: 0, mb: 0.5 }}>
            <Grid item xs={12} md={4}>
              <CardAcao
                rotulo="Corredores / Regiões Críticos" valor={`${corredoresCriticos.length} + ${regioesCriticas.length}`}
                legenda="acima do P75 de mercado" cor={totalCriticos ? GD.danger : GD.ok}
                tint={totalCriticos ? GD.danger : GD.ok}
                acaoRotulo="Ver detalhamento →" onAcao={() => irParaComparacao("REGIAO")}
              />
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
            <Grid item xs={12} md={4}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">Detalhamento completo</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1 }}>
                    Heatmap regional, distribuição percentílica e comparativo por região/corredor
                  </Typography>
                  <Button size="small" sx={{ ml: -1 }} onClick={() => irParaComparacao("REGIAO")}>
                    Ver em Comparação com o Mercado →
                  </Button>
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

          <Card sx={{ mt: 2.5 }}>
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
        </>
      )}
    </Box>
  );
}

// ── Visão · Score Logístico (absorvida de ScoreLogistico.jsx) ──────────────
function ScoreLogisticoView({ score, historico, setorial }) {
  const corClass = score?.classificacao ? COR_CLASSIFICACAO_SCORE[score.classificacao] : GD.indigo;
  const radarData = score
    ? COMPONENTES_SCORE.map((c) => ({
        eixo: c.rotulo,
        valor: score.componentes?.[c.chave] ?? 0,
      }))
    : [];
  const histData = [...historico].reverse().map((h) => ({
    data: new Date(h.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
    score: h.score_total,
  }));

  return (
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
              {COMPONENTES_SCORE.map((c) => {
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
                <ComposedChart data={histData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="data" />
                  <YAxis domain={[0, 100]} />
                  <ReTooltip />
                  <Line type="monotone" dataKey="score" stroke={GD.blue} strokeWidth={2} />
                </ComposedChart>
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
              <Alert severity="warning" sx={{ mb: 2 }}>
                Referências de mercado por setor <strong>preliminares</strong> — valores de
                partida ainda não substituídos por pesquisa de mercado real. Não usar como
                número definitivo em apresentação a cliente.
              </Alert>
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
  );
}
