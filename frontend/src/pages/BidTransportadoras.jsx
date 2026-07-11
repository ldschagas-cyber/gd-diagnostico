import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Card, CardContent, Stack, Button, MenuItem, Select, FormControl,
  InputLabel, Table, TableHead, TableRow, TableCell, TableBody, Chip,
  LinearProgress, Alert, TextField, Rating, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidTransp, useMutacoesTranspBid, useTransportadoras } from "../api/queries";
import { extrairErro } from "../api/client";
import { TRANSP_STATUS_CONFIG } from "../components/BidStatusChip";
import ConfirmDialog from "../components/ConfirmDialog";

const STATUS_OPTIONS = Object.entries(TRANSP_STATUS_CONFIG).map(([v, c]) => ({ value: v, label: c.label }));

export default function BidTransportadoras() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const { data: lista = [], isFetching: carregandoLista } = useBidTransp(id);
  const { data: transp = [] } = useTransportadoras(empresaAtivaId);
  const mut = useMutacoesTranspBid(id, empresaAtivaId);
  const carregando = carregandoLista;

  const [sel, setSel] = useState("");
  const [obs, setObs] = useState("");
  const [avaliacao, setAvaliacao] = useState(5);
  const [confirmar, setConfirmar] = useState(null);

  const idsConvidados = new Set(lista.map((b) => b.transportadora_id));
  const disponiveis = transp.filter((t) => !idsConvidados.has(t.id));

  const convidar = async () => {
    if (!sel) return;
    try {
      await mut.convidar.mutateAsync({
        transportadora_id: Number(sel), observacoes: obs, avaliacao_usuario: avaliacao,
      });
      sucesso("Transportadora convidada."); setSel(""); setObs("");
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const mudarStatus = async (bt, novoStatus) => {
    try {
      await mut.status.mutateAsync({ tid: bt.id, status: novoStatus });
      sucesso("Status atualizado.");
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const remover = async () => {
    try {
      await mut.remover.mutateAsync(confirmar.id);
      sucesso("Removida.");
    } catch (e) { erroToast(extrairErro(e)); }
    finally { setConfirmar(null); }
  };

  const nomeTransp = (bt) =>
    bt.transportadora_nome
    || disponiveis.find((t) => t.id === bt.transportadora_id)?.razao_social
    || `Transportadora ${bt.transportadora_id}`;

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 600 }}>Convidar Transportadora</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="flex-end">
            <FormControl size="small" sx={{ flex: 2 }}>
              <InputLabel>Transportadora</InputLabel>
              <Select value={sel} label="Transportadora" onChange={(e) => setSel(e.target.value)}>
                {disponiveis.map((t) => (
                  <MenuItem key={t.id} value={t.id}>{t.nome_fantasia || t.razao_social}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="caption">Avaliação:</Typography>
              <Rating value={avaliacao} onChange={(_, v) => setAvaliacao(v)} max={10} size="small" />
            </Stack>
            <TextField size="small" label="Observações" value={obs} onChange={(e) => setObs(e.target.value)} sx={{ flex: 2 }} />
            <Button variant="contained" startIcon={<AddIcon />} onClick={convidar} disabled={!sel}>
              Convidar
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {carregando && <LinearProgress sx={{ mb: 1 }} />}

      <Card>
        <CardContent>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Transportadora</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Avaliação</TableCell>
                  <TableCell>Alterar Status</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {lista.map((bt) => {
                  const cfg = TRANSP_STATUS_CONFIG[bt.status] || { label: bt.status, color: "default" };
                  return (
                    <TableRow key={bt.id}>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {nomeTransp(bt)}
                      </TableCell>
                      <TableCell><Chip size="small" label={cfg.label} color={cfg.color} /></TableCell>
                      <TableCell>
                        {bt.avaliacao_usuario !== null && bt.avaliacao_usuario !== undefined
                          ? <Rating value={bt.avaliacao_usuario} max={10} readOnly size="small" />
                          : "—"}
                      </TableCell>
                      <TableCell>
                        <Select size="small" value={bt.status} onChange={(e) => mudarStatus(bt, e.target.value)} sx={{ minWidth: 160 }}>
                          {STATUS_OPTIONS.map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Button size="small" color="error" onClick={() => setConfirmar(bt)}>Remover</Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!confirmar}
        titulo="Remover transportadora do BID?"
        onClose={() => setConfirmar(null)}
        onConfirmar={remover}
      />
    </Box>
  );
}
