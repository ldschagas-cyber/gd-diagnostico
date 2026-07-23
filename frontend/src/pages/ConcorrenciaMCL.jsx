import { useEffect, useState } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Stack, Button, Chip,
  LinearProgress, Alert, TextField, MenuItem, Divider,
  Table, TableHead, TableRow, TableCell, TableBody, Tooltip,
} from "@mui/material";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import GavelIcon from "@mui/icons-material/Gavel";
import TuneIcon from "@mui/icons-material/Tune";
import BlockIcon from "@mui/icons-material/Block";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import InteligenciaRecomendacao from "../components/InteligenciaRecomendacao";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { useBidLista, useMclPrevia, useMutacoesMcl } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";
import { GD } from "../theme";

const COMPONENTES = [
  { k: "score_custo", l: "Custo", peso: "40%" },
  { k: "score_dlg", l: "DLG", peso: "25%" },
  { k: "score_mbl", l: "MBL", peso: "20%" },
  { k: "score_sla", l: "SLA", peso: "10%" },
  { k: "score_estabilidade", l: "Estab.", peso: "5%" },
];

const COR_CLF = { EFICIENTE: GD.ok, ATENCAO: GD.warn, CRITICO: GD.danger, SEM_REF: GD.slate };

function BarraScore({ valor, cor }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
      <Box sx={{ flex: 1, height: 6, bgcolor: "rgba(45,53,97,0.1)", borderRadius: 3, overflow: "hidden" }}>
        <Box sx={{ width: `${Math.round((valor || 0) * 100)}%`, height: "100%", bgcolor: cor || GD.indigo }} />
      </Box>
      <Typography variant="caption" sx={{ minWidth: 32, textAlign: "right" }}>
        {fmtNumero(valor, 2)}
      </Typography>
    </Box>
  );
}

