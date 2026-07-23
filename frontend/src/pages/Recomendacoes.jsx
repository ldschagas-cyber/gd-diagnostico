import { useMemo, useState } from "react";
import { useTelaEstado } from "../hooks/useTelaEstado";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid, MenuItem, TextField, Divider, Tooltip,
  ToggleButton, ToggleButtonGroup, IconButton, Collapse, InputAdornment,
} from "@mui/material";
import RecommendIcon from "@mui/icons-material/Recommend";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import SearchIcon from "@mui/icons-material/Search";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import LegendaBenchmark from "../components/LegendaBenchmark";
import InteligenciaRecomendacao from "../components/InteligenciaRecomendacao";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import {
  useRecomendacoes,
  useRecomendacoesResumo,
  useMutacoesRecomendacao,
} from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda } from "../utils/format";
import { GD } from "../theme";

// Prioridade → cor + emoji (conforme especificação da MELHORIA 8).
const PRIORIDADE = {
  CRITICA: { rotulo: "Crítica", cor: GD.danger, emoji: "🔴" },
  ALTA:    { rotulo: "Alta",    cor: GD.warn,   emoji: "🟠" },
  MEDIA:   { rotulo: "Média",   cor: GD.amber,  emoji: "🟡" },
  BAIXA:   { rotulo: "Baixa",   cor: GD.ok,     emoji: "🟢" },
};
const ORDEM_PRIORIDADE = ["CRITICA", "ALTA", "MEDIA", "BAIXA"];

const STATUS = {
  ABERTA:        "Aberta",
  EM_ANDAMENTO:  "Em andamento",
  CONCLUIDA:     "Concluída",
  DESCARTADA:    "Descartada",
};
const STATUS_COR = {
  ABERTA:       { bg: "transparent", cor: GD.slate },
  EM_ANDAMENTO: { bg: `${GD.warn}1F`, cor: GD.warn },
  CONCLUIDA:    { bg: `${GD.ok}1F`,   cor: GD.ok },
  DESCARTADA:   { bg: "transparent", cor: GD.slate },
};

// Central única de recomendações (antes só "Operação" — o bloco de IA
// "Mercado" vivia duplicado dentro de Potencial de Economia). Mapa
// frontend-only (o RecomendacoesUseCase não tem conceito de módulo) — só
// classifica visualmente, nunca esconde uma linha; indicador não mapeado
// cai no fallback "Outros".
const MODULO_POR_INDICADOR = {
  CUSTO_KG: "mercado", PCT_FRETE: "mercado", REGIAO: "mercado", CONCENTRACAO: "mercado",
  CANCELAMENTOS: "operacao",
  DLG_ROTA: "operacao", DLG_SEM_REF: "operacao",
  DLG_CLIENTE_CONCENTRACAO: "operacao", DLG_CLIENTE_CRITICO: "operacao", DLG_CLIENTE_SEM_REF: "operacao",
};
const MODULO_BADGE = {
  mercado: { rotulo: "Mercado", cor: GD.blue },
  operacao: { rotulo: "Operação", cor: GD.indigo },
  outros: { rotulo: "Outros", cor: GD.slate },
};
function moduloDoIndicador(indicador) {
  return MODULO_POR_INDICADOR[indicador] || "outros";
}

