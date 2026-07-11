/**
 * Empresas e Filiais — tela unificada com busca de CNPJ via BrasilAPI (Receita Federal)
 *
 * Funcionalidades:
 * - CRUD de empresas com busca automática de dados pelo CNPJ
 * - Cadastro de filiais em lote: cole vários CNPJs e o sistema busca e cadastra todos de uma vez
 * - Gerenciamento de filiais individuais na mesma tela
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Box, Grid, Card, CardContent, CardHeader, Button, TextField,
  Table, TableHead, TableRow, TableCell, TableBody, Typography,
  IconButton, Tooltip, Stack, Divider, CircularProgress,
  Dialog, DialogTitle, DialogContent, DialogActions, Chip, Alert,
  MenuItem, LinearProgress, List, ListItem, ListItemIcon, ListItemText,
} from "@mui/material";
import AddIcon          from "@mui/icons-material/Add";
import EditIcon         from "@mui/icons-material/Edit";
import DeleteIcon       from "@mui/icons-material/Delete";
import SearchIcon       from "@mui/icons-material/Search";
import BusinessIcon     from "@mui/icons-material/Business";
import AccountTreeIcon  from "@mui/icons-material/AccountTree";
import CheckCircleIcon  from "@mui/icons-material/CheckCircle";
import ErrorIcon        from "@mui/icons-material/Error";
import PlaylistAddIcon  from "@mui/icons-material/PlaylistAdd";
import PageHeader       from "../components/PageHeader";
import ConfirmDialog    from "../components/ConfirmDialog";
import { useFeedback }  from "../components/Feedback";
import { useEmpresas, useFiliais, useMutacoesEmpresa, useMutacoesFilial } from "../api/queries";
import { qk } from "../api/queryKeys";
import { empresasApi }  from "../api/endpoints";
import { extrairErro }  from "../api/client";
import { mascararCnpj, soDigitos } from "../utils/format";
import { SETORES } from "../utils/setores";
import { GD } from "../theme";

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];

// ── BrasilAPI ──────────────────────────────────────────────────────────────
async function buscarCnpjBrasil(cnpj) {
  const digits = soDigitos(cnpj);
  if (digits.length !== 14) throw new Error("CNPJ deve ter 14 dígitos");
  const r = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${digits}`);
  if (!r.ok) throw new Error(r.status === 404 ? "CNPJ não encontrado na Receita Federal" : `Erro ${r.status} na consulta`);
  return r.json();
}

function mapEmpresa(d) {
  return {
    razao_social:  d.razao_social  || "",
    nome_fantasia: d.nome_fantasia || "",
    cnpj_matriz:   d.cnpj         || "",
    status: d.situacao_cadastral === "ATIVA" ? "ATIVO" : "INATIVO",
  };
}

function mapFilial(d, empresaId) {
  return {
    empresa_id:   empresaId,
    razao_social: d.razao_social || "",
    cnpj:         d.cnpj         || "",
    cidade:       d.municipio    || "",
    uf:           d.uf           || "",
  };
}

// ── Formulário de empresa ──────────────────────────────────────────────────
function EmpresaForm({ inicial, onSalvar, onCancelar }) {
  const [form, setForm]         = useState(inicial || { razao_social: "", nome_fantasia: "", cnpj_matriz: "", status: "ATIVO", setor: "" });
  const [buscando, setBuscando] = useState(false);
  const [erroBusca, setErroBusca] = useState("");
  const [salvando, setSalvando] = useState(false);

  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  const buscarCnpj = async () => {
    setErroBusca("");
    setBuscando(true);
    try {
      const d = await buscarCnpjBrasil(form.cnpj_matriz);
      setForm((p) => ({ ...p, ...mapEmpresa(d) }));
    } catch (e) { setErroBusca(e.message); }
    finally { setBuscando(false); }
  };

  const handleSalvar = async () => {
    setSalvando(true);
    try { await onSalvar({ ...form, cnpj_matriz: mascararCnpj(soDigitos(form.cnpj_matriz)) }); }
    finally { setSalvando(false); }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <TextField
          label="CNPJ Matriz" value={form.cnpj_matriz} size="small" sx={{ flex: 1 }}
          placeholder="00.000.000/0001-00"
          onChange={(e) => setForm((p) => ({ ...p, cnpj_matriz: e.target.value }))}
          onKeyDown={(e) => e.key === "Enter" && buscarCnpj()}
        />
        <Button variant="outlined"
          startIcon={buscando ? <CircularProgress size={16} /> : <SearchIcon />}
          onClick={buscarCnpj}
          disabled={buscando || soDigitos(form.cnpj_matriz).length < 14}>
          {buscando ? "Buscando..." : "Buscar CNPJ"}
        </Button>
      </Stack>

      {erroBusca && <Alert severity="warning" sx={{ mb: 2 }}>{erroBusca}</Alert>}

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField fullWidth size="small" label="Razão Social" value={form.razao_social} onChange={set("razao_social")} />
        </Grid>
        <Grid item xs={12}>
          <TextField fullWidth size="small" label="Nome Fantasia" value={form.nome_fantasia} onChange={set("nome_fantasia")} />
        </Grid>
        <Grid item xs={6}>
          <TextField select fullWidth size="small" label="Status" value={form.status} onChange={set("status")}>
            <MenuItem value="ATIVO">Ativo</MenuItem>
            <MenuItem value="INATIVO">Inativo</MenuItem>
          </TextField>
        </Grid>
        <Grid item xs={6}>
          <TextField
            select required fullWidth size="small" label="Setor"
            value={form.setor || ""} onChange={set("setor")}
            error={!form.setor}
            helperText={!form.setor ? "Selecione o setor (obrigatório)" : " "}
          >
            {SETORES.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
        </Grid>
      </Grid>

      <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ mt: 2 }}>
        <Button onClick={onCancelar} disabled={salvando}>Cancelar</Button>
        <Button variant="contained" onClick={handleSalvar}
          disabled={salvando || !form.razao_social || !form.cnpj_matriz || !form.setor} sx={{ bgcolor: GD.indigo }}>
          {salvando ? "Salvando..." : "Salvar"}
        </Button>
      </Stack>
    </Box>
  );
}

// ── Formulário de filial individual ───────────────────────────────────────
function FilialForm({ inicial, empresaId, onSalvar, onCancelar }) {
  const [form, setForm]         = useState(inicial ? { ...inicial } : { empresa_id: empresaId, razao_social: "", cnpj: "", cidade: "", uf: "" });
  const [buscando, setBuscando] = useState(false);
  const [erroBusca, setErroBusca] = useState("");

  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  const buscarCnpj = async () => {
    setErroBusca("");
    setBuscando(true);
    try {
      const d = await buscarCnpjBrasil(form.cnpj);
      setForm((p) => ({ ...p, ...mapFilial(d, empresaId) }));
    } catch (e) { setErroBusca(e.message); }
    finally { setBuscando(false); }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <TextField
          label="CNPJ Filial" value={form.cnpj} size="small" sx={{ flex: 1 }}
          placeholder="00.000.000/0002-00"
          onChange={(e) => setForm((p) => ({ ...p, cnpj: e.target.value }))}
          onKeyDown={(e) => e.key === "Enter" && buscarCnpj()}
        />
        <Button variant="outlined"
          startIcon={buscando ? <CircularProgress size={16} /> : <SearchIcon />}
          onClick={buscarCnpj}
          disabled={buscando || soDigitos(form.cnpj).length < 14}>
          {buscando ? "Buscando..." : "Buscar"}
        </Button>
      </Stack>

      {erroBusca && <Alert severity="warning" sx={{ mb: 1 }}>{erroBusca}</Alert>}

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField fullWidth size="small" label="Razão Social" value={form.razao_social} onChange={set("razao_social")} />
        </Grid>
        <Grid item xs={8}>
          <TextField fullWidth size="small" label="Cidade" value={form.cidade} onChange={set("cidade")} />
        </Grid>
        <Grid item xs={4}>
          <TextField select fullWidth size="small" label="UF" value={form.uf} onChange={set("uf")}>
            {UFS.map((u) => <MenuItem key={u} value={u}>{u}</MenuItem>)}
          </TextField>
        </Grid>
      </Grid>

      <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ mt: 2 }}>
        <Button onClick={onCancelar}>Cancelar</Button>
        <Button variant="contained" onClick={() => onSalvar({ ...form, cnpj: mascararCnpj(soDigitos(form.cnpj)) })}
          disabled={!form.razao_social || !form.cnpj} sx={{ bgcolor: GD.indigo }}>
          Salvar
        </Button>
      </Stack>
    </Box>
  );
}

// ── Cadastro em lote de filiais ────────────────────────────────────────────
function FilialLoteDialog({ open, empresa, onFechar, onConcluir }) {
  const qc = useQueryClient();
  const [cnpjs, setCnpjs]       = useState("");
  const [progresso, setProgresso] = useState([]);
  const [rodando, setRodando]   = useState(false);

  const iniciar = async () => {
    const lista = cnpjs
      .split(/[\n,;]+/)
      .map((c) => soDigitos(c.trim()))
      .filter((c) => c.length === 14);

    if (!lista.length) return;

    setProgresso(lista.map((c) => ({ cnpj: c, status: "aguardando", msg: "" })));
    setRodando(true);

    let cadastradas = 0;
    for (let i = 0; i < lista.length; i++) {
      const cnpj = lista[i];
      setProgresso((p) => p.map((x, idx) => idx === i ? { ...x, status: "buscando" } : x));

      try {
        const d = await buscarCnpjBrasil(cnpj);
        const payload = mapFilial(d, empresa.id);
        await empresasApi.criarFilial(empresa.id, {
          ...payload,
          cnpj: mascararCnpj(cnpj),
        });
        setProgresso((p) => p.map((x, idx) =>
          idx === i ? { ...x, status: "ok", msg: d.razao_social || cnpj } : x));
        cadastradas++;
      } catch (e) {
        setProgresso((p) => p.map((x, idx) =>
          idx === i ? { ...x, status: "erro", msg: e.message } : x));
      }

      // Pequena pausa para não sobrecarregar a API
      await new Promise((r) => setTimeout(r, 400));
    }

    setRodando(false);
    if (cadastradas > 0) {
      qc.invalidateQueries({ queryKey: qk.filiais(empresa.id) });
      onConcluir(cadastradas);
    }
  };

  const fechar = () => {
    setCnpjs("");
    setProgresso([]);
    setRodando(false);
    onFechar();
  };

  return (
    <Dialog open={open} onClose={fechar} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <PlaylistAddIcon sx={{ color: GD.indigo }} />
          <span>Cadastrar Filiais em Lote</span>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Cole os CNPJs das filiais de <strong>{empresa?.nome_fantasia || empresa?.razao_social}</strong> abaixo
          — um por linha, ou separados por vírgula. O sistema buscará os dados de cada um na Receita Federal
          e os cadastrará automaticamente.
        </Typography>

        {!rodando && progresso.length === 0 && (
          <TextField
            fullWidth multiline rows={6} label="CNPJs das filiais"
            placeholder={"00.000.000/0002-00\n00.000.000/0003-00\n00.000.000/0004-00"}
            value={cnpjs} onChange={(e) => setCnpjs(e.target.value)}
            helperText="Um CNPJ por linha, ou separados por vírgula ou ponto-e-vírgula"
          />
        )}

        {progresso.length > 0 && (
          <Box>
            {rodando && <LinearProgress sx={{ mb: 1 }} />}
            <List dense>
              {progresso.map((item, i) => (
                <ListItem key={i} sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    {item.status === "aguardando" && <CircularProgress size={16} sx={{ opacity: 0.3 }} />}
                    {item.status === "buscando"   && <CircularProgress size={16} />}
                    {item.status === "ok"         && <CheckCircleIcon sx={{ color: "success.main", fontSize: 20 }} />}
                    {item.status === "erro"       && <ErrorIcon sx={{ color: "error.main", fontSize: 20 }} />}
                  </ListItemIcon>
                  <ListItemText
                    primary={mascararCnpj(item.cnpj)}
                    secondary={item.msg || (item.status === "buscando" ? "Consultando Receita Federal..." : item.status === "aguardando" ? "Aguardando..." : "")}
                    primaryTypographyProps={{ fontSize: 13, fontFamily: "monospace" }}
                    secondaryTypographyProps={{ fontSize: 12, color: item.status === "erro" ? "error.main" : "text.secondary" }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={fechar} disabled={rodando}>
          {progresso.length > 0 && !rodando ? "Fechar" : "Cancelar"}
        </Button>
        {progresso.length === 0 && (
          <Button variant="contained" onClick={iniciar}
            disabled={!cnpjs.trim()} sx={{ bgcolor: GD.indigo }}>
            Buscar e Cadastrar
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

// ── Página principal ───────────────────────────────────────────────────────
export default function Empresas() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: empresas = [], isLoading: carregando, error } = useEmpresas();
  const [selecionada, setSelecionada] = useState(null);
  const { data: filiais = [] } = useFiliais(selecionada?.id);
  const { criar: criarEmpresa, atualizar: atualizarEmpresa, inativar } = useMutacoesEmpresa();
  const { criar: criarFilial, atualizar: atualizarFilial, remover: removerFilial } = useMutacoesFilial(selecionada?.id);
  const [dialogEmp, setDialogEmp]     = useState(null);
  const [dialogFil, setDialogFil]     = useState(null);
  const [dialogLote, setDialogLote]   = useState(false);
  const [confirmar, setConfirmar]     = useState(null);

  if (error) erroToast(extrairErro(error));

  const salvarEmpresa = async (payload) => {
    try {
      if (dialogEmp?.id) {
        await atualizarEmpresa.mutateAsync({ id: dialogEmp.id, payload });
        sucesso("Empresa atualizada.");
        if (selecionada?.id === dialogEmp.id) setSelecionada({ ...selecionada, ...payload });
      } else {
        const nova = await criarEmpresa.mutateAsync(payload);
        sucesso("Empresa criada.");
        setSelecionada(nova);
      }
      setDialogEmp(null);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const excluirEmpresa = async (id) => {
    try {
      await inativar.mutateAsync(id);
      sucesso("Empresa removida.");
      if (selecionada?.id === id) setSelecionada(null);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const salvarFilial = async (payload) => {
    try {
      if (dialogFil?.id) {
        await atualizarFilial.mutateAsync({ id: dialogFil.id, payload });
        sucesso("Filial atualizada.");
      } else {
        await criarFilial.mutateAsync(payload);
        sucesso("Filial criada.");
      }
      setDialogFil(null);
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const excluirFilial = async (id) => {
    try {
      await removerFilial.mutateAsync(id);
      sucesso("Filial removida.");
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const aoConcluirLote = (qtd) => {
    sucesso(`${qtd} filial(is) cadastrada(s) com sucesso.`);
  };

  return (
    <Box>
      <PageHeader
        titulo="Empresas e Filiais"
        subtitulo="Cadastre empresas e filiais — busca automática via CNPJ (Receita Federal)"
        acoes={
          <Button variant="contained" startIcon={<AddIcon />}
            onClick={() => setDialogEmp("novo")} sx={{ bgcolor: GD.indigo }}>
            Nova Empresa
          </Button>
        }
      />

      <Grid container spacing={2}>
        {/* ── Lista de Empresas ── */}
        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardHeader
              title={
                <Stack direction="row" alignItems="center" spacing={1}>
                  <BusinessIcon sx={{ color: GD.indigo }} />
                  <Typography fontWeight={700} variant="subtitle1">Empresas</Typography>
                  <Chip label={empresas.length} size="small" />
                </Stack>
              }
              sx={{ pb: 0 }}
            />
            <CardContent sx={{ p: 0 }}>
              {carregando && <Box sx={{ p: 2 }}><CircularProgress size={20} /></Box>}
              {!carregando && empresas.length === 0 && (
                <Box sx={{ p: 3, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">Nenhuma empresa cadastrada</Typography>
                </Box>
              )}
              {empresas.map((emp) => (
                <Box key={emp.id}>
                  <Box
                    onClick={() => setSelecionada(selecionada?.id === emp.id ? null : emp)}
                    sx={{
                      px: 2, py: 1.5, cursor: "pointer", display: "flex",
                      justifyContent: "space-between", alignItems: "center",
                      bgcolor: selecionada?.id === emp.id ? `${GD.indigo}12` : "transparent",
                      borderLeft: selecionada?.id === emp.id ? `3px solid ${GD.indigo}` : "3px solid transparent",
                      "&:hover": { bgcolor: `${GD.indigo}08` },
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" fontWeight={600} noWrap>
                        {emp.nome_fantasia || emp.razao_social}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {mascararCnpj(emp.cnpj_matriz)}
                      </Typography>
                    </Box>
                    <Stack direction="row" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="Editar">
                        <IconButton size="small" onClick={() => setDialogEmp(emp)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Excluir">
                        <IconButton size="small" color="error"
                          onClick={() => setConfirmar({ tipo: "empresa", id: emp.id, nome: emp.razao_social })}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </Box>
                  <Divider />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* ── Filiais ── */}
        <Grid item xs={12} md={8}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardHeader
              title={
                <Stack direction="row" alignItems="center" spacing={1}>
                  <AccountTreeIcon sx={{ color: GD.blue }} />
                  <Typography fontWeight={700} variant="subtitle1">
                    {selecionada
                      ? `Filiais — ${selecionada.nome_fantasia || selecionada.razao_social}`
                      : "Filiais"}
                  </Typography>
                  {selecionada && <Chip label={filiais.length} size="small" />}
                </Stack>
              }
              action={
                selecionada && (
                  <Stack direction="row" spacing={1} sx={{ mr: 1 }}>
                    <Tooltip title="Cadastrar várias filiais de uma vez via CNPJ">
                      <Button size="small" variant="outlined" startIcon={<PlaylistAddIcon />}
                        onClick={() => setDialogLote(true)}>
                        Cadastrar em Lote
                      </Button>
                    </Tooltip>
                    <Button size="small" variant="outlined" startIcon={<AddIcon />}
                      onClick={() => setDialogFil("novo")}>
                      Adicionar
                    </Button>
                  </Stack>
                )
              }
              sx={{ pb: 0 }}
            />
            <CardContent>
              {!selecionada && (
                <Box sx={{ textAlign: "center", py: 6 }}>
                  <BusinessIcon sx={{ fontSize: 48, color: "action.disabled", mb: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    Selecione uma empresa para gerenciar suas filiais
                  </Typography>
                </Box>
              )}

              {selecionada && filiais.length === 0 && (
                <Box sx={{ textAlign: "center", py: 4 }}>
                  <AccountTreeIcon sx={{ fontSize: 40, color: "action.disabled", mb: 1 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Nenhuma filial cadastrada
                  </Typography>
                  <Stack direction="row" spacing={1} justifyContent="center">
                    <Button size="small" variant="outlined" startIcon={<PlaylistAddIcon />}
                      onClick={() => setDialogLote(true)}>
                      Cadastrar em Lote (CNPJ)
                    </Button>
                    <Button size="small" variant="contained" startIcon={<AddIcon />}
                      onClick={() => setDialogFil("novo")} sx={{ bgcolor: GD.indigo }}>
                      Adicionar uma filial
                    </Button>
                  </Stack>
                </Box>
              )}

              {selecionada && filiais.length > 0 && (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Razão Social</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>CNPJ</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Cidade / UF</TableCell>
                      <TableCell />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filiais.map((f) => (
                      <TableRow key={f.id} hover>
                        <TableCell>{f.razao_social}</TableCell>
                        <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{mascararCnpj(f.cnpj)}</TableCell>
                        <TableCell>{f.cidade}{f.uf ? ` — ${f.uf}` : ""}</TableCell>
                        <TableCell align="right">
                          <Tooltip title="Editar">
                            <IconButton size="small" onClick={() => setDialogFil(f)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Excluir">
                            <IconButton size="small" color="error"
                              onClick={() => setConfirmar({ tipo: "filial", id: f.id, nome: f.razao_social })}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Dialogs */}
      <Dialog open={Boolean(dialogEmp)} onClose={() => setDialogEmp(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{dialogEmp?.id ? "Editar Empresa" : "Nova Empresa"}</DialogTitle>
        <DialogContent sx={{ pt: "16px !important" }}>
          <EmpresaForm
            inicial={dialogEmp?.id ? dialogEmp : null}
            onSalvar={salvarEmpresa}
            onCancelar={() => setDialogEmp(null)}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(dialogFil)} onClose={() => setDialogFil(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{dialogFil?.id ? "Editar Filial" : "Nova Filial"}</DialogTitle>
        <DialogContent sx={{ pt: "16px !important" }}>
          {selecionada && (
            <FilialForm
              inicial={dialogFil?.id ? dialogFil : null}
              empresaId={selecionada.id}
              onSalvar={salvarFilial}
              onCancelar={() => setDialogFil(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <FilialLoteDialog
        open={dialogLote}
        empresa={selecionada}
        onFechar={() => setDialogLote(false)}
        onConcluir={aoConcluirLote}
      />

      <ConfirmDialog
        open={Boolean(confirmar)}
        titulo="Confirmar exclusão"
        mensagem={`Deseja remover "${confirmar?.nome}"?`}
        onConfirmar={() => {
          if (confirmar.tipo === "empresa") excluirEmpresa(confirmar.id);
          else excluirFilial(confirmar.id);
          setConfirmar(null);
        }}
        onCancelar={() => setConfirmar(null)}
      />
    </Box>
  );
}
