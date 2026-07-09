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
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import CloseIcon from "@mui/icons-material/Close";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import ResultadoImportacao from "../components/ResultadoImportacao";
import GerenciarDadosImportados from "../components/GerenciarDadosImportados";
import IndicadorBaseCte from "../components/IndicadorBaseCte";
import ImportacaoCancelamento from "../components/ImportacaoCancelamento";
import { useFeedback } from "../components/Feedback";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

export default function ImportacaoCte() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const inputRef = useRef(null);
  const [arquivos, setArquivos] = useState([]);
  const [arrastar, setArrastar] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [progresso, setProgresso] = useState(0);
  const [resultado, setResultado] = useState(null);
  const [recarregarIndicador, setRecarregarIndicador] = useState(0);

  const adicionar = (lista) => {
    const xmls = Array.from(lista).filter((f) => f.name.toLowerCase().endsWith(".xml"));
    setArquivos((prev) => {
      const nomes = new Set(prev.map((f) => f.name + f.size));
      const novos = xmls.filter((f) => !nomes.has(f.name + f.size));
      return [...prev, ...novos];
    });
  };

  const onDrop = (e) => {
    e.preventDefault();
    setArrastar(false);
    adicionar(e.dataTransfer.files);
  };

  const remover = (idx) => setArquivos((prev) => prev.filter((_, i) => i !== idx));

  const enviar = async () => {
    if (!arquivos.length || !empresaAtivaId) return;
    setEnviando(true);
    setProgresso(0);
    setResultado(null);
    try {
      const res = await importacaoApi.importarCte(empresaAtivaId, arquivos, (e) => {
        if (e.total) setProgresso(Math.round((e.loaded / e.total) * 100));
      });
      setResultado(res);
      sucesso(`${res.importados} CT-e(s) importado(s).`);
      setArquivos([]);
      // Atualização automática do indicador de base de CT-e após a importação.
      setRecarregarIndicador((n) => n + 1);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao importar os CT-es."));
    } finally {
      setEnviando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Importar CT-e" subtitulo="Importação de XMLs de CT-e" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Os CT-es são vinculados à empresa ativa. Selecione-a no topo da tela."
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Importar CT-e"
        subtitulo={`Destino: ${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}`}
      />

      <Alert severity="info" sx={{ mb: 2.5 }}>
        Apenas CT-es cujo tomador seja a matriz ou uma filial cadastrada serão
        importados. Documentos duplicados (mesma chave) são ignorados
        automaticamente. Capacidade: até 10.000 CT-es por lote.
      </Alert>

      <Card>
        <CardContent>
          <Box
            onDragOver={(e) => {
              e.preventDefault();
              setArrastar(true);
            }}
            onDragLeave={() => setArrastar(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            sx={{
              border: "2px dashed",
              borderColor: arrastar ? GD.amber : "rgba(45,53,97,0.25)",
              bgcolor: arrastar ? "rgba(201,168,76,0.06)" : "transparent",
              borderRadius: 3,
              p: 6,
              textAlign: "center",
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".xml"
              multiple
              hidden
              onChange={(e) => adicionar(e.target.files)}
            />
            <CloudUploadIcon sx={{ fontSize: 52, color: GD.indigo, mb: 1 }} />
            <Typography variant="h6">Arraste os XMLs aqui</Typography>
            <Typography variant="body2" color="text.secondary">
              ou clique para selecionar (vários arquivos)
            </Typography>
          </Box>

          {arquivos.length > 0 && (
            <Box sx={{ mt: 2.5 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                sx={{ mb: 1 }}
              >
                <Chip
                  label={`${arquivos.length} arquivo(s) selecionado(s)`}
                  color="primary"
                  variant="outlined"
                />
                <Button size="small" color="inherit" onClick={() => setArquivos([])}>
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
                {arquivos.map((f, i) => (
                  <ListItem
                    key={f.name + i}
                    secondaryAction={
                      <IconButton edge="end" size="small" onClick={() => remover(i)}>
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

          {enviando && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress variant="determinate" value={progresso} />
              <Typography variant="caption" color="text.secondary">
                Enviando... {progresso}%
              </Typography>
            </Box>
          )}

          <Button
            variant="contained"
            size="large"
            startIcon={<CloudUploadIcon />}
            onClick={enviar}
            disabled={!arquivos.length || enviando}
            sx={{ mt: 2.5 }}
          >
            {enviando ? "Importando..." : `Importar ${arquivos.length || ""} CT-e(s)`}
          </Button>
        </CardContent>
      </Card>

      <ResultadoImportacao resultado={resultado} />

      <ImportacaoCancelamento
        onConcluido={() => setRecarregarIndicador((n) => n + 1)}
      />

      <IndicadorBaseCte recarregarSinal={recarregarIndicador} />

      <GerenciarDadosImportados />
    </Box>
  );
}
