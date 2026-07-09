import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid, IconButton, Tooltip,
} from "@mui/material";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import DoneIcon from "@mui/icons-material/Done";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { inteligenciaApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

const ESTILO_CLASSIFICACAO = {
  CRITICO:      { cor: "#C62828", icone: <ErrorOutlineIcon />, rotulo: "Crítico" },
  ATENCAO:      { cor: GD.amber, icone: <WarningAmberIcon />, rotulo: "Atenção" },
  OPORTUNIDADE: { cor: "#2E7D32", icone: <TrendingUpIcon />, rotulo: "Oportunidade" },
  INFORMATIVO:  { cor: GD.blue, icone: <InfoOutlinedIcon />, rotulo: "Informativo" },
};

const ROTULO_CATEGORIA = {
  CUSTO: "Custo", PERFORMANCE: "Performance", BENCHMARK: "Benchmark",
  TRANSPORTADORAS: "Transportadoras", FILIAIS: "Filiais", REGIOES: "Regiões",
};

export default function Insights() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [status, setStatus] = useState(null);
  const [insights, setInsights] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [gerando, setGerando] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const [st, lista] = await Promise.all([
        inteligenciaApi.status(),
        inteligenciaApi.listarInsights(empresaAtivaId),
      ]);
      setStatus(st);
      setInsights(lista);
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, fb]);

  useEffect(() => { carregar(); }, [carregar]);

  const gerar = async () => {
    setGerando(true);
    try {
      const r = await inteligenciaApi.gerarInsights(empresaAtivaId);
      fb.sucesso(`${r.total_insights} insight(s) gerado(s).`);
      carregar();
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setGerando(false);
    }
  };

  const marcarLido = async (id) => {
    try {
      await inteligenciaApi.marcarLido(id, empresaAtivaId);
      setInsights((prev) => prev.map((i) => (i.id === id ? { ...i, lido: true } : i)));
    } catch (e) {
      fb.erro(extrairErro(e));
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Insights Automáticos" icone={<LightbulbIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Insights Automáticos"
        subtitulo="Alertas gerados pelo motor de regras sobre custo, desempenho e oportunidades"
        icone={<LightbulbIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={gerar} disabled={gerando}>
            Gerar insights agora
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />
      {(carregando || gerando) && <LinearProgress sx={{ mb: 2 }} />}

      {insights.length === 0 && !carregando ? (
        <Card variant="outlined">
          <CardContent sx={{ textAlign: "center", py: 5 }}>
            <LightbulbIcon sx={{ fontSize: 48, color: GD.amber, mb: 1 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>Nenhum insight no momento</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              O motor de regras roda automaticamente todos os dias. Você também pode
              gerar os insights manualmente agora. Sem CT-es importados, não há dados
              para analisar.
            </Typography>
            <Button variant="contained" onClick={gerar} disabled={gerando}>
              Gerar insights agora
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {insights.map((ins) => {
            const est = ESTILO_CLASSIFICACAO[ins.classificacao] || ESTILO_CLASSIFICACAO.INFORMATIVO;
            return (
              <Grid item xs={12} md={6} key={ins.id}>
                <Card
                  variant="outlined"
                  sx={{
                    height: "100%", borderLeft: `4px solid ${est.cor}`,
                    opacity: ins.lido ? 0.6 : 1,
                  }}
                >
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Box sx={{ color: est.cor }}>{est.icone}</Box>
                        <Chip label={est.rotulo} size="small" sx={{ bgcolor: est.cor, color: "#fff" }} />
                        <Chip label={ROTULO_CATEGORIA[ins.categoria] || ins.categoria} size="small" variant="outlined" />
                      </Stack>
                      {!ins.lido && (
                        <Tooltip title="Marcar como lido">
                          <IconButton size="small" onClick={() => marcarLido(ins.id)}>
                            <DoneIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                      {ins.titulo}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {ins.descricao}
                    </Typography>
                    {ins.impacto_financeiro > 0 && (
                      <Chip
                        icon={<TrendingUpIcon />}
                        label={`Impacto: ${fmtMoeda(ins.impacto_financeiro)}`}
                        size="small" sx={{ bgcolor: GD.ivoryDeep }}
                      />
                    )}
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
}
