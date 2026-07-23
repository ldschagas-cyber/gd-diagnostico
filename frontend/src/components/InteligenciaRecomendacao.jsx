import { useState } from "react";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid, Divider, Collapse,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SavingsIcon from "@mui/icons-material/Savings";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import {
  useIaDiagnostico, useGerarDiagnosticoIA,
  useIaInsights, useGerarInsights,
  useIaOportunidades, useDetectarOportunidades,
} from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

// Diagnóstico IA/Insights/Oportunidades eram 3 telas próprias do extinto módulo
// "Inteligência Logística - IA". Cada uma virou esta seção, mostrada dentro do
// módulo de domínio a que pertence (Operação / Mercado / Concorrência),
// filtrando insights e oportunidades pela categoria/tipo relevante.
const CATEGORIA_INSIGHT_POR_MODULO = {
  operacao:     ["CUSTO", "PERFORMANCE", "FILIAIS"],
  mercado:      ["BENCHMARK", "REGIOES"],
  concorrencia: ["TRANSPORTADORAS"],
};

const TIPO_OPORTUNIDADE_POR_MODULO = {
  operacao:     ["CONCENTRACAO"],
  mercado:      ["CONSOLIDACAO", "REDISTRIBUICAO"],
  concorrencia: ["BID", "RENEGOCIACAO"],
};

const ESTILO_CLASSIFICACAO = {
  CRITICO:      { cor: "#C62828", icone: <ErrorOutlineIcon fontSize="small" /> },
  ATENCAO:      { cor: GD.amber, icone: <WarningAmberIcon fontSize="small" /> },
  OPORTUNIDADE: { cor: "#2E7D32", icone: <TrendingUpIcon fontSize="small" /> },
  INFORMATIVO:  { cor: GD.blue, icone: <InfoOutlinedIcon fontSize="small" /> },
};

const TITULO_MODULO = {
  operacao: "Operação", mercado: "Mercado", concorrencia: "Concorrência",
};

function SecaoNarrativa({ titulo, conteudo, cor }) {
  if (!conteudo) return null;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="subtitle2" fontWeight={700} sx={{ color: cor || GD.indigo }}>
        {titulo}
      </Typography>
      <Typography variant="body2" sx={{ whiteSpace: "pre-line", color: "text.secondary" }}>
        {conteudo}
      </Typography>
    </Box>
  );
}

