import { useNavigate } from "react-router-dom";
import {
  Box, Grid, Card, CardContent, Typography, Stack,
  LinearProgress, Alert, Button, Divider,
} from "@mui/material";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, Cell,
} from "recharts";
import GavelIcon from "@mui/icons-material/Gavel";
import SavingsIcon from "@mui/icons-material/Savings";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import AddIcon from "@mui/icons-material/Add";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidDashboard, useBidLista } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";
import { GD } from "../theme";

const PALETTE = [GD.indigo, GD.blue, GD.amber, "#7030A0", "#375623", "#C00000"];

function KPICard({ titulo, valor, subtitulo, icone, color }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {titulo}
            </Typography>
            <Typography variant="h5" fontWeight={700} sx={{ color: color || GD.indigo }}>
              {valor}
            </Typography>
            {subtitulo && (
              <Typography variant="caption" color="text.secondary">
                {subtitulo}
              </Typography>
            )}
          </Box>
          <Box sx={{ color: color || GD.indigo, opacity: 0.7 }}>{icone}</Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function BidDashboard() {
  const { empresaAtivaId, empresaAtiva } = useEmpresa();
  const nav = useNavigate();

  // Dashboard (KPIs) e lista via React Query: cache + dedup; retorno à tela é instantâneo.
  const { data: kpis, isFetching: carregandoKpis, error: erroKpis } =
    useBidDashboard(empresaAtivaId);
  const { data: bids = [], isFetching: carregandoLista, error: erroLista } =
    useBidLista(empresaAtivaId);

  const carregando = carregandoKpis || carregandoLista;
  const erro = erroKpis || erroLista;

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Dashboard Executivo BIDs" subtitulo="Concorrência Logística" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  // Gráfico 1: economia por BID (top 8)
  const graficoBids = bids
    .filter((b) => b.status === "ENCERRADO" || b.status === "EM_COTACAO")
    .slice(0, 8)
    .map((b) => ({
      nome: b.nome.length > 18 ? b.nome.slice(0, 18) + "…" : b.nome,
      status: b.status,
    }));

  return (
    <Box>
      <PageHeader
        titulo="Dashboard Executivo — Concorrência Logística"
        subtitulo={empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social || ""}
        acoes={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => nav("/bid/novo")}
            sx={{ bgcolor: GD.indigo }}
          >
            Novo BID
          </Button>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{extrairErro(erro)}</Alert>}

      {/* KPIs */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="BIDs Realizados"
            valor={fmtNumero(kpis?.total_bids ?? 0)}
            icone={<GavelIcon sx={{ fontSize: 32 }} />}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="Em Aberto"
            valor={fmtNumero(kpis?.bids_abertos ?? 0)}
            icone={<GavelIcon sx={{ fontSize: 32 }} />}
            color={GD.blue}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="Encerrados"
            valor={fmtNumero(kpis?.bids_encerrados ?? 0)}
            icone={<CheckCircleIcon sx={{ fontSize: 32 }} />}
            color="#375623"
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="Economia Identificada"
            valor={fmtMoeda(kpis?.economia_identificada ?? 0)}
            subtitulo="todos os BIDs"
            icone={<SavingsIcon sx={{ fontSize: 32 }} />}
            color="#375623"
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="Economia Contratada"
            valor={fmtMoeda(kpis?.economia_contratada ?? 0)}
            subtitulo="BIDs encerrados"
            icone={<EmojiEventsIcon sx={{ fontSize: 32 }} />}
            color={GD.amber}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <KPICard
            titulo="Transportadoras"
            valor={fmtNumero(kpis?.transportadoras_avaliadas ?? 0)}
            subtitulo="avaliadas"
            icone={<LocalShippingIcon sx={{ fontSize: 32 }} />}
            color={GD.indigo}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        {/* Gráfico: BIDs por status */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                BIDs Recentes
              </Typography>
              {bids.length === 0 && !carregando ? (
                <VazioEstado
                  mensagem="Nenhum BID criado ainda"
                  icone={<GavelIcon sx={{ fontSize: 48, color: GD.indigo, opacity: 0.3 }} />}
                />
              ) : (
                <Box>
                  {bids.slice(0, 6).map((b, i) => (
                    <Box key={b.id}>
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="center"
                        sx={{ py: 1.5, cursor: "pointer", "&:hover": { bgcolor: "action.hover" }, px: 1, borderRadius: 1 }}
                        onClick={() => nav(`/bid/${b.id}`)}
                      >
                        <Box>
                          <Typography variant="body2" fontWeight={600}>{b.nome}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {b.data_inicio} → {b.data_encerramento || "—"}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: "right" }}>
                          <Typography
                            variant="caption"
                            sx={{
                              fontWeight: 700,
                              color:
                                b.status === "ENCERRADO" ? "#375623"
                                : b.status === "EM_COTACAO" ? GD.amber
                                : b.status === "ABERTO" ? GD.blue
                                : b.status === "CANCELADO" ? "error.main"
                                : "text.secondary",
                            }}
                          >
                            {b.status.replace("_", " ")}
                          </Typography>
                        </Box>
                      </Stack>
                      {i < bids.slice(0, 6).length - 1 && <Divider />}
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Gráfico: Economia por status */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                Resumo Financeiro
              </Typography>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={[
                    { nome: "Identificada", valor: kpis?.economia_identificada ?? 0 },
                    { nome: "Contratada", valor: kpis?.economia_contratada ?? 0 },
                    { nome: "Melhor Proposta", valor: kpis?.melhor_economia ?? 0 },
                  ]}
                  margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                  />
                  <ReTooltip
                    formatter={(v) => [fmtMoeda(v), "Valor"]}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
                    {["#375623", GD.indigo, GD.amber].map((color, i) => (
                      <Cell key={i} fill={color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Call to action se não há BIDs */}
        {bids.length === 0 && !carregando && (
          <Grid item xs={12}>
            <Card
              variant="outlined"
              sx={{ border: `2px dashed ${GD.indigo}`, textAlign: "center", py: 4 }}
            >
              <CardContent>
                <GavelIcon sx={{ fontSize: 56, color: GD.indigo, opacity: 0.3, mb: 1 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Nenhum BID criado ainda
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Crie o primeiro processo de concorrência logística para esta empresa.
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => nav("/bid/novo")}
                  sx={{ bgcolor: GD.indigo }}
                >
                  Criar primeiro BID
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
