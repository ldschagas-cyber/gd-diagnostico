import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Grid, Card, CardContent, Typography, Stack,
  LinearProgress, Alert, Button, Chip, IconButton, Tooltip,
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
import DeleteIcon from "@mui/icons-material/Delete";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import BidStatusChip from "../components/BidStatusChip";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidDashboard, useBidLista, useMutacoesBid } from "../api/queries";
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
  const { sucesso, erro: erroToast } = useFeedback();

  // Dashboard (KPIs) e lista via React Query: cache + dedup; retorno à tela é instantâneo.
  const { data: kpis, isFetching: carregandoKpis, error: erroKpis } =
    useBidDashboard(empresaAtivaId);
  const { data: bids = [], isFetching: carregandoLista, error: erroLista } =
    useBidLista(empresaAtivaId);
  const mut = useMutacoesBid(empresaAtivaId);

  const [confirmar, setConfirmar] = useState(null);

  const carregando = carregandoKpis || carregandoLista;
  const erro = erroKpis || erroLista;

  const excluir = async () => {
    try {
      await mut.deletar.mutateAsync(confirmar.id);
      sucesso("BID excluído.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Dashboard Executivo BIDs" subtitulo="Concorrência Logística" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

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

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* Resumo financeiro */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>
                Resumo Financeiro
              </Typography>
              <ResponsiveContainer width="100%" height={200}>
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
      </Grid>

      {/* Todos os BIDs (grade completa — antes era a tela separada "BIDs de Frete") */}
      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
        Todos os BIDs
      </Typography>

      {bids.length === 0 && !carregando ? (
        <Card variant="outlined" sx={{ border: `2px dashed ${GD.indigo}`, textAlign: "center", py: 4 }}>
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
      ) : (
        <Grid container spacing={2}>
          {bids.map((bid) => (
            <Grid item xs={12} md={6} key={bid.id}>
              <Card
                variant="outlined"
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
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <BidStatusChip status={bid.status} />
                      <Tooltip title={bid.status === "ENCERRADO" ? "BID encerrado não pode ser excluído" : "Excluir BID"}>
                        <span>
                          <IconButton
                            size="small"
                            disabled={bid.status === "ENCERRADO"}
                            onClick={(e) => { e.stopPropagation(); setConfirmar(bid); }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </Stack>
                  {bid.objetivo && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, noWrap: true }}>
                      {bid.objetivo.slice(0, 100)}{bid.objetivo.length > 100 ? "..." : ""}
                    </Typography>
                  )}
                  {bid.data_encerramento && (
                    <Chip size="small" label={`Encerra: ${bid.data_encerramento}`} variant="outlined" sx={{ mt: 1.5 }} />
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <ConfirmDialog
        aberto={Boolean(confirmar)}
        titulo="Excluir BID"
        mensagem={`Deseja excluir o BID "${confirmar?.nome}"? Esta ação não pode ser desfeita.`}
        textoConfirmar="Excluir"
        corConfirmar="error"
        onConfirmar={excluir}
        onCancelar={() => setConfirmar(null)}
        carregando={mut.deletar.isPending}
      />
    </Box>
  );
}
