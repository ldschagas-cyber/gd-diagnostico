import { useParams, useNavigate, useLocation, Outlet } from "react-router-dom";
import {
  Box, Tabs, Tab, Typography, Stack, Button, Alert, LinearProgress,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PageHeader from "../components/PageHeader";
import BidStatusChip from "../components/BidStatusChip";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBid, useMutacoesBid } from "../api/queries";
import { extrairErro } from "../api/client";

// rota "" = índice (Visão Geral / escopo da concorrência)
const TABS = [
  { label: "Visão Geral", rota: "" },
  { label: "Escopo", rota: "escopo" },
  { label: "Transportadoras", rota: "transportadoras" },
  { label: "Propostas", rota: "propostas" },
  { label: "Comparativo", rota: "comparativo" },
  { label: "Simulação", rota: "simulacao" },
  { label: "Relatórios", rota: "relatorios" },
];

const PROXIMOS = {
  RASCUNHO: "ABERTO",
  ABERTO: "EM_COTACAO",
  EM_COTACAO: "ENCERRADO",
};

const LABELS = { ABERTO: "Abrir BID", EM_COTACAO: "Iniciar Cotação", ENCERRADO: "Encerrar BID" };

/**
 * Layout do detalhe de um BID. Mantém header, botão Voltar e as abas fixos
 * em TODAS as telas internas (Escopo, Transportadoras, Propostas, etc.),
 * que são renderizadas no <Outlet> como rotas aninhadas.
 */
export default function BidDetalhe() {
  const { id } = useParams();
  const nav = useNavigate();
  const loc = useLocation();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  // BID via React Query: cache + dedup; retorno à tela é instantâneo.
  const { data: bid, isLoading: carregando } = useBid(id);
  const mut = useMutacoesBid(empresaAtivaId);

  const avancarStatus = async () => {
    const proximo = PROXIMOS[bid.status];
    if (!proximo) return;
    try {
      const atualizado = await mut.alterarStatus.mutateAsync({ id, status: proximo });
      sucesso(`BID → ${atualizado.status}`);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  if (carregando) return <LinearProgress />;
  if (!bid) return <Alert severity="error">BID não encontrado.</Alert>;

  const proximo = PROXIMOS[bid.status];

  // Aba ativa derivada da URL (sufixo após /bid/:id)
  const sub = loc.pathname.replace(`/bid/${id}`, "").replace(/^\//, "");
  const idx = TABS.findIndex((t) => t.rota === sub);
  const tabAtiva = idx >= 0 ? idx : 0;

  return (
    <Box>
      <PageHeader
        titulo={bid.nome}
        subtitulo={bid.objetivo || "Processo de concorrência logística"}
        acoes={
          <Stack direction="row" spacing={1.5} alignItems="center">
            <BidStatusChip status={bid.status} size="medium" />
            {proximo && (
              <Button variant="contained" size="small" onClick={avancarStatus} disabled={mut.alterarStatus.isPending}>
                {LABELS[proximo]}
              </Button>
            )}
            <Button startIcon={<ArrowBackIcon />} size="small" onClick={() => nav("/bid")}>
              Voltar
            </Button>
          </Stack>
        }
      />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {bid.periodo_analise_inicio && `Período analisado: ${bid.periodo_analise_inicio} → ${bid.periodo_analise_fim}`}
        {bid.data_encerramento && `  ·  Prazo: ${bid.data_encerramento}`}
      </Typography>

      <Tabs
        value={tabAtiva}
        onChange={(_, v) => nav(`/bid/${id}${TABS[v].rota ? "/" + TABS[v].rota : ""}`)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 2 }}
      >
        {TABS.map((t) => <Tab key={t.rota || "index"} label={t.label} />)}
      </Tabs>

      <Outlet context={{ bid }} />
    </Box>
  );
}
