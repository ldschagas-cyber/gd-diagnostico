import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress, Alert,
} from "@mui/material";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtNumero, fmtMoeda, fmtPct } from "../utils/format";
import { corClassificacao, corNivelCusto, corDesvio, fmtDesvio } from "../utils/benchmark";

export default function BenchmarkTransportadoras() {
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
      setDados(await benchmarkApi.transportadoras(empresaAtivaId, params));
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
        <PageHeader titulo="Benchmark Transportadoras" subtitulo="Eficiência × mercado nacional" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Benchmark Transportadoras"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — custo × benchmark nacional`}
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
        <Alert severity="info" sx={{ mb: 2 }}>Nenhuma transportadora no período.</Alert>
      )}

      {dados.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Ranking de eficiência (menor custo/kg primeiro)
            </Typography>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>#</TableCell>
                    <TableCell>Transportadora</TableCell>
                    <TableCell align="right">Frete total</TableCell>
                    <TableCell align="right">Part.</TableCell>
                    <TableCell align="right">Peso (kg)</TableCell>
                    <TableCell align="right">R$/kg</TableCell>
                    <TableCell align="right">Desvio</TableCell>
                    <TableCell align="center">Nível de custo</TableCell>
                    <TableCell align="center">Classificação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dados.map((t, i) => (
                    <TableRow key={t.transportadora_id ?? i}>
                      <TableCell>
                        {i === 0 ? (
                          <EmojiEventsIcon sx={{ fontSize: 18, color: "#C9A84C" }} />
                        ) : (
                          i + 1
                        )}
                      </TableCell>
                      <TableCell>{t.nome}</TableCell>
                      <TableCell align="right">{fmtMoeda(t.frete_total)}</TableCell>
                      <TableCell align="right">{fmtPct(t.participacao_pct, 1)}</TableCell>
                      <TableCell align="right">{fmtNumero(t.peso_transportado, 0)}</TableCell>
                      <TableCell align="right">{fmtNumero(t.frete_kg.valor, 4)}</TableCell>
                      <TableCell align="right" sx={{ color: corDesvio(t.frete_kg.desvio_pct), fontWeight: 600 }}>
                        {fmtDesvio(t.frete_kg.desvio_pct)}
                      </TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={t.nivel_custo} color={corNivelCusto(t.nivel_custo)} />
                      </TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={t.frete_kg.classificacao}
                          color={corClassificacao(t.frete_kg.classificacao)} variant="outlined" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
              O custo de cada transportadora é comparado ao benchmark médio nacional. Desvio
              negativo (verde) indica custo abaixo do mercado.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
