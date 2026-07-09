import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress,
  Alert, Tooltip, Grid,
} from "@mui/material";
import RouteIcon from "@mui/icons-material/Route";
import AddchartIcon from "@mui/icons-material/Addchart";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtNumero, fmtMoeda, fmtPct } from "../utils/format";
import { corClassificacao, corDesvio, fmtDesvio } from "../utils/benchmark";

// Cor do score 0-100 (alinha com a classificação do backend).
function corScore(score) {
  if (score >= 90) return "success";
  if (score >= 75) return "success";
  if (score >= 60) return "warning";
  return "error";
}

export default function BenchmarkCorredores() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const navigate = useNavigate();
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
      setDados(await benchmarkApi.corredores(empresaAtivaId, params));
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
        <PageHeader titulo="Benchmark por Corredor" subtitulo="Fluxo Origem → Destino (OD)" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  const corredores = dados?.corredores || [];
  const semRef = dados?.corredores_sem_referencia || 0;

  return (
    <Box>
      <PageHeader
        titulo="Benchmark por Corredor (OD)"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — cada fluxo comparado contra o próprio corredor`}
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

      <Alert severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}>
        O benchmark é por <strong>fluxo logístico (Origem → Destino)</strong>, não por região de
        entrega. Assim, fluxos diferentes que saem do mesmo lugar — por exemplo
        Recife→Sul e Recife→Recife — são comparados cada um contra a referência do
        próprio corredor, eliminando o viés geográfico.
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {dados && (
        <>
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Score Global"
                valor={dados.classificacao_global === "Sem referência" ? "—" : fmtNumero(dados.score_global, 1)}
                legenda={dados.classificacao_global}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Corredores" valor={String(dados.qtd_corredores)} legenda="fluxos OD identificados" />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Frete total" valor={fmtMoeda(dados.frete_total)} legenda="no período" />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Sem referência"
                valor={String(semRef)}
                legenda={semRef ? "corredores a cadastrar" : "todos cobertos"}
              />
            </Grid>
          </Grid>

          {semRef > 0 && (
            <Alert
              severity="warning"
              sx={{ mb: 2.5 }}
              action={
                <Button color="inherit" size="small" startIcon={<AddchartIcon />}
                  onClick={() => navigate("/configuracoes/corredores")}>
                  Cadastrar referências
                </Button>
              }
            >
              {semRef} corredor(es) sem referência de mercado cadastrada. Os dados da
              empresa aparecem na tabela, mas só haverá comparação e score após o
              cadastro da referência do corredor.
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
                          <TableCell align="right">
                            {c.tem_referencia ? fmtNumero(c.frete_kg.benchmark_medio, 4) : "—"}
                          </TableCell>
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
                            <Chip size="small" label={c.classificacao} color={corClassificacao(c.classificacao)}
                              variant={c.tem_referencia ? "filled" : "outlined"} />
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
