import { useState, useEffect } from "react";
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PageHeader from "../components/PageHeader";
import Tabela from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { useUsuarios, useMutacoesCadastro } from "../api/queries";
import { qk } from "../api/queryKeys";
import { usuariosApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useEmpresa } from "../contexts/EmpresaContext";

const VAZIO = { nome: "", email: "", senha: "", is_active: true, is_superuser: false, empresas_ids: [] };

export default function Usuarios() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { usuario: usuarioLogado } = useAuth();
  const { empresas } = useEmpresa();
  const { data: linhas = [], isLoading: carregando, error } = useUsuarios();
  const { criar, atualizar, remover: removerMut } = useMutacoesCadastro(usuariosApi, qk.usuarios());
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
    setForm({
      nome: linha.nome,
      email: linha.email,
      senha: "",
      is_active: linha.is_active,
      is_superuser: linha.is_superuser,
      empresas_ids: linha.empresas_ids || [],
    });
    setDialogo(true);
  };

  const salvando = criar.isPending || atualizar.isPending;

  const salvar = async () => {
    try {
      if (editando) {
        const payload = {
          nome: form.nome,
          email: form.email,
          is_active: form.is_active,
          is_superuser: form.is_superuser,
          empresas_ids: form.empresas_ids,
        };
        if (form.senha) payload.senha = form.senha;
        await atualizar.mutateAsync({ id: editando.id, payload });
        sucesso("Usuário atualizado.");
      } else {
        await criar.mutateAsync(form);
        sucesso("Usuário criado.");
      }
      setDialogo(false);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível salvar o usuário."));
    }
  };

  const remover = async () => {
    try {
      await removerMut.mutateAsync(confirmar.id);
      sucesso("Usuário removido.");
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
      field: "empresas_ids",
      headerName: "Empresas",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: (p) => {
        const ids = p.value || [];
        if (ids.length === 0) return <Chip size="small" label="Global" variant="outlined" />;
        const nomes = ids.map((id) => empresas.find((e) => e.id === id)?.nome_fantasia || `#${id}`);
        return (
          <Tooltip title={nomes.join(", ")}>
            <span>{nomes.length > 1 ? `${nomes[0]} +${nomes.length - 1}` : nomes[0]}</span>
          </Tooltip>
        );
      },
    },
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
              helperText={
                editando
                  ? "Mínimo de 6 caracteres. Deixe em branco para manter a atual."
                  : "Mínimo de 8 caracteres, com pelo menos uma letra e um número."
              }
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
            <FormControl>
              <InputLabel id="usuario-empresas-label">Empresas</InputLabel>
              <Select
                labelId="usuario-empresas-label"
                multiple
                input={<OutlinedInput label="Empresas" />}
                value={form.empresas_ids}
                onChange={(e) => setForm({ ...form, empresas_ids: e.target.value })}
                renderValue={(ids) => ids
                  .map((id) => empresas.find((emp) => emp.id === id)?.nome_fantasia || id)
                  .join(", ")}
              >
                {empresas.map((emp) => (
                  <MenuItem key={emp.id} value={emp.id}>
                    {emp.nome_fantasia || emp.razao_social}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary">
              Vazio + Administrador = superusuário global (acesso a todas as empresas).
              Selecione 1 ou mais empresas para um usuário/admin restrito a elas — a
              tela de login pede para escolher entre elas quando houver mais de uma.
            </Typography>
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
