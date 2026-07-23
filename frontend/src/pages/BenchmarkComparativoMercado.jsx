import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button, MenuItem,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress, Alert,
  ToggleButton, ToggleButtonGroup, Tooltip, Grid, Dialog, DialogTitle, DialogContent, DialogActions,
} from "@mui/material";
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
import IndicadoresTransversais from "../components/IndicadoresTransversais";
import LegendaBenchmark from "../components/LegendaBenchmark";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import {
  useBenchmarkNacional, useBenchmarkRegional, useBenchmarkCorredores,
  useBenchmarkTransportadoras, useTransportadoras, useFiliais, useComparativoMercado,
} from "../api/queries";
import { useTelaEstado, useBenchmarkPeriodo } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtRsKg, fmtPct, rotuloMacro } from "../utils/format";
import { corClassificacao, corDesvio, fmtDesvio, rotuloClassificacaoMercado } from "../utils/benchmark";
import { GD } from "../theme";

// Fusão de "Desvio vs. Benchmark" + "Comparativo de Mercado": mesmo escopo
// (Nacional/Região/Hubs/Transportadora/Cliente) alimenta duas visões —
// Resumo (classificação por faixa fixa, use cases geográficos existentes) e
// Detalhado (percentis P10-P90 vs. mercado, `comparativo_mercado`). São
// vocabulários de classificação genuinamente diferentes (ver utils/benchmark.js),
// não o mesmo dado renderizado de duas formas.
const ESCOPOS = [
  { valor: "NACIONAL", rotulo: "Nacional" },
  { valor: "REGIAO", rotulo: "Região" },
  { valor: "CORREDOR", rotulo: "Hubs" },
  { valor: "TRANSPORTADORA", rotulo: "Transportadora" },
  { valor: "CLIENTE", rotulo: "Cliente" },
];

function corScore(score) {
  if (score >= 75) return "success";
  if (score >= 60) return "warning";
  return "error";
}

function rotuloLinha(linha, escopo) {
  if (escopo === "CORREDOR") return `${rotuloMacro(linha.origem_regiao)} → ${rotuloMacro(linha.destino_regiao)}`;
  if (escopo === "REGIAO") return rotuloMacro(linha.destino_regiao);
  if (escopo === "TRANSPORTADORA") return linha.transportadora_nome;
  if (escopo === "CLIENTE") return linha.cliente_nome;
  return "Brasil (todos os corredores)";
}

