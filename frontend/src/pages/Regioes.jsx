import { useEffect, useState, useCallback, useRef } from "react";
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
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import PageHeader from "../components/PageHeader";
import Tabela from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { regioesApi } from "../api/endpoints";
import { extrairErro } from "../api/client";

export default function Regioes() {
  const { sucesso, erro: erroToast, info } = useFeedback();
  const inputCsv = useRef(null);
  const [linhas, setLinhas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ nome: "", descricao: "" });
  const [salvando, setSalvando] = useState(false);
  const [confirmar, setConfirmar] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setLinhas(await regioesApi.listar());
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
    setForm({ nome: "", descricao: "" });
    setDialogo(true);
  };
  const abrirEdicao = (linha) => {
    setEditando(linha);
    setForm({ nome: linha.nome, descricao: linha.descricao || "" });
    setDialogo(true);
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      if (editando) {
        await regioesApi.atualizar(editando.id, form);
        sucesso("Região atualizada.");
      } else {
        await regioesApi.criar(form);
        sucesso("Região cadastrada.");
      }
      setDialogo(false);
      await carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const remover = async () => {
    try {
      await regioesApi.remover(confirmar.id);
      sucesso("Região removida.");
      await carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  const importarCsv = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    info("Importando CSV...");
    try {
      const res = await regioesApi.importarCsv(file);
      sucesso(res?.mensagem || `Importação concluída (${res?.importados ?? 0} regiões).`);
      await carregar();
    } catch (err) {
      erroToast(extrairErro(err, "Falha ao importar o CSV."));
    } finally {
      if (inputCsv.current) inputCsv.current.value = "";
    }
  };

  const colunas = [
    { field: "nome", headerName: "Região", flex: 1, minWidth: 200 },
    { field: "descricao", headerName: "Descrição", flex: 2, minWidth: 240 },
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

  return (
    <Box>
      <PageHeader
        titulo="Regiões logísticas"
        subtitulo="Agrupamentos regionais para análise de frete"
        acoes={
          <Stack direction="row" spacing={1.5}>
            <input
              ref={inputCsv}
              type="file"
              accept=".csv"
              hidden
              onChange={importarCsv}
            />
            <Button
              variant="outlined"
              startIcon={<UploadFileIcon />}
              onClick={() => inputCsv.current?.click()}
            >
              Importar CSV
            </Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
              Nova região
            </Button>
          </Stack>
        }
      />

      <Tabela rows={linhas} columns={colunas} carregando={carregando} />

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar região" : "Nova região"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Nome"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              required
            />
            <TextField
              label="Descrição"
              value={form.descricao}
              onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              multiline
              rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogo(false)} color="inherit">
            Cancelar
          </Button>
          <Button variant="contained" onClick={salvar} disabled={!form.nome.trim() || salvando}>
            {salvando ? "Salvando..." : "Salvar"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        aberto={Boolean(confirmar)}
        titulo="Remover região"
        mensagem={`Deseja remover a região "${confirmar?.nome}"?`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
