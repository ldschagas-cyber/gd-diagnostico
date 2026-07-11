import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Card, CardContent, Grid, TextField, Button, Stack, MenuItem, Select,
  FormControl, InputLabel, Table, TableHead, TableRow, TableCell, TableBody,
  Typography, LinearProgress, Alert, Tabs, Tab,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { bidApi } from "../api/endpoints";
import { useBidPropostas, useBidTransp, useMutacoesPropostas } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";

const TIPOS = [
  { value: "REGIAO", label: "Região" },
  { value: "UF", label: "UF" },
  { value: "FILIAL", label: "Filial" },
  { value: "TRANSPORTADORA", label: "Transportadora" },
  { value: "FAIXA_PESO", label: "Faixa de Peso" },
];

const VAZIO = {
  bid_transportadora_id: "",
  tipo_agrupamento: "REGIAO",
  valor_grupo: "",
  valor_rs_kg: "",
  valor_minimo: "0",
  prazo_dias: "0",
  cobertura_pct: "100",
  observacoes: "",
};

export default function BidPropostas() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const { data: propostas = [], isFetching: carregandoPropostas } = useBidPropostas(id);
  const { data: bts = [] } = useBidTransp(id);
  const mut = useMutacoesPropostas(id, empresaAtivaId);
  const carregando = carregandoPropostas;
  const salvando = mut.incluir.isPending;

  const [form, setForm] = useState(VAZIO);
  const [aba, setAba] = useState(0);

  const onChange = (c) => (e) => setForm((f) => ({ ...f, [c]: e.target.value }));

  const salvar = async () => {
    if (!form.bid_transportadora_id || !form.valor_grupo || !form.valor_rs_kg) {
      erroToast("Preencha transportadora, grupo e valor R$/kg."); return;
    }
    try {
      await mut.incluir.mutateAsync({
        ...form,
        bid_transportadora_id: Number(form.bid_transportadora_id),
        valor_rs_kg: Number(form.valor_rs_kg),
        valor_minimo: Number(form.valor_minimo) || 0,
        prazo_dias: Number(form.prazo_dias) || 0,
        cobertura_pct: Number(form.cobertura_pct) || 100,
      });
      sucesso("Proposta incluída."); setForm(VAZIO);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const importar = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const r = await mut.importar.mutateAsync(f);
      const msg = r.ignoradas > 0
        ? `${r.importadas} propostas importadas · ${r.ignoradas} ignoradas (transportadora não convidada ou sem preço).`
        : `${r.importadas} propostas importadas.`;
      sucesso(msg);
    } catch (ex) { erroToast(extrairErro(ex)); }
    e.target.value = "";
  };

  const baixarModelo = async () => {
    try {
      await bidApi.baixarModeloPropostas(id, empresaAtivaId);
    } catch (ex) { erroToast(extrairErro(ex, "Falha ao baixar o modelo.")); }
  };

  const btNome = (btId) => {
    const bt = bts.find((b) => b.id === Number(btId));
    if (!bt) return btId;
    return bt.transportadora_nome || `Transportadora ${bt.transportadora_id}`;
  };

  return (
    <Box>
      <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ mb: 2 }}>
        <Tab label="Inclusão Manual" />
        <Tab label="Importar Excel" />
      </Tabs>

      {aba === 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 600 }}>Nova Proposta</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Transportadora</InputLabel>
                  <Select value={form.bid_transportadora_id} label="Transportadora" onChange={onChange("bid_transportadora_id")}>
                    {bts.map((bt) => (
                      <MenuItem key={bt.id} value={bt.id}>Transp. {bt.transportadora_id} — {bt.status}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Tipo agrupamento</InputLabel>
                  <Select value={form.tipo_agrupamento} label="Tipo agrupamento" onChange={onChange("tipo_agrupamento")}>
                    {TIPOS.map((t) => <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Grupo (região, UF, faixa...)" value={form.valor_grupo} onChange={onChange("valor_grupo")} />
              </Grid>
              <Grid item xs={6} sm={2}>
                <TextField fullWidth size="small" label="R$/kg" type="number" value={form.valor_rs_kg} onChange={onChange("valor_rs_kg")} />
              </Grid>
              <Grid item xs={6} sm={2}>
                <TextField fullWidth size="small" label="Mín. (R$)" type="number" value={form.valor_minimo} onChange={onChange("valor_minimo")} />
              </Grid>
              <Grid item xs={6} sm={2}>
                <TextField fullWidth size="small" label="Prazo (dias)" type="number" value={form.prazo_dias} onChange={onChange("prazo_dias")} />
              </Grid>
              <Grid item xs={6} sm={2}>
                <TextField fullWidth size="small" label="Cobertura %" type="number" value={form.cobertura_pct} onChange={onChange("cobertura_pct")} />
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth size="small" label="Observações" value={form.observacoes} onChange={onChange("observacoes")} />
              </Grid>
              <Grid item xs={12}>
                <Button variant="contained" onClick={salvar} disabled={salvando}>Incluir Proposta</Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {aba === 1 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="body2" sx={{ mb: 1.5 }}>
              Baixe o modelo já pré-preenchido com os grupos do escopo e as transportadoras
              convidadas, envie para as transportadoras preencherem os preços e importe o
              arquivo de volta aqui.
            </Typography>
            <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={baixarModelo}
              >
                Baixar Modelo Excel
              </Button>
              <Button variant="contained" component="label" startIcon={<UploadFileIcon />}>
                Importar Excel preenchido
                <input type="file" accept=".xlsx" hidden onChange={importar} />
              </Button>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Colunas obrigatórias: <strong>transportadora_id | tipo_agrupamento | valor_grupo | valor_rs_kg</strong> (opcionais: valor_minimo, prazo_dias, cobertura_pct, observacoes).
            </Typography>
          </CardContent>
        </Card>
      )}

      {carregando && <LinearProgress sx={{ mb: 1 }} />}

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>Propostas ({propostas.length})</Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Transportadora</TableCell>
                  <TableCell>Grupo</TableCell>
                  <TableCell align="right">R$/kg</TableCell>
                  <TableCell align="right">Mínimo</TableCell>
                  <TableCell align="right">Prazo</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell>Origem</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {propostas.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>{btNome(p.bid_transportadora_id)}</TableCell>
                    <TableCell>{p.valor_grupo}</TableCell>
                    <TableCell align="right">{fmtNumero(p.valor_rs_kg, 4)}</TableCell>
                    <TableCell align="right">{fmtMoeda(p.valor_minimo)}</TableCell>
                    <TableCell align="right">{p.prazo_dias}d</TableCell>
                    <TableCell align="right">{p.cobertura_pct}%</TableCell>
                    <TableCell>{p.origem}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