function RecomendacaoRow({ r, expandido, onToggleExpandir, onMudarStatus }) {
  const meta = PRIORIDADE[r.prioridade] || { rotulo: r.prioridade, cor: GD.slate, emoji: "" };
  const m = MODULO_BADGE[moduloDoIndicador(r.indicador)];
  const statusCor = STATUS_COR[r.status] || STATUS_COR.ABERTA;
  const descartada = r.status === "DESCARTADA";

  return (
    <Card
      variant="outlined"
      sx={{ mb: 1, borderLeft: `4px solid ${meta.cor}`, opacity: descartada ? 0.65 : 1 }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, p: 1.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
            <Typography
              variant="body2"
              fontWeight={700}
              sx={{ textDecoration: descartada ? "line-through" : "none", color: descartada ? "text.secondary" : "text.primary" }}
            >
              {r.titulo}
            </Typography>
            <Chip size="small" variant="outlined" label={m.rotulo} sx={{ color: m.cor, borderColor: m.cor, height: 20 }} />
            {r.origem === "IA" && (
              <Tooltip title="Gerada por IA">
                <Chip size="small" label="IA" sx={{ bgcolor: `${GD.indigo}1F`, color: GD.indigo, height: 20 }} />
              </Tooltip>
            )}
          </Stack>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
            {r.descricao}
          </Typography>
          {r.impacto && (
            <Typography variant="caption" display="block" sx={{ color: GD.blue, mt: 0.25 }}>
              {r.impacto}
            </Typography>
          )}
          {r.dados?.acao_recomendada && (
            <Typography variant="caption" display="block" sx={{ color: GD.ok, mt: 0.25 }}>
              <strong>O que fazer:</strong> {r.dados.acao_recomendada}
            </Typography>
          )}
        </Box>

        <Box sx={{ textAlign: "right", minWidth: 130, flexShrink: 0 }}>
          {r.economia_estimada > 0 ? (
            <>
              <Typography variant="body2" fontWeight={700} sx={{ color: GD.ok }}>
                {fmtMoeda(r.economia_estimada)}
              </Typography>
              <Typography variant="caption" color="text.secondary">economia est.</Typography>
            </>
          ) : (
            <Typography variant="caption" color="text.secondary">sem ganho direto</Typography>
          )}
        </Box>

        <TextField
          select size="small" fullWidth={false} value={r.status}
          onChange={(e) => onMudarStatus(r, e.target.value)}
          sx={{
            width: 150, flexShrink: 0,
            "& .MuiOutlinedInput-root": { bgcolor: statusCor.bg, color: statusCor.cor, fontWeight: 700, fontSize: 13 },
          }}
        >
          {Object.keys(STATUS).map((s) => (
            <MenuItem key={s} value={s}>{STATUS[s]}</MenuItem>
          ))}
        </TextField>

        <IconButton
          size="small"
          onClick={() => onToggleExpandir(r.id)}
          aria-label={expandido ? "Ocultar detalhe" : "Ver detalhe"}
          sx={{ transform: expandido ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}
        >
          <ExpandMoreIcon fontSize="small" />
        </IconButton>
      </Box>

      <Collapse in={expandido}>
        <Divider />
        <Stack direction="row" spacing={4} rowGap={1} flexWrap="wrap" sx={{ p: 1.5, pl: 4 }}>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>Indicador</Typography>
            <Chip size="small" variant="outlined" label={r.indicador} sx={{ fontFamily: "monospace" }} />
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>Origem</Typography>
            <Typography variant="body2">{r.origem === "IA" ? "Gerada por IA" : "Regra determinística"}</Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>Encontrado</Typography>
            <Typography variant="body2">{r.valor_encontrado || "—"}</Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>Recomendado</Typography>
            <Typography variant="body2">{r.valor_recomendado || "—"}</Typography>
          </Box>
        </Stack>
      </Collapse>
    </Card>
  );
}

export default function Recomendacoes() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();

  // Filtros + módulo do bloco de IA, persistidos entre navegações.
  const [tela, , patch] = useTelaEstado("recomendacoes", {
    prioridadesOff: [], moduloFiltro: "", busca: "", moduloIa: "operacao",
  });
  const { prioridadesOff, moduloFiltro, busca, moduloIa } = tela;
  const setModuloIa = (v) => patch({ moduloIa: v });
  const [expandidos, setExpandidos] = useState({});
  const toggleExpandir = (id) => setExpandidos((prev) => ({ ...prev, [id]: !prev[id] }));

  const listaQ = useRecomendacoes(empresaAtivaId);
  const resumoQ = useRecomendacoesResumo(empresaAtivaId);
  const mut = useMutacoesRecomendacao(empresaAtivaId);

  const itens = Array.isArray(listaQ.data) ? listaQ.data : [];
  const resumo = resumoQ.data ?? null;
  const carregando = listaQ.isFetching;
  const consolidando = mut.consolidar.isPending;

  const togglePrioridade = (p) => {
    const off = prioridadesOff.includes(p)
      ? prioridadesOff.filter((x) => x !== p)
      : [...prioridadesOff, p];
    patch({ prioridadesOff: off });
  };

  const itensFiltrados = useMemo(() => {
    const buscaNorm = busca.trim().toLowerCase();
    return itens.filter((r) => {
      if (prioridadesOff.includes(r.prioridade)) return false;
      if (moduloFiltro && moduloDoIndicador(r.indicador) !== moduloFiltro) return false;
      if (buscaNorm && !`${r.titulo} ${r.descricao}`.toLowerCase().includes(buscaNorm)) return false;
      return true;
    });
  }, [itens, prioridadesOff, moduloFiltro, busca]);

  const grupos = useMemo(() => {
    const porGrupo = { CRITICA: [], ALTA: [], MEDIA: [], BAIXA: [] };
    itensFiltrados.forEach((r) => {
      if (!porGrupo[r.prioridade]) porGrupo[r.prioridade] = [];
      porGrupo[r.prioridade].push(r);
    });
    return porGrupo;
  }, [itensFiltrados]);

  const consolidar = async () => {
    if (!empresaAtivaId) return;
    try {
      await mut.consolidar.mutateAsync();
      fb.sucesso("Recomendações atualizadas a partir dos indicadores.");
      // A invalidação recarrega lista e resumo automaticamente.
    } catch (e) {
      fb.erro(extrairErro(e, "Falha ao consolidar recomendações."));
    }
  };

  const mudarStatus = async (rec, novo) => {
    try {
      await mut.atualizarStatus.mutateAsync({ recId: rec.id, status: novo });
    } catch (e) {
      fb.erro(extrairErro(e, "Falha ao atualizar o status."));
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader
          titulo="Recomendações"
          subtitulo="Oportunidades consolidadas automaticamente pelos indicadores"
          icone={<RecommendIcon sx={{ color: GD.indigo }} />}
        />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Escolha uma empresa ativa para visualizar as recomendações."
        />
      </Box>
    );
  }

  const porPrioridade = resumo?.por_prioridade || {};

  return (
    <Box>
      <PageHeader
        titulo="Recomendações"
        subtitulo="Oportunidades consolidadas automaticamente a partir dos indicadores do diagnóstico"
        icone={<RecommendIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button
            variant="contained"
            startIcon={<AutorenewIcon />}
            onClick={consolidar}
            disabled={consolidando}
          >
            {consolidando ? "Consolidando..." : "Consolidar recomendações"}
          </Button>
        }
      />

      {(carregando || consolidando) && <LinearProgress sx={{ mb: 2 }} />}

      <LegendaBenchmark fonte="REGRA" />

      {/* Resumo por prioridade — clique para incluir/excluir do filtro abaixo */}
      <Grid container spacing={2} sx={{ mb: 1 }}>
        {ORDEM_PRIORIDADE.map((p) => {
          const desligado = prioridadesOff.includes(p);
          return (
            <Grid item xs={6} md={3} key={p}>
              <Card
                onClick={() => togglePrioridade(p)}
                sx={{
                  cursor: "pointer",
                  opacity: desligado ? 0.45 : 1,
                  borderLeft: `4px solid ${PRIORIDADE[p].cor}`,
                  transition: "opacity 0.15s, border-color 0.15s",
                  "&:hover": { borderColor: PRIORIDADE[p].cor },
                }}
              >
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="overline" color="text.secondary">
                      {PRIORIDADE[p].emoji} {PRIORIDADE[p].rotulo}
                    </Typography>
                  </Stack>
                  <Typography variant="h4" sx={{ color: PRIORIDADE[p].cor, fontWeight: 700 }}>
                    {porPrioridade[p] || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {resumo?.economia_estimada_total > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Economia potencial estimada agregada:{" "}
          <b style={{ color: GD.ok }}>{fmtMoeda(resumo.economia_estimada_total)}</b>
        </Typography>
      )}

      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} alignItems="center" flexWrap="wrap" rowGap={1}>
        <TextField
          size="small"
          placeholder="Buscar por título ou descrição..."
          value={busca}
          onChange={(e) => patch({ busca: e.target.value })}
          sx={{ minWidth: 260, flex: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
              </InputAdornment>
            ),
          }}
        />
        <ToggleButtonGroup
          exclusive size="small" value={moduloFiltro}
          onChange={(_, v) => v !== null && patch({ moduloFiltro: v })}
        >
          <ToggleButton value="">Todas</ToggleButton>
          <ToggleButton value="operacao">Operação</ToggleButton>
          <ToggleButton value="mercado">Mercado</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {!carregando && itens.length === 0 && (
        <VazioEstado
          mensagem="Nenhuma recomendação"
          descricao="Clique em “Consolidar recomendações” para gerar oportunidades a partir dos indicadores atuais."
        />
      )}

      {itens.length > 0 && itensFiltrados.length === 0 && (
        <VazioEstado
          mensagem="Nenhum resultado"
          descricao="Nenhuma recomendação corresponde aos filtros atuais."
        />
      )}

      {ORDEM_PRIORIDADE.filter((p) => grupos[p].length > 0).map((p) => (
        <Box key={p} sx={{ mb: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: PRIORIDADE[p].cor }} />
            <Typography variant="overline" sx={{ color: "text.secondary", fontWeight: 700 }}>
              {PRIORIDADE[p].emoji} {PRIORIDADE[p].rotulo} · {grupos[p].length}
            </Typography>
            <Divider sx={{ flex: 1 }} />
          </Stack>
          {grupos[p].map((r) => (
            <RecomendacaoRow
              key={r.id}
              r={r}
              expandido={!!expandidos[r.id]}
              onToggleExpandir={toggleExpandir}
              onMudarStatus={mudarStatus}
            />
          ))}
        </Box>
      ))}

      {itensFiltrados.length > 0 && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 3 }}>
          As recomendações são geradas de forma determinística a partir dos indicadores
          (Dashboard e DLG). A estrutura já está preparada para receber recomendações
          geradas por IA no futuro.
        </Typography>
      )}

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mt: 3, mb: 1 }}>
        <Typography variant="h6">Inteligência de recomendação</Typography>
        <ToggleButtonGroup exclusive size="small" value={moduloIa} onChange={(_, v) => v && setModuloIa(v)}>
          <ToggleButton value="operacao">Operação</ToggleButton>
          <ToggleButton value="mercado">Mercado</ToggleButton>
        </ToggleButtonGroup>
      </Stack>
      <InteligenciaRecomendacao modulo={moduloIa} />
    </Box>
  );
}
