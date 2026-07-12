import { useState, useRef, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, MenuItem, IconButton,
  Alert, LinearProgress, Chip, Autocomplete, Tab, Tabs, InputAdornment, Divider,
  Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel, Switch, Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import HubIcon from "@mui/icons-material/Hub";
import RouteIcon from "@mui/icons-material/Route";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import ConfirmDialog from "../components/ConfirmDialog";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useAuth } from "../contexts/AuthContext";
import { useFeedback } from "../components/Feedback";
import {
  useHubs, useMutacoesHub, useClusters, useMutacoesCluster,
  useCorredoresRef, useMutacoesCorredorRef,
} from "../api/queries";
import { clustersApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { UFS } from "../utils/format";

function AbaHubs() {
  const { usuario } = useAuth();
  const { sucesso, erro: erroToast } = useFeedback();
  const podeEscrever = Boolean(usuario?.is_superuser);

  const { data: hubs = [], isLoading: carregando, error } = useHubs(false);
  const { criar, atualizar, remover: removerMut } = useMutacoesHub();
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ codigo: "", nome: "", descricao: "", ativo: true });
  const [confirmar, setConfirmar] = useState(null);

  if (error) erroToast(extrairErro(error));

  const abrirNovo = () => {
    setEditando(null);
    setForm({ codigo: "", nome: "", descricao: "", ativo: true });
    setDialogo(true);
  };
  const abrirEdicao = (hub) => {
    setEditando(hub);
    setForm({ codigo: hub.codigo, nome: hub.nome, descricao: hub.descricao || "", ativo: hub.ativo });
    setDialogo(true);
  };

  const salvando = criar.isPending || atualizar.isPending;

  const salvar = async () => {
    try {
      if (editando) {
        await atualizar.mutateAsync({ id: editando.id, payload: form });
        sucesso("Hub atualizado.");
      } else {
        await criar.mutateAsync(form);
        sucesso("Hub cadastrado.");
      }
      setDialogo(false);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const remover = async () => {
    try {
      await removerMut.mutateAsync(confirmar.id);
      sucesso("Hub removido.");
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setConfirmar(null);
    }
  };

  return (
    <Box sx={{ pt: 2.5 }}>
      <Alert severity="info" icon={<HubIcon />} sx={{ mb: 2.5 }}>
        Catálogo global de hubs — vale para toda a plataforma, não só para esta empresa.
        {!podeEscrever && " Somente um superusuário pode criar, editar ou remover hubs."}
      </Alert>

      {podeEscrever && (
        <Stack direction="row" justifyContent="flex-end" sx={{ mb: 2 }}>
          <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
            Novo hub
          </Button>
        </Stack>
      )}

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Card>
        <CardContent>
          {!hubs.length ? (
            <VazioEstado mensagem="Nenhum hub cadastrado." />
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Código</TableCell>
                    <TableCell>Nome</TableCell>
                    <TableCell>Descrição</TableCell>
                    <TableCell>Status</TableCell>
                    {podeEscrever && <TableCell align="right">Ações</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {hubs.map((h) => (
                    <TableRow key={h.id}>
                      <TableCell><Chip size="small" label={h.codigo} /></TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{h.nome}</TableCell>
                      <TableCell>{h.descricao || <em style={{ color: "#888" }}>—</em>}</TableCell>
                      <TableCell>
                        <Chip size="small" label={h.ativo ? "Ativo" : "Inativo"} color={h.ativo ? "success" : "default"} />
                      </TableCell>
                      {podeEscrever && (
                        <TableCell align="right">
                          <Tooltip title="Editar">
                            <IconButton size="small" onClick={() => abrirEdicao(h)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Remover">
                            <IconButton size="small" color="error" onClick={() => setConfirmar(h)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogo} onClose={() => setDialogo(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar hub" : "Novo hub"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Código"
              value={form.codigo}
              onChange={(e) => setForm({ ...form, codigo: e.target.value })}
              helperText="Ex.: SUDESTE_HUB — normalizado em maiúsculas ao salvar"
              required
            />
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
            <FormControlLabel
              control={<Switch checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} />}
              label="Ativo"
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogo(false)} color="inherit">
            Cancelar
          </Button>
          <Button variant="contained" onClick={salvar} disabled={!form.codigo.trim() || !form.nome.trim() || salvando}>
            {salvando ? "Salvando..." : "Salvar"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        aberto={Boolean(confirmar)}
        titulo="Remover hub"
        mensagem={`Deseja remover o hub "${confirmar?.nome}"? Isso pode afetar mapeamentos de clientes que apontam para ele.`}
        textoConfirmar="Remover"
        corConfirmar="error"
        onConfirmar={remover}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}

function AbaMapeamento() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const fileRef = useRef(null);

  const { data: hubs = [] } = useHubs(true);
  const { data: lista = [], isLoading: carregando, error } = useClusters(empresaAtivaId);
  const { criar, remover: removerMut, importarExcel: importarExcelMut } = useMutacoesCluster(empresaAtivaId);
  const [novo, setNovo] = useState({ uf: "", municipio: "", hub_id: "" });

  if (error) erroToast(extrairErro(error));

  const baixarModelo = async () => {
    try {
      await clustersApi.baixarModelo(empresaAtivaId);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const importarExcel = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      const r = await importarExcelMut.mutateAsync(file);
      const msg = r.ignorados > 0
        ? `${r.importados} clusters importados · ${r.ignorados} ignorados (UF/hub inválido ou duplicado).`
        : `${r.importados} clusters importados.`;
      sucesso(msg);
    } catch (ex) { erroToast(extrairErro(ex)); }
  };

  const salvando = criar.isPending;

  const adicionar = async () => {
    if (!novo.uf || !novo.hub_id) {
      erroToast("Selecione ao menos a UF e o hub.");
      return;
    }
    try {
      await criar.mutateAsync({
        uf: novo.uf,
        municipio: novo.municipio.trim(),
        hub_id: Number(novo.hub_id),
      });
      setNovo({ uf: "", municipio: "", hub_id: "" });
      sucesso("Regra de mapeamento adicionada.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const remover = async (id) => {
    try {
      await removerMut.mutateAsync(id);
      sucesso("Regra removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box sx={{ pt: 2.5 }}>
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box sx={{ pt: 2.5 }}>
      <Alert severity="info" icon={<HubIcon />} sx={{ mb: 2.5 }}>
        Defina como municípios e UFs de <strong>{empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}</strong> são
        agrupados em hubs logísticos. Esses hubs formam os corredores logísticos utilizados pelos módulos analíticos do
        sistema. Uma regra de <strong>município</strong> tem prioridade sobre a regra da UF; UFs sem regra são tratadas
        como hub próprio (a sigla da UF).
      </Alert>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={baixarModelo}>
          Baixar modelo
        </Button>
        <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileRef.current?.click()}>
          Importar Excel
        </Button>
        <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={importarExcel} />
      </Stack>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Nova regra de mapeamento</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
            <Autocomplete
              options={UFS}
              value={novo.uf || null}
              onChange={(_, v) => setNovo((p) => ({ ...p, uf: v || "" }))}
              renderInput={(params) => <TextField {...params} label="UF" />}
              sx={{ width: 120 }}
            />
            <TextField
              label="Município (opcional)"
              value={novo.municipio}
              onChange={(e) => setNovo((p) => ({ ...p, municipio: e.target.value }))}
              helperText="Vazio = vale para toda a UF"
              sx={{ minWidth: 240 }}
            />
            <TextField
              select
              label="Hub"
              value={novo.hub_id}
              onChange={(e) => setNovo((p) => ({ ...p, hub_id: e.target.value }))}
              sx={{ minWidth: 240 }}
            >
              {hubs.map((h) => (
                <MenuItem key={h.id} value={h.id}>{h.nome}</MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={adicionar} disabled={salvando}>
              Adicionar
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>Regras cadastradas</Typography>
          {!lista.length ? (
            <Alert severity="info">
              Nenhuma regra cadastrada. O benchmark ainda funciona usando cada UF como
              hub próprio, mas o agrupamento por corredor fica mais fiel após o cadastro.
            </Alert>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>UF</TableCell>
                    <TableCell>Município</TableCell>
                    <TableCell>Hub</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lista.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell><Chip size="small" label={c.uf} /></TableCell>
                      <TableCell>{c.municipio || <em style={{ color: "#888" }}>toda a UF</em>}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{c.hub_nome}</TableCell>
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
        </CardContent>
      </Card>
    </Box>
  );
}

const CORREDOR_VAZIO = {
  hub_origem_codigo: "", hub_destino_codigo: "",
  frete_kg_min: 0, frete_kg_medio: 0, frete_kg_max: 0,
  frete_pct_min: 0, frete_pct_medio: 0, frete_pct_max: 0,
  volume_referencia: 0, dispersao_kg: 0, observacoes: "",
};

function AbaCorredor() {
  const { usuario } = useAuth();
  const { sucesso, erro: erroToast } = useFeedback();
  const podeEscrever = Boolean(usuario?.is_superuser);

  const { data: hubs = [] } = useHubs(true);
  const { data: lista = [], isLoading: carregando, error } = useCorredoresRef();
  const { salvar: salvarMut, remover: removerMut } = useMutacoesCorredorRef();
  const [form, setForm] = useState(CORREDOR_VAZIO);

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
      setForm(CORREDOR_VAZIO);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const editar = (c) => podeEscrever && setForm({ ...c });

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
    <Box sx={{ pt: 2.5 }}>
      <Alert severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}>
        Referência de mercado por corredor (Hub origem → Hub destino) — <strong>global</strong>,
        usada como detalhamento "por corredor" dentro do Potencial de Economia.
        {!podeEscrever && " Somente um superusuário pode criar, editar ou remover referências."}
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {podeEscrever && (
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
                  <Button sx={{ ml: 1 }} onClick={() => setForm(CORREDOR_VAZIO)}>Cancelar edição</Button>
                )}
              </Box>
            </Stack>
          </CardContent>
        </Card>
      )}

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
                    {podeEscrever && <TableCell align="right">Ações</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lista.map((c) => (
                    <TableRow key={c.id} hover sx={{ cursor: podeEscrever ? "pointer" : "default" }}>
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
                      {podeEscrever && (
                        <TableCell align="right">
                          <IconButton size="small" color="error" onClick={() => remover(c.id)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
          {podeEscrever && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="caption" color="text.secondary">
                Clique em uma linha para carregar os valores no formulário e editar.
              </Typography>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

export default function HubsLogisticos() {
  const [aba, setAba] = useState(0);

  return (
    <Box>
      <PageHeader
        titulo="Hubs Logísticos"
        subtitulo="Configuração › catálogo de hubs, mapeamento cliente→hub e referência de mercado por corredor"
      />

      <Card>
        <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}>
          <Tab label="Hubs" />
          <Tab label="Mapeamento Cliente → Hub" />
          <Tab label="Referência de Corredor" />
        </Tabs>
        <CardContent>
          {aba === 0 && <AbaHubs />}
          {aba === 1 && <AbaMapeamento />}
          {aba === 2 && <AbaCorredor />}
        </CardContent>
      </Card>
    </Box>
  );
}
