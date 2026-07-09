import { useState } from "react";
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Stack,
  TextField,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  LinearProgress,
} from "@mui/material";
import PaidIcon from "@mui/icons-material/Paid";
import ScaleIcon from "@mui/icons-material/Scale";
import PercentIcon from "@mui/icons-material/Percent";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import GraficosDiagnostico from "../components/GraficosDiagnostico";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useDashboard } from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import {
  fmtMoeda,
  fmtNumero,
  fmtPct,
  fmtRsKg,
  rotuloMacro,
} from "../utils/format";
import { GD } from "../theme";

/**
 * Sparkline (SVG) do Frete Total: tendência dos últimos meses. Sem eixos nem
 * rótulos — apenas a linha e o ponto do mês mais recente. Normaliza os valores
 * ao próprio min/max para dar amplitude visual mesmo com variações pequenas.
 */
function Sparkline({ pontos, cor = GD.blue, altura = 38 }) {
  if (!pontos || pontos.length < 2) return null;
  const W = 220;
  const H = 44;
  const PAD = 4;
  const min = Math.min(...pontos);
  const max = Math.max(...pontos);
  const span = max - min || 1;
  const passo = (W - PAD * 2) / (pontos.length - 1);
  const coords = pontos.map((v, i) => {
    const x = PAD + i * passo;
    const y = PAD + (H - PAD * 2) * (1 - (v - min) / span);
    return [x, y];
  });
  const linha = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [ux, uy] = coords[coords.length - 1];
  return (
    <Box sx={{ mt: 1.25 }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: altura, display: "block" }}>
        <polyline
          points={linha}
          fill="none"
          stroke={cor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx={ux} cy={uy} r="3.5" fill="#fff" stroke={cor} strokeWidth="2" />
      </svg>
    </Box>
  );
}

