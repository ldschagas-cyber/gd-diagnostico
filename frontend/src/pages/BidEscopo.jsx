import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, Button, MenuItem, Select,
  FormControl, InputLabel, Table, TableHead, TableRow, TableCell, TableBody,
  LinearProgress, Alert, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, IconButton,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { bidApi } from "../api/endpoints";
import { useBidEscopo, useMutacoesEscopo } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";

const TIPOS = [
  { value: "REGIAO", label: "Região" },
  { value: "UF", label: "UF" },
  { value: "TRANSPORTADORA", label: "Transportadora" },
  { value: "FILIAL", label: "Filial / Tomador" },
  { value: "FAIXA_PESO", label: "Faixa de Peso (livre)" },
];

export default function BidEscopo() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const { data: escopos = [], isFetching: carregando } = useBidEscopo(id);
  const mut = useMutacoesEscopo(id, empresaAtivaId);
  const gerando = mut.gerar.isPending;

  const [gerandoTipo, setGerandoTipo] = useState("REGIAO");
  const [faixas, setFaixas] = useState([{ label: "", min: 0, max: null }]);
  const [dialogFaixa, setDialogFaixa] = useState(false);

  const gerar = async () => {
    try {
      const payload = { tipo_agrupamento: gerandoTipo };
      if (gerandoTipo === "FAIXA_PESO") payload.faixas_peso = faixas;
      await mut.gerar.mutateAsync(payload);
      sucesso("Escopo gerado.");
      setDialogFaixa(false);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const baixarPacote = () => bidApi.baixarRelatorio(id, empresaAtivaId, "pacote_cotacao", "pdf");

  const deletarItem = async (eid) => {
    try {
      await mut.remover.mutateAsync(eid);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const total_frete = escopos.reduce((a, e) => a + e.valor_frete_total, 0);
  const total_peso = escopos.reduce((a, e) => a + e.peso_total, 0);
  const total_embarques = escopos.reduce((a, e) => a + e.qtd_embarques, 0);

  return (
    <Box>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }} sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ width: 220 }}>
          <InputLabel>Tipo de agrupamento</InputLabel>
          <Select value={gerandoTipo} label="Tipo de agrupamento" onChange={(e) => setGerandoTipo(e.target.value)}>
            {TIPOS.map((t) => <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>)}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          onClick={gerandoTipo === "FAIXA_PESO" ? () => setDialogFaixa(true) : gerar}
          disabled={gerando}
        >
          Gerar Escopo
        </Button>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={baixarPacote}>
          Pacote de Cotação (PDF)
        </Button>
      </Stack>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {escopos.length === 0 && !carregando && (
        <Alert severity="info">Nenhum escopo gerado. Selecione um agrupamento e clique em Gerar Escopo.</Alert>
      )}

      {escopos.length > 0 && (
        <Card>
          <CardContent>
            <Stack direction="row" spacing={3} sx={{ mb: 2 }}>
              <Typography variant="body2">Embarques: <strong>{fmtNumero(total_embarques, 0)}</strong></Typography>
              <Typography variant="body2">Peso total: <strong>{fmtNumero(total_peso, 0)} kg</strong></Typography>
              <Typography variant="body2">Frete total: <strong>{fmtMoeda(total_frete)}</strong></Typography>
            </Stack>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tipo</TableCell>
                    <TableCell>Grupo</TableCell>
                    <TableCell align="right">Embarques</TableCell>
                    <TableCell align="right">Peso (kg)</TableCell>
                    <TableCell align="right">Frete (R$)</TableCell>
                    <TableCell align="right">R$/kg</TableCell>
                    <TableCell align="right">% Frete</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {escopos.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell><Chip size="small" label={e.tipo_agrupamento} variant="outlined" /></TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{e.valor_grupo}</TableCell>
                      <TableCell align="right">{e.qtd_embarques}</TableCell>
                      <TableCell align="right">{fmtNumero(e.peso_total, 0)}</TableCell>
                      <TableCell align="right">{fmtMoeda(e.valor_frete_total)}</TableCell>
                      <TableCell align="right">{fmtNumero(e.frete_rs_kg, 4)}</TableCell>
                      <TableCell align="right">{fmtNumero(e.frete_pct, 1)}%</TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => deletarItem(e.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Dialog faixas de peso */}
      <Dialog open={dialogFaixa} onClose={() => setDialogFaixa(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Definir Faixas de Peso Livres</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Defina as faixas de peso para o agrupamento. Os campos são livres — use a nomenclatura da sua operação.
          </Typography>
          {faixas.map((f, i) => (
            <Stack direction="row" spacing={1} sx={{ mb: 1 }} key={i}>
              <TextField size="small" label="Label" value={f.label} onChange={(e) => {
                const copia = [...faixas]; copia[i] = { ...copia[i], label: e.target.value }; setFaixas(copia);
              }} sx={{ flex: 2 }} />
              <TextField size="small" label="Min (kg)" type="number" value={f.min} onChange={(e) => {
                const copia = [...faixas]; copia[i] = { ...copia[i], min: Number(e.target.value) }; setFaixas(copia);
              }} sx={{ flex: 1 }} />
              <TextField size="small" label="Max (kg)" type="number" value={f.max || ""} onChange={(e) => {
                const copia = [...faixas]; copia[i] = { ...copia[i], max: e.target.value ? Number(e.target.value) : null }; setFaixas(copia);
              }} sx={{ flex: 1 }} />
              <IconButton size="small" onClick={() => setFaixas(faixas.filter((_, j) => j !== i))}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Stack>
          ))}
          <Button startIcon={<AddIcon />} onClick={() => setFaixas([...faixas, { label: "", min: 0, max: null }])}>
            Adicionar faixa
          </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogFaixa(false)}>Cancelar</Button>
          <Button variant="contained" onClick={gerar} disabled={gerando}>Gerar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