export default function InteligenciaRecomendacao({ modulo }) {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [aberto, setAberto] = useState(false);

  const diagQ = useIaDiagnostico(empresaAtivaId);
  const gerarDiagMut = useGerarDiagnosticoIA(empresaAtivaId);
  const insightsQ = useIaInsights(empresaAtivaId);
  const gerarInsightsMut = useGerarInsights(empresaAtivaId);
  const oportunidadesQ = useIaOportunidades(empresaAtivaId);
  const detectarOportMut = useDetectarOportunidades(empresaAtivaId);

  const diag = diagQ.data ?? null;
  const insights = (insightsQ.data ?? []).filter((i) =>
    (CATEGORIA_INSIGHT_POR_MODULO[modulo] || []).includes(i.categoria)
  );
  const oportunidades = (oportunidadesQ.data ?? []).filter((o) =>
    (TIPO_OPORTUNIDADE_POR_MODULO[modulo] || []).includes(o.tipo)
  );

  const atualizando = gerarDiagMut.isPending || gerarInsightsMut.isPending || detectarOportMut.isPending;
  const carregando = diagQ.isFetching || insightsQ.isFetching || oportunidadesQ.isFetching;

  const atualizar = async () => {
    try {
      await Promise.all([
        gerarDiagMut.mutateAsync(true),
        gerarInsightsMut.mutateAsync(),
        detectarOportMut.mutateAsync(),
      ]);
      fb.sucesso("Inteligência de recomendação atualizada.");
    } catch (e) {
      fb.erro(extrairErro(e));
    }
  };

  if (!empresaAtivaId) return null;
  if (!diag && insights.length === 0 && oportunidades.length === 0 && !carregando) {
    return (
      <Card variant="outlined" sx={{ mt: 3 }}>
        <CardContent sx={{ textAlign: "center", py: 3 }}>
          <AutoAwesomeIcon sx={{ fontSize: 32, color: GD.amber, mb: 1 }} />
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Nenhuma inteligência de recomendação gerada ainda para {TITULO_MODULO[modulo]}.
          </Typography>
          <Button variant="outlined" size="small" onClick={atualizar} disabled={atualizando}>
            Gerar inteligência de recomendação
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="outlined" sx={{ mt: 3 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <AutoAwesomeIcon sx={{ color: GD.indigo }} />
            <Typography variant="subtitle1" fontWeight={700}>Inteligência de recomendação</Typography>
            <Chip label="gerado por IA" size="small" sx={{ bgcolor: `${GD.amber}26`, color: GD.amberDark, fontWeight: 700 }} />
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button size="small" onClick={() => setAberto((v) => !v)} endIcon={aberto ? <ExpandLessIcon /> : <ExpandMoreIcon />}>
              {aberto ? "Recolher" : "Detalhar"}
            </Button>
            <Button size="small" variant="outlined" onClick={atualizar} disabled={atualizando}>
              {atualizando ? "Atualizando..." : "Atualizar"}
            </Button>
          </Stack>
        </Stack>

        {(carregando || atualizando) && <LinearProgress sx={{ mb: 1.5 }} />}

        {diag && (
          <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
            <Chip label={`Score: ${diag.score_logistico}/100`} size="small" sx={{ bgcolor: GD.indigo, color: "#fff", fontWeight: 700 }} />
            <Chip
              icon={<SavingsIcon sx={{ color: "#fff !important" }} fontSize="small" />}
              label={`Economia potencial: ${fmtMoeda(diag.economia_potencial)}/ano`}
              size="small" sx={{ bgcolor: GD.blue, color: "#fff", fontWeight: 700 }}
            />
          </Stack>
        )}

        <Collapse in={aberto} unmountOnExit>
          {diag && (
            <Box sx={{ mb: 2 }}>
              <SecaoNarrativa titulo="Resumo Executivo" conteudo={diag.resumo_executivo} />
              <SecaoNarrativa titulo="Pontos de Atenção" conteudo={diag.pontos_atencao} cor={GD.amber} />
              <SecaoNarrativa titulo="Plano de Ação Sugerido" conteudo={diag.plano_acao} cor={GD.blue} />
            </Box>
          )}

          {insights.length > 0 && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Typography variant="overline" color="text.secondary">Insights</Typography>
              <Grid container spacing={1.5} sx={{ mb: 1 }}>
                {insights.map((ins) => {
                  const est = ESTILO_CLASSIFICACAO[ins.classificacao] || ESTILO_CLASSIFICACAO.INFORMATIVO;
                  return (
                    <Grid item xs={12} md={6} key={ins.id}>
                      <Box sx={{ p: 1.25, borderLeft: `3px solid ${est.cor}`, bgcolor: GD.ivoryDeep, borderRadius: 1 }}>
                        <Stack direction="row" spacing={0.75} alignItems="center" sx={{ color: est.cor, mb: 0.25 }}>
                          {est.icone}
                          <Typography variant="body2" fontWeight={700}>{ins.titulo}</Typography>
                        </Stack>
                        <Typography variant="caption" color="text.secondary">{ins.descricao}</Typography>
                        {ins.impacto_financeiro > 0 && (
                          <Typography variant="caption" display="block" sx={{ color: GD.ok, fontWeight: 700, mt: 0.25 }}>
                            {fmtMoeda(ins.impacto_financeiro)}
                          </Typography>
                        )}
                      </Box>
                    </Grid>
                  );
                })}
              </Grid>
            </>
          )}

          {oportunidades.length > 0 && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Typography variant="overline" color="text.secondary">Oportunidades</Typography>
              <Grid container spacing={1.5}>
                {oportunidades.map((op) => (
                  <Grid item xs={12} md={6} key={op.id}>
                    <Box sx={{ p: 1.25, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                      <Typography variant="body2" fontWeight={700}>{op.titulo}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                        {op.descricao}
                      </Typography>
                      {op.economia_estimada > 0 && (
                        <Typography variant="caption" sx={{ color: "#2E7D32", fontWeight: 700 }}>
                          {fmtMoeda(op.economia_estimada)}/ano
                        </Typography>
                      )}
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
}
