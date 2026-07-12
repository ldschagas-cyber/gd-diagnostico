import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  Grid,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  InputAdornment,
  Divider,
  CircularProgress,
  Alert,
  Chip,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import {
  useMetaNacional, useMetasRegionais, useSalvarMetas,
  useBenchmarksPct, useMutacoesBenchmarkPct,
} from "../api/queries";
import { extrairErro } from "../api/client";
import { MACRO_REGIOES, rotuloMacro } from "../utils/format";
import { GD } from "../theme";

// Passthrough silencioso: R$/kg do benchmark legado (V1) não tem mais
// nenhum consumidor desde a consolidação SSoT (v6.9.0) — não é editável
// aqui, só preservado ao salvar para não zerar dado histórico à toa.
const BENCH_VAZIO = {
  frete_kg_min: 0, frete_kg_medio: 0, frete_kg_max: 0,
  frete_pct_min: 0, frete_pct_medio: 0, frete_pct_max: 0,
};

const fmtPct = (v) => `${(Number(v) || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

// Mini-visualização da faixa de mercado (mín–médio–máx): avisa quando o
// "médio" cadastrado cai fora do intervalo mín–máx — validação de
// consistência do cadastro, não é comparação com a meta.
function FaixaMercado({ min, medio, max }) {
  const mn = Number(min) || 0, md = Number(medio) || 0, mx = Number(max) || 0;
  const span = mx - mn;
  const pad = (span || 1) * 0.18;
  const lo = mn - pad, hi = mx + pad, w = hi - lo || 1;
  const pct = (v) => Math.max(0, Math.min(100, ((v - lo) / w) * 100));
  const foraDaFaixa = md < mn || md > mx;

  return (
    <Box sx={{ minWidth: 108 }}>
      <Box sx={{ position: "relative", height: 6, borderRadius: 3, bgcolor: "rgba(45,53,97,0.08)" }}>
        <Box
          sx={{
            position: "absolute", top: 0, height: 6, borderRadius: 3,
            left: `${pct(mn)}%`, width: `${Math.max(0, pct(mx) - pct(mn))}%`,
            bgcolor: "rgba(0,119,168,0.30)",
          }}
        />
        <Box
          sx={{
            position: "absolute", top: -3, left: `${pct(md)}%`, width: 10, height: 10, borderRadius: "50%",
            bgcolor: foraDaFaixa ? GD.danger : GD.indigo, border: "2px solid #fff",
            boxShadow: "0 0 0 1px rgba(28,32,48,0.15)", transform: "translateX(-50%)",
          }}
        />
      </Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.4 }}>
        <Typography sx={{ fontSize: 10, color: "text.secondary" }}>{fmtPct(mn)}</Typography>
        <Typography sx={{ fontSize: 10, fontWeight: foraDaFaixa ? 700 : 400, color: foraDaFaixa ? "error.main" : "text.secondary" }}>
          {fmtPct(md)}
        </Typography>
        <Typography sx={{ fontSize: 10, color: "text.secondary" }}>{fmtPct(mx)}</Typography>
      </Stack>
    </Box>
  );
}

export default function Metas() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: nac, isLoading: carregandoNac, error: erroNac } = useMetaNacional();
  const { data: regs = [], isLoading: carregandoRegs, error: erroRegs } = useMetasRegionais();
  const { data: benchs = [], isLoading: carregandoBench, error: erroBench } = useBenchmarksPct();
  const { nacional: salvarNacionalMut, regional: salvarRegionalMut } = useSalvarMetas();
  const { salvar: salvarBenchMut } = useMutacoesBenchmarkPct();
  const carregando = carregandoNac || carregandoRegs || carregandoBench;

  const [nacional, setNacional] = useState({ meta_rs_kg: 0, meta_pct_frete: 0 });
  const [benchNacional, setBenchNacional] = useState(BENCH_VAZIO);
  const [regionais, setRegionais] = useState({});
  const [benchRegionais, setBenchRegionais] = useState({});
  const [salvandoReg, setSalvandoReg] = useState(null);
  const [salvandoTodas, setSalvandoTodas] = useState(false);
  const [sujas, setSujas] = useState(new Set());

  const preencherDoServidor = () => {
    const mapaMeta = {};
    const mapaBench = {};
    MACRO_REGIOES.forEach((m) => {
      const existenteMeta = regs.find((r) => r.macro_regiao === m.valor);
      mapaMeta[m.valor] = {
        meta_rs_kg: existenteMeta?.meta_rs_kg ?? 0,
        meta_pct_frete: existenteMeta?.meta_pct_frete ?? 0,
        prazo_medio_meta: existenteMeta?.prazo_medio_meta ?? 0,
      };
      const existenteBench = benchs.find((b) => b.regiao === m.valor);
      mapaBench[m.valor] = existenteBench ? { ...BENCH_VAZIO, ...existenteBench } : BENCH_VAZIO;
    });
    setRegionais(mapaMeta);
    setBenchRegionais(mapaBench);
  };

  useEffect(() => {
    if (nac) setNacional({ meta_rs_kg: nac.meta_rs_kg, meta_pct_frete: nac.meta_pct_frete });
  }, [nac]);

  useEffect(() => {
    const nacBench = benchs.find((b) => b.regiao === "NACIONAL");
    setBenchNacional(nacBench ? { ...BENCH_VAZIO, ...nacBench } : BENCH_VAZIO);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchs]);

  useEffect(() => {
    preencherDoServidor();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regs, benchs]);

  if (erroNac) erroToast(extrairErro(erroNac));
  if (erroRegs) erroToast(extrairErro(erroRegs));
  if (erroBench) erroToast(extrairErro(erroBench));

  const salvandoNac = salvarNacionalMut.isPending || salvarBenchMut.isPending;

  const salvarNacional = async () => {
    try {
      await Promise.all([
        salvarNacionalMut.mutateAsync({
          meta_rs_kg: Number(nacional.meta_rs_kg) || 0,
          meta_pct_frete: Number(nacional.meta_pct_frete) || 0,
        }),
        salvarBenchMut.mutateAsync({
          regiao: "NACIONAL",
          payload: {
            ...benchNacional,
            frete_pct_min: Number(benchNacional.frete_pct_min) || 0,
            frete_pct_medio: Number(benchNacional.frete_pct_medio) || 0,
            frete_pct_max: Number(benchNacional.frete_pct_max) || 0,
          },
        }),
      ]);
      sucesso("Meta e referência de mercado nacional salvas.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const persistirRegional = async (macro) => {
    const r = regionais[macro];
    const b = benchRegionais[macro] || BENCH_VAZIO;
    await Promise.all([
      salvarRegionalMut.mutateAsync({
        macro_regiao: macro,
        meta_rs_kg: Number(r.meta_rs_kg) || 0,
        meta_pct_frete: Number(r.meta_pct_frete) || 0,
        prazo_medio_meta: Number(r.prazo_medio_meta) || 0,
      }),
      salvarBenchMut.mutateAsync({
        regiao: macro,
        payload: {
          ...b,
          frete_pct_min: Number(b.frete_pct_min) || 0,
          frete_pct_medio: Number(b.frete_pct_medio) || 0,
          frete_pct_max: Number(b.frete_pct_max) || 0,
        },
      }),
    ]);
  };

  const salvarRegional = async (macro) => {
    setSalvandoReg(macro);
    try {
      await persistirRegional(macro);
      setSujas((prev) => { const p = new Set(prev); p.delete(macro); return p; });
      sucesso(`Meta e referência de mercado de ${rotuloMacro(macro)} salvas.`);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvandoReg(null);
    }
  };

  const salvarTodasSujas = async () => {
    setSalvandoTodas(true);
    try {
      await Promise.all([...sujas].map(persistirRegional));
      sucesso(`${sujas.size} região(ões) salvas.`);
      setSujas(new Set());
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvandoTodas(false);
    }
  };

  const descartarTodas = () => {
    preencherDoServidor();
    setSujas(new Set());
  };

  const marcarSuja = (macro) => setSujas((prev) => new Set(prev).add(macro));

  const atualizarReg = (macro, campo, valor) => {
    setRegionais((prev) => ({ ...prev, [macro]: { ...prev[macro], [campo]: valor } }));
    marcarSuja(macro);
  };

  const atualizarBenchReg = (macro, campo, valor) => {
    setBenchRegionais((prev) => ({ ...prev, [macro]: { ...prev[macro], [campo]: valor } }));
    marcarSuja(macro);
  };

  if (carregando) {
    return (
      <Box>
        <PageHeader
          titulo="Metas & Referência de Mercado (%)"
          subtitulo="Metas nacionais/regionais e faixa de mercado de % Frete, lado a lado"
        />
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ pb: sujas.size ? 9 : 0 }}>
      <PageHeader
        titulo="Metas & Referência de Mercado (%)"
        subtitulo="Configuração › meta interna e faixa de mercado de % Frete/Mercadoria por região — mesmo cadastro, mesma decisão"
      />

      <Alert severity="info" sx={{ mb: 2.5 }}>
        As colunas <strong>Meta</strong> alimentam o selo de desvio no Dashboard e em Recomendações.
        As colunas <strong>Mercado (% Frete)</strong> alimentam a faixa "Ideal / Mercado" do mesmo
        Dashboard — vêm do cadastro legado de benchmark (V1), mantido só para este campo específico
        até a Matriz Benchmark (OD) passar a modelá-lo também.
      </Alert>

      <Grid container spacing={2.5}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 0.5 }}>
                Nacional
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
                Referência geral — meta interna e faixa de mercado de % Frete.
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2.5} useFlexGap flexWrap="wrap" alignItems={{ md: "flex-end" }}>
                <TextField
                  label="Meta R$/kg"
                  type="number"
                  value={nacional.meta_rs_kg}
                  onChange={(e) => setNacional({ ...nacional, meta_rs_kg: e.target.value })}
                  InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                  sx={{ width: 150 }}
                />
                <TextField
                  label="Meta % Frete"
                  type="number"
                  value={nacional.meta_pct_frete}
                  onChange={(e) => setNacional({ ...nacional, meta_pct_frete: e.target.value })}
                  InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                  sx={{ width: 150 }}
                />
                <Divider orientation="vertical" flexItem sx={{ display: { xs: "none", md: "block" } }} />
                <TextField
                  label="Mercado % mín."
                  type="number"
                  value={benchNacional.frete_pct_min}
                  onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_min: e.target.value })}
                  InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                  sx={{ width: 150 }}
                />
                <TextField
                  label="Mercado % médio"
                  type="number"
                  value={benchNacional.frete_pct_medio}
                  onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_medio: e.target.value })}
                  InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                  sx={{ width: 150 }}
                />
                <TextField
                  label="Mercado % máx."
                  type="number"
                  value={benchNacional.frete_pct_max}
                  onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_max: e.target.value })}
                  InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                  sx={{ width: 150 }}
                />
                <Box sx={{ pb: 0.5 }}>
                  <FaixaMercado min={benchNacional.frete_pct_min} medio={benchNacional.frete_pct_medio} max={benchNacional.frete_pct_max} />
                </Box>
              </Stack>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={salvarNacional}
                disabled={salvandoNac}
                sx={{ mt: 2.5 }}
              >
                {salvandoNac ? "Salvando..." : "Salvar Nacional"}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" sx={{ mb: 1.5 }}>
                <Box>
                  <Typography variant="h6" sx={{ mb: 0.5 }}>
                    Por macro-região
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Meta interna e faixa de mercado de % Frete, por região. O ponto mostra onde o
                    médio cadastrado cai dentro da faixa mín–máx.
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Chip size="small" label="Meta interna" sx={{ bgcolor: "rgba(45,53,97,0.10)", color: GD.indigo, fontWeight: 600 }} />
                  <Chip size="small" label="Mercado (% Frete)" sx={{ bgcolor: "rgba(0,119,168,0.10)", color: GD.blue, fontWeight: 600 }} />
                </Stack>
              </Stack>
              <Divider sx={{ mb: 1 }} />
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell rowSpan={2} sx={{ verticalAlign: "bottom" }}>
                        Macro-região
                      </TableCell>
                      <TableCell colSpan={3} align="center" sx={{ bgcolor: "rgba(45,53,97,0.06)", borderRadius: "8px 8px 0 0" }}>
                        Meta
                      </TableCell>
                      <TableCell colSpan={4} align="center" sx={{ bgcolor: "rgba(0,119,168,0.06)", borderRadius: "8px 8px 0 0" }}>
                        Mercado — % Frete
                      </TableCell>
                      <TableCell rowSpan={2} align="right" sx={{ verticalAlign: "bottom" }}>
                        Ação
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ bgcolor: "rgba(45,53,97,0.06)" }}>R$/kg</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(45,53,97,0.06)" }}>% Frete</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(45,53,97,0.06)" }}>Prazo (d)</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(0,119,168,0.06)" }}>Mín.</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(0,119,168,0.06)" }}>Médio</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(0,119,168,0.06)" }}>Máx.</TableCell>
                      <TableCell sx={{ bgcolor: "rgba(0,119,168,0.06)" }}>Faixa</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {MACRO_REGIOES.map((m) => {
                      const r = regionais[m.valor] || {};
                      const b = benchRegionais[m.valor] || BENCH_VAZIO;
                      const suja = sujas.has(m.valor);
                      return (
                        <TableRow key={m.valor} sx={suja ? { bgcolor: "rgba(201,168,76,0.09)" } : undefined}>
                          <TableCell sx={{ fontWeight: 600 }}>
                            <Stack direction="row" spacing={0.75} alignItems="center">
                              {m.rotulo}
                              {suja && <Chip size="small" label="não salvo" sx={{ height: 18, fontSize: 10, bgcolor: "rgba(201,168,76,0.25)", color: GD.amberDark }} />}
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.meta_rs_kg ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "meta_rs_kg", e.target.value)}
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.meta_pct_frete ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "meta_pct_frete", e.target.value)}
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.prazo_medio_meta ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "prazo_medio_meta", e.target.value)}
                              sx={{ width: 80 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_min ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_min", e.target.value)}
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_medio ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_medio", e.target.value)}
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_max ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_max", e.target.value)}
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <FaixaMercado min={b.frete_pct_min} medio={b.frete_pct_medio} max={b.frete_pct_max} />
                          </TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => salvarRegional(m.valor)}
                              disabled={salvandoReg === m.valor}
                            >
                              {salvandoReg === m.valor ? "..." : "Salvar"}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {sujas.size > 0 && (
        <Box
          sx={{
            position: "fixed", left: { xs: 0, md: 264 }, right: 0, bottom: 0, zIndex: 30,
            bgcolor: GD.indigo, color: "#fff", px: 3, py: 1.5,
            display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1.5,
            boxShadow: "0 -8px 24px rgba(28,32,48,0.25)",
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <WarningAmberIcon sx={{ fontSize: 18, color: GD.amber }} />
            <Typography sx={{ fontSize: 13.5 }}>
              {sujas.size === 1 ? "1 região com alterações não salvas" : `${sujas.size} regiões com alterações não salvas`}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1.25}>
            <Button size="small" onClick={descartarTodas} sx={{ color: "rgba(255,255,255,0.85)" }}>
              Descartar
            </Button>
            <Button
              size="small" variant="contained" onClick={salvarTodasSujas} disabled={salvandoTodas}
              sx={{ bgcolor: GD.amber, color: GD.indigo, fontWeight: 700, "&:hover": { bgcolor: GD.amberDark } }}
            >
              {salvandoTodas ? "Salvando..." : "Salvar todas"}
            </Button>
          </Stack>
        </Box>
      )}
    </Box>
  );
}
