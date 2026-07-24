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
  Tooltip,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useMetaNacional, useMetasRegionais, useSalvarMetas } from "../api/queries";
import { extrairErro } from "../api/client";
import { MACRO_REGIOES, rotuloMacro, fmtMoeda } from "../utils/format";
import { GD } from "../theme";

// Referência estável: usar `[]` inline como default do destructuring recria o
// array a cada render, o que reacenderia o useEffect abaixo indefinidamente.
const REGS_VAZIAS = [];

export default function Metas() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: nac, isLoading: carregandoNac, error: erroNac } = useMetaNacional(empresaAtivaId);
  const { data: regs = REGS_VAZIAS, isLoading: carregandoRegs, error: erroRegs } = useMetasRegionais(empresaAtivaId);
  const { nacional: salvarNacionalMut, regional: salvarRegionalMut } = useSalvarMetas(empresaAtivaId);
  const carregando = carregandoNac || carregandoRegs;

  const [nacional, setNacional] = useState({ meta_rs_kg: 0, meta_pct_frete: 0 });
  const [regionais, setRegionais] = useState({});
  const [salvandoReg, setSalvandoReg] = useState(null);
  const [salvandoTodas, setSalvandoTodas] = useState(false);
  const [sujas, setSujas] = useState(new Set());

  const preencherDoServidor = () => {
    const mapa = {};
    MACRO_REGIOES.forEach((m) => {
      const existente = regs.find((r) => r.macro_regiao === m.valor);
      mapa[m.valor] = {
        meta_rs_kg: existente?.meta_rs_kg ?? 0,
        meta_pct_frete: existente?.meta_pct_frete ?? 0,
        prazo_medio_meta: existente?.prazo_medio_meta ?? 0,
        orcamento_mensal: existente?.orcamento_mensal ?? 0,
      };
    });
    setRegionais(mapa);
  };

  useEffect(() => {
    if (nac) setNacional({ meta_rs_kg: nac.meta_rs_kg, meta_pct_frete: nac.meta_pct_frete });
  }, [nac]);

  // Orçamento Mensal Nacional = soma dos 5 orçamentos regionais (não existe
  // valor nacional independente — sempre a soma, nunca fica dessincronizado).
  const orcamentoNacional = MACRO_REGIOES.reduce(
    (soma, m) => soma + (Number(regionais[m.valor]?.orcamento_mensal) || 0),
    0,
  );

  useEffect(() => {
    preencherDoServidor();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regs]);

  useEffect(() => {
    if (erroNac) erroToast(extrairErro(erroNac));
  }, [erroNac, erroToast]);

  useEffect(() => {
    if (erroRegs) erroToast(extrairErro(erroRegs));
  }, [erroRegs, erroToast]);

  const salvandoNac = salvarNacionalMut.isPending;

  const salvarNacional = async () => {
    try {
      await salvarNacionalMut.mutateAsync({
        meta_rs_kg: Number(nacional.meta_rs_kg) || 0,
        meta_pct_frete: Number(nacional.meta_pct_frete) || 0,
      });
      sucesso("Meta nacional salva.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const persistirRegional = async (macro) => {
    const r = regionais[macro];
    await salvarRegionalMut.mutateAsync({
      macro_regiao: macro,
      meta_rs_kg: Number(r.meta_rs_kg) || 0,
      meta_pct_frete: Number(r.meta_pct_frete) || 0,
      prazo_medio_meta: Number(r.prazo_medio_meta) || 0,
      orcamento_mensal: Number(r.orcamento_mensal) || 0,
    });
  };

  const salvarRegional = async (macro) => {
    setSalvandoReg(macro);
    try {
      await persistirRegional(macro);
      setSujas((prev) => { const p = new Set(prev); p.delete(macro); return p; });
      sucesso(`Meta de ${rotuloMacro(macro)} salva.`);
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

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader
          titulo="Metas"
          subtitulo="Configuração › meta interna de R$/kg, % Frete, prazo médio e orçamento mensal por região"
        />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  if (carregando) {
    return (
      <Box>
        <PageHeader
          titulo="Metas"
          subtitulo="Metas nacionais e regionais de R$/kg, % Frete e prazo médio"
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
        titulo="Metas"
        subtitulo="Configuração › meta interna de R$/kg, % Frete, prazo médio e orçamento mensal por região"
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
                      <TableCell sx={{ whiteSpace: "nowrap" }}>R$/kg</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>% Frete</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Prazo</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>Orçamento Mensal</TableCell>
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
                            value={nacional.meta_rs_kg}
                            onChange={(e) => setNacional({ ...nacional, meta_rs_kg: e.target.value })}
                            InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                            sx={{ width: 150 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="number"
                            size="small"
                            value={nacional.meta_pct_frete}
                            onChange={(e) => setNacional({ ...nacional, meta_pct_frete: e.target.value })}
                            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                            sx={{ width: 150 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ color: "text.disabled" }}>—</Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Soma automática dos orçamentos mensais das 5 regiões — não é editável aqui.">
                            <Typography sx={{ fontWeight: 600 }}>
                              {fmtMoeda(orcamentoNacional)}
                              <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                                /mês
                              </Typography>
                            </Typography>
                          </Tooltip>
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
                        <TableCell colSpan={6} sx={{ p: 0, borderBottom: "2px solid rgba(45,53,97,0.14)" }} />
                      </TableRow>
                    </Fragment>
                    {MACRO_REGIOES.map((m) => {
                      const r = regionais[m.valor] || {};
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
                              value={r.meta_rs_kg ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "meta_rs_kg", e.target.value)}
                              InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                              sx={{ width: 150 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.meta_pct_frete ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "meta_pct_frete", e.target.value)}
                              InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                              sx={{ width: 150 }}
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
                              value={r.orcamento_mensal ?? 0}
                              onChange={(e) => atualizarReg(m.valor, "orcamento_mensal", e.target.value)}
                              InputProps={{
                                startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                                endAdornment: <InputAdornment position="end">/mês</InputAdornment>,
                              }}
                              sx={{ width: 175 }}
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
