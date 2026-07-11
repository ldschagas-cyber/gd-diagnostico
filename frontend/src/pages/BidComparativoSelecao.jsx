import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, Divider,
  LinearProgress, Alert,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import BidStatusChip from "../components/BidStatusChip";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidLista } from "../api/queries";
import { extrairErro } from "../api/client";

/**
 * Tela de entrada do "Comparativo" no menu (Concorrência Logística - BID).
 *
 * O comparativo de propostas é sempre relativo a um BID específico
 * (rota /bid/:id/comparativo). Esta tela lista os BIDs da empresa ativa
 * e encaminha para o comparativo do BID selecionado. Não altera nem
 * substitui a tela BidComparativo existente — apenas oferece o ponto de
 * entrada que faltava no menu.
 */
export default function BidComparativoSelecao() {
  const { empresaAtivaId, empresaAtiva } = useEmpresa();
  const nav = useNavigate();

  const { data: bids = [], isFetching: carregando, error } = useBidLista(empresaAtivaId);
  const erro = error ? extrairErro(error) : "";

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Comparativo de Propostas" subtitulo="Concorrência Logística" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Comparativo de Propostas"
        subtitulo={empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social || ""}
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      <Alert severity="info" sx={{ mb: 2.5 }}>
        Selecione um BID para ver o comparativo de propostas e o ranking de transportadoras.
      </Alert>

      {bids.length === 0 && !carregando ? (
        <VazioEstado
          mensagem="Nenhum BID criado ainda"
          descricao="Crie um processo de concorrência em “BIDs de Frete” para comparar propostas."
        />
      ) : (
        <Card>
          <CardContent>
            {bids.map((b, i) => (
              <Box key={b.id}>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  sx={{
                    py: 1.5, px: 1, borderRadius: 1, cursor: "pointer",
                    "&:hover": { bgcolor: "action.hover" },
                  }}
                  onClick={() => nav(`/bid/${b.id}/comparativo`)}
                >
                  <Box>
                    <Typography variant="body2" fontWeight={600}>{b.nome}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {b.data_inicio} → {b.data_encerramento || "—"}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <BidStatusChip status={b.status} />
                    <ChevronRightIcon sx={{ color: "text.secondary" }} />
                  </Stack>
                </Stack>
                {i < bids.length - 1 && <Divider />}
              </Box>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
