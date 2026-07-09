import { useEffect, useState, useCallback } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, LinearProgress, Alert, Divider,
} from "@mui/material";
import SavingsIcon from "@mui/icons-material/Savings";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtPct, fmtRsKg, rotuloMacro } from "../utils/format";
import { GD } from "../theme";

function CardProjecao({ titulo, valor, destaque }) {
  return (
    <Card sx={{ height: "100%", borderColor: destaque ? GD.amber : undefined, borderWidth: destaque ? 1.5 : 1 }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">{titulo}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, color: destaque ? GD.amberDark : GD.indigo, fontFamily: "'Sora', sans-serif" }}>
          {fmtMoeda(valor)}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function PotencialEconomia() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    setErro("");
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      setDados(await benchmarkApi.economia(empresaAtivaId, params));
    } catch (e) {
      setErro(extrairErro(e));
      setDados(null);
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, dataInicio, dataFim]);

  useEffect(() => {
    carregar();
  }, [empresaAtivaId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Potencial de Economia" subtitulo="Quanto há para economizar vs. mercado" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Potencial de Economia"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — economia vs. benchmark de mercado`}
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <TextField label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <Button variant="contained" onClick={carregar} disabled={carregando}>Aplicar</Button>
          </Stack>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && dados.economia_total <= 0 && !carregando && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Nenhuma economia potencial identificada no período — os custos estão dentro
          ou abaixo do benchmark de mercado. Operação eficiente.
        </Alert>
      )}

      {dados && (
        <>
          {/* Destaque principal */}
          <Card sx={{ mb: 2.5, bgcolor: GD.indigo, color: "#fff" }}>
            <CardContent>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={1.5} sx={{ textAlign: "center" }}>
                  <SavingsIcon sx={{ fontSize: 48, color: GD.amber }} />
                </Grid>
                <Grid item xs={12} sm={6.5}>
                  <Typography variant="overline" sx={{ color: "rgba(255,255,255,0.7)" }}>
                    Economia potencial no período
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: "'Sora', sans-serif" }}>
                    {fmtMoeda(dados.economia_total)}
                  </Typography>
                  <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.8)" }}>
                    {fmtPct(dados.economia_pct)} do frete total · base de {fmtNumero(dados.meses_periodo, 1)} {dados.meses_periodo <= 1 ? "mês" : "meses"} de dados
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography variant="overline" sx={{ color: "rgba(255,255,255,0.7)" }}>
                    Projeção anual
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: GD.amber, fontFamily: "'Sora', sans-serif" }}>
                    {fmtMoeda(dados.proj_anual)}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Projeções */}
          <Typography variant="overline" color="text.secondary">Projeção (ritmo mensal × período)</Typography>
          <Grid container spacing={2} sx={{ mt: 0, mb: 2.5 }}>
            <Grid item xs={6} md={3}><CardProjecao titulo="Mensal" valor={dados.proj_mensal} /></Grid>
            <Grid item xs={6} md={3}><CardProjecao titulo="Trimestral" valor={dados.proj_trimestral} /></Grid>
            <Grid item xs={6} md={3}><CardProjecao titulo="Semestral" valor={dados.proj_semestral} /></Grid>
            <Grid item xs={6} md={3}><CardProjecao titulo="Anual" valor={dados.proj_anual} destaque /></Grid>
          </Grid>

          {/* Por região */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Economia por região</Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Região</TableCell>
                      <TableCell align="right">Frete total</TableCell>
                      <TableCell align="right">Peso (kg)</TableCell>
                      <TableCell align="right">R$/kg atual</TableCell>
                      <TableCell align="right">Bench. médio</TableCell>
                      <TableCell align="right">Economia</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dados.por_regiao.map((r) => (
                      <TableRow key={r.macro_regiao}>
                        <TableCell sx={{ fontWeight: 600 }}>{rotuloMacro(r.macro_regiao)}</TableCell>
                        <TableCell align="right">{fmtMoeda(r.frete_total)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.peso_total, 0)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.frete_rs_kg, 4)}</TableCell>
                        <TableCell align="right">{fmtNumero(r.benchmark_medio, 4)}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: r.economia > 0 ? GD.danger : GD.ok }}>
                          {fmtMoeda(r.economia)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
              <Divider sx={{ my: 2 }} />
              <Typography variant="caption" color="text.secondary">
                Economia = (custo atual por kg − benchmark médio da região) × peso movimentado,
                considerada apenas onde o custo está acima do mercado. As projeções assumem a
                manutenção do ritmo atual.
              </Typography>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
