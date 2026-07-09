import { useState, useRef, useEffect, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, Stack, Chip,
  LinearProgress, Alert, List, ListItem, ListItemText, IconButton,
  Table, TableHead, TableRow, TableCell, TableBody, Divider, Collapse,
} from "@mui/material";
import EventBusyIcon from "@mui/icons-material/EventBusy";
import DescriptionIcon from "@mui/icons-material/Description";
import CloseIcon from "@mui/icons-material/Close";
import HistoryIcon from "@mui/icons-material/History";
import { useFeedback } from "./Feedback";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

const COR_RESULTADO = {
  CANCELADO: GD.ok,
  DUPLICADO: GD.warn,
  CTE_NAO_ENCONTRADO: GD.slate,
  ERRO: GD.danger,
};
const ROTULO_RESULTADO = {
  CANCELADO: "Cancelado",
  DUPLICADO: "Duplicado",
  CTE_NAO_ENCONTRADO: "CT-e não encontrado",
  ERRO: "Erro",
};

/**
 * Importação de eventos de cancelamento de CT-e (MELHORIA 1).
 *
 * Recebe os XMLs oficiais de evento de cancelamento (tpEvento 110111), efetiva
 * o cancelamento dos CT-es correspondentes e exibe o resultado e o histórico
 * (log) de todas as ocorrências.
 */
export default function ImportacaoCancelamento({ onConcluido }) {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtivaId } = useEmpresa();
  const inputRef = useRef(null);

  const [arquivos, setArquivos] = useState([]);
  const [arrastar, setArrastar] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [log, setLog] = useState([]);
  const [mostrarLog, setMostrarLog] = useState(false);

  const carregarLog = useCallback(async () => {
    if (!empresaAtivaId) return;
    try {
      const dados = await importacaoApi.cancelamentos(empresaAtivaId);
      setLog(Array.isArray(dados) ? dados : []);
    } catch (e) {
      // silencioso — o log é complementar
    }
  }, [empresaAtivaId]);

  useEffect(() => { carregarLog(); }, [carregarLog]);

  const adicionar = (lista) => {
    const xmls = Array.from(lista).filter((f) => f.name.toLowerCase().endsWith(".xml"));
    setArquivos((prev) => {
      const nomes = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...xmls.filter((f) => !nomes.has(f.name + f.size))];
    });
  };

  const remover = (idx) => setArquivos((prev) => prev.filter((_, i) => i !== idx));

  const enviar = async () => {
    if (!arquivos.length || !empresaAtivaId) return;
    setEnviando(true);
    setResultado(null);
    try {
      const res = await importacaoApi.importarCancelamento(empresaAtivaId, arquivos);
      setResultado(res);
      sucesso(`${res.cancelados} CT-e(s) cancelado(s).`);
      setArquivos([]);
      await carregarLog();
      onConcluido?.();
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao importar os eventos de cancelamento."));
    } finally {
      setEnviando(false);
    }
  };

  if (!empresaAtivaId) return null;

  return (
    <Card sx={{ mt: 2.5, border: `1px solid ${GD.danger}22` }}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <EventBusyIcon sx={{ color: GD.danger }} />
          <Typography variant="subtitle1" fontWeight={700}>
            Cancelamento de CT-e (XML de evento)
          </Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Importe os XMLs oficiais de evento de cancelamento (tpEvento 110111). O
          CT-e correspondente é localizado pela chave de acesso e marcado como
          cancelado — deixando de compor os indicadores financeiros. Duplicidades
          e CT-es inexistentes são apenas registrados no histórico.
        </Typography>

        <Box
          onDragOver={(e) => { e.preventDefault(); setArrastar(true); }}
          onDragLeave={() => setArrastar(false)}
          onDrop={(e) => { e.preventDefault(); setArrastar(false); adicionar(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          sx={{
            border: "2px dashed",
            borderColor: arrastar ? GD.danger : "rgba(180,69,59,0.35)",
            bgcolor: arrastar ? "rgba(180,69,59,0.05)" : "transparent",
            borderRadius: 3, p: 4, textAlign: "center", cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          <input
            ref={inputRef} type="file" accept=".xml" multiple hidden
            onChange={(e) => adicionar(e.target.files)}
          />
          <EventBusyIcon sx={{ fontSize: 40, color: GD.danger, mb: 1 }} />
          <Typography variant="body1" fontWeight={600}>
            Arraste os XMLs de cancelamento aqui
          </Typography>
          <Typography variant="body2" color="text.secondary">
            ou clique para selecionar
          </Typography>
        </Box>

        {arquivos.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Chip label={`${arquivos.length} arquivo(s)`} color="error" variant="outlined" />
              <Button size="small" color="inherit" onClick={() => setArquivos([])}>Limpar</Button>
            </Stack>
            <List dense sx={{ maxHeight: 180, overflowY: "auto",
              border: "1px solid rgba(45,53,97,0.12)", borderRadius: 2 }}>
              {arquivos.map((f, i) => (
                <ListItem key={f.name + i} secondaryAction={
                  <IconButton edge="end" size="small" onClick={() => remover(i)}>
                    <CloseIcon fontSize="small" />
                  </IconButton>
                }>
                  <DescriptionIcon sx={{ mr: 1.5, color: GD.danger }} />
                  <ListItemText primary={f.name} secondary={`${(f.size / 1024).toFixed(1)} KB`} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {enviando && <LinearProgress sx={{ mt: 2 }} />}

        <Button
          variant="contained" color="error" startIcon={<EventBusyIcon />}
          onClick={enviar} disabled={!arquivos.length || enviando} sx={{ mt: 2 }}
        >
          {enviando ? "Processando..." : "Importar cancelamentos"}
        </Button>

        {resultado && (
          <Alert
            severity={resultado.cancelados > 0 ? "success" : "info"}
            sx={{ mt: 2 }}
          >
            <b>{resultado.cancelados}</b> cancelado(s) · <b>{resultado.duplicados}</b> duplicado(s) ·{" "}
            <b>{resultado.nao_encontrados}</b> não encontrado(s) · <b>{resultado.erros}</b> erro(s)
            {resultado.ocorrencias?.length > 0 && (
              <Box sx={{ mt: 1 }}>
                {resultado.ocorrencias.slice(0, 20).map((o, i) => (
                  <Typography key={i} variant="caption" display="block">
                    {o.arquivo}: {ROTULO_RESULTADO[o.resultado] || o.resultado} — {o.mensagem}
                  </Typography>
                ))}
              </Box>
            )}
          </Alert>
        )}

        {log.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Button
              size="small" startIcon={<HistoryIcon />}
              onClick={() => setMostrarLog((v) => !v)}
            >
              {mostrarLog ? "Ocultar histórico" : `Histórico de cancelamentos (${log.length})`}
            </Button>
            <Collapse in={mostrarLog}>
              <Box sx={{ mt: 1.5, overflowX: "auto", maxHeight: 320 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Chave</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Protocolo</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Data</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Resultado</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {log.map((l) => (
                      <TableRow key={l.id} hover>
                        <TableCell>
                          <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                            …{(l.chave || "").slice(-12)}
                          </Typography>
                        </TableCell>
                        <TableCell>{l.protocolo || "—"}</TableCell>
                        <TableCell>{l.data_cancelamento || "—"}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={ROTULO_RESULTADO[l.resultado] || l.resultado}
                            sx={{
                              bgcolor: `${COR_RESULTADO[l.resultado] || GD.slate}1F`,
                              color: COR_RESULTADO[l.resultado] || GD.slate,
                              fontWeight: 700,
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </Collapse>
          </>
        )}
      </CardContent>
    </Card>
  );
}
