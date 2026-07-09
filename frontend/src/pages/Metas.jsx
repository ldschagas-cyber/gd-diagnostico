import { useEffect, useState, useCallback } from "react";
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
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { metasApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { MACRO_REGIOES, rotuloMacro } from "../utils/format";

export default function Metas() {
  const { sucesso, erro: erroToast } = useFeedback();
  const [carregando, setCarregando] = useState(true);
  const [nacional, setNacional] = useState({ meta_rs_kg: 0, meta_pct_frete: 0 });
  const [regionais, setRegionais] = useState({});
  const [salvandoNac, setSalvandoNac] = useState(false);
  const [salvandoReg, setSalvandoReg] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [nac, regs] = await Promise.all([
        metasApi.obterNacional(),
        metasApi.listarRegionais(),
      ]);
      if (nac) setNacional({ meta_rs_kg: nac.meta_rs_kg, meta_pct_frete: nac.meta_pct_frete });
      const mapa = {};
      MACRO_REGIOES.forEach((m) => {
        const existente = regs.find((r) => r.macro_regiao === m.valor);
        mapa[m.valor] = {
          meta_rs_kg: existente?.meta_rs_kg ?? 0,
          meta_pct_frete: existente?.meta_pct_frete ?? 0,
          prazo_medio_meta: existente?.prazo_medio_meta ?? 0,
        };
      });
      setRegionais(mapa);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [erroToast]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const salvarNacional = async () => {
    setSalvandoNac(true);
    try {
      await metasApi.salvarNacional({
        meta_rs_kg: Number(nacional.meta_rs_kg) || 0,
        meta_pct_frete: Number(nacional.meta_pct_frete) || 0,
      });
      sucesso("Meta nacional salva.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvandoNac(false);
    }
  };

  const salvarRegional = async (macro) => {
    setSalvandoReg(macro);
    try {
      const r = regionais[macro];
      await metasApi.salvarRegional({
        macro_regiao: macro,
        meta_rs_kg: Number(r.meta_rs_kg) || 0,
        meta_pct_frete: Number(r.meta_pct_frete) || 0,
        prazo_medio_meta: Number(r.prazo_medio_meta) || 0,
      });
      sucesso(`Meta de ${rotuloMacro(macro)} salva.`);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvandoReg(null);
    }
  };

  const atualizarReg = (macro, campo, valor) =>
    setRegionais((prev) => ({ ...prev, [macro]: { ...prev[macro], [campo]: valor } }));

  if (carregando) {
    return (
      <Box>
        <PageHeader titulo="Metas" subtitulo="Metas nacionais e regionais de frete" />
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Metas"
        subtitulo="Defina metas nacionais e por macro-região para comparar com os indicadores"
      />

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 0.5 }}>
                Meta nacional
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
                Referência geral para custo por kg e percentual de frete.
              </Typography>
              <Stack spacing={2.5}>
                <TextField
                  label="Custo por kg (meta)"
                  type="number"
                  value={nacional.meta_rs_kg}
                  onChange={(e) =>
                    setNacional({ ...nacional, meta_rs_kg: e.target.value })
                  }
                  InputProps={{
                    startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                  }}
                />
                <TextField
                  label="% Frete sobre mercadoria (meta)"
                  type="number"
                  value={nacional.meta_pct_frete}
                  onChange={(e) =>
                    setNacional({ ...nacional, meta_pct_frete: e.target.value })
                  }
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={salvarNacional}
                  disabled={salvandoNac}
                >
                  {salvandoNac ? "Salvando..." : "Salvar meta nacional"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 0.5 }}>
                Metas regionais
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Por macro-região: custo por kg, percentual de frete e prazo médio.
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Macro-região</TableCell>
                      <TableCell>R$/kg</TableCell>
                      <TableCell>% Frete</TableCell>
                      <TableCell>Prazo (d)</TableCell>
                      <TableCell align="right">Ação</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {MACRO_REGIOES.map((m) => {
                      const r = regionais[m.valor] || {};
                      return (
                        <TableRow key={m.valor}>
                          <TableCell sx={{ fontWeight: 600 }}>{m.rotulo}</TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.meta_rs_kg ?? 0}
                              onChange={(e) =>
                                atualizarReg(m.valor, "meta_rs_kg", e.target.value)
                              }
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.meta_pct_frete ?? 0}
                              onChange={(e) =>
                                atualizarReg(m.valor, "meta_pct_frete", e.target.value)
                              }
                              sx={{ width: 90 }}
                            />
                          </TableCell>
                          <TableCell>
                            <TextField
                              type="number"
                              size="small"
                              value={r.prazo_medio_meta ?? 0}
                              onChange={(e) =>
                                atualizarReg(m.valor, "prazo_medio_meta", e.target.value)
                              }
                              sx={{ width: 80 }}
                            />
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
    </Box>
  );
}
