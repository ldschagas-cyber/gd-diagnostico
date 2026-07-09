import { useEffect, useState, useCallback, useRef } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, MenuItem, IconButton,
  Alert, LinearProgress, Chip, Autocomplete,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import HubIcon from "@mui/icons-material/Hub";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { clustersApi, hubsApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { UFS } from "../utils/format";

export default function Clusters() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const fileRef = useRef(null);

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
      const r = await clustersApi.importarExcel(empresaAtivaId, file);
      const msg = r.ignorados > 0
        ? `${r.importados} clusters importados · ${r.ignorados} ignorados (UF/hub inválido ou duplicado).`
        : `${r.importados} clusters importados.`;
      sucesso(msg);
      carregar();
    } catch (ex) { erroToast(extrairErro(ex)); }
  };
  const [hubs, setHubs] = useState([]);
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [novo, setNovo] = useState({ uf: "", municipio: "", hub_id: "" });

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const [h, c] = await Promise.all([hubsApi.listar(true), clustersApi.listar(empresaAtivaId)]);
      setHubs(h);
      setLista(c);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, erroToast]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const adicionar = async () => {
    if (!novo.uf || !novo.hub_id) {
      erroToast("Selecione ao menos a UF e o hub.");
      return;
    }
    setSalvando(true);
    try {
      await clustersApi.criar(empresaAtivaId, {
        uf: novo.uf,
        municipio: novo.municipio.trim(),
        hub_id: Number(novo.hub_id),
      });
      setNovo({ uf: "", municipio: "", hub_id: "" });
      sucesso("Regra de cluster adicionada.");
      carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const remover = async (id) => {
    try {
      await clustersApi.remover(empresaAtivaId, id);
      sucesso("Regra removida.");
      carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Clusters Logísticos" subtitulo="Mapa UF/município → hub, por cliente" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Clusters Logísticos"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — agrupamento de origens e destinos em hubs`}
      />

      <Alert severity="info" icon={<HubIcon />} sx={{ mb: 2.5 }}>
        Defina como as UFs e municípios deste cliente se agrupam em hubs logísticos.
        Esses hubs formam os corredores (Origem → Destino) usados no benchmark.
        Uma regra de <strong>município</strong> tem prioridade sobre a regra da UF.
        UFs sem regra são tratadas como hub próprio (a sigla da UF).
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
          <Typography variant="h6" sx={{ mb: 2 }}>Nova regra de cluster</Typography>
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
