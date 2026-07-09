import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress, Alert,
} from "@mui/material";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Legend,
} from "recharts";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtNumero, fmtMoeda, fmtRsKg, fmtPct, rotuloMacro } from "../utils/format";
import { corClassificacao, corDesvio, fmtDesvio } from "../utils/benchmark";
import { GD } from "../theme";

export default function BenchmarkRegional() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [dados, setDados] = useState([]);
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
      setDados(await benchmarkApi.regional(empresaAtivaId, params));
    } catch (e) {
      setErro(extrairErro(e));
      setDados([]);
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
        <PageHeader titulo="Benchmark Regional" subtitulo="Por região de entrega × mercado" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  const grafico = dados.map((r) => ({
    nome: rotuloMacro(r.macro_regiao),
    "R$/kg": Number(r.frete_kg.valor.toFixed(4)),
    "Benchmark médio": Number(r.frete_kg.benchmark_medio.toFixed(4)),
  }));

  return (
    <Box>
      <PageHeader
        titulo="Benchmark Regional"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — por região de entrega`}
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
      {!carregando && !dados.length && (
        <Alert severity="info" sx={{ mb: 2 }}>Nenhum dado regional no período.</Alert>
      )}

      {dados.length > 0 && (
        <>
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Custo por kg × benchmark — por região
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={grafico}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="nome" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <ReTooltip formatter={(v) => fmtRsKg(v)} />
                  <Legend />
                  <Bar dataKey="R$/kg" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={38} />
                  <Line dataKey="Benchmark médio" stroke={GD.amber} strokeWidth={3} dot={{ r: 4 }} />
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
                      <TableCell align="right">Bench. médio</TableCell>
                      <TableCell align="right">Desvio</TableCell>
                      <TableCell align="center">Classificação</TableCell>
                      <TableCell align="right">% Frete</TableCell>
                      <TableCell align="center">Classif. %</TableCell>
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
                          <Chip size="small" label={r.frete_kg.classificacao}
                            color={corClassificacao(r.frete_kg.classificacao)} />
                        </TableCell>
                        <TableCell align="right">{fmtPct(r.frete_pct.valor)}</TableCell>
                        <TableCell align="center">
                          <Chip size="small" label={r.frete_pct.classificacao}
                            color={corClassificacao(r.frete_pct.classificacao)} variant="outlined" />
                        </TableCell>
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
