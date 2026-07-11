import { useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
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
  Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import PageHeader from "../components/PageHeader";
import Tabela from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useFeedback } from "../components/Feedback";
import { useCidades, useRegioes, useMutacoesCadastro } from "../api/queries";
import { qk } from "../api/queryKeys";
import { cidadesApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { UFS, MACRO_REGIOES, rotuloMacro } from "../utils/format";

const VAZIO = { nome: "", uf: "", regiao_id: "", macro_regiao: "" };

export default function Cidades() {
  const { sucesso, erro: erroToast } = useFeedback();
  const qc = useQueryClient();
  const { data: linhas = [], isLoading: carregando, error } = useCidades();
  const { data: regioes = [] } = useRegioes();
  const { criar, atualizar, remover: removerMut } = useMutacoesCadastro(cidadesApi, qk.cidades());
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(VAZIO);
  const [confirmar, setConfirmar] = useState(null);
  const fileRef = useRef(null);

  if (error) erroToast(extrairErro(error));

  const baixarModelo = async () => {
    try {
      await cidadesApi.baixarModelo();
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const importarExcel = async (e) => {
    const file = e.target.files?.[0];
    if (file) e.target.value = "";
    if (!file) return;
    try {
      const r = await cidadesApi.importarExcel(file);
      const msg = r.ignoradas > 0
        ? `${r.importadas} cidades importadas · ${r.ignoradas} ignoradas (já cadastradas ou inválidas).`
        : `${r.importadas} cidades importadas.`;
      sucesso(msg);
      qc.invalidateQueries({ queryKey: qk.cidades() });
    } catch (ex) {
      erroToast(extrairErro(ex));
    }
  };

  const abrirNovo = () => {
    setEditando(null);
    setForm(VAZIO);
    setDialogo(true);
  };
  const abrirEdicao = (linha) => {
    setEditando(linha);
    setForm({
      nome: linha.nome,
      uf: linha.uf || "",
      regiao_id: linha.regiao_id || "",
      macro_regiao: linha.macro_regiao || "",
    });
    setDialogo(true);
  };

  const salvando = criar.isPending || atualizar.isPending;

  const salvar = async () => {
    try {
      const payload = {
        nome: form.nome,
        uf: form.uf,
        regiao_id: form.regiao_id || null,
        macro_regiao: form.macro_regiao || null,
      };
      if (editando) {
        await atualizar.mutateAsync({ id: editando.id, payload });
        sucesso("Cidade atualizada.");
      } else {
        await criar.mutateAsync(payload);
        sucesso("Cidade cadastrada.");
      }
      setDialogo(false);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const remover = async () => {
    try {
      await removerMut.mutateAsync(confirmar.id);
      sucesso("Cidade removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  const nomeRegiao = (id) => regioes.find((r) => r.id === id)?.nome || "—";

  const colunas = [
    { field: "nome", headerName: "Cidade", flex: 1, minWidth: 180 },
    { field: "uf", headerName: "UF", width: 80 },
    {
      field: "macro_regiao",
      headerName: "Macro-região",
      width: 150,
      renderCell: (p) =>
        p.value ? <Chip size="small" label={rotuloMacro(p.value)} variant="outlined" /> : "—",
    },
    {
      field: "regiao_id",
      headerName: "Região logística",
      flex: 1,
      minWidth: 160,
      valueFormatter: (v) => nomeRegiao(v),
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
          <Tooltip title="Remover">
            <IconButton size="small" color="error" onClick={() => setConfirmar(p.row)}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      ),
    },
  ];

  const valido = form.nome.trim() && form.uf;

  return (
    <Box>
      <PageHeader
        titulo="Cidades"
        subtitulo="Cidades, UF e vínculo com regiões e macro-regiões"
        acoes={
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="outlined" startIcon={<DownloadIcon />} onClick={baixarModelo}>
              Baixar modelo
            </Button>
            <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileRef.current?.click()}>
              Importar Excel
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              hidden
              onChange={importarExcel}
            />
            <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
              Nova cidade
            </Button>
          </Box>
        }
      />

      <Tabela rows={linhas} columns={colunas} carregando={carregando} />

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar cidade" : "Nova cidade"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <Stack direction="row" spacing={2}>
              <TextField
                label="Cidade"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                required
              />
              <TextField
                select
                label="UF"
                value={form.uf}
                onChange={(e) => setForm({ ...form, uf: e.target.value })}
                sx={{ width: 120 }}
                required
              >
                {UFS.map((uf) => (
                  <MenuItem key={uf} value={uf}>
                    {uf}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <TextField
              select
              label="Macro-região"
              value={form.macro_regiao}
              onChange={(e) => setForm({ ...form, macro_regiao: e.target.value })}
            >
              <MenuItem value="">—</MenuItem>
              {MACRO_REGIOES.map((m) => (
                <MenuItem key={m.valor} value={m.valor}>
                  {m.rotulo}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Região logística"
              value={form.regiao_id}
              onChange={(e) => setForm({ ...form, regiao_id: e.target.value })}
            >
              <MenuItem value="">—</MenuItem>
              {regioes.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.nome}
                </MenuItem>
              ))}
            </TextField>
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
        titulo="Remover cidade"
        mensagem={`Deseja remover "${confirmar?.nome}"?`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
