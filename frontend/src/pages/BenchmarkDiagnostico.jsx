import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button, MenuItem,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress,
  Alert, Tooltip, Grid, Tab, Tabs, Dialog, DialogTitle, DialogContent, DialogActions,
} from "@mui/material";
import { useState } from "react";
import RouteIcon from "@mui/icons-material/Route";
import AddchartIcon from "@mui/icons-material/Addchart";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend,
} from "recharts";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import BenchmarkComparacao from "../components/BenchmarkComparacao";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBenchmarkNacional, useBenchmarkRegional, useBenchmarkCorredores, useTransportadoras } from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtRsKg, fmtPct, rotuloMacro } from "../utils/format";
import { corClassificacao, corDesvio, fmtDesvio } from "../utils/benchmark";
import { GD } from "../theme";

function corScore(score) {
  if (score >= 75) return "success";
  if (score >= 60) return "warning";
  return "error";
}

// ── Aba Nacional ─────────────────────────────────────────────────────────
function AbaNacional({ empresaAtivaId, dataInicio, dataFim }) {
  const [transportadoraId, setTransportadoraId] = useState("");
  const [criteriosAberto, setCriteriosAberto] = useState(false);

  const { data: transportadoras = [] } = useTransportadoras(empresaAtivaId);

  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  if (transportadoraId) params.transportadora_id = transportadoraId;
  const { data: dados, isFetching: carregando, error } = useBenchmarkNacional(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const semDados = dados && dados.qtd_ctes === 0;

  return (
    <Box sx={{ pt: 2.5 }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2.5 }}>
        <TextField
          select label="Transportadora" size="small" value={transportadoraId}
          onChange={(e) => setTransportadoraId(e.target.value)} sx={{ width: 220 }}
        >
          <MenuItem value="">Todas</MenuItem>
          {transportadoras.map((t) => (
            <MenuItem key={t.id} value={t.id}>{t.nome_fantasia || t.razao_social}</MenuItem>
          ))}
        </TextField>
      </Stack>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {semDados && !carregando && <Alert severity="info" sx={{ mb: 2 }}>Nenhum CT-e no período selecionado.</Alert>}

      {dados && (
        <>
          <Grid container spacing={2.5} sx={{ mb: 1 }}>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Frete Total (R$)" valor={fmtMoeda(dados.valor_total_frete)}
                legenda={`${dados.qtd_ctes} CT-es`} cor={GD.indigo} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Mercadoria (R$)" valor={fmtMoeda(dados.valor_total_mercadoria)} cor={GD.blue} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Peso Transportado (kg)" valor={`${fmtNumero(dados.peso_total, 0)} kg`} cor={GD.ok} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Custo Médio (R$/kg)" valor={fmtRsKg(dados.frete_kg.valor)} cor={GD.amberDark} />
            </Grid>
          </Grid>

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <BenchmarkComparacao titulo="Custo por kg × Matriz Benchmark (OD)" comp={dados.frete_kg} formatar={(v) => fmtRsKg(v)} />
            </Grid>
            <Grid item xs={12} md={6}>
              <BenchmarkComparacao titulo="% Frete s/ mercadoria" comp={dados.frete_pct} formatar={(v) => fmtPct(v)} />
            </Grid>
          </Grid>

          <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
            <Button size="small" startIcon={<InfoOutlinedIcon fontSize="small" />} onClick={() => setCriteriosAberto(true)} sx={{ color: "text.secondary" }}>
              Critérios de classificação
            </Button>
          </Stack>

          <Dialog open={criteriosAberto} onClose={() => setCriteriosAberto(false)} maxWidth="sm" fullWidth>
            <DialogTitle>Critérios de classificação</DialogTitle>
            <DialogContent>
              <Typography variant="body2" color="text.secondary">
                A classificação do custo por kg é relativa à Matriz Benchmark (OD)
                (≤ mediana: Excelente · até +10%: Bom · até +20%: Atenção · acima: Crítico). O
                percentual de frete usa faixas fixas de mercado (≤5% Excelente, 5–8% Muito Bom,
                8–12% Atenção, 12–18% Crítico, &gt;18% Muito Crítico).
              </Typography>
            </DialogContent>
            <DialogActions><Button onClick={() => setCriteriosAberto(false)}>Fechar</Button></DialogActions>
          </Dialog>
        </>
      )}
    </Box>
  );
}

