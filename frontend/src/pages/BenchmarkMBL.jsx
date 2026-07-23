import { useEffect, useMemo } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button, Chip,
  LinearProgress, Alert, ToggleButton, ToggleButtonGroup, TextField,
  MenuItem, Table, TableHead, TableRow, TableCell, TableBody, Collapse,
  Tooltip,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PageHeader from "../components/PageHeader";
import LegendaBenchmark from "../components/LegendaBenchmark";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { useMblBenchmark, useMblComparar, useProcessarMbl } from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtNumero } from "../utils/format";
import { GD } from "../theme";

const DIMENSOES = [
  { v: "REGIAO", l: "Região" },
  { v: "CLUSTER", l: "Cluster" },
  { v: "ROTA", l: "Rota (OD)" },
  { v: "TRANSPORTADORA", l: "Transportadora" },
  { v: "FILIAL", l: "Filial" },
  { v: "CLIENTE", l: "Cliente" },
];
const DIMENSOES_COM_BUSCA = new Set(["TRANSPORTADORA", "FILIAL", "CLIENTE"]);
const METRICAS = [
  { v: "RS_KG", l: "R$/kg", dec: 2, unit: "R$/kg" },
  { v: "PCT_FRETE", l: "% Frete", dec: 1, unit: "%" },
  { v: "CUSTO_ENTREGA", l: "Custo/entrega", dec: 0, unit: "R$" },
];
const COR_FAIXA = { EFICIENTE: GD.ok, NORMAL: GD.blue, INEFICIENTE: GD.danger };
const STATUS_LABEL = { EFICIENTE: "Eficiente", NORMAL: "Normal", INEFICIENTE: "Ineficiente" };

// Mesma regra de classificação do backend (MblUseCase.faixa).
function classificar(valor, p25, p75) {
  if (valor <= p25) return "EFICIENTE";
  if (valor >= p75) return "INEFICIENTE";
  return "NORMAL";
}
function posicaoPct(v, lo, hi) {
  if (hi === lo) return 0;
  return Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
}

function LegendaItem({ children }) {
  return (
    <Stack direction="row" alignItems="center" spacing={0.75} sx={{ whiteSpace: "nowrap" }}>
      {children}
    </Stack>
  );
}