export default function ConcorrenciaMCL() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const [bidId, setBidId] = useState("");
  const [decisaoManual, setDecisaoManual] = useState(null);

  // simulador
  const [variacao, setVariacao] = useState(-10);
  const [faturamento, setFaturamento] = useState("");
  const [simulacao, setSimulacao] = useState(null);

  const { data: bids = [], error: erroBids } = useBidLista(empresaAtivaId);
  const previaQ = useMclPrevia(bidId);
  const mut = useMutacoesMcl(bidId);

  const carregando = previaQ.isFetching;
  const decidindo = mut.decidir.isPending;
  const decisao = decisaoManual || (previaQ.error ? null : previaQ.data);

  useEffect(() => {
    if (erroBids) erroToast(extrairErro(erroBids));
  }, [erroBids, erroToast]);

  useEffect(() => {
    if (previaQ.error) erroToast(extrairErro(previaQ.error));
  }, [previaQ.error, erroToast]);

  const onSelecionarBid = (id) => {
    setBidId(id);
    setDecisaoManual(null);
    setSimulacao(null);
  };

  const decidir = async () => {
    if (!bidId) return;
    try {
      const r = await mut.decidir.mutateAsync();
      setDecisaoManual(r);
      sucesso(`Decisão registrada (v${r.versao}): ${r.vencedora?.nome} venceu.`);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const simular = async () => {
    if (!bidId) return;
    try {
      const payload = { variacao_preco_pct: Number(variacao) || 0 };
      if (faturamento) payload.faturamento_mensal = Number(faturamento);
      setSimulacao(await mut.simular.mutateAsync(payload));
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const venc = decisao?.vencedora;
  const ranking = decisao?.ranking || [];
  const rejeitadas = decisao?.rejeitadas || [];

  return (
    <Box>
      <PageHeader
        titulo="Concorrência Logística (MCL)"
        subtitulo="Motor de decisão de BID — score multi-critério com DLG, MBL e regras comerciais"
      />

      {/* Seletor de BID */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
            <TextField
              select label="BID" size="small" value={bidId}
              onChange={(e) => onSelecionarBid(e.target.value)}
              sx={{ minWidth: 280 }}
            >
              {bids.length === 0 && <MenuItem disabled value="">Nenhum BID cadastrado</MenuItem>}
              {bids.map((b) => (
                <MenuItem key={b.id} value={b.id}>{b.nome}</MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained" startIcon={<GavelIcon />}
              onClick={decidir} disabled={decidindo || !bidId}
            >
              {decidindo ? "Registrando…" : "Registrar decisão"}
            </Button>
            <Typography variant="caption" color="text.secondary">
              A prévia é determinística; "Registrar decisão" versiona para rastreabilidade.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      {!bidId && !carregando && (
        <Alert severity="info">Selecione um BID para calcular o ranking de propostas.</Alert>
      )}

      {decisao && venc && (
        <>
          {/* Vencedora + justificativa */}
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} md={5}>
              <Card sx={{ height: "100%", borderLeft: `4px solid ${GD.amber}` }}>
                <CardContent>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <EmojiEventsIcon sx={{ color: GD.amber }} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Vencedora</Typography>
                  </Stack>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: GD.indigo }}>
                    {venc.nome}
                  </Typography>
                  <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Score final</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>{fmtNumero(venc.score_final, 3)}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">R$/kg</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>R$ {fmtNumero(venc.rs_kg, 2)}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">vs 2ª</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: GD.ok }}>
                        +{fmtNumero(decisao.diferenca_segunda, 3)}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={7}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                    Justificativa da decisão
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1.5 }}>{decisao.justificativa}</Typography>
                  <Divider sx={{ mb: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    Pesos: custo {Math.round(decisao.pesos.custo * 100)}% · DLG {Math.round(decisao.pesos.dlg * 100)}% ·
                    MBL {Math.round(decisao.pesos.mbl * 100)}% · SLA {Math.round(decisao.pesos.sla * 100)}% ·
                    estabilidade {Math.round(decisao.pesos.estabilidade * 100)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Ranking com breakdown */}
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                Ranking de propostas
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>#</TableCell>
                    <TableCell>Transportadora</TableCell>
                    <TableCell align="right">R$/kg</TableCell>
                    <TableCell align="center">DLG</TableCell>
                    {COMPONENTES.map((c) => (
                      <TableCell key={c.k} align="center">
                        <Tooltip title={`Peso ${c.peso}`}><span>{c.l}</span></Tooltip>
                      </TableCell>
                    ))}
                    <TableCell align="right">Score</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {ranking.map((r, i) => (
                    <TableRow key={r.bid_transportadora_id} hover sx={i === 0 ? { bgcolor: GD.amber + "11" } : {}}>
                      <TableCell sx={{ fontWeight: 700 }}>{i + 1}º</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {i === 0 && <EmojiEventsIcon sx={{ fontSize: 16, color: GD.amber, verticalAlign: "middle", mr: 0.5 }} />}
                        {r.nome}
                      </TableCell>
                      <TableCell align="right">R$ {fmtNumero(r.rs_kg, 2)}</TableCell>
                      <TableCell align="center">
                        <Chip size="small" label={r.dlg_classificacao === "SEM_REF" ? "—" : r.dlg_classificacao}
                          sx={{ bgcolor: (COR_CLF[r.dlg_classificacao] || GD.slate) + "22", color: COR_CLF[r.dlg_classificacao] || GD.slate, fontWeight: 600 }} />
                      </TableCell>
                      {COMPONENTES.map((c) => (
                        <TableCell key={c.k} align="center" sx={{ minWidth: 90 }}>
                          <BarraScore valor={r[c.k]} cor={i === 0 ? GD.amber : GD.blue} />
                        </TableCell>
                      ))}
                      <TableCell align="right" sx={{ fontWeight: 800 }}>{fmtNumero(r.score_final, 3)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {rejeitadas.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: GD.danger, mb: 1 }}>
                    <BlockIcon fontSize="small" sx={{ verticalAlign: "middle", mr: 0.5 }} />
                    Propostas rejeitadas
                  </Typography>
                  <Stack spacing={0.5}>
                    {rejeitadas.map((r) => (
                      <Typography key={r.bid_transportadora_id} variant="body2" color="text.secondary">
                        <strong>{r.nome}</strong> (R$ {fmtNumero(r.rs_kg, 2)}/kg) — {r.motivo_rejeicao}
                      </Typography>
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Simulador */}
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                <TuneIcon fontSize="small" sx={{ verticalAlign: "middle", mr: 0.5 }} />
                Simulação de cenário
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }} sx={{ mb: 2 }}>
                <TextField
                  label="Variação de preço (%)" type="number" size="small" value={variacao}
                  onChange={(e) => setVariacao(e.target.value)} sx={{ width: 180 }}
                  helperText="negativo = redução de tarifa"
                />
                <TextField
                  label="Faturamento mensal (opcional)" type="number" size="small" value={faturamento}
                  onChange={(e) => setFaturamento(e.target.value)} sx={{ width: 220 }}
                  helperText="para calcular % frete"
                />
                <Button variant="outlined" onClick={simular}>Simular</Button>
              </Stack>

              {simulacao && (
                <>
                  <Grid container spacing={2} sx={{ mb: 1 }}>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="text.secondary">Custo base</Typography>
                      <Typography variant="h6">{fmtMoeda(simulacao.custo_total_base)}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="text.secondary">Custo simulado</Typography>
                      <Typography variant="h6">{fmtMoeda(simulacao.custo_total_simulado)}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="text.secondary">Impacto</Typography>
                      <Typography variant="h6" sx={{ color: simulacao.delta_custo <= 0 ? GD.ok : GD.danger }}>
                        {simulacao.delta_custo > 0 ? "+" : ""}{fmtMoeda(simulacao.delta_custo)} ({fmtNumero(simulacao.delta_custo_pct, 1)}%)
                      </Typography>
                    </Grid>
                    {simulacao.pct_frete_base != null && (
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" color="text.secondary">% Frete</Typography>
                        <Typography variant="h6">
                          {fmtNumero(simulacao.pct_frete_base, 2)}% → {fmtNumero(simulacao.pct_frete_simulado, 2)}%
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                  <Typography variant="caption" color="text.secondary">
                    Peso total do BID: {fmtNumero(simulacao.peso_total_kg, 0)} kg.
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {decisao && !venc && !carregando && (
        <VazioEstado mensagem="Nenhuma proposta elegível" descricao="Cadastre propostas no BID (ou verifique as restrições do benchmark) para gerar o ranking." />
      )}

      <InteligenciaRecomendacao modulo="concorrencia" />
    </Box>
  );
}