export default function Dashboard() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();

  // Filtros de data persistidos entre navegações (voltar mantém o período).
  const [tela, , patch] = useTelaEstado("dashboard", { dataInicio: "", dataFim: "" });
  const dataInicio = tela.dataInicio;
  const dataFim = tela.dataFim;
  const setDataInicio = (v) => patch({ dataInicio: v });
  const setDataFim = (v) => patch({ dataFim: v });

  // A consulta só muda ao clicar em "Aplicar" (parâmetros efetivamente aplicados).
  const [aplicado, setAplicado] = useState({
    dataInicio: tela.dataInicio,
    dataFim: tela.dataFim,
  });

  // Dados via React Query: cacheados por (empresa + período), reusados ao voltar.
  const { data, isFetching, error, refetch } = useDashboard(empresaAtivaId, aplicado);
  const diag = data ?? null;
  const carregando = isFetching;
  const erro = error
    ? extrairErro(error, "Não foi possível carregar o diagnóstico.")
    : "";

  const carregar = () => {
    setAplicado({ dataInicio: tela.dataInicio, dataFim: tela.dataFim });
    refetch();
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Dashboard" subtitulo="Diagnóstico de custos logísticos" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Cadastre e selecione uma empresa ativa para visualizar o diagnóstico."
        />
      </Box>
    );
  }

  const nac = diag?.nacional;
  const semDados = diag && nac && nac.qtd_ctes === 0;

  // Série mensal do Frete Total (sparkline). Regra de negócio: só exibe a
  // tendência com ao menos 6 meses de movimentação (evita ruído com poucos pontos).
  const serieFrete = (diag?.evolucao_frete || []).map((e) => e.frete_total);
  const temHistoricoFrete = serieFrete.length >= 6;

  return (
    <Box>
      <PageHeader
        titulo="Dashboard"
        subtitulo={
          empresaAtiva
            ? `Diagnóstico de ${empresaAtiva.nome_fantasia || empresaAtiva.razao_social}`
            : "Diagnóstico de custos logísticos"
        }
        acoes={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
            <TextField
              label="De"
              type="date"
              size="small"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ width: 160 }}
            />
            <TextField
              label="Até"
              type="date"
              size="small"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ width: 160 }}
            />
            <Button variant="contained" onClick={carregar} disabled={carregando}>
              Aplicar
            </Button>
          </Stack>
        }
      />

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {erro}
        </Alert>
      )}

      {semDados && !carregando && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Nenhum CT-e importado no período. Importe documentos para gerar o diagnóstico.
        </Alert>
      )}

      {nac && (
        <>
          {/* Indicadores nacionais (RF011) — 3 cards (redesenho mock 07/2026) */}
          <Grid container spacing={2.5} sx={{ mb: 1 }}>
            {/* Frete total com sparkline de evolução (últimos 6 meses) */}
            <Grid item xs={12} sm={6} md={4}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Typography variant="overline" color="text.secondary" sx={{ lineHeight: 1.3 }}>
                      Frete total
                    </Typography>
                    <Box sx={{ color: GD.indigo, opacity: 0.8 }}>
                      <PaidIcon />
                    </Box>
                  </Stack>
                  <Typography
                    variant="h4"
                    sx={{ color: GD.indigo, fontWeight: 700, mt: 0.5, fontFamily: "'Sora', sans-serif" }}
                  >
                    {fmtMoeda(nac.valor_total_frete)}
                  </Typography>
                  {temHistoricoFrete ? (
                    <>
                      <Sparkline pontos={serieFrete} cor={GD.blue} />
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                        Últimos {serieFrete.length} meses
                      </Typography>
                    </>
                  ) : (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                      {`${nac.qtd_ctes} CT-es`}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="Custo por kg"
                valor={fmtRsKg(nac.frete_rs_kg)}
                legenda={nac.meta_rs_kg ? `Meta: ${fmtRsKg(nac.meta_rs_kg)}` : "Sem meta definida"}
                cor={GD.blue}
                desvio={nac.desvio_rs_kg}
                icone={<ScaleIcon />}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="% Frete s/ mercadoria"
                valor={fmtPct(nac.frete_pct)}
                legenda={nac.meta_pct ? `Meta: ${fmtPct(nac.meta_pct)}` : "Sem meta definida"}
                cor={GD.amberDark}
                desvio={nac.desvio_pct}
                icone={<PercentIcon />}
              />
            </Grid>
            {/* Card "Peso total" removido do mock — desabilitado (apagar depois). */}
            {false && (
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Peso total"
                valor={`${fmtNumero(nac.peso_total, 0)} kg`}
                legenda={`Mercadoria: ${fmtMoeda(nac.valor_total_mercadoria)}`}
                cor={GD.ok}
                icone={<ReceiptLongIcon />}
              />
            </Grid>
            )}
          </Grid>

          {/* Situação dos CT-es e custos (MELHORIAS 3 a 7) — fora do mock, desabilitados (apagar depois). */}
          {false && (
          <Grid container spacing={2.5} sx={{ mb: 1, mt: 0.5 }}>
            {/* MELHORIA 3 — CT-es Ativos */}
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="CT-es Ativos"
                valor={fmtNumero(nac.qtd_ctes_ativos ?? nac.qtd_ctes, 0)}
                legenda={`de ${fmtNumero(nac.qtd_ctes_emitidos ?? nac.qtd_ctes, 0)} emitidos`}
                cor={GD.ok}
                icone={<CheckCircleOutlineIcon />}
              />
            </Grid>
            {/* MELHORIA 4 — CT-es Cancelados */}
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="CT-es Cancelados"
                valor={fmtNumero(nac.qtd_ctes_cancelados ?? 0, 0)}
                legenda={`${fmtPct(nac.pct_cancelados ?? 0)} do total`}
                cor={GD.danger}
                icone={<CancelOutlinedIcon />}
              />
            </Grid>
            {/* MELHORIA 5 — Frete dos CT-es Ativos */}
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Frete dos CT-es Ativos"
                valor={fmtMoeda(nac.valor_total_frete)}
                legenda="Considera apenas CT-es ativos"
                cor={GD.indigo}
                icone={<LocalShippingIcon />}
              />
            </Grid>
            {/* MELHORIA 7 — Custo Médio por Kg */}
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Custo Médio por Kg"
                valor={`${fmtRsKg(nac.custo_medio_kg ?? nac.frete_rs_kg)}`}
                legenda="Frete ativo ÷ peso transportado"
                cor={GD.blue}
                icone={<ScaleIcon />}
              />
            </Grid>
            {/* MELHORIA 6 — Frete / Mercadoria com referência */}
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Typography variant="overline" color="text.secondary" sx={{ lineHeight: 1.3 }}>
                      Frete / Mercadoria
                    </Typography>
                    <Box sx={{ color: GD.amberDark, opacity: 0.8 }}>
                      <PercentIcon />
                    </Box>
                  </Stack>
                  <Typography
                    variant="h4"
                    sx={{ color: GD.amberDark, fontWeight: 700, mt: 0.5, fontFamily: "'Sora', sans-serif" }}
                  >
                    {fmtPct(nac.frete_pct)}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Referência:
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Ideal: {nac.ref_pct_ideal_max != null ? `até ${fmtPct(nac.ref_pct_ideal_max)}` : "—"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Mercado:{" "}
                      {nac.ref_pct_mercado_min != null && nac.ref_pct_mercado_max != null
                        ? `${fmtPct(nac.ref_pct_mercado_min)} a ${fmtPct(nac.ref_pct_mercado_max)}`
                        : "—"}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          )}

          {/* Gráficos do diagnóstico (2 painéis regionais — mock) */}
          <GraficosDiagnostico diag={diag} />

          {/* Tabela "Indicadores regionais" (RF012) — fora do mock, desabilitada (apagar depois). */}
          {false && (
          <Card sx={{ mt: 2.5 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Indicadores regionais
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Macro-região</TableCell>
                      <TableCell align="right">CT-es</TableCell>
                      <TableCell align="right">Frete total</TableCell>
                      <TableCell align="right">Peso (kg)</TableCell>
                      <TableCell align="right">R$/kg</TableCell>
                      <TableCell align="right">Meta R$/kg</TableCell>
                      <TableCell align="right">% Frete</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {diag.regionais.map((r) => {
                      const acima = r.meta_rs_kg && r.frete_rs_kg > r.meta_rs_kg;
                      return (
                        <TableRow key={r.macro_regiao}>
                          <TableCell>{rotuloMacro(r.macro_regiao)}</TableCell>
                          <TableCell align="right">{r.qtd_ctes}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.frete_total)}</TableCell>
                          <TableCell align="right">{fmtNumero(r.peso_total, 0)}</TableCell>
                          <TableCell align="right">
                            <Chip
                              size="small"
                              label={fmtNumero(r.frete_rs_kg, 4)}
                              color={r.meta_rs_kg ? (acima ? "warning" : "success") : "default"}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="right">
                            {r.meta_rs_kg ? fmtNumero(r.meta_rs_kg, 4) : "—"}
                          </TableCell>
                          <TableCell align="right">{fmtPct(r.frete_pct)}</TableCell>
                        </TableRow>
                      );
                    })}
                    {!diag.regionais.length && (
                      <TableRow>
                        <TableCell colSpan={7} align="center" sx={{ color: "text.secondary" }}>
                          Sem dados regionais.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
          )}

          {/* Ranking de transportadoras (RF013) — largura total (mock) */}
          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    Ranking de transportadoras
                  </Typography>
                  <Box sx={{ overflowX: "auto" }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>#</TableCell>
                          <TableCell>Transportadora</TableCell>
                          <TableCell align="right">CT-es</TableCell>
                          <TableCell align="right">R$/kg</TableCell>
                          <TableCell align="right" sx={{ color: GD.blue }}>
                            % de Frete
                          </TableCell>
                          <TableCell align="right">Custo/entrega</TableCell>
                          <TableCell align="right">Frete</TableCell>
                          <TableCell align="right">Participação</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {diag.transportadoras.map((t, i) => (
                          <TableRow key={t.transportadora_id ?? i}>
                            <TableCell>{i + 1}</TableCell>
                            <TableCell>{t.nome}</TableCell>
                            <TableCell align="right">{t.qtd_ctes}</TableCell>
                            <TableCell align="right">{fmtNumero(t.frete_rs_kg, 4)}</TableCell>
                            <TableCell align="right" sx={{ color: GD.blue, fontWeight: 600 }}>
                              {fmtPct(t.frete_pct, 1)}
                            </TableCell>
                            <TableCell align="right">{fmtMoeda(t.custo_medio_entrega)}</TableCell>
                            <TableCell align="right">{fmtMoeda(t.frete_total)}</TableCell>
                            <TableCell align="right">{fmtPct(t.participacao_pct, 1)}</TableCell>
                          </TableRow>
                        ))}
                        {!diag.transportadoras.length && (
                          <TableRow>
                            <TableCell colSpan={8} align="center" sx={{ color: "text.secondary" }}>
                              Sem dados de transportadoras.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            {/* Desempenho de prazo (SLA) — fora do mock, desabilitado (apagar depois). */}
            {false && (
            <Grid item xs={12} md={5}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    Desempenho de prazo (SLA)
                  </Typography>
                  <Box sx={{ overflowX: "auto" }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Região</TableCell>
                          <TableCell align="right">Prazo méd.</TableCell>
                          <TableCell align="right">SLA</TableCell>
                          <TableCell align="right">Meta</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {diag.prazos.map((p) => (
                          <TableRow key={p.macro_regiao}>
                            <TableCell>{rotuloMacro(p.macro_regiao)}</TableCell>
                            <TableCell align="right">
                              {fmtNumero(p.prazo_medio, 1)} d
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                size="small"
                                label={fmtPct(p.sla_pct, 0)}
                                color={p.sla_pct >= 90 ? "success" : p.sla_pct >= 75 ? "warning" : "error"}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {p.prazo_meta ? `${p.prazo_meta} d` : "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                        {!diag.prazos.length && (
                          <TableRow>
                            <TableCell colSpan={4} align="center" sx={{ color: "text.secondary" }}>
                              Sem dados de prazo.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            )}
          </Grid>

          {/* Oportunidades (RF015) */}
          {diag.oportunidades?.length > 0 && (
            <Card sx={{ mt: 2.5, borderColor: GD.amber, borderWidth: 1.5 }}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                  <LightbulbIcon sx={{ color: GD.amberDark }} />
                  <Typography variant="h6">Oportunidades identificadas</Typography>
                </Stack>
                <Divider sx={{ mb: 2 }} />
                <Stack spacing={1.5}>
                  {diag.oportunidades.map((op, i) => (
                    <Stack key={i} direction="row" spacing={1.5} alignItems="flex-start">
                      <Box
                        sx={{
                          mt: 0.4,
                          width: 22,
                          height: 22,
                          borderRadius: "50%",
                          bgcolor: GD.indigo,
                          color: "#fff",
                          display: "grid",
                          placeItems: "center",
                          fontSize: 12,
                          fontWeight: 700,
                          flexShrink: 0,
                        }}
                      >
                        {i + 1}
                      </Box>
                      <Typography variant="body2">{op}</Typography>
                    </Stack>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Notas de rodapé do dashboard (padrão do mock) */}
          <Stack spacing={0.5} sx={{ mt: 2.5, px: 0.5 }}>
            <Stack direction="row" spacing={0.75} alignItems="center">
              <InfoOutlinedIcon sx={{ fontSize: 15, color: "text.disabled" }} />
              <Typography variant="caption" color="text.secondary">
                Métricas calculadas sobre CT-es ativos — eventos de cancelamento excluídos.
              </Typography>
            </Stack>
            <Stack direction="row" spacing={0.75} alignItems="center">
              <InfoOutlinedIcon sx={{ fontSize: 15, color: "text.disabled" }} />
              <Typography variant="caption" color="text.secondary">
                O histórico de Frete Total (sparkline) requer no mínimo 6 meses de movimentação.
              </Typography>
            </Stack>
          </Stack>
        </>
      )}

      {!nac && carregando && (
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
}
