import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Divider, Chip, Alert,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SavingsIcon from "@mui/icons-material/Savings";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import DescriptionIcon from "@mui/icons-material/Description";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { inteligenciaApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

function Secao({ titulo, conteudo, cor }) {
  if (!conteudo) return null;
  return (
    <Box sx={{ mb: 2.5 }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ color: cor || GD.indigo, mb: 0.5 }}>
        {titulo}
      </Typography>
      <Typography variant="body2" sx={{ whiteSpace: "pre-line", color: "text.secondary" }}>
        {conteudo}
      </Typography>
    </Box>
  );
}

export default function DiagnosticoIA() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [status, setStatus] = useState(null);
  const [diag, setDiag] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [semDiagnostico, setSemDiagnostico] = useState(false);
  const [menuRel, setMenuRel] = useState(null);
  const [baixando, setBaixando] = useState(false);

  const baixarRelatorio = async (formato) => {
    setMenuRel(null);
    setBaixando(true);
    try {
      await inteligenciaApi.baixarRelatorio(empresaAtivaId, formato);
      fb.sucesso("Relatório gerado.");
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setBaixando(false);
    }
  };

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    setSemDiagnostico(false);
    try {
      const st = await inteligenciaApi.status();
      setStatus(st);
      try {
        const d = await inteligenciaApi.obterDiagnostico(empresaAtivaId);
        setDiag(d);
      } catch {
        setSemDiagnostico(true);
        setDiag(null);
      }
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, fb]);

  useEffect(() => { carregar(); }, [carregar]);

  const gerar = async (forcar) => {
    setGerando(true);
    try {
      const d = await inteligenciaApi.gerarDiagnostico(empresaAtivaId, forcar);
      setDiag(d);
      setSemDiagnostico(false);
      fb.sucesso("Diagnóstico gerado.");
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setGerando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Diagnóstico IA" icone={<AutoAwesomeIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Diagnóstico IA"
        subtitulo="Análise executiva automática da operação logística"
        icone={<AutoAwesomeIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Stack direction="row" spacing={1}>
            {diag && (
              <>
                <Button variant="outlined" disabled={baixando}
                        onClick={(e) => setMenuRel(e.currentTarget)}>
                  Baixar relatório
                </Button>
                <Menu anchorEl={menuRel} open={Boolean(menuRel)} onClose={() => setMenuRel(null)}>
                  <MenuItem onClick={() => baixarRelatorio("pdf")}>
                    <PictureAsPdfIcon fontSize="small" sx={{ mr: 1 }} /> PDF
                  </MenuItem>
                  <MenuItem onClick={() => baixarRelatorio("word")}>
                    <DescriptionIcon fontSize="small" sx={{ mr: 1 }} /> Word
                  </MenuItem>
                  <MenuItem onClick={() => baixarRelatorio("powerpoint")}>
                    <SlideshowIcon fontSize="small" sx={{ mr: 1 }} /> PowerPoint
                  </MenuItem>
                </Menu>
                <Button variant="outlined" onClick={() => gerar(true)} disabled={gerando}>
                  Reprocessar
                </Button>
              </>
            )}
            <Button variant="contained" onClick={() => gerar(false)} disabled={gerando}>
              {diag ? "Atualizar" : "Gerar diagnóstico"}
            </Button>
          </Stack>
        }
      />

      <ModoSimuladoBanner status={status} />
      {(carregando || gerando) && <LinearProgress sx={{ mb: 2 }} />}

      {gerando && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Gerando diagnóstico... A IA está analisando seus dados.
        </Alert>
      )}

      {semDiagnostico && !diag && !gerando && (
        <Card variant="outlined">
          <CardContent sx={{ textAlign: "center", py: 5 }}>
            <AutoAwesomeIcon sx={{ fontSize: 48, color: GD.amber, mb: 1 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>Nenhum diagnóstico ainda</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Clique em "Gerar diagnóstico" para que a IA analise sua operação e produza
              um resumo executivo com pontos fortes, desvios e plano de ação.
            </Typography>
            <Button variant="contained" size="large" onClick={() => gerar(false)} disabled={gerando}>
              Gerar diagnóstico
            </Button>
          </CardContent>
        </Card>
      )}

      {diag && (
        <Card variant="outlined">
          <CardContent>
            {/* Cabeçalho com score e economia */}
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 3 }}>
              <Chip
                label={`Score: ${diag.score_logistico}/100`}
                sx={{ bgcolor: GD.indigo, color: "#fff", fontWeight: 700 }}
              />
              <Chip
                icon={<SavingsIcon sx={{ color: "#fff !important" }} />}
                label={`Economia potencial: ${fmtMoeda(diag.economia_potencial)}/ano`}
                sx={{ bgcolor: GD.blue, color: "#fff", fontWeight: 700 }}
              />
              {diag.modelo_usado && (
                <Chip label={diag.modelo_usado} variant="outlined" size="small" />
              )}
            </Stack>

            <Divider sx={{ mb: 3 }} />

            <Secao titulo="Resumo Executivo" conteudo={diag.resumo_executivo} />
            <Secao titulo="Pontos Fortes" conteudo={diag.pontos_fortes} cor="#2E7D32" />
            <Secao titulo="Pontos de Atenção" conteudo={diag.pontos_atencao} cor={GD.amber} />
            <Secao titulo="Principais Desvios" conteudo={diag.principais_desvios} cor="#C62828" />
            <Secao titulo="Plano de Ação Sugerido" conteudo={diag.plano_acao} cor={GD.blue} />

            {diag.created_at && (
              <Typography variant="caption" color="text.secondary">
                Gerado em {new Date(diag.created_at).toLocaleString("pt-BR")}
              </Typography>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
