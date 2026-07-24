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
  MenuItem,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PageHeader from "../components/PageHeader";
import Tabela, { VazioEstado } from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { useFiliais, useMutacoesFilial } from "../api/queries";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { mascararCnpj, soDigitos, UFS } from "../utils/format";

export default function Filiais() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const { data: linhas = [], isLoading: carregando, error } = useFiliais(empresaAtivaId);
  const { criar, atualizar, remover: removerMut } = useMutacoesFilial(empresaAtivaId);
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ razao_social: "", cnpj: "", cidade: "", uf: "" });
  const [confirmar, setConfirmar] = useState(null);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  const abrirNovo = () => {
    setEditando(null);
    setForm({ razao_social: "", cnpj: "", cidade: "", uf: "" });
    setDialogo(true);
  };
  const abrirEdicao = (linha) => {
    setEditando(linha);
    setForm({
      razao_social: linha.razao_social,
      cnpj: linha.cnpj,
      cidade: linha.cidade || "",
      uf: linha.uf || "",
    });
    setDialogo(true);
  };

  const salvando = criar.isPending || atualizar.isPending;

  const salvar = async () => {
    try {
      const payload = {
        empresa_id: empresaAtivaId,
        razao_social: form.razao_social,
        cnpj: soDigitos(form.cnpj),
        cidade: form.cidade,
        uf: form.uf,
      };
      if (editando) {
        await atualizar.mutateAsync({ id: editando.id, payload });
        sucesso("Filial atualizada.");
      } else {
        await criar.mutateAsync(payload);
        sucesso("Filial cadastrada.");
      }
      setDialogo(false);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível salvar a filial."));
    }
  };

  const remover = async () => {
    try {
      await removerMut.mutateAsync(confirmar.id);
      sucesso("Filial removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  const colunas = [
    { field: "razao_social", headerName: "Razão social", flex: 1, minWidth: 220 },
    {
      field: "cnpj",
      headerName: "CNPJ",
      width: 180,
      valueFormatter: (v) => mascararCnpj(v),
    },
    { field: "cidade", headerName: "Cidade", flex: 1, minWidth: 140 },
    { field: "uf", headerName: "UF", width: 80 },
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

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Filiais" subtitulo="Unidades vinculadas à empresa ativa" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="As filiais são cadastradas por empresa. Selecione a empresa ativa no topo."
        />
      </Box>
    );
  }

  const valido = form.razao_social.trim() && soDigitos(form.cnpj).length === 14;

  return (
    <Box>
      <PageHeader
        titulo="Filiais"
        subtitulo={`Unidades de ${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}`}
        acoes={
          <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
            Nova filial
          </Button>
        }
      />

      <Alert severity="info" sx={{ mb: 2 }}>
        Os CNPJs das filiais (junto com o da matriz) determinam quais CT-es são
        importados para esta empresa.
      </Alert>

      <Tabela rows={linhas} columns={colunas} carregando={carregando} />

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar filial" : "Nova filial"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Razão social"
              value={form.razao_social}
              onChange={(e) => setForm({ ...form, razao_social: e.target.value })}
              required
            />
            <TextField
              label="CNPJ"
              value={mascararCnpj(form.cnpj)}
              onChange={(e) => setForm({ ...form, cnpj: e.target.value })}
              placeholder="00.000.000/0000-00"
              required
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="Cidade"
                value={form.cidade}
                onChange={(e) => setForm({ ...form, cidade: e.target.value })}
              />
              <TextField
                select
                label="UF"
                value={form.uf}
                onChange={(e) => setForm({ ...form, uf: e.target.value })}
                sx={{ width: 120 }}
              >
                <MenuItem value="">—</MenuItem>
                {UFS.map((uf) => (
                  <MenuItem key={uf} value={uf}>
                    {uf}
                  </MenuItem>
                ))}
              </TextField>
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
        titulo="Remover filial"
        mensagem={`Deseja remover a filial "${confirmar?.razao_social}"?`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
