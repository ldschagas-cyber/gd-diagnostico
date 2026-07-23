import { useMemo, useState } from "react";
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
  TableSortLabel,
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
import FactCheckIcon from "@mui/icons-material/FactCheck";
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

// ---- Ranking de transportadoras: campo de ordenação (v6.11) ----
const OPCOES_ORDENACAO_RANKING = [
  { campo: "frete_total", rotulo: "Frete", tipo: "numero" },
  { campo: "frete_rs_kg", rotulo: "R$/kg", tipo: "numero" },
  { campo: "frete_pct", rotulo: "% de Frete", tipo: "numero" },
  { campo: "custo_medio_entrega", rotulo: "Custo/entrega", tipo: "numero" },
  { campo: "participacao_pct", rotulo: "Participação", tipo: "numero" },
  { campo: "qtd_ctes", rotulo: "CT-es", tipo: "numero" },
  { campo: "nome", rotulo: "Transportadora", tipo: "texto" },
];
// Direção padrão ao trocar de campo: texto começa A→Z, números começam do
// maior para o menor (é um ranking — o topo é o mais relevante).
const direcaoPadraoRanking = (campo) =>
  OPCOES_ORDENACAO_RANKING.find((o) => o.campo === campo)?.tipo === "texto" ? "asc" : "desc";

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

  // Ordenação do Ranking de transportadoras — client-side, a lista completa
  // já vem em diag.transportadoras (sem paginação/servidor envolvido).
  const [ordenacaoRanking, setOrdenacaoRanking] = useState({
    campo: "frete_total",
    direcao: "desc",
  });
  const ordenarPorColuna = (campo) =>
    setOrdenacaoRanking((s) =>
      s.campo === campo
        ? { campo, direcao: s.direcao === "asc" ? "desc" : "asc" }
        : { campo, direcao: direcaoPadraoRanking(campo) }
    );

  const transportadorasOrdenadas = useMemo(() => {
    const lista = diag?.transportadoras || [];
    const { campo, direcao } = ordenacaoRanking;
    const ehTexto = campo === "nome";
    return [...lista].sort((a, b) => {
      const cmp = ehTexto
        ? String(a[campo] || "").localeCompare(String(b[campo] || ""), "pt-BR")
        : (a[campo] || 0) - (b[campo] || 0);
      return direcao === "asc" ? cmp : -cmp;
    });
  }, [diag?.transportadoras, ordenacaoRanking]);

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Diagnóstico Logístico" subtitulo="Diagnóstico de custos logísticos" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Cadastre e selecione uma empresa ativa para visualizar o diagnóstico."
        />
      </Box>
    );
  }

  const nac = diag?.nacional;
  const semDados = diag && nac && nac.qtd_ctes === 0;

  return (
    <Box>
      <PageHeader
        titulo="Diagnóstico Logístico"
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
          {/* Indicadores nacionais (RF011) — ordem MELHORIA v6.10 (revisão 3):
              Linha 1 — CT-e Analisados, Valor de Mercadoria Transportada,
              Peso Transportado. Linha 2 — Total de Frete, Custo por kg,
              % Frete/Mercadoria — 6 cards no mesmo padrão StatCard, sem
              sparkline (a evolução mensal já tem gráfico dedicado logo
              abaixo) nem velocímetro (revertido a pedido). */}
          <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="CT-e Analisados"
                valor={fmtNumero(nac.qtd_ctes, 0)}
                legenda="CT-es ativos no período"
                cor={GD.indigo}
                icone={<FactCheckIcon />}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="Valor de Mercadoria Transportada"
                valor={fmtMoeda(nac.valor_total_mercadoria)}
                legenda={`${fmtNumero(nac.qtd_ctes, 0)} CT-es`}
                cor={GD.ok}
                icone={<ReceiptLongIcon />}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="Peso Transportado"
                valor={`${fmtNumero(nac.peso_total, 0)} kg`}
                legenda={fmtRsKg(nac.frete_rs_kg)}
                cor={GD.blueDark}
                icone={<ScaleIcon />}
              />
            </Grid>
          </Grid>

          <Grid container spacing={2.5} sx={{ mb: 1 }} alignItems="stretch">
            {/* Total de Frete — a evolução mensal já tem gráfico dedicado
                logo abaixo ("Evolução do Valor de Frete"); a sparkline foi
                removida daqui por ser a mesma série duplicada sem rótulo. */}
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                rotulo="Total de Frete"
                valor={fmtMoeda(nac.valor_total_frete)}
                legenda={`${fmtNumero(nac.qtd_ctes, 0)} CT-es`}
                cor={GD.indigo}
                icone={<PaidIcon />}
              />
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
                rotulo="% Frete / Mercadoria"
                valor={fmtPct(nac.frete_pct)}
                legenda={nac.meta_pct ? `Meta: ${fmtPct(nac.meta_pct)}` : "Sem meta definida"}
                cor={GD.amberDark}
                desvio={nac.desvio_pct}
                icone={<PercentIcon />}
              />
            </Grid>
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
                              label={fmtNumero(r.frete_rs_kg, 2)}
                              color={r.meta_rs_kg ? (acima ? "warning" : "success") : "default"}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="right">
                            {r.meta_rs_kg ? fmtNumero(r.meta_rs_kg, 2) : "—"}
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
                          <TableCell>
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "nome"}
                              direction={ordenacaoRanking.campo === "nome" ? ordenacaoRanking.direcao : "asc"}
                              onClick={() => ordenarPorColuna("nome")}
                            >
                              Transportadora
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right">
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "qtd_ctes"}
                              direction={ordenacaoRanking.campo === "qtd_ctes" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("qtd_ctes")}
                            >
                              CTe
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right">
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "frete_rs_kg"}
                              direction={ordenacaoRanking.campo === "frete_rs_kg" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("frete_rs_kg")}
                            >
                              R$/kg
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right" sx={{ color: GD.blue, whiteSpace: "nowrap" }}>
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "frete_pct"}
                              direction={ordenacaoRanking.campo === "frete_pct" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("frete_pct")}
                              sx={{ color: "inherit", "&.Mui-active": { color: GD.blue } }}
                            >
                              % de Frete
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right">
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "custo_medio_entrega"}
                              direction={ordenacaoRanking.campo === "custo_medio_entrega" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("custo_medio_entrega")}
                            >
                              Custo/entrega
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right">
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "frete_total"}
                              direction={ordenacaoRanking.campo === "frete_total" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("frete_total")}
                            >
                              Frete
                            </TableSortLabel>
                          </TableCell>
                          <TableCell align="right">
                            <TableSortLabel
                              active={ordenacaoRanking.campo === "participacao_pct"}
                              direction={ordenacaoRanking.campo === "participacao_pct" ? ordenacaoRanking.direcao : "desc"}
                              onClick={() => ordenarPorColuna("participacao_pct")}
                            >
                              Participação
                            </TableSortLabel>
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {transportadorasOrdenadas.map((t, i) => (
                          <TableRow key={t.transportadora_id ?? i}>
                            <TableCell>{t.nome}</TableCell>
                            <TableCell align="right">{t.qtd_ctes}</TableCell>
                            <TableCell align="right">{fmtNumero(t.frete_rs_kg, 2)}</TableCell>
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
                            <TableCell colSpan={7} align="center" sx={{ color: "text.secondary" }}>
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
