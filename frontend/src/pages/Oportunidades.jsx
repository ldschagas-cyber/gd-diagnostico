import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid,
} from "@mui/material";
import SavingsIcon from "@mui/icons-material/Savings";
import GavelIcon from "@mui/icons-material/Gavel";
import MergeIcon from "@mui/icons-material/Merge";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import HandshakeIcon from "@mui/icons-material/Handshake";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import SearchIcon from "@mui/icons-material/Search";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { inteligenciaApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

const ESTILO_TIPO = {
  BID:           { icone: <GavelIcon />, rotulo: "BID", cor: GD.indigo },
  CONSOLIDACAO:  { icone: <MergeIcon />, rotulo: "Consolidação", cor: GD.blue },
  REDISTRIBUICAO:{ icone: <SwapHorizIcon />, rotulo: "Redistribuição", cor: "#7030A0" },
  RENEGOCIACAO:  { icone: <HandshakeIcon />, rotulo: "Renegociação", cor: GD.amber },
  CONCENTRACAO:  { icone: <WarningAmberIcon />, rotulo: "Concentração", cor: "#C62828" },
};

const COR_IMPACTO = { ALTO: "#C62828", MEDIO: GD.amber, BAIXO: "#2E7D32" };

export default function Oportunidades() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [status, setStatus] = useState(null);
  const [oportunidades, setOportunidades] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [detectando, setDetectando] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const [st, lista] = await Promise.all([
        inteligenciaApi.status(),
        inteligenciaApi.listarOportunidades(empresaAtivaId),
      ]);
      setStatus(st);
      setOportunidades(lista);
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, fb]);

  useEffect(() => { carregar(); }, [carregar]);

  const detectar = async () => {
    setDetectando(true);
    try {
      const r = await inteligenciaApi.detectarOportunidades(empresaAtivaId);
      fb.sucesso(`${r.total} oportunidade(s) identificada(s).`);
      carregar();
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setDetectando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Oportunidades" icone={<SavingsIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  const economiaTotal = oportunidades.reduce((s, o) => s + (o.economia_estimada || 0), 0);

  return (
    <Box>
      <PageHeader
        titulo="Oportunidades Automáticas"
        subtitulo="Economias identificadas pela análise dos seus dados"
        icone={<SavingsIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="contained" startIcon={<SearchIcon />} onClick={detectar} disabled={detectando}>
            Detectar oportunidades
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />
      {(carregando || detectando) && <LinearProgress sx={{ mb: 2 }} />}

      {oportunidades.length > 0 && (
        <Card sx={{ mb: 3, bgcolor: GD.blue, color: "#fff" }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="overline" sx={{ opacity: 0.8 }}>
                  Economia potencial total identificada
                </Typography>
                <Typography variant="h4" fontWeight={800}>{fmtMoeda(economiaTotal)}/ano</Typography>
              </Box>
              <SavingsIcon sx={{ fontSize: 48, opacity: 0.7 }} />
            </Stack>
          </CardContent>
        </Card>
      )}

      {oportunidades.length === 0 && !carregando ? (
        <Card variant="outlined">
          <CardContent sx={{ textAlign: "center", py: 5 }}>
            <SavingsIcon sx={{ fontSize: 48, color: GD.amber, mb: 1 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>Nenhuma oportunidade detectada</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Clique em "Detectar oportunidades" para a IA analisar seus dados e
              identificar economias via BID, consolidação, renegociação e mais.
            </Typography>
            <Button variant="contained" onClick={detectar} disabled={detectando}>
              Detectar oportunidades
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {oportunidades.map((op) => {
            const est = ESTILO_TIPO[op.tipo] || ESTILO_TIPO.BID;
            return (
              <Grid item xs={12} md={6} key={op.id}>
                <Card variant="outlined" sx={{ height: "100%", borderTop: `3px solid ${est.cor}` }}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Box sx={{ color: est.cor }}>{est.icone}</Box>
                        <Chip label={est.rotulo} size="small" sx={{ bgcolor: est.cor, color: "#fff" }} />
                      </Stack>
                      <Chip
                        label={`Impacto ${op.impacto}`}
                        size="small"
                        sx={{ bgcolor: COR_IMPACTO[op.impacto] || GD.amber, color: "#fff" }}
                      />
                    </Stack>

                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                      {op.titulo}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      {op.descricao}
                    </Typography>

                    {op.economia_estimada > 0 && (
                      <Typography variant="h6" sx={{ color: "#2E7D32", fontWeight: 700, mb: 1 }}>
                        {fmtMoeda(op.economia_estimada)}/ano
                      </Typography>
                    )}

                    <Stack direction="row" spacing={1}>
                      <Chip label={`Complexidade: ${op.complexidade}`} size="small" variant="outlined" />
                      <Chip label={`Prioridade ${op.prioridade}`} size="small" variant="outlined" />
                    </Stack>

                    {op.justificativa && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
                        {op.justificativa}
                      </Typography>
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
