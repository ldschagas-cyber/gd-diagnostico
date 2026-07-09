import { useEffect, useState, useCallback } from "react";
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
  Chip,
  FormControlLabel,
  Switch,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PageHeader from "../components/PageHeader";
import Tabela from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { usuariosApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

const VAZIO = { nome: "", email: "", senha: "", is_active: true, is_superuser: false };

export default function Usuarios() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { usuario: usuarioLogado } = useAuth();
  const [linhas, setLinhas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [confirmar, setConfirmar] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setLinhas(await usuariosApi.listar());
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [erroToast]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const abrirNovo = () => {
    setEditando(null);
    setForm(VAZIO);
    setDialogo(true);
  };
  const abrirEdicao = (linha) => {
    setEditando(linha);
    setForm({
      nome: linha.nome,
      email: linha.email,
      senha: "",
      is_active: linha.is_active,
      is_superuser: linha.is_superuser,
    });
    setDialogo(true);
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      if (editando) {
        const payload = {
          nome: form.nome,
          email: form.email,
          is_active: form.is_active,
          is_superuser: form.is_superuser,
        };
        if (form.senha) payload.senha = form.senha;
        await usuariosApi.atualizar(editando.id, payload);
        sucesso("Usuário atualizado.");
      } else {
        await usuariosApi.criar(form);
        sucesso("Usuário criado.");
      }
      setDialogo(false);
      await carregar();
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível salvar o usuário."));
    } finally {
      setSalvando(false);
    }
  };

  const remover = async () => {
    try {
      await usuariosApi.remover(confirmar.id);
      sucesso("Usuário removido.");
      await carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  const colunas = [
    { field: "nome", headerName: "Nome", flex: 1, minWidth: 180 },
    { field: "email", headerName: "E-mail", flex: 1, minWidth: 220 },
    {
      field: "is_superuser",
      headerName: "Perfil",
      width: 140,
      renderCell: (p) => (
        <Chip
          size="small"
          label={p.value ? "Administrador" : "Operador"}
          color={p.value ? "secondary" : "default"}
          variant="outlined"
        />
      ),
    },
    {
      field: "is_active",
      headerName: "Status",
      width: 110,
      renderCell: (p) => (
        <Chip
          size="small"
          label={p.value ? "Ativo" : "Inativo"}
          color={p.value ? "success" : "default"}
        />
      ),
    },
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
          <Tooltip title={p.row.id === usuarioLogado?.id ? "Não é possível remover você mesmo" : "Remover"}>
            <span>
              <IconButton
                size="small"
                color="error"
                disabled={p.row.id === usuarioLogado?.id}
                onClick={() => setConfirmar(p.row)}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      ),
    },
  ];

  const valido =
    form.nome.trim() &&
    form.email.trim() &&
    (editando || form.senha.length >= 6);

  return (
    <Box>
      <PageHeader
        titulo="Usuários"
        subtitulo="Gestão de acessos ao sistema"
        acoes={
          <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
            Novo usuário
          </Button>
        }
      />

      <Tabela rows={linhas} columns={colunas} carregando={carregando} />

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar usuário" : "Novo usuário"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Nome"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              required
            />
            <TextField
              label="E-mail"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
            <TextField
              label={editando ? "Nova senha (deixe em branco para manter)" : "Senha"}
              type="password"
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
              helperText="Mínimo de 6 caracteres."
              required={!editando}
            />
            <Stack direction="row" spacing={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                }
                label="Ativo"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_superuser}
                    onChange={(e) => setForm({ ...form, is_superuser: e.target.checked })}
                  />
                }
                label="Administrador"
              />
            </Stack>
          </Stack>
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
        titulo="Remover usuário"
        mensagem={`Deseja remover o usuário "${confirmar?.nome}"?`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