function KpiCard({ color, label, value, sub, barPct }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color, flex: "none" }} />
          <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {label}
          </Typography>
        </Stack>
        <Typography noWrap sx={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: 26, lineHeight: 1.15 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          {sub}
        </Typography>
        {barPct != null && (
          <Box sx={{ height: 5, borderRadius: 4, bgcolor: "rgba(45,53,97,0.08)", mt: 1.25, overflow: "hidden" }}>
            <Box sx={{ height: "100%", width: `${barPct}%`, bgcolor: color, borderRadius: 4 }} />
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function FaixaRow({ r, lo, hi, dec, unit, cmpMarker, destacado }) {
  const status = classificar(r.media, r.p25, r.p75);
  const desvio = r.p50 ? ((r.media - r.p50) / r.p50) * 100 : 0;
  const lineL = posicaoPct(r.p10, lo, hi), lineW = posicaoPct(r.p90, lo, hi) - lineL;
  const bandL = posicaoPct(r.p25, lo, hi), bandW = posicaoPct(r.p75, lo, hi) - bandL;
  const medP = posicaoPct(r.p50, lo, hi), markP = posicaoPct(r.media, lo, hi);

  const tooltip = (
    <Box sx={{ fontSize: 12, lineHeight: 1.65, minWidth: 190 }}>
      <Box sx={{ fontWeight: 700, mb: 0.5 }}>{r.segmento}</Box>
      {[
        ["P90", r.p90], ["P75", r.p75], ["P50 (mediana)", r.p50], ["P25", r.p25], ["P10", r.p10],
      ].map(([lbl, val]) => (
        <Stack key={lbl} direction="row" justifyContent="space-between" spacing={2}>
          <span>{lbl}</span><b>{fmtNumero(val, dec)}</b>
        </Stack>
      ))}
      <Box sx={{ borderTop: "1px solid rgba(255,255,255,0.25)", my: 0.5 }} />
      <Stack direction="row" justifyContent="space-between" spacing={2}>
        <span>Média (posição atual)</span><b>{fmtNumero(r.media, dec)} · {STATUS_LABEL[status]}</b>
      </Stack>
      <Stack direction="row" justifyContent="space-between" spacing={2}>
        <span>Amostra</span><b>{r.amostra}{r.low_confidence ? " · low conf." : ""}</b>
      </Stack>
    </Box>
  );

  return (
    <Tooltip title={tooltip} arrow placement="top"
      slotProps={{ tooltip: { sx: { bgcolor: GD.indigo, "& .MuiTooltip-arrow": { color: GD.indigo } } } }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "116px 1fr 104px", sm: "200px 1fr 168px" },
          alignItems: "center", gap: 1.5, py: 1, px: 0.5, borderRadius: 1.5,
          bgcolor: destacado ? "rgba(201,168,76,0.16)" : "transparent",
          transition: "background-color 0.2s",
          "&:hover": { bgcolor: destacado ? "rgba(201,168,76,0.22)" : "action.hover" },
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography noWrap sx={{ fontSize: 13.5, fontWeight: 700 }}>{r.segmento}</Typography>
          <Typography sx={{ fontSize: 11, color: "text.secondary" }}>
            amostra {r.amostra}
            {r.low_confidence && <Box component="span" sx={{ color: GD.warn, fontWeight: 700 }}> · low confidence</Box>}
          </Typography>
        </Box>

        <Box sx={{ position: "relative", height: 26 }}>
          <Box sx={{ position: "absolute", top: "50%", left: `${lineL}%`, width: `${lineW}%`, height: 2,
            bgcolor: GD.slate, opacity: 0.5, borderRadius: 1, transform: "translateY(-50%)" }} />
          <Box sx={{ position: "absolute", top: "50%", left: `${bandL}%`, width: `${bandW}%`, height: 11,
            bgcolor: `${GD.blue}33`, border: `1px solid ${GD.blue}88`, borderRadius: 1, transform: "translateY(-50%)" }} />
          <Box sx={{ position: "absolute", top: "50%", left: `${medP}%`, width: 2, height: 19,
            bgcolor: GD.indigo, borderRadius: 1, transform: "translate(-50%,-50%)" }} />
          <Box sx={{ position: "absolute", top: "50%", left: `${markP}%`, width: 11, height: 11, borderRadius: "50%",
            bgcolor: COR_FAIXA[status], boxShadow: "0 0 0 2px #fff", transform: "translate(-50%,-50%)" }} />
          {cmpMarker != null && !Number.isNaN(cmpMarker) && (
            <Box sx={{ position: "absolute", top: "50%", left: `${posicaoPct(cmpMarker, lo, hi)}%`, width: 11, height: 11,
              bgcolor: GD.amberDark, boxShadow: "0 0 0 2px #fff", borderRadius: 0.5,
              transform: "translate(-50%,-50%) rotate(45deg)" }} />
          )}
        </Box>

        <Box sx={{ textAlign: "right" }}>
          <Typography component="span" sx={{ fontWeight: 700, fontSize: 14, fontVariantNumeric: "tabular-nums" }}>
            {fmtNumero(r.media, dec)} {unit}
          </Typography>
          <Typography component="span" sx={{ fontSize: 11.5, fontWeight: 700, ml: 0.6,
            color: desvio > 0.5 ? GD.danger : desvio < -0.5 ? GD.ok : "text.secondary" }}>
            {desvio >= 0 ? "+" : ""}{fmtNumero(desvio, 1)}%
          </Typography>
          <Chip size="small" label={STATUS_LABEL[status]} sx={{ display: "block", mt: 0.4, height: 18, fontSize: 10.5,
            fontWeight: 700, bgcolor: `${COR_FAIXA[status]}22`, color: COR_FAIXA[status] }} />
        </Box>
      </Box>
    </Tooltip>
  );
}

export default function BenchmarkMBL() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const [tela, , patch] = useTelaEstado("benchmark-mbl", {
    dimensao: "REGIAO", metrica: "RS_KG", threshold: 5, buscaSegmento: "",
    cmpSegmento: "", cmpValor: "", cmpValorCommitted: null, tabelaAberta: false,
  });
  const {
    dimensao, metrica, threshold, buscaSegmento,
    cmpSegmento, cmpValor, cmpValorCommitted, tabelaAberta,
  } = tela;
  const setDimensao = (v) => patch({ dimensao: v, cmpSegmento: "", cmpValorCommitted: null });
  const setMetrica = (v) => patch({ metrica: v, cmpValorCommitted: null });
  const setThreshold = (v) => patch({ threshold: v });
  const setBuscaSegmento = (v) => patch({ buscaSegmento: v });
  const setCmpSegmento = (v) => patch({ cmpSegmento: v });
  const setCmpValor = (v) => patch({ cmpValor: v });
  const setTabelaAberta = (v) => patch({ tabelaAberta: v });

  const metricaInfo = METRICAS.find((m) => m.v === metrica);

  const mblParams = { dimensao, metrica };
  if (DIMENSOES_COM_BUSCA.has(dimensao) && buscaSegmento) mblParams.segmento_contains = buscaSegmento;
  const { data: rows = [], isFetching: carregando, error } = useMblBenchmark(empresaAtivaId, mblParams);
  const comparaQ = useMblComparar(empresaAtivaId, {
    dimensao, segmento: cmpSegmento, metrica, valor: cmpValorCommitted,
  });
  const cmpResult = comparaQ.data;
  const processarMut = useProcessarMbl(empresaAtivaId);
  const processando = processarMut.isPending;

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  useEffect(() => {
    if (comparaQ.error) erroToast(extrairErro(comparaQ.error));
  }, [comparaQ.error, erroToast]);

  const processar = async () => {
    if (!empresaAtivaId) return;
    try {
      const r = await processarMut.mutateAsync({ threshold });
      if (r.status === "sem_dados") {
        erroToast("Nenhum CT-e encontrado para construir o benchmark.");
      } else {
        sucesso(`Benchmark gerado: ${r.linhas_benchmark} linhas em ${r.periodos?.length || 0} período(s). Outliers do DLG excluídos.`);
      }
      // A mutação invalida o cache de MBL (benchmark + comparador) automaticamente.
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const comparar = () => {
    if (!cmpSegmento || !cmpValor) {
      erroToast("Informe o segmento e o valor a comparar.");
      return;
    }
    patch({ cmpValorCommitted: Number(cmpValor) });
  };

  // A API devolve o histórico completo (todos os períodos/versões) por
  // segmento, ordenado por periodo_ref desc — fica só o mais recente de cada
  // segmento para o radar e os KPIs; o histórico completo continua na tabela.
  const rowsAtuais = useMemo(() => {
    const vistos = new Set();
    const out = [];
    for (const r of rows) {
      if (!vistos.has(r.segmento)) { vistos.add(r.segmento); out.push(r); }
    }
    return out.sort((a, b) => b.p50 - a.p50);
  }, [rows]);

  const segmentos = useMemo(() => [...new Set(rows.map((r) => r.segmento))], [rows]);

  const escala = useMemo(() => {
    if (rowsAtuais.length === 0) return { lo: 0, hi: 1 };
    const lo = Math.max(0, Math.min(...rowsAtuais.map((r) => r.p10)) * 0.94);
    const hiBruto = Math.max(...rowsAtuais.map((r) => Math.max(r.p90, r.media))) * 1.06;
    return { lo, hi: hiBruto > lo ? hiBruto : lo + 1 };
  }, [rowsAtuais]);

  const kpis = useMemo(() => {
    if (rowsAtuais.length === 0) return null;
    const classificados = rowsAtuais.map((r) => ({
      r, status: classificar(r.media, r.p25, r.p75),
      desvio: r.p50 ? ((r.media - r.p50) / r.p50) * 100 : 0,
    }));
    const normalCount = classificados.filter((c) => c.status !== "INEFICIENTE").length;
    const pctNormal = Math.round((normalCount / classificados.length) * 100);
    const melhor = [...classificados].sort((a, b) => a.desvio - b.desvio)[0];
    const ineficientes = classificados.filter((c) => c.status === "INEFICIENTE");
    const pior = ineficientes.length ? [...ineficientes].sort((a, b) => b.desvio - a.desvio)[0] : null;
    return { normalCount, pctNormal, melhor, pior, total: classificados.length };
  }, [rowsAtuais]);

  return (
    <Box>
      <PageHeader
        titulo="Radar de Custo"
        subtitulo="Histórico próprio da empresa — percentis P10–P90, excluindo outliers do DLG (antes chamado “Benchmark Interno” / “Benchmark (MBL)”)"
      />

      <LegendaBenchmark fonte="INTERNO" />

      <Alert severity="info" sx={{ mb: 2.5 }}>
        Isto <strong>não é</strong> referência de mercado — é estatística calculada sobre o
        histórico de CT-e da própria empresa. Para comparar com o mercado externo, use a tela{" "}
        <strong>Comparação com o Mercado</strong>.
      </Alert>

      {/* Barra de ação */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
            <TextField
              label="Amostra mínima" type="number" size="small" value={threshold}
              onChange={(e) => setThreshold(Math.max(1, Number(e.target.value) || 1))}
              sx={{ width: 160 }}
            />
            <Button
              variant="contained" startIcon={<PlayArrowIcon />}
              onClick={processar} disabled={processando || !empresaAtivaId}
            >
              {processando ? "Processando…" : "Gerar benchmark"}
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
            Abaixo desse valor, o segmento é marcado como low confidence.
          </Typography>
        </CardContent>
      </Card>
      {processando && <LinearProgress sx={{ mb: 2 }} />}

      {/* Filtros */}
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap alignItems="center" sx={{ mb: 2 }}>
        <ToggleButtonGroup size="small" exclusive value={dimensao} onChange={(_, v) => v && setDimensao(v)}>
          {DIMENSOES.map((d) => <ToggleButton key={d.v} value={d.v}>{d.l}</ToggleButton>)}
        </ToggleButtonGroup>
        <ToggleButtonGroup size="small" exclusive value={metrica} onChange={(_, v) => v && setMetrica(v)}>
          {METRICAS.map((m) => <ToggleButton key={m.v} value={m.v}>{m.l}</ToggleButton>)}
        </ToggleButtonGroup>
        {DIMENSOES_COM_BUSCA.has(dimensao) && (
          <TextField
            label="Buscar segmento" size="small" value={buscaSegmento}
            onChange={(e) => setBuscaSegmento(e.target.value)}
            placeholder="Nome..." sx={{ width: 220 }}
          />
        )}
      </Stack>

      {dimensao === "CLIENTE" && (
        <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
          Mostra a posição percentílica de cada cliente vs. o histórico próprio — não substitui o
          diagnóstico causal (adicionais, fragmentação) da tela Recomendações, que já cobre
          clientes com concentração acima do limite.
        </Alert>
      )}

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {rowsAtuais.length === 0 && !carregando ? (
        <Alert severity="info">
          Nenhum benchmark gerado para esta combinação. Clique em <strong>Gerar benchmark</strong> e
          confira as dimensões/métricas disponíveis.
        </Alert>
      ) : (
        <>
          {/* KPIs */}
          {kpis && (
            <Grid container spacing={2} sx={{ mb: 2.5 }}>
              <Grid item xs={12} sm={6} md={3}>
                <KpiCard
                  color={GD.indigo} label="Segmentos analisados" value={kpis.total}
                  sub={`${DIMENSOES.find((d) => d.v === dimensao)?.l} · ${metricaInfo?.l}`}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <KpiCard
                  color={GD.blue} label="Dentro da faixa esperada" value={`${kpis.pctNormal}%`}
                  sub={`${kpis.normalCount} de ${kpis.total} segmentos ≤ P75`} barPct={kpis.pctNormal}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <KpiCard
                  color={GD.ok} label="Mais eficiente" value={kpis.melhor.r.segmento}
                  sub={`${fmtNumero(kpis.melhor.r.media, metricaInfo.dec)} ${metricaInfo.unit} · ${kpis.melhor.desvio >= 0 ? "+" : ""}${fmtNumero(kpis.melhor.desvio, 1)}% vs P50`}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <KpiCard
                  color={GD.danger} label={kpis.pior ? "Fora da faixa (ineficiente)" : "Fora da faixa"}
                  value={kpis.pior ? kpis.pior.r.segmento : "—"}
                  sub={kpis.pior
                    ? `${fmtNumero(kpis.pior.r.media, metricaInfo.dec)} ${metricaInfo.unit} · +${fmtNumero(kpis.pior.desvio, 1)}% vs P50`
                    : "Nenhum segmento acima de P75"}
                />
              </Grid>
            </Grid>
          )}

          {/* Radar de faixas percentílicas */}
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Faixas percentílicas — {metricaInfo?.l} por {DIMENSOES.find((d) => d.v === dimensao)?.l.toLowerCase()}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
                Cada barra mostra a faixa observada (P10–P90) do segmento; o marcador colorido mostra onde a
                operação está hoje (média do último período) dentro dessa faixa.
              </Typography>

              <Stack direction="row" spacing={2.5} flexWrap="wrap" useFlexGap alignItems="center"
                sx={{ mb: 1.5, fontSize: 12, color: "text.secondary" }}>
                <LegendaItem><Box sx={{ width: 16, height: 2, bgcolor: GD.slate, opacity: 0.5, borderRadius: 1 }} /> Faixa observada (P10–P90)</LegendaItem>
                <LegendaItem><Box sx={{ width: 16, height: 9, bgcolor: `${GD.blue}33`, border: `1px solid ${GD.blue}88`, borderRadius: 0.6 }} /> Faixa normal (P25–P75)</LegendaItem>
                <LegendaItem><Box sx={{ width: 2, height: 12, bgcolor: GD.indigo, borderRadius: 1 }} /> Mediana (P50)</LegendaItem>
                <LegendaItem><Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: GD.ok }} /> Eficiente (≤P25)</LegendaItem>
                <LegendaItem><Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: GD.blue }} /> Normal</LegendaItem>
                <LegendaItem><Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: GD.danger }} /> Ineficiente (≥P75)</LegendaItem>
                {cmpResult && (
                  <LegendaItem><Box sx={{ width: 9, height: 9, bgcolor: GD.amberDark, transform: "rotate(45deg)", borderRadius: 0.4 }} /> Valor comparado manualmente</LegendaItem>
                )}
              </Stack>

              <Box>
                {rowsAtuais.map((r) => (
                  <FaixaRow
                    key={r.segmento}
                    r={r} lo={escala.lo} hi={escala.hi}
                    dec={metricaInfo.dec} unit={metricaInfo.unit}
                    cmpMarker={cmpResult && cmpSegmento === r.segmento ? Number(cmpValor) : null}
                    destacado={!!(cmpResult && cmpSegmento === r.segmento)}
                  />
                ))}
              </Box>

              <Box sx={{ borderTop: "1px solid", borderColor: "divider", mt: 1, pt: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                  <CompareArrowsIcon fontSize="small" sx={{ verticalAlign: "middle", mr: 0.5 }} />
                  Comparar um valor específico
                  <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    — ex.: uma cotação pontual, fora da posição atual
                  </Typography>
                </Typography>
                <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap alignItems="flex-end">
                  <TextField
                    select label="Segmento" size="small" value={cmpSegmento} sx={{ width: 200 }}
                    onChange={(e) => setCmpSegmento(e.target.value)}
                  >
                    {segmentos.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                  </TextField>
                  <TextField
                    label="Valor a comparar" type="number" size="small" value={cmpValor} sx={{ width: 160 }}
                    onChange={(e) => setCmpValor(e.target.value)}
                  />
                  <Button variant="outlined" onClick={comparar}>Comparar</Button>
                </Stack>
                {cmpResult && (
                  <Stack direction="row" alignItems="center" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                    <Chip
                      label={STATUS_LABEL[cmpResult.faixa] || cmpResult.faixa}
                      sx={{ bgcolor: `${COR_FAIXA[cmpResult.faixa] || GD.slate}22`,
                            color: COR_FAIXA[cmpResult.faixa] || GD.slate, fontWeight: 700 }}
                    />
                    <Typography variant="body2">
                      desvio vs P50: <strong style={{ color: cmpResult.desvio_p50_pct > 0 ? GD.danger : GD.ok }}>
                        {cmpResult.desvio_p50_pct > 0 ? "+" : ""}{fmtNumero(cmpResult.desvio_p50_pct, 1)}%
                      </strong>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      P50 de referência: {fmtNumero(cmpResult.p50, metricaInfo.dec)} · amostra {cmpResult.amostra}
                      {cmpResult.low_confidence ? " · ⚠ low confidence" : ""}
                    </Typography>
                  </Stack>
                )}
              </Box>
            </CardContent>
          </Card>

          {/* Tabela completa (histórico de todos os períodos) */}
          <Card>
            <CardContent sx={{ pb: tabelaAberta ? 2 : "12px !important" }}>
              <Button
                onClick={() => setTabelaAberta(!tabelaAberta)}
                sx={{ textTransform: "none", fontWeight: 700, p: 0, minWidth: 0 }}
                startIcon={
                  <ExpandMoreIcon sx={{ transform: tabelaAberta ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
                }
              >
                Ver tabela completa de datasets percentílicos
              </Button>
              <Collapse in={tabelaAberta}>
                <Table size="small" sx={{ mt: 1.5 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Segmento</TableCell>
                      <TableCell>Período</TableCell>
                      <TableCell align="right">P10</TableCell>
                      <TableCell align="right">P25</TableCell>
                      <TableCell align="right">P50</TableCell>
                      <TableCell align="right">P75</TableCell>
                      <TableCell align="right">P90</TableCell>
                      <TableCell align="right">Média</TableCell>
                      <TableCell align="right">Amostra</TableCell>
                      <TableCell align="center">Conf.</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r) => {
                      const status = classificar(r.media, r.p25, r.p75);
                      return (
                        <TableRow key={r.id} hover>
                          <TableCell sx={{ fontWeight: 600 }}>{r.segmento}</TableCell>
                          <TableCell>
                            {r.periodo_ref} <Typography variant="caption" color="text.secondary">v{r.versao}</Typography>
                          </TableCell>
                          <TableCell align="right">{fmtNumero(r.p10, metricaInfo.dec)}</TableCell>
                          <TableCell align="right">{fmtNumero(r.p25, metricaInfo.dec)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtNumero(r.p50, metricaInfo.dec)}</TableCell>
                          <TableCell align="right">{fmtNumero(r.p75, metricaInfo.dec)}</TableCell>
                          <TableCell align="right">{fmtNumero(r.p90, metricaInfo.dec)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtNumero(r.media, metricaInfo.dec)}</TableCell>
                          <TableCell align="right">{r.amostra}</TableCell>
                          <TableCell align="center">
                            {r.low_confidence
                              ? <Chip size="small" label="baixa" color="warning" variant="outlined" />
                              : <Chip size="small" label="ok" color="success" variant="outlined" />}
                          </TableCell>
                          <TableCell>
                            <Chip size="small" label={STATUS_LABEL[status]}
                              sx={{ bgcolor: `${COR_FAIXA[status]}22`, color: COR_FAIXA[status], fontWeight: 700 }} />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Collapse>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
