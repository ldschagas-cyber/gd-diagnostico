import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Stack,
  TextField,
  Button,
  MenuItem,
  LinearProgress,
  Alert,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import BenchmarkComparacao from "../components/BenchmarkComparacao";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { benchmarkApi, transportadorasApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtRsKg, fmtPct } from "../utils/format";
import { GD } from "../theme";

export default function BenchmarkNacional() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [dados, setDados] = useState(null);
  const [transportadoras, setTransportadoras] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [transportadoraId, setTransportadoraId] = useState("");

  useEffect(() => {
    if (empresaAtivaId) {
      transportadorasApi.listar(empresaAtivaId).then(setTransportadoras).catch(() => {});
    }
  }, [empresaAtivaId]);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    setErro("");
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      if (transportadoraId) params.transportadora_id = transportadoraId;
      setDados(await benchmarkApi.nacional(empresaAtivaId, params));
    } catch (e) {
      setErro(extrairErro(e));
      setDados(null);
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, dataInicio, dataFim, transportadoraId]);

  useEffect(() => {
    carregar();
  }, [empresaAtivaId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Benchmark Nacional" subtitulo="Empresa × mercado nacional" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  const semDados = dados && dados.qtd_ctes === 0;

  return (
    <Box>
      <PageHeader
        titulo="Benchmark Nacional"
        subtitulo={
          empresaAtiva
            ? `${empresaAtiva.nome_fantasia || empresaAtiva.razao_social} × mercado nacional`
            : "Empresa × mercado nacional"
        }
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField
              label="De" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              InputLabelProps={{ shrink: true }} sx={{ width: 150 }}
            />
            <TextField
              label="Até" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              InputLabelProps={{ shrink: true }} sx={{ width: 150 }}
            />
            <TextField
              select label="Transportadora" size="small" value={transportadoraId}
              onChange={(e) => setTransportadoraId(e.target.value)} sx={{ width: 180 }}
            >
              <MenuItem value="">Todas</MenuItem>
              {transportadoras.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.nome_fantasia || t.razao_social}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={carregar} disabled={carregando}>
              Aplicar
            </Button>
          </Stack>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      {semDados && !carregando && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Nenhum CT-e no período selecionado.
        </Alert>
      )}

      {dados && (
        <>
          <Grid container spacing={2.5} sx={{ mb: 1 }}>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Frete total" valor={fmtMoeda(dados.valor_total_frete)}
                legenda={`${dados.qtd_ctes} CT-es`} cor={GD.indigo} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Mercadoria" valor={fmtMoeda(dados.valor_total_mercadoria)} cor={GD.blue} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Peso total" valor={`${fmtNumero(dados.peso_total, 0)} kg`} cor={GD.ok} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard rotulo="Custo médio/kg" valor={fmtRsKg(dados.frete_kg.valor)} cor={GD.amberDark} />
            </Grid>
          </Grid>

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <BenchmarkComparacao
                titulo="Custo por kg × benchmark nacional"
                comp={dados.frete_kg}
                formatar={(v) => fmtRsKg(v)}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <BenchmarkComparacao
                titulo="% Frete s/ mercadoria × benchmark nacional"
                comp={dados.frete_pct}
                formatar={(v) => fmtPct(v)}
              />
            </Grid>
          </Grid>

          <Card sx={{ mt: 2.5 }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                A classificação do custo por kg é relativa ao benchmark médio nacional
                (≤ médio: Excelente · até +10%: Bom · até +20%: Atenção · acima: Crítico). O
                percentual de frete usa as faixas de mercado (≤5% Excelente, 5–8% Muito Bom,
                8–12% Atenção, 12–18% Crítico, &gt;18% Muito Crítico).
              </Typography>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
