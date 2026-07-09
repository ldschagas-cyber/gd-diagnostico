import { useEffect, useState, useCallback } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button, Chip,
  LinearProgress, Alert, ToggleButton, ToggleButtonGroup, TextField,
  MenuItem, Table, TableHead, TableRow, TableCell, TableBody, Divider,
} from "@mui/material";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { mblApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtNumero } from "../utils/format";
import { GD } from "../theme";

const DIMENSOES = [
  { v: "REGIAO", l: "Região" },
  { v: "CLUSTER", l: "Cluster" },
  { v: "ROTA", l: "Rota (OD)" },
];
const METRICAS = [
  { v: "RS_KG", l: "R$/kg" },
  { v: "PCT_FRETE", l: "% Frete" },
  { v: "CUSTO_ENTREGA", l: "Custo/entrega" },
];
const COR_FAIXA = { EFICIENTE: GD.ok, NORMAL: GD.blue, INEFICIENTE: GD.danger };

export default function BenchmarkMBL() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const [dimensao, setDimensao] = useState("REGIAO");
  const [metrica, setMetrica] = useState("RS_KG");
  const [rows, setRows] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [threshold, setThreshold] = useState(5);

  // comparador
  const [cmpSegmento, setCmpSegmento] = useState("");
  const [cmpValor, setCmpValor] = useState("");
  const [cmpResult, setCmpResult] = useState(null);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      setRows(await mblApi.benchmark(empresaAtivaId, { dimensao, metrica }));
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, dimensao, metrica, erroToast]);

  useEffect(() => { carregar(); }, [carregar]);

  const processar = async () => {
    if (!empresaAtivaId) return;
    setProcessando(true);
    try {
      const r = await mblApi.processar(empresaAtivaId, { threshold });
      if (r.status === "sem_dados") {
        erroToast("Nenhum CT-e encontrado para construir o benchmark.");
      } else {
        sucesso(`Benchmark gerado: ${r.linhas_benchmark} linhas em ${r.periodos?.length || 0} período(s). Outliers do DLG excluídos.`);
      }
      carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setProcessando(false);
    }
  };

  const comparar = async () => {
    if (!cmpSegmento || !cmpValor) {
      erroToast("Informe o segmento e o valor a comparar.");
      return;
    }
    try {
      const r = await mblApi.comparar(empresaAtivaId, {
        dimensao, segmento: cmpSegmento, metrica, valor: Number(cmpValor),
      });
      setCmpResult(r);
    } catch (e) {
      setCmpResult(null);
      erroToast(extrairErro(e));
    }
  };

  // dados do gráfico de curvas percentílicas (por segmento)
  const chartData = rows.map((r) => ({
    segmento: r.segmento,
    P10: r.p10, P25: r.p25, P50: r.p50, P75: r.p75, P90: r.p90,
  }));
  const segmentos = [...new Set(rows.map((r) => r.segmento))];

  return (
    <Box>
      <PageHeader
        titulo="Benchmark Logístico (MBL)"
        subtitulo="Referência estatística de custo logístico — percentis P10–P90, excluindo outliers do DLG"
      />

      {/* Barra de processamento */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
            <TextField
              label="Amostra mínima" type="number" size="small" value={threshold}
              onChange={(e) => setThreshold(Math.max(1, Number(e.target.value) || 1))}
              sx={{ width: 140 }} helperText="abaixo disso = low confidence"
            />
            <Button
              variant="contained" startIcon={<PlayArrowIcon />}
              onClick={processar} disabled={processando || !empresaAtivaId}
            >
              {processando ? "Processando…" : "Gerar benchmark"}
            </Button>
            <Typography variant="caption" color="text.secondary">
              Recálculo versionado e auditável — outliers do DLG não entram no cálculo.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      {/* Filtros */}
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        <ToggleButtonGroup size="small" exclusive value={dimensao} onChange={(_, v) => v && setDimensao(v)}>
          {DIMENSOES.map((d) => <ToggleButton key={d.v} value={d.v}>{d.l}</ToggleButton>)}
        </ToggleButtonGroup>
        <ToggleButtonGroup size="small" exclusive value={metrica} onChange={(_, v) => v && setMetrica(v)}>
          {METRICAS.map((m) => <ToggleButton key={m.v} value={m.v}>{m.l}</ToggleButton>)}
        </ToggleButtonGroup>
      </Stack>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {rows.length === 0 && !carregando ? (
        <Alert severity="info">
          Nenhum benchmark gerado para esta combinação. Clique em <strong>Gerar benchmark</strong> e
          confira as dimensões/métricas disponíveis.
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {/* Curvas percentílicas */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                  Curvas percentílicas — {METRICAS.find((m) => m.v === metrica)?.l} por {DIMENSOES.find((d) => d.v === dimensao)?.l.toLowerCase()}
                </Typography>
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,53,97,0.08)" />
                    <XAxis dataKey="segmento" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <ReTooltip />
                    <Legend />
                    <Line type="monotone" dataKey="P10" stroke={GD.ok} strokeWidth={1.5} dot={false} />
                    <Line type="monotone" dataKey="P25" stroke={GD.blue} strokeWidth={1.5} dot={false} />
                    <Line type="monotone" dataKey="P50" stroke={GD.indigo} strokeWidth={2.5} dot />
                    <Line type="monotone" dataKey="P75" stroke={GD.amber} strokeWidth={1.5} dot={false} />
                    <Line type="monotone" dataKey="P90" stroke={GD.danger} strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <Typography variant="caption" color="text.secondary">
                  Faixas: ≤ P25 eficiente · P25–P75 normal · ≥ P75 ineficiente.
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Comparador */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                  <CompareArrowsIcon fontSize="small" sx={{ verticalAlign: "middle", mr: 0.5 }} />
                  Comparar valor real
                </Typography>
                <Stack spacing={1.5}>
                  <TextField
                    select label="Segmento" size="small" value={cmpSegmento}
                    onChange={(e) => setCmpSegmento(e.target.value)}
                  >
                    {segmentos.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                  </TextField>
                  <TextField
                    label="Valor real" type="number" size="small" value={cmpValor}
                    onChange={(e) => setCmpValor(e.target.value)}
                  />
                  <Button variant="outlined" onClick={comparar}>Comparar</Button>
                </Stack>
                {cmpResult && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ mb: 1.5 }} />
                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                      <Chip
                        label={cmpResult.faixa}
                        sx={{ bgcolor: (COR_FAIXA[cmpResult.faixa] || GD.slate) + "22",
                              color: COR_FAIXA[cmpResult.faixa] || GD.slate, fontWeight: 700 }}
                      />
                      <Typography variant="body2">
                        desvio vs P50: <strong style={{ color: cmpResult.desvio_p50_pct > 0 ? GD.danger : GD.ok }}>
                          {cmpResult.desvio_p50_pct > 0 ? "+" : ""}{fmtNumero(cmpResult.desvio_p50_pct, 1)}%
                        </strong>
                      </Typography>
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                      P50 de referência: {fmtNumero(cmpResult.p50, 4)} · amostra {cmpResult.amostra}
                      {cmpResult.low_confidence ? " · ⚠ low confidence" : ""}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Tabela de benchmark */}
          <Grid item xs={12} md={8}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                  Datasets percentílicos
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Segmento</TableCell>
                      <TableCell>Período</TableCell>
                      <TableCell align="right">P10</TableCell>
                      <TableCell align="right">P25</TableCell>
                      <TableCell align="right">P50</TableCell>
                      <TableCell align="right">P75</TableCell>
                      <TableCell align="right">P90</TableCell>
                      <TableCell align="right">Amostra</TableCell>
                      <TableCell align="center">Conf.</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r) => (
                      <TableRow key={r.id} hover>
                        <TableCell sx={{ fontWeight: 600 }}>{r.segmento}</TableCell>
                        <TableCell>
                          {r.periodo_ref} <Typography variant="caption" color="text.secondary">v{r.versao}</Typography>
                        </TableCell>
                        <TableCell align="right">{fmtNumero(r.p10, 4)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.p25, 4)}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtNumero(r.p50, 4)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.p75, 4)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.p90, 4)}</TableCell>
                        <TableCell align="right">{r.amostra}</TableCell>
                        <TableCell align="center">
                          {r.low_confidence
                            ? <Chip size="small" label="baixa" color="warning" variant="outlined" />
                            : <Chip size="small" label="ok" color="success" variant="outlined" />}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
