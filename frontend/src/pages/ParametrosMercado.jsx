import { Fragment, useEffect, useState } from "react";
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
  CircularProgress,
  Chip,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { useBenchmarksPct, useMutacoesBenchmarkPct } from "../api/queries";
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

export default function ParametrosMercado() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: benchs = [], isLoading: carregando, error: erroBench } = useBenchmarksPct();
  const { salvar: salvarBenchMut } = useMutacoesBenchmarkPct();

  const [benchNacional, setBenchNacional] = useState(BENCH_VAZIO);
  const [benchRegionais, setBenchRegionais] = useState({});
  const [salvandoReg, setSalvandoReg] = useState(null);
  const [salvandoTodas, setSalvandoTodas] = useState(false);
  const [sujas, setSujas] = useState(new Set());

  const preencherDoServidor = () => {
    const mapaBench = {};
    MACRO_REGIOES.forEach((m) => {
      const existenteBench = benchs.find((b) => b.regiao === m.valor);
      mapaBench[m.valor] = existenteBench ? { ...BENCH_VAZIO, ...existenteBench } : BENCH_VAZIO;
    });
    setBenchRegionais(mapaBench);
  };

  useEffect(() => {
    const nacBench = benchs.find((b) => b.regiao === "NACIONAL");
    setBenchNacional(nacBench ? { ...BENCH_VAZIO, ...nacBench } : BENCH_VAZIO);
    preencherDoServidor();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchs]);

  if (erroBench) erroToast(extrairErro(erroBench));

  const salvandoNac = salvarBenchMut.isPending;

  const salvarNacional = async () => {
    try {
      await salvarBenchMut.mutateAsync({
        regiao: "NACIONAL",
        payload: {
          ...benchNacional,
          frete_pct_min: Number(benchNacional.frete_pct_min) || 0,
          frete_pct_medio: Number(benchNacional.frete_pct_medio) || 0,
          frete_pct_max: Number(benchNacional.frete_pct_max) || 0,
        },
      });
      sucesso("Referência de mercado nacional salva.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const persistirRegional = async (macro) => {
    const b = benchRegionais[macro] || BENCH_VAZIO;
    await salvarBenchMut.mutateAsync({
      regiao: macro,
      payload: {
        ...b,
        frete_pct_min: Number(b.frete_pct_min) || 0,
        frete_pct_medio: Number(b.frete_pct_medio) || 0,
        frete_pct_max: Number(b.frete_pct_max) || 0,
      },
    });
  };

  const salvarRegional = async (macro) => {
    setSalvandoReg(macro);
    try {
      await persistirRegional(macro);
      setSujas((prev) => { const p = new Set(prev); p.delete(macro); return p; });
      sucesso(`Referência de mercado de ${rotuloMacro(macro)} salva.`);
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

  const atualizarBenchReg = (macro, campo, valor) => {
    setBenchRegionais((prev) => ({ ...prev, [macro]: { ...prev[macro], [campo]: valor } }));
    marcarSuja(macro);
  };

  if (carregando) {
    return (
      <Box>
        <PageHeader
          titulo="Referência de Frete"
          subtitulo="Faixa de mercado de % Frete/Mercadoria por região"
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
        titulo="Referência de Frete"
        subtitulo="Configuração › faixa de mercado (mín/médio/máx) de % Frete/Mercadoria por região"
      />

      <Grid container spacing={2.5}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Abrangência</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Mín. (%)</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Médio (%)</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Máx. (%)</TableCell>
                      <TableCell>Ação</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <Fragment>
                      <TableRow sx={{ bgcolor: "rgba(45,53,97,0.045)" }}>
                        <TableCell sx={{ fontWeight: 700, whiteSpace: "nowrap" }}>Nacional</TableCell>
                        <TableCell>
                          <TextField
                            type="number"
                            size="small"
                            value={benchNacional.frete_pct_min}
                            onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_min: e.target.value })}
                            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                            sx={{ width: 130 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="number"
                            size="small"
                            value={benchNacional.frete_pct_medio}
                            onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_medio: e.target.value })}
                            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                            sx={{ width: 130 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="number"
                            size="small"
                            value={benchNacional.frete_pct_max}
                            onChange={(e) => setBenchNacional({ ...benchNacional, frete_pct_max: e.target.value })}
                            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                            sx={{ width: 130 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<SaveIcon sx={{ fontSize: 15 }} />}
                            onClick={salvarNacional}
                            disabled={salvandoNac}
                            sx={{ whiteSpace: "nowrap" }}
                          >
                            {salvandoNac ? "Salvando..." : "Salvar"}
                          </Button>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell colSpan={5} sx={{ p: 0, borderBottom: "2px solid rgba(45,53,97,0.14)" }} />
                      </TableRow>
                    </Fragment>
                    {MACRO_REGIOES.map((m) => {
                      const b = benchRegionais[m.valor] || BENCH_VAZIO;
                      const suja = sujas.has(m.valor);
                      return (
                        <TableRow key={m.valor} sx={suja ? { bgcolor: "rgba(201,168,76,0.09)" } : undefined}>
                          <TableCell sx={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                            <Stack direction="row" spacing={0.75} alignItems="center">
                              {m.rotulo}
                              {suja && <Chip size="small" label="não salvo" sx={{ height: 18, fontSize: 10, bgcolor: "rgba(201,168,76,0.25)", color: GD.amberDark }} />}
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_min ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_min", e.target.value)}
                              InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                              sx={{ width: 130 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_medio ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_medio", e.target.value)}
                              InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                              sx={{ width: 130 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={b.frete_pct_max ?? 0}
                              onChange={(e) => atualizarBenchReg(m.valor, "frete_pct_max", e.target.value)}
                              InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                              sx={{ width: 130 }}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<SaveIcon sx={{ fontSize: 15 }} />}
                              onClick={() => salvarRegional(m.valor)}
                              disabled={salvandoReg === m.valor}
                              sx={{ whiteSpace: "nowrap" }}
                            >
                              Salvar
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
