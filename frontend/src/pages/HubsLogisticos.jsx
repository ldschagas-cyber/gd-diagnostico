import { useState, useRef, useCallback, useEffect } from "react";
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
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
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
import { clustersApi, corredoresApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { UFS } from "../utils/format";

// Separador de grupo dentro da grade compacta de campos numéricos (aba
// Parâmetros de Hubs) — ocupa a linha inteira (gridColumn 1/-1), o que força
// o próximo grupo a começar numa linha nova mesmo sem célula vazia extra.
function SeparadorGrupo({ texto }) {
  return (
    <Box sx={{ gridColumn: "1 / -1", display: "flex", alignItems: "center", gap: 1.25, mt: 0.5 }}>
      <Typography variant="overline" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
        {texto}
      </Typography>
      <Divider sx={{ flex: 1 }} />
    </Box>
  );
}

function AbaHubs() {
  const { usuario } = useAuth();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const podeEscrever = usuario?.role !== "VISUALIZADOR";

  const { data: hubs = [], isLoading: carregando, error } = useHubs(empresaAtivaId, false);
  const { criar, atualizar, remover: removerMut } = useMutacoesHub(empresaAtivaId);
  const [dialogo, setDialogo] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ codigo: "", nome: "", descricao: "", ativo: true });
  const [confirmar, setConfirmar] = useState(null);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  if (!empresaAtivaId) {
    return (
      <Box sx={{ pt: 2.5 }}>
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

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
        Catálogo de hubs de <strong>{empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}</strong> —
        próprio desta empresa, não é compartilhado com outras.
        {!podeEscrever && " Seu perfil é somente leitura e não permite criar, editar ou remover hubs."}
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

  const { data: hubs = [] } = useHubs(empresaAtivaId, true);
  const { data: lista = [], isLoading: carregando, error } = useClusters(empresaAtivaId);
  const { criar, remover: removerMut, importarExcel: importarExcelMut } = useMutacoesCluster(empresaAtivaId);
  const [novo, setNovo] = useState({ uf: "", municipio: "", hub_id: "" });

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

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
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "140px 1.4fr 1.4fr auto" },
              gap: 2,
              alignItems: "start",
            }}
          >
            <Autocomplete
              options={UFS}
              value={novo.uf || null}
              onChange={(_, v) => setNovo((p) => ({ ...p, uf: v || "" }))}
              renderInput={(params) => <TextField {...params} label="UF" helperText=" " />}
              sx={{ width: "100%" }}
            />
            <TextField
              label="Município (opcional)"
              value={novo.municipio}
              onChange={(e) => setNovo((p) => ({ ...p, municipio: e.target.value }))}
              helperText="Vazio = vale para toda a UF"
            />
            <TextField
              select
              label="Hub"
              value={novo.hub_id}
              onChange={(e) => setNovo((p) => ({ ...p, hub_id: e.target.value }))}
              helperText=" "
            >
              {hubs.map((h) => (
                <MenuItem key={h.id} value={h.id}>{h.nome}</MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              onClick={adicionar}
              disabled={salvando}
              sx={{ height: 40, width: { xs: "100%", md: "auto" } }}
            >
              Adicionar
            </Button>
          </Box>
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
  volume_referencia: 0, dispersao_kg: 0, prazo_dias_medio: 0, observacoes: "",
};

function AbaCorredor() {
  const { usuario } = useAuth();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const podeEscrever = usuario?.role !== "VISUALIZADOR";
  const fileRef = useRef(null);

  const { data: hubs = [] } = useHubs(empresaAtivaId, true);
  const { data: lista = [], isLoading: carregando, error } = useCorredoresRef(empresaAtivaId);
  const { salvar: salvarMut, remover: removerMut, importarExcel: importarExcelMut } = useMutacoesCorredorRef(empresaAtivaId);
  const [form, setForm] = useState(CORREDOR_VAZIO);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  const baixarModelo = async () => {
    try {
      await corredoresApi.baixarModelo(empresaAtivaId);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const importarExcel = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      const r = await importarExcelMut.mutateAsync(file);
      const partes = [`${r.importados} novo(s)`, `${r.atualizados} atualizado(s)`];
      if (r.ignorados > 0) partes.push(`${r.ignorados} ignorado(s) (hub inválido)`);
      sucesso(`Importação concluída: ${partes.join(" · ")}.`);
    } catch (ex) { erroToast(extrairErro(ex)); }
  };

  if (!empresaAtivaId) {
    return (
      <Box sx={{ pt: 2.5 }}>
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

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
        prazo_dias_medio: Number(form.prazo_dias_medio) || 0,
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

  const num = (campo, label, adorno, fim = false) => (
    <TextField
      label={label} type="number" size="small" value={form[campo] ?? 0}
      onChange={(e) => set(campo, e.target.value)}
      InputProps={fim
        ? { endAdornment: <InputAdornment position="end">{adorno}</InputAdornment> }
        : { startAdornment: <InputAdornment position="start">{adorno}</InputAdornment> }}
    />
  );

  return (
    <Box sx={{ pt: 2.5 }}>
      <Alert severity="info" icon={<RouteIcon />} sx={{ mb: 2.5 }}>
        Referência de mercado por corredor (Hub origem → Hub destino) desta empresa,
        usada como detalhamento "por corredor" dentro do Potencial de Economia.
        {!podeEscrever && " Seu perfil é somente leitura e não permite criar, editar ou remover referências."}
      </Alert>

      {podeEscrever && (
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={baixarModelo}>
            Baixar modelo
          </Button>
          <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileRef.current?.click()}>
            Importar Excel
          </Button>
          <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={importarExcel} />
        </Stack>
      )}

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {podeEscrever && (
        <Card sx={{ mb: 2.5 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Nova referência / edição</Typography>
            <Stack spacing={2}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Hub de origem" value={form.hub_origem_codigo}
                  onChange={(e) => set("hub_origem_codigo", e.target.value)}
                  sx={{ width: { xs: "100%", md: "auto" }, minWidth: { md: 280 }, maxWidth: { md: 400 } }}>
                  {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
                </TextField>
                <TextField select label="Hub de destino" value={form.hub_destino_codigo}
                  onChange={(e) => set("hub_destino_codigo", e.target.value)}
                  sx={{ width: { xs: "100%", md: "auto" }, minWidth: { md: 280 }, maxWidth: { md: 400 } }}>
                  {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
                </TextField>
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "repeat(3, 1fr)", md: "repeat(6, 1fr)" },
                  gap: 2,
                }}
              >
                <SeparadorGrupo texto="R$/KG" />
                {num("frete_kg_min", "Mín.", "R$")}
                {num("frete_kg_medio", "Médio", "R$")}
                {num("frete_kg_max", "Máx.", "R$")}

                <SeparadorGrupo texto="% MERCADORIA" />
                {num("frete_pct_min", "Mín.", "%", true)}
                {num("frete_pct_medio", "Médio", "%", true)}
                {num("frete_pct_max", "Máx.", "%", true)}

                <SeparadorGrupo texto="METADADOS" />
                <Box sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}>
                  <TextField
                    type="number" label="Volume de referência" size="small"
                    value={form.volume_referencia} onChange={(e) => set("volume_referencia", e.target.value)}
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <Tooltip title="peso de mercado do fluxo">
                            <InfoOutlinedIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                          </Tooltip>
                        </InputAdornment>
                      ),
                    }}
                  />
                </Box>
                <Box sx={{ gridColumn: { xs: "1 / -1", md: "auto" } }}>
                  <TextField
                    type="number" label="Dispersão (0–1)" size="small"
                    value={form.dispersao_kg} onChange={(e) => set("dispersao_kg", e.target.value)}
                    inputProps={{ step: 0.05, min: 0, max: 1 }}
                  />
                </Box>
                <Box sx={{ gridColumn: { xs: "1 / -1", md: "auto" } }}>
                  <TextField
                    type="number" label="Prazo (dias)" size="small"
                    value={form.prazo_dias_medio} onChange={(e) => set("prazo_dias_medio", e.target.value)}
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <Tooltip title="prazo de entrega de referência do corredor — usado pelo Simulador de Hub">
                            <InfoOutlinedIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                          </Tooltip>
                        </InputAdornment>
                      ),
                    }}
                    inputProps={{ min: 0 }}
                  />
                </Box>
                <Box sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}>
                  <TextField
                    label="Observações" size="small" value={form.observacoes}
                    onChange={(e) => set("observacoes", e.target.value)}
                  />
                </Box>
              </Box>
              <Box>
                <Button variant="contained" onClick={salvar} disabled={salvando}>
                  {form.id ? "Atualizar" : "Salvar"}
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
                    <TableCell align="right">Prazo</TableCell>
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
                      <TableCell align="right" onClick={() => editar(c)}>
                        {c.prazo_dias_medio > 0 ? `${c.prazo_dias_medio}d` : <em style={{ color: "#888" }}>—</em>}
                      </TableCell>
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
        subtitulo="Parâmetros › catálogo de hubs, mapeamento cliente→hub e referência de mercado por corredor"
      />

      <Card>
        <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}>
          <Tab label="Hubs" />
          <Tab label="Mapeamentos de Hubs" />
          <Tab label="Parâmetros de Hubs" />
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