// ── Aba Regional ─────────────────────────────────────────────────────────
function AbaRegional({ empresaAtivaId, dataInicio, dataFim }) {
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: dados = [], isFetching: carregando, error } = useBenchmarkRegional(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const grafico = dados.map((r) => ({
    nome: rotuloMacro(r.macro_regiao),
    "R$/kg": Number(r.frete_kg.valor.toFixed(4)),
    "Matriz Benchmark (OD)": Number(r.frete_kg.benchmark_medio.toFixed(4)),
  }));

  return (
    <Box sx={{ pt: 2.5 }}>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {!carregando && !dados.length && <Alert severity="info" sx={{ mb: 2 }}>Nenhum dado regional no período.</Alert>}

      {dados.length > 0 && (
        <>
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Custo por kg × Matriz Benchmark (OD) — por região</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={grafico}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="nome" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <ReTooltip formatter={(v) => fmtRsKg(v)} />
                  <Legend />
                  <Bar dataKey="R$/kg" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={38} />
                  <Line dataKey="Matriz Benchmark (OD)" stroke={GD.amber} strokeWidth={3} dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Detalhamento por região</Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Região</TableCell>
                      <TableCell align="right">CT-es</TableCell>
                      <TableCell align="right">Frete total</TableCell>
                      <TableCell align="right">R$/kg</TableCell>
                      <TableCell align="right">Referência</TableCell>
                      <TableCell align="right">Desvio</TableCell>
                      <TableCell align="center">Classificação</TableCell>
                      <TableCell align="right">% Frete</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dados.map((r) => (
                      <TableRow key={r.macro_regiao}>
                        <TableCell sx={{ fontWeight: 600 }}>{rotuloMacro(r.macro_regiao)}</TableCell>
                        <TableCell align="right">{r.qtd_ctes}</TableCell>
                        <TableCell align="right">{fmtMoeda(r.frete_total)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.frete_kg.valor, 4)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.frete_kg.benchmark_medio, 4)}</TableCell>
                        <TableCell align="right" sx={{ color: corDesvio(r.frete_kg.desvio_pct), fontWeight: 600 }}>
                          {fmtDesvio(r.frete_kg.desvio_pct)}
                        </TableCell>
                        <TableCell align="center">
                          <Chip size="small" label={r.frete_kg.classificacao} color={corClassificacao(r.frete_kg.classificacao)} />
                        </TableCell>
                        <TableCell align="right">{fmtPct(r.frete_pct.valor)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}

// ── Aba Corredor (OD) ────────────────────────────────────────────────────
function AbaCorredor({ empresaAtivaId, dataInicio, dataFim }) {
  const navigate = useNavigate();

  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: dados, isFetching: carregando, error } = useBenchmarkCorredores(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const corredores = dados?.corredores || [];
  const semRef = dados?.corredores_sem_referencia || 0;

  return (
    <Box sx={{ pt: 2.5 }}>
      <Alert severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}>
        O benchmark por corredor compara cada fluxo <strong>Origem → Destino</strong> contra a
        referência do próprio corredor (legado, hub-a-hub) — evita o viés de comparar apenas
        pelo destino.
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && (
        <>
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Score Global" valor={dados.classificacao_global === "Sem referência" ? "—" : fmtNumero(dados.score_global, 1)} legenda={dados.classificacao_global} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Corredores" valor={String(dados.qtd_corredores)} legenda="fluxos OD identificados" />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Frete total" valor={fmtMoeda(dados.frete_total)} legenda="no período" />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Sem referência" valor={String(semRef)} legenda={semRef ? "corredores a cadastrar" : "todos cobertos"} />
            </Grid>
          </Grid>

          {semRef > 0 && (
            <Alert severity="warning" sx={{ mb: 2.5 }} action={
              <Button color="inherit" size="small" startIcon={<AddchartIcon />} onClick={() => navigate("/configuracoes/corredores")}>
                Cadastrar referências
              </Button>
            }>
              {semRef} corredor(es) sem referência cadastrada.
            </Alert>
          )}

          {!corredores.length ? (
            <Alert severity="info">Nenhum fluxo OD no período selecionado.</Alert>
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>Corredores (Origem → Destino)</Typography>
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Corredor</TableCell>
                        <TableCell align="right">CT-es</TableCell>
                        <TableCell align="right">Frete total</TableCell>
                        <TableCell align="right">R$/kg</TableCell>
                        <TableCell align="right">Ref. média</TableCell>
                        <TableCell align="right">Desvio</TableCell>
                        <TableCell align="right">% Frete</TableCell>
                        <TableCell align="center">Score</TableCell>
                        <TableCell align="center">Classificação</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {corredores.map((c, i) => (
                        <TableRow key={`${c.hub_origem}-${c.hub_destino}-${i}`}>
                          <TableCell sx={{ fontWeight: 600 }}>
                            <Tooltip title={`Origens: ${c.ufs_origem.join(", ") || "—"} • Destinos: ${c.ufs_destino.join(", ") || "—"}`}>
                              <span>{c.corredor}</span>
                            </Tooltip>
                          </TableCell>
                          <TableCell align="right">{c.qtd_ctes}</TableCell>
                          <TableCell align="right">{fmtMoeda(c.frete_total)}</TableCell>
                          <TableCell align="right">{fmtNumero(c.frete_rs_kg, 4)}</TableCell>
                          <TableCell align="right">{c.tem_referencia ? fmtNumero(c.frete_kg.benchmark_medio, 4) : "—"}</TableCell>
                          <TableCell align="right" sx={{ color: c.tem_referencia ? corDesvio(c.frete_kg.desvio_pct) : "text.disabled", fontWeight: 600 }}>
                            {c.tem_referencia ? fmtDesvio(c.frete_kg.desvio_pct) : "—"}
                          </TableCell>
                          <TableCell align="right">{fmtPct(c.frete_pct)}</TableCell>
                          <TableCell align="center">
                            {c.tem_referencia
                              ? <Chip size="small" label={fmtNumero(c.score, 0)} color={corScore(c.score)} />
                              : <Chip size="small" label="—" variant="outlined" />}
                          </TableCell>
                          <TableCell align="center">
                            <Chip size="small" label={c.classificacao} color={corClassificacao(c.classificacao)} variant={c.tem_referencia ? "filled" : "outlined"} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
}

export default function BenchmarkDiagnostico() {
  const { empresaAtivaId } = useEmpresa();
  const [tela, , patch] = useTelaEstado("benchmark-diagnostico", { aba: 0, dataInicio: "", dataFim: "" });
  const { aba, dataInicio, dataFim } = tela;
  const setAba = (v) => patch({ aba: v });
  const setDataInicio = (v) => patch({ dataInicio: v });
  const setDataFim = (v) => patch({ dataFim: v });

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Diagnóstico" subtitulo="Nacional · Regional · Corredor (OD) — operação × Matriz Benchmark (OD)" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Diagnóstico"
        subtitulo="Operação × Matriz Benchmark (OD), por dimensão"
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <TextField label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
          </Stack>
        }
      />

      <Card>
        <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}>
          <Tab label="Nacional" />
          <Tab label="Regional" />
          <Tab label="Corredor (OD)" />
        </Tabs>
        <CardContent>
          {aba === 0 && <AbaNacional empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />}
          {aba === 1 && <AbaRegional empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />}
          {aba === 2 && <AbaCorredor empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />}
        </CardContent>
      </Card>
    </Box>
  );
}
