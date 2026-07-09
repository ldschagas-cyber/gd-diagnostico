import { useTelaEstado } from "../hooks/useTelaEstado";
import {
  Box, Card, CardContent, Typography, Button, LinearProgress,
  Stack, Chip, Grid, Table, TableHead, TableRow, TableCell, TableBody,
  MenuItem, TextField, Divider, Tooltip,
} from "@mui/material";
import RecommendIcon from "@mui/icons-material/Recommend";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
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

const STATUS = {
  ABERTA:        "Aberta",
  EM_ANDAMENTO:  "Em andamento",
  CONCLUIDA:     "Concluída",
  DESCARTADA:    "Descartada",
};

function ChipPrioridade({ valor }) {
  const p = PRIORIDADE[valor] || { rotulo: valor, cor: GD.slate, emoji: "" };
  return (
    <Chip
      size="small"
      label={`${p.emoji} ${p.rotulo}`}
      sx={{ bgcolor: `${p.cor}1F`, color: p.cor, fontWeight: 700 }}
    />
  );
}

export default function Recomendacoes() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();

  // Filtro de prioridade persistido entre navegações.
  const [tela, , patch] = useTelaEstado("recomendacoes", { filtroPrioridade: "" });
  const filtroPrioridade = tela.filtroPrioridade;
  const setFiltroPrioridade = (v) => patch({ filtroPrioridade: v });

  const params = filtroPrioridade ? { prioridade: filtroPrioridade } : {};
  const listaQ = useRecomendacoes(empresaAtivaId, params);
  const resumoQ = useRecomendacoesResumo(empresaAtivaId);
  const mut = useMutacoesRecomendacao(empresaAtivaId);

  const itens = Array.isArray(listaQ.data) ? listaQ.data : [];
  const resumo = resumoQ.data ?? null;
  const carregando = listaQ.isFetching;
  const consolidando = mut.consolidar.isPending;

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

      {/* Resumo por prioridade */}
      <Grid container spacing={2} sx={{ mb: 1 }}>
        {["CRITICA", "ALTA", "MEDIA", "BAIXA"].map((p) => (
          <Grid item xs={6} md={3} key={p}>
            <Card>
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
        ))}
      </Grid>

      {resumo?.economia_estimada_total > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Economia potencial estimada agregada:{" "}
          <b style={{ color: GD.ok }}>{fmtMoeda(resumo.economia_estimada_total)}</b>
        </Typography>
      )}

      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} alignItems="center">
        <TextField
          select size="small" label="Prioridade"
          value={filtroPrioridade}
          onChange={(e) => setFiltroPrioridade(e.target.value)}
          sx={{ width: 200 }}
        >
          <MenuItem value="">Todas</MenuItem>
          {Object.keys(PRIORIDADE).map((p) => (
            <MenuItem key={p} value={p}>
              {PRIORIDADE[p].emoji} {PRIORIDADE[p].rotulo}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      {!carregando && itens.length === 0 && (
        <VazioEstado
          mensagem="Nenhuma recomendação"
          descricao="Clique em “Consolidar recomendações” para gerar oportunidades a partir dos indicadores atuais."
        />
      )}

      {itens.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Prioridade</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Recomendação</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Indicador</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align="right">Encontrado</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align="right">Recomendado</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align="right">Economia est.</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {itens.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell><ChipPrioridade valor={r.prioridade} /></TableCell>
                      <TableCell sx={{ maxWidth: 360 }}>
                        <Typography variant="body2" fontWeight={700}>{r.titulo}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {r.descricao}
                        </Typography>
                        {r.impacto && (
                          <Typography variant="caption" display="block" sx={{ color: GD.blue, mt: 0.5 }}>
                            {r.impacto}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip size="small" variant="outlined" label={r.indicador} />
                        {r.origem === "IA" && (
                          <Tooltip title="Gerada por IA">
                            <Chip size="small" label="IA" sx={{ ml: 0.5, bgcolor: `${GD.indigo}1F`, color: GD.indigo }} />
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell align="right">{r.valor_encontrado || "—"}</TableCell>
                      <TableCell align="right">{r.valor_recomendado || "—"}</TableCell>
                      <TableCell align="right">
                        {r.economia_estimada > 0 ? fmtMoeda(r.economia_estimada) : "—"}
                      </TableCell>
                      <TableCell>
                        <TextField
                          select size="small" value={r.status}
                          onChange={(e) => mudarStatus(r, e.target.value)}
                          sx={{ minWidth: 150 }}
                        >
                          {Object.keys(STATUS).map((s) => (
                            <MenuItem key={s} value={s}>{STATUS[s]}</MenuItem>
                          ))}
                        </TextField>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
            <Divider sx={{ my: 1.5 }} />
            <Typography variant="caption" color="text.secondary">
              As recomendações são geradas de forma determinística a partir dos indicadores
              (Dashboard e DLG). A estrutura já está preparada para receber recomendações
              geradas por IA no futuro.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
