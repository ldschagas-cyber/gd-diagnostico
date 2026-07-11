import { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid, TextField, MenuItem, Divider, List, ListItem,
  ListItemText, InputAdornment,
} from "@mui/material";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import SearchIcon from "@mui/icons-material/Search";
import AddIcon from "@mui/icons-material/Add";
import GavelIcon from "@mui/icons-material/Gavel";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { useIaStatus, useRagStatus, useRagDocumentos, useMutacoesRag } from "../api/queries";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

const TIPOS = [
  { valor: "benchmark", rotulo: "Benchmark" },
  { valor: "relatorio", rotulo: "Relatório" },
  { valor: "diagnostico", rotulo: "Diagnóstico" },
  { valor: "bid", rotulo: "BID encerrado" },
  { valor: "legislacao", rotulo: "Legislação" },
];

const COR_TIPO = {
  benchmark: GD.blue, relatorio: GD.indigo, diagnostico: "#7030A0",
  bid: GD.amber, legislacao: "#2E7D32",
};

export default function BaseConhecimento() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();

  // Busca — não é armazenada em cache "por chave", pois o resultado depende
  // do texto digitado a cada vez: é tratada como mutação.
  const [consulta, setConsulta] = useState("");

  // Novo documento
  const [novoTipo, setNovoTipo] = useState("benchmark");
  const [novoTitulo, setNovoTitulo] = useState("");
  const [novoConteudo, setNovoConteudo] = useState("");

  const statusQ = useIaStatus();
  const statsQ = useRagStatus(empresaAtivaId);
  const documentosQ = useRagDocumentos(empresaAtivaId);
  const mut = useMutacoesRag(empresaAtivaId);

  const status = statusQ.data ?? null;
  const stats = statsQ.data ?? null;
  const documentos = documentosQ.data ?? [];
  const resultados = mut.buscar.data ?? null;
  const carregando = statusQ.isFetching || statsQ.isFetching || documentosQ.isFetching;
  const buscando = mut.buscar.isPending;
  const salvando = mut.indexar.isPending;

  useEffect(() => {
    const e = statsQ.error || documentosQ.error;
    if (e) fb.erro(extrairErro(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statsQ.error, documentosQ.error]);

  const buscar = async () => {
    if (!consulta.trim()) return;
    try {
      await mut.buscar.mutateAsync({ consulta, topK: 5 });
    } catch (e) {
      fb.erro(extrairErro(e));
    }
  };

  const indexar = async () => {
    if (!novoTitulo.trim() || !novoConteudo.trim()) {
      fb.erro("Informe título e conteúdo.");
      return;
    }
    try {
      await mut.indexar.mutateAsync({
        tipo_documento: novoTipo, titulo: novoTitulo, conteudo: novoConteudo,
      });
      fb.sucesso("Documento indexado.");
      setNovoTitulo(""); setNovoConteudo("");
      // Sem carregar() manual: a mutação invalida o cache e a lista recarrega.
    } catch (e) {
      fb.erro(extrairErro(e));
    }
  };

  const seedLegislacao = async () => {
    try {
      const r = await mut.seedLegislacao.mutateAsync();
      fb.sucesso(`${r.documentos_indexados} documento(s) de legislação ANTT indexado(s).`);
    } catch (e) {
      fb.erro(extrairErro(e));
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Base de Conhecimento" icone={<LibraryBooksIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Base de Conhecimento (RAG)"
        subtitulo="Documentos indexados para busca semântica do assistente"
        icone={<LibraryBooksIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="outlined" startIcon={<GavelIcon />} onClick={seedLegislacao}>
            Indexar legislação ANTT
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />
      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {/* Estatísticas */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined"><CardContent>
              <Typography variant="body2" color="text.secondary">Documentos</Typography>
              <Typography variant="h5" fontWeight={700} sx={{ color: GD.indigo }}>{stats.total_documentos}</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined"><CardContent>
              <Typography variant="body2" color="text.secondary">Indexados</Typography>
              <Typography variant="h5" fontWeight={700} sx={{ color: "#2E7D32" }}>{stats.indexados}</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Card variant="outlined"><CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>Por tipo</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {Object.entries(stats.por_tipo || {}).map(([tipo, qtd]) => (
                  <Chip key={tipo} size="small" label={`${tipo}: ${qtd}`}
                        sx={{ bgcolor: COR_TIPO[tipo] || GD.indigo, color: "#fff" }} />
                ))}
                {Object.keys(stats.por_tipo || {}).length === 0 && (
                  <Typography variant="caption" color="text.secondary">Nenhum documento ainda</Typography>
                )}
              </Stack>
            </CardContent></Card>
          </Grid>
        </Grid>
      )}

      <Grid container spacing={3}>
        {/* Busca semântica */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                Busca semântica
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <TextField
                  fullWidth size="small" placeholder="Ex: piso mínimo de frete"
                  value={consulta} onChange={(e) => setConsulta(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && buscar()}
                  InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
                />
                <Button variant="contained" onClick={buscar} disabled={buscando}>Buscar</Button>
              </Stack>
              {buscando && <LinearProgress sx={{ mb: 1 }} />}
              {resultados && (
                resultados.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    Nenhum documento relevante encontrado.
                  </Typography>
                ) : (
                  <List dense>
                    {resultados.map((r) => (
                      <ListItem key={r.id} sx={{ px: 0, alignItems: "flex-start" }}>
                        <ListItemText
                          primary={
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip size="small" label={r.tipo}
                                    sx={{ bgcolor: COR_TIPO[r.tipo] || GD.indigo, color: "#fff" }} />
                              <Typography variant="body2" fontWeight={600}>{r.titulo}</Typography>
                              <Chip size="small" variant="outlined" label={`${(r.similaridade * 100).toFixed(0)}%`} />
                            </Stack>
                          }
                          secondary={
                            <Typography variant="caption" color="text.secondary">
                              {r.conteudo.slice(0, 140)}...
                            </Typography>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Indexar novo documento */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                Indexar documento
              </Typography>
              <Stack spacing={2}>
                <TextField select size="small" label="Tipo" value={novoTipo}
                           onChange={(e) => setNovoTipo(e.target.value)}>
                  {TIPOS.map((t) => <MenuItem key={t.valor} value={t.valor}>{t.rotulo}</MenuItem>)}
                </TextField>
                <TextField size="small" label="Título" value={novoTitulo}
                           onChange={(e) => setNovoTitulo(e.target.value)} />
                <TextField size="small" label="Conteúdo" multiline rows={4} value={novoConteudo}
                           onChange={(e) => setNovoConteudo(e.target.value)} />
                <Button variant="contained" startIcon={<AddIcon />} onClick={indexar} disabled={salvando}>
                  Indexar
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Lista de documentos */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                Documentos indexados
              </Typography>
              {documentos.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhum documento. Indexe benchmarks, relatórios ou a legislação ANTT para
                  enriquecer as respostas do assistente.
                </Typography>
              ) : (
                <List dense>
                  {documentos.map((doc) => (
                    <ListItem key={doc.id} sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Chip size="small" label={doc.tipo}
                                  sx={{ bgcolor: COR_TIPO[doc.tipo] || GD.indigo, color: "#fff" }} />
                            <Typography variant="body2">{doc.titulo}</Typography>
                            {doc.empresa_id === 0 && (
                              <Chip size="small" variant="outlined" label="Global" />
                            )}
                          </Stack>
                        }
                      />
                      {doc.indexado
                        ? <Chip size="small" label="Indexado" color="success" variant="outlined" />
                        : <Chip size="small" label="Pendente" variant="outlined" />}
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
