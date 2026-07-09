import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Stack,
  IconButton,
  Tooltip,
  MenuItem,
  Grid,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PageHeader from "../components/PageHeader";
import Tabela from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { VazioEstado } from "../components/Tabela";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useTransportadoras, useMutacoesTransportadora } from "../api/queries";
import { useDataGridEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { mascararCnpj, soDigitos, UFS } from "../utils/format";

const VAZIO = {
  razao_social: "",
  nome_fantasia: "",
  cnpj: "",
  endereco: "",
  cidade: "",
  uf: "",
  cep: "",
  contato: "",
  telefone: "",
  email: "",
};

export default function Transportadoras() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtivaId } = useEmpresa();

  // Lista via React Query: cache + dedup; retorno à tela é instantâneo.
  const { data: linhas = [], isFetching: carregando, error } =
    useTransportadoras(empresaAtivaId);
  const mut = useMutacoesTransportadora(empresaAtivaId);
  const salvando = mut.criar.isPending || mut.atualizar.isPending;

  // Estado do DataGrid (paginação/ordenação/filtro/colunas) preservado na navegação.
  const { props: gridProps } = useDataGridEstado("transportadoras");

  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(VAZIO);
  const [confirmar, setConfirmar] = useState(null);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  const abrirNovo = () => {
    setEditando(null);
    setForm(VAZIO);
    setDialogo(true);
  };
  const abrirEdicao = (linha) => {
    setEditando(linha);
    setForm({ ...VAZIO, ...linha });
    setDialogo(true);
  };

  const salvar = async () => {
    try {
      const payload = { ...form, cnpj: soDigitos(form.cnpj) };
      if (editando) {
        await mut.atualizar.mutateAsync({ id: editando.id, payload });
        sucesso("Transportadora atualizada.");
      } else {
        await mut.criar.mutateAsync(payload);
        sucesso("Transportadora cadastrada.");
      }
      setDialogo(false);
      // Sem carregar() manual: a mutação invalida o cache e a lista recarrega.
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível salvar a transportadora."));
    }
  };

  const remover = async () => {
    try {
      await mut.remover.mutateAsync(confirmar.id);
      sucesso("Transportadora removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  const colunas = [
    { field: "razao_social", headerName: "Razão social", flex: 1, minWidth: 200 },
    { field: "nome_fantasia", headerName: "Nome fantasia", flex: 1, minWidth: 150 },
    { field: "cnpj", headerName: "CNPJ", width: 170, valueFormatter: (v) => mascararCnpj(v) },
    { field: "cidade", headerName: "Cidade", width: 140 },
    { field: "uf", headerName: "UF", width: 70 },
    { field: "telefone", headerName: "Telefone", width: 130 },
    {
      field: "acoes",
      headerName: "Ações",
      width: 110,
      sortable: false,
      filterable: false,
      renderCell: (p) => (
        <Stack direction="row">
          <Tooltip title="Editar">
            <IconButton size="small" onClick={() => abrirEdicao(p.row)}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Remover">
            <IconButton size="small" color="error" onClick={() => setConfirmar(p.row)}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      ),
    },
  ];

  const valido = form.razao_social.trim();

  return (
    <Box>
      <PageHeader
        titulo="Transportadoras"
        subtitulo="Cadastro de transportadoras (criadas automaticamente na importação de CT-e)"
        acoes={
          <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
            Nova transportadora
          </Button>
        }
      />

      <Tabela rows={linhas} columns={colunas} carregando={carregando} {...gridProps} />

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editando ? "Editar transportadora" : "Nova transportadora"}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2.5} sx={{ mt: 0 }}>
            <Grid item xs={12} sm={8}>
              <TextField
                label="Razão social"
                value={form.razao_social}
                onChange={(e) => setForm({ ...form, razao_social: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="CNPJ"
                value={mascararCnpj(form.cnpj)}
                onChange={(e) => setForm({ ...form, cnpj: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nome fantasia"
                value={form.nome_fantasia}
                onChange={(e) => setForm({ ...form, nome_fantasia: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Endereço"
                value={form.endereco}
                onChange={(e) => setForm({ ...form, endereco: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={5}>
              <TextField
                label="Cidade"
                value={form.cidade}
                onChange={(e) => setForm({ ...form, cidade: e.target.value })}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                select
                label="UF"
                value={form.uf}
                onChange={(e) => setForm({ ...form, uf: e.target.value })}
              >
                <MenuItem value="">—</MenuItem>
                {UFS.map((uf) => (
                  <MenuItem key={uf} value={uf}>
                    {uf}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={6} sm={4}>
              <TextField
                label="CEP"
                value={form.cep}
                onChange={(e) => setForm({ ...form, cep: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Contato"
                value={form.contato}
                onChange={(e) => setForm({ ...form, contato: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Telefone"
                value={form.telefone}
                onChange={(e) => setForm({ ...form, telefone: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="E-mail"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogo(false)} color="inherit">
            Cancelar
          </Button>
          <Button variant="contained" onClick={salvar} disabled={!valido || salvando}>
            {salvando ? "Salvando..." : "Salvar"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        aberto={Boolean(confirmar)}
        titulo="Remover transportadora"
        mensagem={`Deseja remover "${confirmar?.razao_social}"?`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
