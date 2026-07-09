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
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  FormControlLabel,
  Checkbox,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import TableChartIcon from "@mui/icons-material/TableChart";
import DownloadIcon from "@mui/icons-material/Download";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import ResultadoImportacao from "../components/ResultadoImportacao";
import GerenciarDadosImportados from "../components/GerenciarDadosImportados";
import { useFeedback } from "../components/Feedback";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

const COLUNAS_ESPERADAS = [
  ["Nota Fiscal", "Identificador da NF (obrigatório)"],
  ["CT-e", "Número do Conhecimento de Transporte (opcional)"],
  ["Data Embarque / Saída / Entrega", "Datas do transporte"],
  ["Transportadora", "Nome da transportadora"],
  ["Cidade Origem / Destino", "Praças de coleta e entrega"],
  ["Peso", "Peso transportado (kg)"],
  ["Valor Mercadoria", "Valor da mercadoria (R$)"],
  ["Valor Frete", "Valor total do frete (R$)"],
  [
    "Componentes (opcionais)",
    "Frete Peso, Frete Valor, Pedágio, GRIS, Seguro, Ademe, Despacho, Outros",
  ],
];

export default function ImportacaoExcel() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const inputRef = useRef(null);
  const [arquivo, setArquivo] = useState(null);
  const [arrastar, setArrastar] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [atualizarExistentes, setAtualizarExistentes] = useState(false);

  const escolher = (lista) => {
    const f = Array.from(lista).find((x) => /\.(xlsx|xls)$/i.test(x.name));
    if (f) setArquivo(f);
    else erroToast("Selecione um arquivo .xlsx ou .xls.");
  };

  const baixarModelo = async () => {
    try {
      await importacaoApi.baixarModeloExcel();
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao baixar o modelo."));
    }
  };

  const enviar = async () => {
    if (!arquivo || !empresaAtivaId) return;
    setEnviando(true);
    setResultado(null);
    try {
      const res = await importacaoApi.importarExcel(
        empresaAtivaId,
        arquivo,
        atualizarExistentes,
      );
      setResultado(res);
      const msg =
        res.atualizados > 0
          ? `${res.importados} importado(s), ${res.atualizados} atualizado(s).`
          : `${res.importados} registro(s) importado(s).`;
      sucesso(msg);
      setArquivo(null);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao importar a planilha."));
    } finally {
      setEnviando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Importar Excel" subtitulo="Importação alternativa por planilha" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Os registros são vinculados à empresa ativa. Selecione-a no topo."
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Importar Excel"
        subtitulo={`Destino: ${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}`}
      />

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
            sx={{ mb: 1.5 }}
          >
            <Typography variant="subtitle2">
              Colunas esperadas
            </Typography>
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={baixarModelo}
            >
              Baixar modelo
            </Button>
          </Stack>
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
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box
            onDragOver={(e) => {
              e.preventDefault();
              setArrastar(true);
            }}
            onDragLeave={() => setArrastar(false)}
            onDrop={(e) => {
              e.preventDefault();
              setArrastar(false);
              escolher(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
            sx={{
              border: "2px dashed",
              borderColor: arrastar ? GD.amber : "rgba(45,53,97,0.25)",
              bgcolor: arrastar ? "rgba(201,168,76,0.06)" : "transparent",
              borderRadius: 3,
              p: 6,
              textAlign: "center",
              cursor: "pointer",
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              hidden
              onChange={(e) => escolher(e.target.files)}
            />
            <TableChartIcon sx={{ fontSize: 52, color: GD.indigo, mb: 1 }} />
            <Typography variant="h6">Arraste a planilha aqui</Typography>
            <Typography variant="body2" color="text.secondary">
              ou clique para selecionar (.xlsx / .xls)
            </Typography>
          </Box>

          {arquivo && (
            <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2.5 }}>
              <Chip
                icon={<TableChartIcon />}
                label={`${arquivo.name} · ${(arquivo.size / 1024).toFixed(1)} KB`}
                color="primary"
                variant="outlined"
                onDelete={() => setArquivo(null)}
              />
            </Stack>
          )}

          {enviando && <LinearProgress sx={{ mt: 2 }} />}

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
            onClick={enviar}
            disabled={!arquivo || enviando}
            sx={{ mt: 1.5, display: "block" }}
          >
            {enviando ? "Importando..." : "Importar planilha"}
          </Button>
        </CardContent>
      </Card>

      <ResultadoImportacao resultado={resultado} />

      <GerenciarDadosImportados />
    </Box>
  );
}
