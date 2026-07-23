import { useState, useRef } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Chip,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  FormControlLabel,
  Checkbox,
  ToggleButton,
  ToggleButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DescriptionIcon from "@mui/icons-material/Description";
import CloseIcon from "@mui/icons-material/Close";
import TableChartIcon from "@mui/icons-material/TableChart";
import DownloadIcon from "@mui/icons-material/Download";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import ResultadoImportacao from "../components/ResultadoImportacao";
import GerenciarDadosImportados from "../components/GerenciarDadosImportados";
import IndicadorBaseCte from "../components/IndicadorBaseCte";
import GridCte from "../components/GridCte";
import { useFeedback } from "../components/Feedback";
import { importacaoApi } from "../api/endpoints";
import { useInvalidarDadosEmpresa } from "../api/queries";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

// Após uma falha sem resposta HTTP (conexão perdida/timeout de proxy), o
// backend pode ter concluído a importação mesmo sem a resposta chegar ao
// navegador (processamento síncrono longo em lotes grandes) — reconsulta a
// contagem algumas vezes antes de declarar falha ao usuário.
async function confirmarImportacaoAposFalhaDeRede(
  empresaId, totalAntes, tentativas = 3, intervaloMs = 3000,
) {
  for (let i = 0; i < tentativas; i++) {
    await new Promise((resolve) => setTimeout(resolve, intervaloMs));
    try {
      const atual = await importacaoApi.contarDados(empresaId);
      if (atual.total > totalAntes) return true;
    } catch {
      // ignora e tenta de novo
    }
  }
  return false;
}

const COLUNAS_ESPERADAS = [
  ["Nota Fiscal", "Identificador da NF (obrigatório)"],
  ["CT-e", "Número do Conhecimento de Transporte (opcional)"],
  ["Data Emissão", "Data de emissão do CT-e (obrigatório) — define o mês/competência do frete"],
  ["Data Embarque / Saída / Entrega", "Datas operacionais do transporte (opcionais)"],
  ["Transportadora", "Nome da transportadora"],
  [
    "Destinatário / Destinatário CNPJ",
    "Cliente final da carga (opcional) — alimenta a dimensão Cliente do diagnóstico",
  ],
  [
    "CNPJ Tomador (ou \"Tomador\" / \"Filial\")",
    "CNPJ da matriz/filial responsável pelo frete (opcional) — alimenta a dimensão Filial do diagnóstico. Aceita só os números ou um texto com o CNPJ embutido (ex: \"03822909000113 - Razão Social\"). Deve ser o CNPJ de uma filial (ou matriz) já cadastrada em Empresas e Filiais.",
  ],
  ["Cidade Origem / Destino", "Praças de coleta e entrega"],
  ["Peso", "Peso transportado (kg)"],
  ["Valor Mercadoria", "Valor da mercadoria (R$)"],
  ["Valor Frete", "Valor total do frete (R$)"],
  [
    "Componentes (opcionais)",
    "Frete Peso, Frete Valor, Pedágio, GRIS, Seguro, Ademe, Despacho, Outros",
  ],
];

