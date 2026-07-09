import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Grid, TextField, Button, Stack, Alert, Typography,
  FormControl, InputLabel, Select, MenuItem,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { bidApi, regioesApi } from "../api/endpoints";
import { extrairErro } from "../api/client";

const MACRO_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];

const SEGMENTACOES = [
  { value: "GERAL", label: "Geral (todos os fretes)" },
  { value: "REGIAO", label: "Região (macrorregião)" },
  { value: "CIDADE", label: "Cidade" },
  { value: "REGIAO_LOGISTICA", label: "Região Logística" },
];

const VAZIO = {
  nome: "",
  descricao: "",
  objetivo: "",
  observacoes: "",
  segmentacao_tipo: "GERAL",
  segmentacao_valor: "",
  data_inicio: "",
  data_encerramento: "",
  periodo_analise_inicio: "",
  periodo_analise_fim: "",
};

export default function BidFormulario() {
  const { empresaAtivaId } = useEmpresa();
  const nav = useNavigate();
  const { sucesso, erro: erroToast } = useFeedback();
  const [form, setForm] = useState(VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [regioes, setRegioes] = useState([]);

  useEffect(() => {
    regioesApi.listar().then(setRegioes).catch(() => {});
  }, []);

  const onChange = (campo) => (e) => setForm((f) => ({ ...f, [campo]: e.target.value }));

  // Ao trocar o tipo de segmentação, limpa o valor anterior
  const onChangeTipoSeg = (e) =>
    setForm((f) => ({ ...f, segmentacao_tipo: e.target.value, segmentacao_valor: "" }));

  const salvar = async () => {
    if (!form.nome.trim()) { setErro("Nome do BID é obrigatório."); return; }
    setSalvando(true);
    setErro("");
    try {
      const payload = {
        ...form,
        data_inicio: form.data_inicio || null,
        data_encerramento: form.data_encerramento || null,
        periodo_analise_inicio: form.periodo_analise_inicio || null,
        periodo_analise_fim: form.periodo_analise_fim || null,
      };
      const criado = await bidApi.criar(empresaAtivaId, payload);
      sucesso("BID criado com sucesso.");
      nav(`/bid/${criado.id}`);
    } catch (e) {
      setErro(extrairErro(e, "Não foi possível criar o BID."));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Box>
      <PageHeader titulo="Novo BID de Frete" subtitulo="Configure o processo de concorrência logística" />
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}
      <Card>
        <CardContent>
          <Grid container spacing={2.5}>
            <Grid item xs={12}>
              <TextField fullWidth label="Nome do BID *" value={form.nome} onChange={onChange("nome")} />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth multiline rows={2} label="Objetivo estratégico" value={form.objetivo} onChange={onChange("objetivo")} />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth multiline rows={2} label="Descrição" value={form.descricao} onChange={onChange("descricao")} />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="overline" color="text.secondary">Período de análise (CT-es que gerarão o escopo)</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth type="date" label="De" value={form.periodo_analise_inicio} onChange={onChange("periodo_analise_inicio")} InputLabelProps={{ shrink: true }} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth type="date" label="Até" value={form.periodo_analise_fim} onChange={onChange("periodo_analise_fim")} InputLabelProps={{ shrink: true }} />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="overline" color="text.secondary">Vigência do BID</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth type="date" label="Início" value={form.data_inicio} onChange={onChange("data_inicio")} InputLabelProps={{ shrink: true }} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth type="date" label="Prazo para propostas" value={form.data_encerramento} onChange={onChange("data_encerramento")} InputLabelProps={{ shrink: true }} />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="overline" color="text.secondary">Segmentação da concorrência</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Tipo de segmentação</InputLabel>
                <Select
                  label="Tipo de segmentação"
                  value={form.segmentacao_tipo}
                  onChange={onChangeTipoSeg}
                >
                  {SEGMENTACOES.map((s) => (
                    <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              {form.segmentacao_tipo === "REGIAO" && (
                <FormControl fullWidth>
                  <InputLabel>Macrorregião</InputLabel>
                  <Select label="Macrorregião" value={form.segmentacao_valor} onChange={onChange("segmentacao_valor")}>
                    {MACRO_REGIOES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                  </Select>
                </FormControl>
              )}
              {form.segmentacao_tipo === "CIDADE" && (
                <TextField
                  fullWidth label="Cidade (município de destino)"
                  value={form.segmentacao_valor} onChange={onChange("segmentacao_valor")}
                  placeholder="Ex.: Recife"
                />
              )}
              {form.segmentacao_tipo === "REGIAO_LOGISTICA" && (
                <FormControl fullWidth>
                  <InputLabel>Região logística</InputLabel>
                  <Select label="Região logística" value={form.segmentacao_valor} onChange={onChange("segmentacao_valor")}>
                    {regioes.length === 0 && <MenuItem value="" disabled>Nenhuma região cadastrada</MenuItem>}
                    {regioes.map((r) => <MenuItem key={r.id} value={r.nome}>{r.nome}</MenuItem>)}
                  </Select>
                </FormControl>
              )}
            </Grid>

            <Grid item xs={12}>
              <TextField fullWidth multiline rows={2} label="Observações" value={form.observacoes} onChange={onChange("observacoes")} />
            </Grid>
          </Grid>

          <Stack direction="row" spacing={2} sx={{ mt: 3 }} justifyContent="flex-end">
            <Button variant="outlined" onClick={() => nav("/bid")}>Cancelar</Button>
            <Button variant="contained" onClick={salvar} disabled={salvando}>
              {salvando ? "Salvando..." : "Criar BID"}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
