import { Fragment, useEffect, useState, useMemo } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button, Chip,
  LinearProgress, Alert, ToggleButton, ToggleButtonGroup, TextField,
  Table, TableHead, TableRow, TableCell, TableBody, Tab, Tabs,
  MenuItem, IconButton, Collapse,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  PieChart, Pie, Cell, Tooltip as ReTooltip, ResponsiveContainer,
} from "recharts";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { useDlgResumo, useDlgAnalitico, useDlgOutliers, useProcessarDlg } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtPct } from "../utils/format";
import { GD } from "../theme";

const DIMENSOES = [
  { v: "FILIAL", l: "Filial" },
  { v: "ROTA", l: "Rota" },
  { v: "TRANSPORTADORA", l: "Transportadora" },
  { v: "REGIAO", l: "Região" },
  { v: "CLIENTE_FINAL", l: "Cliente" },
];

// v6.7.0 — Dimensão Cliente: chip de causa dominante (RN-76), ao lado do chip
// de Classificação já existente — mesmo sistema de cor, sem paleta nova.
const ROTULO_CAUSA = {
  ADICIONAIS: "📦 Adicionais",
  FRAGMENTACAO: "🔀 Fragmentação",
  AMBAS: "⚠️ Ambas",
  NENHUMA: "Sem causa específica",
};
const COR_CAUSA = {
  ADICIONAIS: GD.warn,
  FRAGMENTACAO: GD.warn,
  AMBAS: GD.danger,
  NENHUMA: GD.slate,
};

// Rankings da dimensão Cliente (PRD §8) — os 5 já existentes primeiro, os 2
// novos ao final. Ordenação aplicada sobre a página carregada.
const RANKINGS_CLIENTE = [
  { v: "frete_total", l: "Maior custo de frete" },
  { v: "pct_frete", l: "Maior % frete" },
  { v: "rs_kg", l: "Maior R$/Kg" },
  { v: "impacto", l: "Maior impacto financeiro potencial" },
  { v: "peso_total", l: "Maior volume movimentado" },
  { v: "adicionais", l: "Maior % de componentes adicionais" },
  { v: "fragmentacao", l: "Maior sinal de fragmentação" },
];
const PAGE_SIZE_CLIENTE = 50;

const CORES_PIZZA_CLIENTE = [
  GD.indigo, GD.blue, "#4F8FC0", GD.ok, GD.amber, GD.warn, GD.danger, "#7E57C2",
];

const COR_CLF = {
  EFICIENTE: GD.ok,
  ATENCAO: GD.warn,
  CRITICO: GD.danger,
  SEM_REF: GD.slate,
};
const ROTULO_CLF = {
  EFICIENTE: "Eficiente",
  ATENCAO: "Atenção",
  CRITICO: "Crítico",
  SEM_REF: "Sem ref.",
};

// Ordem visual dos cards de distribuição (conforme especificação): Crítico → Atenção → Eficiente
const CARDS_CLF = ["CRITICO", "ATENCAO", "EFICIENTE"];

function ChipClf({ valor }) {
  return (
    <Chip
      size="small"
      label={ROTULO_CLF[valor] || valor}
      sx={{
        bgcolor: (COR_CLF[valor] || GD.slate) + "22",
        color: COR_CLF[valor] || GD.slate,
        fontWeight: 700,
      }}
    />
  );
}

function ChipCausa({ causa }) {
  if (!causa) return null;
  const cor = COR_CAUSA[causa] || GD.slate;
  return (
    <Chip
      size="small"
      label={ROTULO_CAUSA[causa] || causa}
      sx={{ bgcolor: cor + "22", color: cor, fontWeight: 700, ml: 0.75 }}
    />
  );
}

/** Camada 2 (v6.7.0) — Cartão de Diagnóstico do Cliente: composição em pizza +
 * métricas de adicionais + fragmentação + causa dominante narrada. Autocontido
 * pensando em reuso futuro no Relatório Executivo HTML (Protótipo A.5). */
