import { useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, MenuItem, IconButton,
  Alert, LinearProgress, InputAdornment, Divider,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import RouteIcon from "@mui/icons-material/Route";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { useHubs, useCorredoresRef, useMutacoesCorredorRef } from "../api/queries";
import { extrairErro } from "../api/client";

const VAZIO = {
  hub_origem_codigo: "", hub_destino_codigo: "",
  frete_kg_min: 0, frete_kg_medio: 0, frete_kg_max: 0,
  frete_pct_min: 0, frete_pct_medio: 0, frete_pct_max: 0,
  volume_referencia: 0, dispersao_kg: 0, observacoes: "",
};

export default function BenchmarksCorredor() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: hubs = [] } = useHubs(true);
  const { data: lista = [], isLoading: carregando, error } = useCorredoresRef();
  const { salvar: salvarMut, remover: removerMut } = useMutacoesCorredorRef();
  const [form, setForm] = useState(VAZIO);

  if (error) erroToast(extrairErro(error));

  const nomeHub = useCallback(
    (cod) => hubs.find((h) => h.codigo === cod)?.nome || cod,
    [hubs]
  );

  const set = (campo, valor) => setForm((p) => ({ ...p, [campo]: valor }));

  const salvando = salvarMut.isPending;

  const salvar = async () => {
    if (!form.hub_origem_codigo || !form.hub_destino_codigo) {
      erroToast("Selecione o hub de origem e o de destino.");
      return;
    }
    try {
      const payload = {
        ...form,
        frete_kg_min: Number(form.frete_kg_min) || 0,
        frete_kg_medio: Number(form.frete_kg_medio) || 0,
        frete_kg_max: Number(form.frete_kg_max) || 0,
        frete_pct_min: Number(form.frete_pct_min) || 0,
        frete_pct_medio: Number(form.frete_pct_medio) || 0,
        frete_pct_max: Number(form.frete_pct_max) || 0,
        volume_referencia: Number(form.volume_referencia) || 0,
        dispersao_kg: Number(form.dispersao_kg) || 0,
      };
      await salvarMut.mutateAsync(payload);
      sucesso("Referência de corredor salva.");
      setForm(VAZIO);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const editar = (c) => setForm({ ...c });

  const remover = async (id) => {
    try {
      await removerMut.mutateAsync(id);
      sucesso("Referência removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const num = (campo, adorno, fim = false) => (
    <TextField
      type="number" size="small" value={form[campo] ?? 0}
      onChange={(e) => set(campo, e.target.value)} sx={{ width: 110 }}
      InputProps={fim
        ? { endAdornment: <InputAdornment position="end">{adorno}</InputAdornment> }
        : { startAdornment: <InputAdornment position="start">{adorno}</InputAdornment> }}
    />
  );

  return (
    <Box>
      <PageHeader
        titulo="Referências de Corredor"
        subtitulo="Configurações › Benchmark OD — referência de mercado por fluxo (Hub origem → Hub destino)"
      />

      <Alert severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}>
        Cadastre a referência de mercado de cada corredor. Esses valores são
        <strong> globais</strong> (valem para todos os clientes) e alimentam o
        score e a economia do Benchmark por Corredor. A dispersão (0 a 1) suaviza a
        penalização de corredores naturalmente mais voláteis.
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Nova referência / edição</Typography>
          <Stack spacing={2}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField select label="Hub de origem" value={form.hub_origem_codigo}
                onChange={(e) => set("hub_origem_codigo", e.target.value)} sx={{ minWidth: 220 }}>
                {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
              </TextField>
              <TextField select label="Hub de destino" value={form.hub_destino_codigo}
                onChange={(e) => set("hub_destino_codigo", e.target.value)} sx={{ minWidth: 220 }}>
                {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
              </TextField>
            </Stack>
            <Box>
              <Typography variant="overline" color="text.secondary">Frete por kg (R$)</Typography>
              <Stack direction="row" spacing={1.5} sx={{ mt: 0.5 }}>
                {num("frete_kg_min", "R$")}{num("frete_kg_medio", "R$")}{num("frete_kg_max", "R$")}
              </Stack>
            </Box>
            <Box>
              <Typography variant="overline" color="text.secondary">Frete sobre mercadoria (%)</Typography>
              <Stack direction="row" spacing={1.5} sx={{ mt: 0.5 }}>
                {num("frete_pct_min", "%", true)}{num("frete_pct_medio", "%", true)}{num("frete_pct_max", "%", true)}
              </Stack>
            </Box>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
              <TextField type="number" label="Volume de referência" size="small"
                value={form.volume_referencia} onChange={(e) => set("volume_referencia", e.target.value)}
                helperText="peso de mercado do fluxo" sx={{ width: 200 }} />
              <TextField type="number" label="Dispersão (0–1)" size="small"
                value={form.dispersao_kg} onChange={(e) => set("dispersao_kg", e.target.value)}
                inputProps={{ step: 0.05, min: 0, max: 1 }} sx={{ width: 160 }} />
              <TextField label="Observações" size="small" value={form.observacoes}
                onChange={(e) => set("observacoes", e.target.value)} sx={{ flex: 1, minWidth: 200 }} />
            </Stack>
            <Box>
              <Button variant="contained" onClick={salvar} disabled={salvando}>
                {form.id ? "Atualizar" : "Salvar"} referência
              </Button>
              {form.id && (
                <Button sx={{ ml: 1 }} onClick={() => setForm(VAZIO)}>Cancelar edição</Button>
              )}
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>Corredores cadastrados</Typography>
          {!lista.length ? (
            <Alert severity="info">Nenhuma referência de corredor cadastrada ainda.</Alert>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Corredor</TableCell>
                    <TableCell align="right">R$/kg (mín/méd/máx)</TableCell>
                    <TableCell align="right">% (mín/méd/máx)</TableCell>
                    <TableCell align="right">Disp.</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lista.map((c) => (
                    <TableRow key={c.id} hover sx={{ cursor: "pointer" }}>
                      <TableCell sx={{ fontWeight: 600 }} onClick={() => editar(c)}>
                        {nomeHub(c.hub_origem_codigo)} → {nomeHub(c.hub_destino_codigo)}
                      </TableCell>
                      <TableCell align="right" onClick={() => editar(c)}>
                        {c.frete_kg_min} / {c.frete_kg_medio} / {c.frete_kg_max}
                      </TableCell>
                      <TableCell align="right" onClick={() => editar(c)}>
                        {c.frete_pct_min} / {c.frete_pct_medio} / {c.frete_pct_max}
                      </TableCell>
                      <TableCell align="right" onClick={() => editar(c)}>{c.dispersao_kg}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" color="error" onClick={() => remover(c.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
          <Divider sx={{ my: 2 }} />
          <Typography variant="caption" color="text.secondary">
            Clique em uma linha para carregar os valores no formulário e editar.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
