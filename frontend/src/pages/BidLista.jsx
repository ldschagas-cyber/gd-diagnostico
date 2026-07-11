import { useNavigate } from "react-router-dom";
import {
  Box, Button, Card, CardContent, Grid, Typography, Stack,
  LinearProgress, Alert, Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import GavelIcon from "@mui/icons-material/Gavel";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import BidStatusChip from "../components/BidStatusChip";
import StatCard from "../components/StatCard";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidLista, useBidDashboard } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";
import { GD } from "../theme";

export default function BidLista() {
  const { empresaAtivaId, empresaAtiva } = useEmpresa();
  const nav = useNavigate();

  // Lista e KPIs via React Query: cache + dedup; retorno à tela é instantâneo.
  const { data: bids = [], isFetching: carregandoLista, error: erroLista } =
    useBidLista(empresaAtivaId);
  const { data: kpis, isFetching: carregandoKpis, error: erroKpis } =
    useBidDashboard(empresaAtivaId);

  const carregando = carregandoLista || carregandoKpis;
  const erro = erroLista || erroKpis;

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Concorrência Logística" subtitulo="BIDs de Frete" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="BIDs de Frete"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — processos de concorrência logística`}
        acoes={
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => nav("/bid/novo")}>
            Novo BID
          </Button>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{extrairErro(erro)}</Alert>}

      {kpis && (
        <Grid container spacing={2.5} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <StatCard rotulo="BIDs Realizados" valor={kpis.total_bids} cor={GD.indigo} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard rotulo="Abertos" valor={kpis.bids_abertos} cor={GD.blue} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard rotulo="Economia Identificada" valor={fmtMoeda(kpis.economia_identificada)} cor={GD.ok} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard rotulo="Transportadoras Avaliadas" valor={kpis.transportadoras_avaliadas} cor={GD.amberDark} />
          </Grid>
        </Grid>
      )}

      {!carregando && bids.length === 0 && (
        <Alert severity="info">
          Nenhum BID criado ainda. Clique em "Novo BID" para iniciar um processo de concorrência.
        </Alert>
      )}

      <Grid container spacing={2}>
        {bids.map((bid) => (
          <Grid item xs={12} md={6} key={bid.id}>
            <Card
              sx={{ cursor: "pointer", "&:hover": { boxShadow: 4 }, transition: "box-shadow 0.2s" }}
              onClick={() => nav(`/bid/${bid.id}`)}
            >
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <GavelIcon sx={{ color: GD.indigo, fontSize: 28 }} />
                    <Box>
                      <Typography variant="h6" sx={{ fontFamily: "'Sora', sans-serif", color: GD.indigo }}>
                        {bid.nome}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {bid.periodo_analise_inicio && bid.periodo_analise_fim
                          ? `Período: ${bid.periodo_analise_inicio} → ${bid.periodo_analise_fim}`
                          : "Período não definido"}
                      </Typography>
                    </Box>
                  </Stack>
                  <BidStatusChip status={bid.status} />
                </Stack>
                {bid.objetivo && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, noWrap: true }}>
                    {bid.objetivo.slice(0, 100)}{bid.objetivo.length > 100 ? "..." : ""}
                  </Typography>
                )}
                <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                  {bid.data_encerramento && (
                    <Chip size="small" label={`Encerra: ${bid.data_encerramento}`} variant="outlined" />
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