function PainelDiagnosticoCliente({ row }) {
  const comp = row.composicao_frete || {};
  const dadosPizza = Object.entries(comp)
    .map(([nome, valor]) => ({ nome, valor: Number(valor) }))
    .filter((d) => d.valor > 0)
    .sort((a, b) => b.valor - a.valor);
  const semComposicao = dadosPizza.length === 0;
  const ranking = row.ranking_componentes || [];
  const ofensores = ranking.slice(0, 2).map(([nome]) => nome).join(" e ");

  const textoCausa = () => {
    if (!row.causa_dominante || row.classificacao === "EFICIENTE") return null;
    if (row.causa_dominante === "NENHUMA") {
      return `Cliente ${row.classificacao === "CRITICO" ? "crítico" : "em atenção"}, ${fmtNumero(Math.abs(row.desvio_pct), 1)}% acima do benchmark — sem causa específica identificada (adicionais ou fragmentação) para este período.`;
    }
    if (row.causa_dominante === "ADICIONAIS") {
      return `Possui R$/kg acima do benchmark principalmente devido à alta incidência de ${ofensores || "componentes adicionais"} (${fmtPct(row.pct_componentes_adicionais || 0, 1)} do frete total).`;
    }
    if (row.causa_dominante === "FRAGMENTACAO") {
      return `Apresenta fragmentação operacional: múltiplos despachos em janela curta (peso médio abaixo do padrão da empresa), aumentando o custo por kg.`;
    }
    return `Combina fragmentação de despachos com alta incidência de ${ofensores || "componentes adicionais"} — ambos elevando o custo de frete acima do benchmark.`;
  };
  const texto = textoCausa();

  return (
    <Box sx={{ p: 2, bgcolor: "action.hover", borderRadius: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          {semComposicao ? (
            <Typography variant="body2" color="text.secondary">
              Sem dado de composição do frete para este cliente.
            </Typography>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={dadosPizza} dataKey="valor" nameKey="nome"
                  cx="50%" cy="50%" outerRadius={70} paddingAngle={1}
                  isAnimationActive={false}
                >
                  {dadosPizza.map((_, i) => (
                    <Cell key={i} fill={CORES_PIZZA_CLIENTE[i % CORES_PIZZA_CLIENTE.length]} stroke="#fff" />
                  ))}
                </Pie>
                <ReTooltip formatter={(v, n) => [fmtMoeda(v), n]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Grid>
        <Grid item xs={12} md={8}>
          <Stack spacing={0.75}>
            {/* PRD §5 — campos financeiros completos da dimensão Cliente, na
                Camada 2 (a Camada 1 preserva as mesmas colunas já usadas
                pelas outras 4 dimensões, CA-1). */}
            <Typography variant="body2" color="text.secondary">
              Valor da Mercadoria: {fmtMoeda(row.mercadoria_total)} · Peso: {fmtNumero(row.peso_total, 0)} kg
              {row.peso_medio != null && ` · Peso Médio: ${fmtNumero(row.peso_medio, 1)} kg`}
              {row.ticket_medio != null && ` · Ticket Médio: ${fmtMoeda(row.ticket_medio)}`}
              {" · Distância Média: indisponível"}
            </Typography>
            <Typography variant="body2">
              <strong>Frete Transp. Principal:</strong>{" "}
              {row.frete_transporte_principal != null ? fmtMoeda(row.frete_transporte_principal) : "—"}
              {"  ·  "}
              <strong>Adicionais:</strong>{" "}
              {row.pct_componentes_adicionais != null
                ? `${fmtMoeda(Math.max(0, row.frete_total - (row.frete_transporte_principal || 0)))} (${fmtPct(row.pct_componentes_adicionais, 1)})`
                : "sem dado de composição"}
            </Typography>
            {ranking.length > 0 && (
              <Typography variant="body2">
                <strong>Componente(s) ofensor(es):</strong>{" "}
                {ranking.slice(0, 2).map(([nome, v]) => `${nome} (${fmtMoeda(v)})`).join(", ")}
              </Typography>
            )}
            {row.sinal_fragmentacao && (
              <Typography variant="body2">
                <strong>Sinal de fragmentação:</strong> múltiplos despachos em janela curta,
                peso médio abaixo do padrão da empresa.
              </Typography>
            )}
            {texto && (
              <Typography variant="body2" sx={{ fontStyle: "italic", mt: 0.5 }}>
                "{texto}"
              </Typography>
            )}
            {row.classificacao === "EFICIENTE" && (
              <Typography variant="body2" color="text.secondary">
                Este cliente está dentro do benchmark; nenhum diagnóstico causal aplicável.
              </Typography>
            )}
            <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mt: 1 }}>
              <InfoOutlinedIcon sx={{ fontSize: 16, color: "text.secondary" }} />
              <Typography variant="caption" color="text.secondary">
                CT-e importados antes da granularização de componentes (v6.7.0) podem ter
                TDE/TDA/Estadia agrupados em "Outros".
              </Typography>
            </Stack>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

/** Card de classificação: quantidade + % sobre o total da dimensão + barra horizontal. */
function CardClassificacao({ clf, qtd, total }) {
  const cor = COR_CLF[clf] || GD.slate;
  const pct = total > 0 ? (qtd / total) * 100 : 0;
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.25 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: cor }} />
          <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
            {ROTULO_CLF[clf]}
          </Typography>
        </Stack>
        <Typography
          sx={{ fontSize: 34, fontWeight: 700, lineHeight: 1, color: cor,
                fontFamily: "'Sora', sans-serif" }}
        >
          {fmtNumero(qtd, 0)}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
          {fmtNumero(pct, 1)}% do total
        </Typography>
        <Box sx={{ height: 4, bgcolor: cor + "22", borderRadius: 1, mt: 1.75, overflow: "hidden" }}>
          <Box sx={{ width: `${pct}%`, minWidth: pct > 0 ? 3 : 0, height: "100%", bgcolor: cor }} />
        </Box>
      </CardContent>
    </Card>
  );
}

export default function DiagnosticoDLG() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  // Estado de tela persistente (dimensão + modo de visualização + período)
  const [tela, , patchTela] = useTelaEstado("dlg", {
    dimensao: "FILIAL",
    modo: "consolidado",   // abre em Consolidado por padrão
    classifFiltro: "TODAS", // filtro de classificação da análise por dimensão
    dataInicio: "",
    dataFim: "",
  });
  const { dimensao, modo, classifFiltro, dataInicio, dataFim } = tela;
  const setDataInicio = (v) => patchTela({ dataInicio: v });
  const setDataFim = (v) => patchTela({ dataFim: v });

  const [aba, setAba] = useState(0);
  const processarMut = useProcessarDlg(empresaAtivaId);
  const processando = processarMut.isPending;

  // v6.7.0 — dimensão Cliente: expansão de linha (Camada 2), ranking próprio
  // e paginação server-side (CA-16 — Cliente é a dimensão de maior
  // cardinalidade potencial das 5).
  const ehCliente = dimensao === "CLIENTE_FINAL";
  const [expandidos, setExpandidos] = useState(() => new Set());
  const [rankingCliente, setRankingCliente] = useState("frete_total");
  const [paginaCliente, setPaginaCliente] = useState(1);

  useEffect(() => { setPaginaCliente(1); setExpandidos(new Set()); }, [dimensao, modo, classifFiltro, dataInicio, dataFim]);

  // O intervalo de datas filtra a visualização (KPIs, cards, tabela e outliers).
  const periodo = {};
  if (dataInicio) periodo.data_inicio = dataInicio;
  if (dataFim) periodo.data_fim = dataFim;
  const paramsAnalitico = { dimensao, modo, ...periodo };
  if (ehCliente) {
    // CA-16: filtro de classificação e paginação aplicados server-side
    // para Cliente — evita baixar a listagem inteira de destinatários.
    paramsAnalitico.page = paginaCliente;
    paramsAnalitico.page_size = PAGE_SIZE_CLIENTE;
    if (classifFiltro !== "TODAS") paramsAnalitico.classificacao = classifFiltro;
  }

  const { data: resumoBruto, isFetching: carregandoResumo, error: erroResumo } = useDlgResumo(empresaAtivaId, periodo);
  const { data: analitico = [], isFetching: carregandoAnalitico, error: erroAnalitico } = useDlgAnalitico(empresaAtivaId, paramsAnalitico);
  const { data: outliers = [], isFetching: carregandoOutliers, error: erroOutliers } = useDlgOutliers(empresaAtivaId, periodo);
  const resumo = resumoBruto && Object.keys(resumoBruto).length ? resumoBruto : null;
  const carregando = carregandoResumo || carregandoAnalitico || carregandoOutliers;
  const erroCarregamento = erroResumo || erroAnalitico || erroOutliers;
  if (erroCarregamento) erroToast(extrairErro(erroCarregamento));

  const processar = async () => {
    if (!empresaAtivaId) return;
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      const r = await processarMut.mutateAsync(params);
      if (r.status === "sem_dados") {
        erroToast("Nenhum CT-e encontrado no período para processar.");
      } else {
        sucesso(`Diagnóstico processado: ${r.analiticos} análises, ${r.outliers} outliers em ${r.periodos?.length || 0} período(s).`);
      }
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const consolidado = modo === "consolidado";

  // Distribuição de eficiência dos cards: calculada sobre o total de registros
  // da dimensão exibida, no modo atual (entidades no consolidado; linhas
  // entidade×mês no mensal). Sempre coerente com a tabela abaixo.
  // Para Cliente (paginado — CA-16), a tabela só carrega 1 página por vez;
  // a distribuição usa o total real da dimensão vindo de `resumo.por_dimensao`
  // (já calculado sobre todos os clientes do período, sem paginação).
  const distDimensao = useMemo(() => {
    if (ehCliente && resumo?.por_dimensao?.CLIENTE_FINAL) {
      const d = resumo.por_dimensao.CLIENTE_FINAL;
      return { CRITICO: d.CRITICO || 0, ATENCAO: d.ATENCAO || 0, EFICIENTE: d.EFICIENTE || 0, SEM_REF: d.SEM_REF || 0 };
    }
    const cont = { CRITICO: 0, ATENCAO: 0, EFICIENTE: 0, SEM_REF: 0 };
    for (const r of analitico) cont[r.classificacao] = (cont[r.classificacao] || 0) + 1;
    return cont;
  }, [analitico, ehCliente, resumo]);
  const totalDimensao = ehCliente && resumo?.por_dimensao?.CLIENTE_FINAL
    ? Object.values(resumo.por_dimensao.CLIENTE_FINAL).reduce((a, b) => a + b, 0)
    : analitico.length;

  // Item 3: filtro de classificação — a TABELA de análise por dimensão passa a
  // exibir apenas os registros da classificação escolhida. Os cards de
  // distribuição continuam sobre o total da dimensão (não são filtrados).
  // Para Cliente, o filtro já é aplicado server-side (CA-16) — `analitico`
  // já vem filtrado, não reaplica no cliente.
  const linhasTabelaBase = useMemo(() => {
    if (ehCliente) return analitico;
    if (classifFiltro === "TODAS") return analitico;
    return analitico.filter((r) => r.classificacao === classifFiltro);
  }, [analitico, classifFiltro, ehCliente]);

  // Ranking da dimensão Cliente (PRD §8) — ordenação client-side sobre a
  // página carregada. "Maior sinal de fragmentação" filtra implicitamente
  // (PRD §8/Protótipo C.4).
  const linhasTabela = useMemo(() => {
    if (!ehCliente) return linhasTabelaBase;
    const linhas = [...linhasTabelaBase];
    switch (rankingCliente) {
      case "pct_frete": return linhas.sort((a, b) => (b.pct_frete || 0) - (a.pct_frete || 0));
      case "rs_kg": return linhas.sort((a, b) => (b.rs_kg || 0) - (a.rs_kg || 0));
      case "impacto": return linhas.sort((a, b) => (b.impacto_financeiro_potencial || 0) - (a.impacto_financeiro_potencial || 0));
      case "peso_total": return linhas.sort((a, b) => (b.peso_total || 0) - (a.peso_total || 0));
      case "adicionais": return linhas.sort((a, b) => (b.pct_componentes_adicionais || 0) - (a.pct_componentes_adicionais || 0));
      case "fragmentacao": return linhas
        .filter((r) => r.sinal_fragmentacao)
        .sort((a, b) => (b.impacto_financeiro_potencial || 0) - (a.impacto_financeiro_potencial || 0));
      default: return linhas.sort((a, b) => (b.frete_total || 0) - (a.frete_total || 0));
    }
  }, [linhasTabelaBase, ehCliente, rankingCliente]);

  const rotuloDim = DIMENSOES.find((d) => d.v === dimensao)?.l || dimensao;

  return (
    <Box>
      <PageHeader
        titulo="Diagnóstico Logístico"
        subtitulo="Eficiência por filial, rota, transportadora e região — com detecção de outliers"
      />

      {/* Barra de processamento (layout alinhado ao padrão do Dashboard) */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
            <TextField
              label="Início" type="date" size="small" value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)} InputLabelProps={{ shrink: true }}
              sx={{ width: { xs: "100%", sm: 180 } }}
            />
            <TextField
              label="Fim" type="date" size="small" value={dataFim}
              onChange={(e) => setDataFim(e.target.value)} InputLabelProps={{ shrink: true }}
              sx={{ width: { xs: "100%", sm: 180 } }}
            />
            <Button
              variant="contained" startIcon={<PlayArrowIcon />}
              onClick={processar} disabled={processando || !empresaAtivaId}
              sx={{ whiteSpace: "nowrap", width: { xs: "100%", sm: "auto" } }}
            >
              {processando ? "Processando…" : "Processar diagnóstico"}
            </Button>
          </Stack>
          {/* Rodapé discreto (item 6) */}
          <Typography
            variant="caption" color="text.secondary"
            sx={{ display: "block", textAlign: "left", mt: 1.25 }}
          >
            Reprocessamento idempotente — sem duplicar dados.
          </Typography>
        </CardContent>
      </Card>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {!resumo && !carregando && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Nenhum diagnóstico processado ainda. Clique em <strong>Processar diagnóstico</strong> para
          gerar as análises a partir dos CT-e importados.
        </Alert>
      )}

      {resumo && (
        <>
          {/* ── KPIs (independentes do modo) ─────────────────────────────── */}
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="CT-e analisados" valor={fmtNumero(resumo.total_ctes, 0)} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Frete total" valor={fmtMoeda(resumo.frete_total)} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="R$/kg médio" valor={`R$ ${fmtNumero(resumo.rs_kg_medio, 4)}`} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="% Frete / merc. médio"
                valor={`${fmtNumero(resumo.pct_frete_merc_medio, 2)}%`}
                cor={GD.blue}
                legenda="Base: CT-e com valor de mercadoria"
              />
            </Grid>
          </Grid>

          {/* ── Controles: dimensão + classificação (esquerda) | modo (direita) ──
               Layout aprovado no mock: uma única linha. O filtro de Classificação
               usa o MESMO componente do filtro "Prioridade" (tela Recomendações).
               Os botões de dimensão e modo têm largura mínima uniforme para
               ficarem do tamanho do botão "Consolidado". */}
          <Stack
            direction={{ xs: "column", md: "row" }} spacing={1.5}
            justifyContent="space-between" alignItems={{ md: "center" }} sx={{ mb: 1.5 }}
          >
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} flexWrap="wrap" useFlexGap>
              <ToggleButtonGroup
                size="small" exclusive value={dimensao}
                onChange={(_, v) => v && patchTela({ dimensao: v })}
                sx={{ "& .MuiToggleButton-root": { height: 40, minWidth: 116 } }}
              >
                {DIMENSOES.map((d) => (
                  <ToggleButton key={d.v} value={d.v}>{d.l}</ToggleButton>
                ))}
              </ToggleButtonGroup>

              <TextField
                select size="small" label="Classificação"
                value={classifFiltro}
                onChange={(e) => patchTela({ classifFiltro: e.target.value })}
                sx={{ width: 200 }}
              >
                <MenuItem value="TODAS">Todas</MenuItem>
                <MenuItem value="CRITICO">🔴 Crítico</MenuItem>
                <MenuItem value="ATENCAO">🟠 Atenção</MenuItem>
                <MenuItem value="EFICIENTE">🟢 Eficiente</MenuItem>
                <MenuItem value="SEM_REF">⚪ Sem ref.</MenuItem>
              </TextField>

              {/* v6.7.0 — ranking próprio da dimensão Cliente (PRD §8/C.4) */}
              {ehCliente && (
                <TextField
                  select size="small" label="Ordenar por"
                  value={rankingCliente}
                  onChange={(e) => setRankingCliente(e.target.value)}
                  sx={{ width: 260 }}
                >
                  {RANKINGS_CLIENTE.map((r) => (
                    <MenuItem key={r.v} value={r.v}>{r.l}</MenuItem>
                  ))}
                </TextField>
              )}
            </Stack>

            <ToggleButtonGroup
              size="small" exclusive value={modo}
              onChange={(_, v) => v && patchTela({ modo: v })}
              sx={{ "& .MuiToggleButton-root": { height: 40, minWidth: 116 } }}
            >
              <ToggleButton value="consolidado">Consolidado</ToggleButton>
              <ToggleButton value="mensal">Mês</ToggleButton>
            </ToggleButtonGroup>
          </Stack>

          {/* ── Distribuição de eficiência (3 cards) ─────────────────────── */}
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
            Distribuição de eficiência — {rotuloDim}
            <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              ({fmtNumero(totalDimensao, 0)} {consolidado ? "registros" : "registros mensais"})
            </Typography>
          </Typography>
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            {CARDS_CLF.map((clf) => (
              <Grid item xs={12} sm={4} key={clf}>
                <CardClassificacao clf={clf} qtd={distDimensao[clf] || 0} total={totalDimensao} />
              </Grid>
            ))}
          </Grid>

          {/* ── Abas: Análise por dimensão | Outliers ────────────────────── */}
          <Card>
            <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}>
              <Tab label="Análise por dimensão" />
              <Tab label={`Outliers (${outliers.length})`} icon={<WarningAmberIcon fontSize="small" />} iconPosition="start" />
            </Tabs>
            <CardContent>
              {aba === 0 && (
                analitico.length === 0 ? (
                  <VazioEstado mensagem="Sem dados para esta dimensão" />
                ) : (
                  <>
                    {classifFiltro !== "TODAS" && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                        Filtro de classificação: {ROTULO_CLF[classifFiltro]} — {fmtNumero(linhasTabela.length, 0)} de {fmtNumero(analitico.length, 0)} registros.
                      </Typography>
                    )}
                    {ehCliente && rankingCliente === "fragmentacao" && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                        Mostrando apenas clientes com sinal de fragmentação ativo, ordenados por impacto financeiro potencial.
                      </Typography>
                    )}
                    {linhasTabela.length === 0 ? (
                      <VazioEstado mensagem={`Nenhum registro classificado como "${ROTULO_CLF[classifFiltro]}" nesta dimensão`} />
                    ) : (
                    <Table size="small">
                    <TableHead>
                      <TableRow>
                        {ehCliente && <TableCell padding="checkbox" />}
                        <TableCell>{rotuloDim}</TableCell>
                        {!consolidado && <TableCell>Mês</TableCell>}
                        <TableCell align="right">CT-e</TableCell>
                        <TableCell align="right">R$/kg</TableCell>
                        <TableCell align="right">% Frete</TableCell>
                        <TableCell align="right">Custo/entrega</TableCell>
                        <TableCell align="right">Frete total</TableCell>
                        <TableCell align="right">Desvio</TableCell>
                        <TableCell align="center">Classificação</TableCell>
                        {ehCliente && <TableCell align="right">Impacto potencial</TableCell>}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {linhasTabela.map((r, i) => {
                        const chaveLinha = consolidado ? r.chave : (r.id || i);
                        const aberto = expandidos.has(chaveLinha);
                        const alternarExpansao = () => {
                          setExpandidos((prev) => {
                            const novo = new Set(prev);
                            novo.has(chaveLinha) ? novo.delete(chaveLinha) : novo.add(chaveLinha);
                            return novo;
                          });
                        };
                        return (
                        <Fragment key={chaveLinha}>
                        <TableRow
                          hover
                          onClick={ehCliente ? alternarExpansao : undefined}
                          sx={ehCliente ? { cursor: "pointer" } : undefined}
                        >
                          {ehCliente && (
                            <TableCell padding="checkbox">
                              <IconButton size="small" onClick={(e) => { e.stopPropagation(); alternarExpansao(); }}>
                                {aberto ? <KeyboardArrowDownIcon fontSize="small" /> : <KeyboardArrowRightIcon fontSize="small" />}
                              </IconButton>
                            </TableCell>
                          )}
                          <TableCell sx={{ fontWeight: 600 }}>{r.chave_label}</TableCell>
                          {!consolidado && <TableCell>{r.periodo_ref}</TableCell>}
                          <TableCell align="right">{r.qtd_ctes}</TableCell>
                          <TableCell align="right">R$ {fmtNumero(r.rs_kg, 4)}</TableCell>
                          <TableCell align="right">{fmtNumero(r.pct_frete, 2)}%</TableCell>
                          <TableCell align="right">{fmtMoeda(r.custo_medio_entrega)}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.frete_total)}</TableCell>
                          <TableCell align="right" sx={{ color: r.desvio_pct > 0 ? GD.danger : GD.ok }}>
                            {r.classificacao === "SEM_REF" ? "—" : `${r.desvio_pct > 0 ? "+" : ""}${fmtNumero(r.desvio_pct, 1)}%`}
                          </TableCell>
                          <TableCell align="center">
                            <ChipClf valor={r.classificacao} />
                            {ehCliente && <ChipCausa causa={r.causa_dominante} />}
                          </TableCell>
                          {ehCliente && (
                            <TableCell align="right">
                              {r.impacto_financeiro_potencial ? fmtMoeda(r.impacto_financeiro_potencial) : "—"}
                            </TableCell>
                          )}
                        </TableRow>
                        {ehCliente && (
                          <TableRow>
                            <TableCell colSpan={consolidado ? 10 : 11} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
                              <Collapse in={aberto} timeout="auto" unmountOnExit>
                                <Box sx={{ py: 1.5 }}>
                                  <PainelDiagnosticoCliente row={r} />
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        )}
                        </Fragment>
                        );
                      })}
                    </TableBody>
                    </Table>
                    )}
                    {ehCliente && (
                      <Stack direction="row" alignItems="center" justifyContent="center" spacing={1} sx={{ mt: 2 }}>
                        <IconButton size="small" disabled={paginaCliente <= 1} onClick={() => setPaginaCliente((p) => Math.max(1, p - 1))}>
                          <ChevronLeftIcon />
                        </IconButton>
                        <Typography variant="body2" color="text.secondary">
                          Página {paginaCliente} · {fmtNumero(linhasTabela.length, 0)} cliente(s) nesta página
                        </Typography>
                        <IconButton size="small" disabled={linhasTabela.length < PAGE_SIZE_CLIENTE} onClick={() => setPaginaCliente((p) => p + 1)}>
                          <ChevronRightIcon />
                        </IconButton>
                      </Stack>
                    )}
                  </>
                )
              )}

              {aba === 1 && (
                outliers.length === 0 ? (
                  <VazioEstado mensagem="Nenhum outlier detectado" descricao="Registros fora do padrão (R$/kg acima de média+2σ ou % frete acima do limite) aparecem aqui." />
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Período</TableCell>
                        <TableCell>Tipo</TableCell>
                        <TableCell align="right">Valor real</TableCell>
                        <TableCell align="right">Limite</TableCell>
                        <TableCell align="right">Desvio</TableCell>
                        <TableCell align="right">CT-e #</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {outliers.map((o) => (
                        <TableRow key={o.id} hover>
                          <TableCell>{o.periodo_ref}</TableCell>
                          <TableCell>
                            <Chip size="small" variant="outlined" color="warning"
                              label={o.tipo_outlier === "RS_KG_2DP" ? "R$/kg > média+2σ" : o.tipo_outlier === "PCT_FRETE" ? "% Frete > limite" : o.tipo_outlier} />
                          </TableCell>
                          <TableCell align="right">{fmtNumero(o.valor_real, 4)}</TableCell>
                          <TableCell align="right">{fmtNumero(o.valor_limite, 4)}</TableCell>
                          <TableCell align="right" sx={{ color: GD.danger, fontWeight: 700 }}>
                            +{fmtNumero(o.desvio_pct, 1)}%
                          </TableCell>
                          <TableCell align="right">{o.cte_id}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