// ── Resumo · Nacional ───────────────────────────────────────────────────
function ResumoNacional({ empresaAtivaId, dataInicio, dataFim, transportadoraId, filialCnpj }) {
  const [criteriosAberto, setCriteriosAberto] = useState(false);

  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  if (transportadoraId) params.transportadora_id = transportadoraId;
  if (filialCnpj) params.filial_cnpj = filialCnpj;
  const { data: dados, isFetching: carregando, error } = useBenchmarkNacional(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const semDados = dados && dados.qtd_ctes === 0;

  return (
    <Box>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {semDados && !carregando && <Alert severity="info" sx={{ mb: 2 }}>Nenhum CT-e no período/filtros selecionados.</Alert>}

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
              <BenchmarkComparacao titulo="Custo por kg × Matriz Benchmark" comp={dados.frete_kg} formatar={(v) => fmtRsKg(v)} />
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
                A classificação do custo por kg é relativa à Matriz Benchmark
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

// ── Resumo · Regional ───────────────────────────────────────────────────
function ResumoRegional({ empresaAtivaId, dataInicio, dataFim, transportadoraId, filialCnpj }) {
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  if (transportadoraId) params.transportadora_id = transportadoraId;
  if (filialCnpj) params.filial_cnpj = filialCnpj;
  const { data: dados = [], isFetching: carregando, error } = useBenchmarkRegional(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const grafico = dados.map((r) => ({
    nome: rotuloMacro(r.macro_regiao),
    "R$/kg": Number(r.frete_kg.valor.toFixed(4)),
    "Matriz Benchmark": Number(r.frete_kg.benchmark_medio.toFixed(4)),
  }));

  return (
    <Box>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {!carregando && !dados.length && <Alert severity="info" sx={{ mb: 2 }}>Nenhum dado regional no período/filtros.</Alert>}

      {dados.length > 0 && (
        <>
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Custo por kg × Matriz Benchmark — por região</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={grafico}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="nome" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <ReTooltip formatter={(v) => fmtRsKg(v)} />
                  <Legend />
                  <Bar dataKey="R$/kg" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={38} />
                  <Line dataKey="Matriz Benchmark" stroke={GD.amber} strokeWidth={3} dot={{ r: 4 }} />
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
                        <TableCell align="right">{fmtNumero(r.frete_kg.valor, 2)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.frete_kg.benchmark_medio, 2)}</TableCell>
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

// ── Resumo · Hubs (corredor hub-a-hub) ───────────────────────────────────
function ResumoHubs({ empresaAtivaId, dataInicio, dataFim }) {
  const navigate = useNavigate();
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: dados, isFetching: carregando, error } = useBenchmarkCorredores(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const corredores = dados?.corredores || [];
  const semRef = dados?.corredores_sem_referencia || 0;

  return (
    <Box>
      <Alert
        severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}
        action={
          <Button size="small" onClick={() => navigate("/benchmark/executivo?aba=score")}>
            Ver Score Logístico Geral
          </Button>
        }
      >
        O <strong>Índice de Competitividade do Corredor</strong> (mercado) compara cada fluxo Hub
        Origem → Hub Destino contra a referência do próprio corredor entre hubs — evita o viés de
        comparar apenas pelo destino. É diferente do Score Logístico Geral (operação inteira, 5
        componentes), no Dashboard Executivo (aba Score Logístico).
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && (
        <>
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Índice de Competitividade do Corredor" valor={dados.classificacao_global === "Sem referência" ? "—" : fmtNumero(dados.score_global, 1)} legenda={dados.classificacao_global} />
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
                        <TableCell align="center">Índice</TableCell>
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
                          <TableCell align="right">{fmtNumero(c.frete_rs_kg, 2)}</TableCell>
                          <TableCell align="right">{c.tem_referencia ? fmtNumero(c.frete_kg.benchmark_medio, 2) : "—"}</TableCell>
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

// ── Resumo · Transportadora ──────────────────────────────────────────────
function ResumoTransportadora({ empresaAtivaId, dataInicio, dataFim }) {
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: dados = [], isFetching: carregando, error } = useBenchmarkTransportadoras(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  return (
    <Box>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {!carregando && !dados.length && <Alert severity="info">Nenhuma transportadora com CT-e no período.</Alert>}

      {dados.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>Ranking por custo (R$/kg)</Typography>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Transportadora</TableCell>
                    <TableCell align="right">Frete total</TableCell>
                    <TableCell align="right">Participação</TableCell>
                    <TableCell align="right">R$/kg</TableCell>
                    <TableCell align="right">Desvio</TableCell>
                    <TableCell align="center">Nível de custo</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dados.map((t) => (
                    <TableRow key={t.transportadora_id}>
                      <TableCell sx={{ fontWeight: 600 }}>{t.nome}</TableCell>
                      <TableCell align="right">{fmtMoeda(t.frete_total)}</TableCell>
                      <TableCell align="right">{fmtPct(t.participacao_pct)}</TableCell>
                      <TableCell align="right">{fmtNumero(t.frete_kg.valor, 2)}</TableCell>
                      <TableCell align="right" sx={{ color: corDesvio(t.frete_kg.desvio_pct), fontWeight: 600 }}>
                        {fmtDesvio(t.frete_kg.desvio_pct)}
                      </TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={t.nivel_custo} color={corClassificacao(t.frete_kg.classificacao)} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

// ── Detalhado (percentis P10-P90, todos os escopos) ──────────────────────
function Detalhado({ empresaAtivaId, escopo, dataInicio, dataFim, clienteBusca }) {
  const params = { escopo };
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  if (escopo === "CLIENTE" && clienteBusca) params.busca = clienteBusca;
  const { data: linhas = [], isFetching: carregando, error } = useComparativoMercado(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  const mostraPercentil = escopo !== "TRANSPORTADORA" && escopo !== "CLIENTE";

  return (
    <Box>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {!carregando && !linhas.length && (
        <Alert severity="info">
          Sem dados observados de mercado no período — importe CT-es ou gere o Benchmark
          Observado para este recorte.
        </Alert>
      )}

      {linhas.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {escopo === "CORREDOR" ? "Corredor"
                        : escopo === "REGIAO" ? "Região"
                        : escopo === "TRANSPORTADORA" ? "Transportadora"
                        : escopo === "CLIENTE" ? "Cliente"
                        : "Escopo"}
                    </TableCell>
                    <TableCell align="right">CT-es</TableCell>
                    <TableCell align="right">Cliente (P50)</TableCell>
                    <TableCell align="right">P10</TableCell>
                    <TableCell align="right">P25</TableCell>
                    <TableCell align="right">P50</TableCell>
                    <TableCell align="right">P75</TableCell>
                    <TableCell align="right">P90</TableCell>
                    {mostraPercentil && <TableCell align="center">Percentil</TableCell>}
                    <TableCell align="right">Diferença</TableCell>
                    <TableCell align="center">Classificação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {linhas.map((l, i) => (
                    <TableRow key={i}>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {rotuloLinha(l, escopo)}
                        {l.low_confidence && (
                          <Tooltip title="Amostra pequena (menos de 5 CT-es) — interpretar com cautela">
                            <Chip size="small" label="baixa confiança" variant="outlined" color="warning" sx={{ ml: 1 }} />
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell align="right">{l.qtd_ctes}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtNumero(l.cliente_p50, 2)}</TableCell>
                      <TableCell align="right">{l.mercado_p10 != null ? fmtNumero(l.mercado_p10, 2) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p25 != null ? fmtNumero(l.mercado_p25, 2) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p50 != null ? fmtNumero(l.mercado_p50, 2) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p75 != null ? fmtNumero(l.mercado_p75, 2) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p90 != null ? fmtNumero(l.mercado_p90, 2) : "—"}</TableCell>
                      {mostraPercentil && (
                        <TableCell align="center">
                          <Chip size="small" label={l.percentil} variant="outlined" />
                        </TableCell>
                      )}
                      <TableCell align="right" sx={{ color: corDesvio(l.diferenca_pct), fontWeight: 600 }}>
                        {l.diferenca_pct != null ? fmtDesvio(l.diferenca_pct) : "—"}
                      </TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={rotuloClassificacaoMercado(l.classificacao)} color={corClassificacao(l.classificacao)} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

export default function BenchmarkComparativoMercado() {
  const { empresaAtivaId } = useEmpresa();
  const [searchParams] = useSearchParams();
  const [periodo, , patchPeriodo] = useBenchmarkPeriodo();
  const { dataInicio, dataFim } = periodo;
  const setDataInicio = (v) => patchPeriodo({ dataInicio: v });
  const setDataFim = (v) => patchPeriodo({ dataFim: v });

  const [tela, , patch] = useTelaEstado("benchmark-comparativo-mercado", {
    escopo: "NACIONAL", visao: "RESUMO",
    transportadoraId: "", filialCnpj: "", clienteBusca: "",
  });
  const { escopo, visao, transportadoraId, filialCnpj, clienteBusca } = tela;
  // Cliente não tem versão Resumo (não existe use case de faixa fixa para
  // cliente — a Matriz Benchmark não segmenta por cliente) — força Detalhado.
  const setEscopo = (v) => patch(v === "CLIENTE" ? { escopo: v, visao: "DETALHADO" } : { escopo: v });
  const setVisao = (v) => patch({ visao: v });
  const setTransportadoraId = (v) => patch({ transportadoraId: v });
  const setFilialCnpj = (v) => patch({ filialCnpj: v });
  const setClienteBusca = (v) => patch({ clienteBusca: v });

  // Deep-link vindo do Dashboard Executivo (ex.: ?escopo=REGIAO) — sobrescreve
  // o estado salvo uma única vez, no mount.
  useEffect(() => {
    const escopoParam = searchParams.get("escopo");
    if (escopoParam && ESCOPOS.some((e) => e.valor === escopoParam)) {
      patch({ escopo: escopoParam, visao: searchParams.get("visao") === "DETALHADO" ? "DETALHADO" : "RESUMO" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: transportadoras = [] } = useTransportadoras(empresaAtivaId);
  const { data: filiais = [] } = useFiliais(empresaAtivaId);

  // busca de cliente com pequeno debounce — evita 1 request por tecla
  const [clienteBuscaInput, setClienteBuscaInput] = useState(clienteBusca);
  useEffect(() => {
    const t = setTimeout(() => setClienteBusca(clienteBuscaInput), 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteBuscaInput]);

  const filtrosResumoDisponiveis = visao === "RESUMO" && (escopo === "NACIONAL" || escopo === "REGIAO");
  const resumoIndisponivel = escopo === "CLIENTE";

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Comparação com o Mercado" subtitulo="Operação × Matriz Benchmark, por dimensão" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Comparação com o Mercado"
        subtitulo="Operação × Matriz Benchmark (P10-P90) — fonte: mercado externo"
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center" flexWrap="wrap" sx={{ rowGap: 1 }}>
            <TextField label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <TextField label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <Tooltip title={filtrosResumoDisponiveis ? "" : "Disponível no Resumo de Nacional/Região"}>
              <TextField
                select label="Transportadora" size="small" value={transportadoraId}
                onChange={(e) => setTransportadoraId(e.target.value)}
                disabled={!filtrosResumoDisponiveis} sx={{ width: 190 }}
              >
                <MenuItem value="">Todas</MenuItem>
                {transportadoras.map((t) => (
                  <MenuItem key={t.id} value={t.id}>{t.nome_fantasia || t.razao_social}</MenuItem>
                ))}
              </TextField>
            </Tooltip>
            <Tooltip title={filtrosResumoDisponiveis ? "" : "Disponível no Resumo de Nacional/Região"}>
              <TextField
                select label="Filial" size="small" value={filialCnpj}
                onChange={(e) => setFilialCnpj(e.target.value)}
                disabled={!filtrosResumoDisponiveis} sx={{ width: 190 }}
              >
                <MenuItem value="">Todas</MenuItem>
                {filiais.map((f) => (
                  <MenuItem key={f.id} value={f.cnpj}>{f.razao_social}</MenuItem>
                ))}
              </TextField>
            </Tooltip>
          </Stack>
        }
      />

      <LegendaBenchmark fonte="MERCADO" mostrarClassificacao={visao === "DETALHADO"} />
      <IndicadoresTransversais empresaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} justifyContent="space-between" flexWrap="wrap" sx={{ mb: 2.5, rowGap: 1.5 }}>
        <ToggleButtonGroup exclusive value={escopo} onChange={(_, v) => v && setEscopo(v)} size="small">
          {ESCOPOS.map((e) => <ToggleButton key={e.valor} value={e.valor}>{e.rotulo}</ToggleButton>)}
        </ToggleButtonGroup>

        <Tooltip title={resumoIndisponivel ? "Não há versão resumida para Cliente — só o detalhamento percentílico está disponível." : ""}>
          <ToggleButtonGroup exclusive value={visao} onChange={(_, v) => v && setVisao(v)} size="small">
            <ToggleButton value="RESUMO" disabled={resumoIndisponivel}>Resumo</ToggleButton>
            <ToggleButton value="DETALHADO">Detalhado</ToggleButton>
          </ToggleButtonGroup>
        </Tooltip>
      </Stack>

      {escopo === "CLIENTE" && visao === "DETALHADO" && (
        <TextField
          label="Buscar cliente" size="small" value={clienteBuscaInput}
          onChange={(e) => setClienteBuscaInput(e.target.value)}
          placeholder="Nome do cliente..." sx={{ mb: 2.5, width: 280 }}
        />
      )}

      {escopo === "CORREDOR" && (transportadoraId || filialCnpj) && (
        <Alert severity="warning" sx={{ mb: 2.5 }}>
          Filtro de Transportadora/Filial ainda não é aplicado na aba Hubs — mostrando todos os fluxos.
        </Alert>
      )}

      {visao === "RESUMO" ? (
        <>
          {escopo === "NACIONAL" && <ResumoNacional empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} transportadoraId={transportadoraId} filialCnpj={filialCnpj} />}
          {escopo === "REGIAO" && <ResumoRegional empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} transportadoraId={transportadoraId} filialCnpj={filialCnpj} />}
          {escopo === "CORREDOR" && <ResumoHubs empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />}
          {escopo === "TRANSPORTADORA" && <ResumoTransportadora empresaAtivaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />}
        </>
      ) : (
        <Detalhado empresaAtivaId={empresaAtivaId} escopo={escopo} dataInicio={dataInicio} dataFim={dataFim} clienteBusca={clienteBusca} />
      )}
    </Box>
  );
}