export default function Importacao() {
  const { sucesso, erro: erroToast, info } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const invalidarDadosEmpresa = useInvalidarDadosEmpresa();

  const [modo, setModo] = useState(null);
  const [importarAberto, setImportarAberto] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [recarregarIndicador, setRecarregarIndicador] = useState(0);
  const [colunasAbertas, setColunasAbertas] = useState(false);

  const alternarImportar = () => {
    setImportarAberto((aberto) => {
      if (aberto) setModo(null);
      return !aberto;
    });
  };
  const fecharImportar = () => {
    setImportarAberto(false);
    setModo(null);
  };

  // ---- Aba Importar CT-e (+ cancelamento, detectado automaticamente) ----
  const inputCteRef = useRef(null);
  const [arquivosCte, setArquivosCte] = useState([]);
  const [arrastarCte, setArrastarCte] = useState(false);
  const [enviandoCte, setEnviandoCte] = useState(false);
  const [progressoCte, setProgressoCte] = useState(0);

  const adicionarCte = (lista) => {
    const xmls = Array.from(lista).filter((f) => f.name.toLowerCase().endsWith(".xml"));
    setArquivosCte((prev) => {
      const nomes = new Set(prev.map((f) => f.name + f.size));
      const novos = xmls.filter((f) => !nomes.has(f.name + f.size));
      return [...prev, ...novos];
    });
  };
  const removerCte = (idx) => setArquivosCte((prev) => prev.filter((_, i) => i !== idx));

  const enviarCte = async () => {
    if (!arquivosCte.length || !empresaAtivaId) return;
    setEnviandoCte(true);
    setProgressoCte(0);
    setResultado(null);

    let contagemAntes = null;
    try {
      contagemAntes = await importacaoApi.contarDados(empresaAtivaId);
    } catch {
      // ignora — usado apenas para checagem em caso de falha de rede
    }

    try {
      const res = await importacaoApi.importarCte(empresaAtivaId, arquivosCte, (e) => {
        if (e.total) setProgressoCte(Math.round((e.loaded / e.total) * 100));
      });
      const importados = res.importacao.importados || 0;
      const cancelados = res.cancelamento.cancelados || 0;
      const cartasCorrecao = res.carta_correcao?.registradas || 0;
      const cartasCorrecaoOcorrencias = (res.carta_correcao?.ocorrencias || [])
        .filter((o) => o.resultado === "REGISTRADA");
      setResultado({
        ...res.importacao,
        cancelados,
        cartas_correcao: cartasCorrecao,
        cartas_correcao_ocorrencias: cartasCorrecaoOcorrencias,
      });

      const partes = [];
      if (importados) partes.push(`${importados} CT-e(s) importado(s)`);
      if (cancelados) partes.push(`${cancelados} cancelamento(s) processado(s)`);
      if (cartasCorrecao) partes.push(`${cartasCorrecao} carta(s) de correção registrada(s) para revisão`);
      sucesso(partes.length ? `${partes.join(" e ")}.` : "Lote processado, nenhuma novidade.");

      setArquivosCte([]);
      setRecarregarIndicador((n) => n + 1);
      invalidarDadosEmpresa(empresaAtivaId);
    } catch (e) {
      // Sem resposta HTTP (conexão perdida/timeout): o backend pode ter
      // concluído a importação mesmo assim — confirma antes de dar como falha.
      if (!e.response && contagemAntes) {
        info("Conexão instável — verificando se a importação foi concluída...");
        const confirmado = await confirmarImportacaoAposFalhaDeRede(
          empresaAtivaId, contagemAntes.total,
        );
        if (confirmado) {
          sucesso("Conexão instável, mas a importação foi concluída no servidor.");
          setArquivosCte([]);
          setRecarregarIndicador((n) => n + 1);
          invalidarDadosEmpresa(empresaAtivaId);
          return;
        }
      }
      erroToast(extrairErro(e, "Falha ao importar os CT-es."));
    } finally {
      setEnviandoCte(false);
    }
  };

  // ---- Aba Importar Excel ----
  const inputExcelRef = useRef(null);
  const [arquivoExcel, setArquivoExcel] = useState(null);
  const [arrastarExcel, setArrastarExcel] = useState(false);
  const [enviandoExcel, setEnviandoExcel] = useState(false);
  const [atualizarExistentes, setAtualizarExistentes] = useState(false);

  const escolherExcel = (lista) => {
    const f = Array.from(lista).find((x) => /\.(xlsx|xls)$/i.test(x.name));
    if (f) setArquivoExcel(f);
    else erroToast("Selecione um arquivo .xlsx ou .xls.");
  };

  const baixarModelo = async () => {
    try {
      await importacaoApi.baixarModeloExcel();
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao baixar o modelo."));
    }
  };

  const enviarExcel = async () => {
    if (!arquivoExcel || !empresaAtivaId) return;
    setEnviandoExcel(true);
    setResultado(null);
    try {
      const res = await importacaoApi.importarExcel(
        empresaAtivaId,
        arquivoExcel,
        atualizarExistentes,
      );
      setResultado(res);
      const msg =
        res.atualizados > 0
          ? `${res.importados} importado(s), ${res.atualizados} atualizado(s).`
          : `${res.importados} registro(s) importado(s).`;
      sucesso(msg);
      setArquivoExcel(null);
      setRecarregarIndicador((n) => n + 1);
      invalidarDadosEmpresa(empresaAtivaId);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao importar a planilha."));
    } finally {
      setEnviandoExcel(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Importação" subtitulo="Importação de CT-e e planilha" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Os dados são vinculados à empresa ativa. Selecione-a no topo da tela."
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Importação"
        subtitulo={`Destino: ${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}`}
        acoes={
          <Button
            variant={importarAberto ? "outlined" : "contained"}
            startIcon={<UploadFileIcon />}
            onClick={alternarImportar}
          >
            Importar
          </Button>
        }
      />

      <Dialog
        open={importarAberto}
        onClose={fecharImportar}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { maxHeight: "90vh" } }}
      >
        <DialogTitle sx={{ pr: 6 }}>
          Importar
          <IconButton
            onClick={fecharImportar}
            sx={{ position: "absolute", right: 12, top: 12 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={modo}
            onChange={(_, v) => v && setModo(v)}
            sx={{ mb: 2.5, "& .MuiToggleButton-root": { height: 40, minWidth: 140 } }}
          >
            <ToggleButton value="cte">Importar CT-e</ToggleButton>
            <ToggleButton value="excel">Importar Excel</ToggleButton>
          </ToggleButtonGroup>

          {modo === "cte" && (
        <Box>
          <Alert severity="info" sx={{ mb: 2.5 }}>
            Apenas CT-es cujo tomador seja a matriz ou uma filial cadastrada serão
            importados. Documentos duplicados (mesma chave) são ignorados
            automaticamente. XMLs de evento de cancelamento (tpEvento 110111) são
            detectados automaticamente no mesmo lote — não é preciso separá-los.
            Capacidade: até 10.000 CT-es por lote.
          </Alert>

          <Card>
            <CardContent>
              <Box
                onDragOver={(e) => { e.preventDefault(); setArrastarCte(true); }}
                onDragLeave={() => setArrastarCte(false)}
                onDrop={(e) => { e.preventDefault(); setArrastarCte(false); adicionarCte(e.dataTransfer.files); }}
                onClick={() => inputCteRef.current?.click()}
                sx={{
                  border: "2px dashed",
                  borderColor: arrastarCte ? GD.amber : "rgba(45,53,97,0.25)",
                  bgcolor: arrastarCte ? "rgba(201,168,76,0.06)" : "transparent",
                  borderRadius: 3,
                  p: 6,
                  textAlign: "center",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                <input
                  ref={inputCteRef}
                  type="file"
                  accept=".xml"
                  multiple
                  hidden
                  onChange={(e) => adicionarCte(e.target.files)}
                />
                <CloudUploadIcon sx={{ fontSize: 52, color: GD.indigo, mb: 1 }} />
                <Typography variant="h6">Arraste os XMLs aqui</Typography>
                <Typography variant="body2" color="text.secondary">
                  ou clique para selecionar (CT-e e cancelamento juntos)
                </Typography>
              </Box>

              {arquivosCte.length > 0 && (
                <Box sx={{ mt: 2.5 }}>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    sx={{ mb: 1 }}
                  >
                    <Chip
                      label={`${arquivosCte.length} arquivo(s) selecionado(s)`}
                      color="primary"
                      variant="outlined"
                    />
                    <Button size="small" color="inherit" onClick={() => setArquivosCte([])}>
                      Limpar
                    </Button>
                  </Stack>
                  <List
                    dense
                    sx={{
                      maxHeight: 240,
                      overflowY: "auto",
                      border: "1px solid rgba(45,53,97,0.12)",
                      borderRadius: 2,
                    }}
                  >
                    {arquivosCte.map((f, i) => (
                      <ListItem
                        key={f.name + i}
                        secondaryAction={
                          <IconButton edge="end" size="small" onClick={() => removerCte(i)}>
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        }
                      >
                        <DescriptionIcon sx={{ mr: 1.5, color: GD.blue }} />
                        <ListItemText
                          primary={f.name}
                          secondary={`${(f.size / 1024).toFixed(1)} KB`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {enviandoCte && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress variant="determinate" value={progressoCte} />
                  <Typography variant="caption" color="text.secondary">
                    Enviando... {progressoCte}%
                  </Typography>
                </Box>
              )}

              <Button
                variant="contained"
                size="large"
                startIcon={<CloudUploadIcon />}
                onClick={enviarCte}
                disabled={!arquivosCte.length || enviandoCte}
                sx={{ mt: 2.5 }}
              >
                {enviandoCte ? "Importando..." : `Importar ${arquivosCte.length || ""} arquivo(s)`}
              </Button>
            </CardContent>
          </Card>
        </Box>
      )}

      {modo === "excel" && (
        <Box>
          <Alert severity="info" sx={{ mb: 2.5 }}>
            Use esta opção quando não houver XML de CT-e. A planilha deve conter as
            colunas abaixo (a ordem é livre; nomes acentuados são reconhecidos).
          </Alert>

          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                flexWrap="wrap"
                useFlexGap
                spacing={1}
              >
                <Typography variant="body2" color="text.secondary">
                  Obrigatórias: Nota Fiscal, Data Emissão, Transportadora, Cidade Origem,
                  Cidade Destino, Peso, Valor Mercadoria, Valor Frete.
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    startIcon={<InfoOutlinedIcon fontSize="small" />}
                    onClick={() => setColunasAbertas(true)}
                    sx={{ color: "text.secondary" }}
                  >
                    Colunas esperadas
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={baixarModelo}
                  >
                    Baixar modelo
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          <Dialog open={colunasAbertas} onClose={() => setColunasAbertas(false)} maxWidth="sm" fullWidth>
            <DialogTitle>Colunas esperadas</DialogTitle>
            <DialogContent>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Coluna</TableCell>
                      <TableCell>Descrição</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {COLUNAS_ESPERADAS.map(([col, desc]) => (
                      <TableRow key={col}>
                        <TableCell sx={{ fontWeight: 600 }}>{col}</TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>{desc}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setColunasAbertas(false)}>Fechar</Button>
            </DialogActions>
          </Dialog>

          <Card>
            <CardContent>
              <Box
                onDragOver={(e) => { e.preventDefault(); setArrastarExcel(true); }}
                onDragLeave={() => setArrastarExcel(false)}
                onDrop={(e) => { e.preventDefault(); setArrastarExcel(false); escolherExcel(e.dataTransfer.files); }}
                onClick={() => inputExcelRef.current?.click()}
                sx={{
                  border: "2px dashed",
                  borderColor: arrastarExcel ? GD.amber : "rgba(45,53,97,0.25)",
                  bgcolor: arrastarExcel ? "rgba(201,168,76,0.06)" : "transparent",
                  borderRadius: 3,
                  p: 6,
                  textAlign: "center",
                  cursor: "pointer",
                }}
              >
                <input
                  ref={inputExcelRef}
                  type="file"
                  accept=".xlsx,.xls"
                  hidden
                  onChange={(e) => escolherExcel(e.target.files)}
                />
                <TableChartIcon sx={{ fontSize: 52, color: GD.indigo, mb: 1 }} />
                <Typography variant="h6">Arraste a planilha aqui</Typography>
                <Typography variant="body2" color="text.secondary">
                  ou clique para selecionar (.xlsx / .xls)
                </Typography>
              </Box>

              {arquivoExcel && (
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2.5 }}>
                  <Chip
                    icon={<TableChartIcon />}
                    label={`${arquivoExcel.name} · ${(arquivoExcel.size / 1024).toFixed(1)} KB`}
                    color="primary"
                    variant="outlined"
                    onDelete={() => setArquivoExcel(null)}
                  />
                </Stack>
              )}

              {enviandoExcel && <LinearProgress sx={{ mt: 2 }} />}

              <FormControlLabel
                sx={{ mt: 2, display: "block" }}
                control={
                  <Checkbox
                    checked={atualizarExistentes}
                    onChange={(e) => setAtualizarExistentes(e.target.checked)}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      Atualizar registros existentes
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Quando marcado, registros já importados (mesma NF/CT-e) são
                      atualizados com os dados da planilha, em vez de criar novos.
                    </Typography>
                  </Box>
                }
              />

              <Button
                variant="contained"
                size="large"
                startIcon={<CloudUploadIcon />}
                onClick={enviarExcel}
                disabled={!arquivoExcel || enviandoExcel}
                sx={{ mt: 1.5, display: "block" }}
              >
                {enviandoExcel ? "Importando..." : "Importar planilha"}
              </Button>
            </CardContent>
          </Card>
        </Box>
      )}
        </DialogContent>
      </Dialog>

      <ResultadoImportacao resultado={resultado} />

      <IndicadorBaseCte recarregarSinal={recarregarIndicador} />

      <GridCte
        recarregarSinal={recarregarIndicador}
        onExcluido={() => setRecarregarIndicador((n) => n + 1)}
      />

      <GerenciarDadosImportados />
    </Box>
  );
}
