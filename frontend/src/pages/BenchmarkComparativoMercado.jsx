import {
  Box, Card, CardContent, Typography, Stack, TextField, Button, ToggleButton, ToggleButtonGroup,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress, Alert,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import IndicadoresTransversais from "../components/IndicadoresTransversais";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useComparativoMercado } from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtNumero, rotuloMacro } from "../utils/format";
import { corClassificacao, corDesvio, fmtDesvio, rotuloClassificacaoMercado } from "../utils/benchmark";

const ESCOPOS = [
  { valor: "NACIONAL", rotulo: "Nacional" },
  { valor: "REGIAO", rotulo: "Região" },
  { valor: "CORREDOR", rotulo: "Corredor" },
];

function rotuloLinha(linha, escopo) {
  if (escopo === "CORREDOR") return `${rotuloMacro(linha.origem_regiao)} → ${rotuloMacro(linha.destino_regiao)}`;
  if (escopo === "REGIAO") return rotuloMacro(linha.destino_regiao);
  return "Brasil (todos os corredores)";
}

export default function BenchmarkComparativoMercado() {
  const { empresaAtivaId } = useEmpresa();
  const [tela, , patch] = useTelaEstado("benchmark-comparativo-mercado", {
    escopo: "REGIAO", dataInicio: "", dataFim: "",
  });
  const { escopo, dataInicio, dataFim } = tela;
  const setEscopo = (v) => patch({ escopo: v });
  const setDataInicio = (v) => patch({ dataInicio: v });
  const setDataFim = (v) => patch({ dataFim: v });

  const params = { escopo };
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  const { data: linhas = [], isFetching: carregando, error } = useComparativoMercado(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Comparativo de Mercado" subtitulo="Cliente × Mercado, por percentil" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Comparativo de Mercado"
        subtitulo="Cliente × Mercado (P10-P90) — fonte: Matriz Benchmark (OD)"
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
            <TextField label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 150 }} />
          </Stack>
        }
      />

      <IndicadoresTransversais empresaId={empresaAtivaId} dataInicio={dataInicio} dataFim={dataFim} />

      <ToggleButtonGroup
        exclusive value={escopo} onChange={(_, v) => v && setEscopo(v)}
        size="small" sx={{ mb: 2.5 }}
      >
        {ESCOPOS.map((e) => <ToggleButton key={e.valor} value={e.valor}>{e.rotulo}</ToggleButton>)}
      </ToggleButtonGroup>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {!carregando && !linhas.length && (
        <Alert severity="info">
          Sem dados observados de mercado no período — importe CT-es ou gere o Benchmark
          Observado para este recorte.
        </Alert>
      )}

      {linhas.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{escopo === "CORREDOR" ? "Corredor" : escopo === "REGIAO" ? "Região" : "Escopo"}</TableCell>
                    <TableCell align="right">CT-es</TableCell>
                    <TableCell align="right">Cliente (P50)</TableCell>
                    <TableCell align="right">P10</TableCell>
                    <TableCell align="right">P25</TableCell>
                    <TableCell align="right">P50</TableCell>
                    <TableCell align="right">P75</TableCell>
                    <TableCell align="right">P90</TableCell>
                    <TableCell align="center">Percentil</TableCell>
                    <TableCell align="right">Diferença</TableCell>
                    <TableCell align="center">Classificação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {linhas.map((l, i) => (
                    <TableRow key={i}>
                      <TableCell sx={{ fontWeight: 600 }}>{rotuloLinha(l, escopo)}</TableCell>
                      <TableCell align="right">{l.qtd_ctes}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtNumero(l.cliente_p50, 4)}</TableCell>
                      <TableCell align="right">{l.mercado_p10 != null ? fmtNumero(l.mercado_p10, 4) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p25 != null ? fmtNumero(l.mercado_p25, 4) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p50 != null ? fmtNumero(l.mercado_p50, 4) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p75 != null ? fmtNumero(l.mercado_p75, 4) : "—"}</TableCell>
                      <TableCell align="right">{l.mercado_p90 != null ? fmtNumero(l.mercado_p90, 4) : "—"}</TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={l.percentil} variant="outlined" />
                      </TableCell>
                      <TableCell align="right" sx={{ color: corDesvio(l.diferenca_pct), fontWeight: 600 }}>
                        {l.diferenca_pct != null ? fmtDesvio(l.diferenca_pct) : "—"}
                      </TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={rotuloClassificacaoMercado(l.classificacao)} color={corClassificacao(l.classificacao)} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
