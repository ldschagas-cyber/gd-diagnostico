import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  Grid,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  InputAdornment,
  CircularProgress,
  Chip,
  MenuItem,
  Menu,
  LinearProgress,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import LockIcon from "@mui/icons-material/Lock";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import DescriptionIcon from "@mui/icons-material/Description";
import CodeIcon from "@mui/icons-material/Code";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import GridOnIcon from "@mui/icons-material/GridOn";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import {
  useFechamentoMensal,
  useHistoricoFechamentos,
  useFechamentoMutacoes,
} from "../api/queries";
import { relatoriosApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { MACRO_REGIOES, rotuloMacro, fmtMoeda, fmtPct } from "../utils/format";
import { GD } from "../theme";

const CAMPO_FAT = {
  NORTE: "fat_norte",
  NORDESTE: "fat_nordeste",
  CENTRO_OESTE: "fat_centro_oeste",
  SUDESTE: "fat_sudeste",
  SUL: "fat_sul",
};

const VAZIO = { fat_norte: 0, fat_nordeste: 0, fat_centro_oeste: 0, fat_sudeste: 0, fat_sul: 0, devolucao: 0, frete_complementar: 0 };

function competenciaAtual() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function competenciaAnoAnterior(competencia) {
  const [ano, mes] = competencia.split("-").map(Number);
  return `${ano - 1}-${String(mes).padStart(2, "0")}`;
}

function opcoesCompetencia(qtd = 12) {
  const hoje = new Date();
  const out = [];
  for (let i = 0; i < qtd; i++) {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
    const valor = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const rotulo = d.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    out.push({ valor, rotulo: rotulo.charAt(0).toUpperCase() + rotulo.slice(1) });
  }
  return out;
}

function rotuloCompetencia(competencia) {
  const [ano, mes] = competencia.split("-").map(Number);
  const rotulo = new Date(ano, mes - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  return rotulo.charAt(0).toUpperCase() + rotulo.slice(1);
}

function Delta({ atual, anterior, inverterCor = false }) {
  if (!anterior) {
    return <Typography variant="caption" color="text.disabled">sem base de comparação</Typography>;
  }
  const delta = ((atual - anterior) / anterior) * 100;
  const positivo = delta >= 0;
  const bom = inverterCor ? !positivo : positivo;
  return (
    <Typography variant="body2" sx={{ fontWeight: 700, color: bom ? GD.ok : GD.danger }}>
      {positivo ? "▲" : "▼"} {fmtPct(Math.abs(delta), 2)} <Typography component="span" variant="caption" color="text.secondary">vs. mesmo mês ano anterior</Typography>
    </Typography>
  );
}

function BarraRepresentatividade({ real, budget }) {
  const max = Math.max(real, budget, 1) * 1.15;
  const deltaPP = real - budget;
  return (
    <Box sx={{ minWidth: 160 }}>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="body2" sx={{ fontWeight: 600 }}>{fmtPct(real, 1)}</Typography>
        <Typography variant="caption" color="text.secondary">meta {fmtPct(budget, 1)}</Typography>
      </Stack>
      <Box sx={{ position: "relative", mt: 0.5 }}>
        <LinearProgress
          variant="determinate"
          value={(real / max) * 100}
          sx={{ height: 6, borderRadius: 3, "& .MuiLinearProgress-bar": { backgroundColor: GD.indigo } }}
        />
        <Box
          sx={{
            position: "absolute", top: -2, bottom: -2, width: "2px", bgcolor: GD.slate,
            left: `${(budget / max) * 100}%`,
          }}
        />
      </Box>
      <Typography variant="caption" sx={{ color: deltaPP >= 0 ? GD.indigo : "text.secondary", fontWeight: 700 }}>
        {deltaPP >= 0 ? "+" : ""}{deltaPP.toFixed(1)} p.p. vs meta
      </Typography>
    </Box>
  );
}

export default function FechamentoFrete() {
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const [competencia, setCompetencia] = useState(competenciaAtual());
  const [form, setForm] = useState(VAZIO);
  const [menuRelatorio, setMenuRelatorio] = useState(null);
  const [gerandoRelatorio, setGerandoRelatorio] = useState(null);

  const { data, isLoading, error } = useFechamentoMensal(empresaAtivaId, competencia);
  const { data: historico = [], isLoading: carregandoHistorico } = useHistoricoFechamentos(empresaAtivaId, 13);
  const { salvar, fechar, reabrir } = useFechamentoMutacoes(empresaAtivaId);

  useEffect(() => {
    if (data) {
      setForm({
        fat_norte: data.fat_norte, fat_nordeste: data.fat_nordeste, fat_centro_oeste: data.fat_centro_oeste,
        fat_sudeste: data.fat_sudeste, fat_sul: data.fat_sul,
        devolucao: data.devolucao, frete_complementar: data.frete_complementar,
      });
    }
  }, [data]);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  const fechado = data?.status === "FECHADO";
  const totalNacional = useMemo(
    () => MACRO_REGIOES.reduce((soma, m) => soma + (Number(form[CAMPO_FAT[m.valor]]) || 0), 0),
    [form]
  );

  const anoAnterior = useMemo(() => {
    const alvo = competenciaAnoAnterior(competencia);
    return historico.find((h) => h.competencia === alvo);
  }, [historico, competencia]);

  const atualizarCampo = (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor }));

  const salvarFechamento = async () => {
    try {
      const numerico = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v) || 0]));
      await salvar.mutateAsync({ competencia, ...numerico });
      sucesso("Fechamento salvo.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const fecharMes = async () => {
    try {
      await fechar.mutateAsync(competencia);
      sucesso(`${rotuloCompetencia(competencia)} fechado.`);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const reabrirMes = async () => {
    try {
      await reabrir.mutateAsync(competencia);
      sucesso(`${rotuloCompetencia(competencia)} reaberto.`);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const gerarRelatorio = async (formato) => {
    setMenuRelatorio(null);
    setGerandoRelatorio(formato);
    try {
      await relatoriosApi.baixarFechamento(empresaAtivaId, formato, competencia);
      sucesso("Relatório do fechamento gerado.");
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível gerar o relatório."));
    } finally {
      setGerandoRelatorio(null);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Fechamento de Custo de Frete" subtitulo="Faturamento por região, devoluções e frete complementar do mês" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  const kpis = [
    { label: "Faturamento", atual: totalNacional, anterior: anoAnterior?.faturamento_total, inverter: false },
    { label: "Devoluções", atual: Number(form.devolucao) || 0, anterior: anoAnterior?.devolucao, inverter: true },
    { label: "Frete contratado", atual: data?.frete_contratado ?? 0, anterior: anoAnterior?.frete_contratado, inverter: true },
    { label: "Frete complementar", atual: Number(form.frete_complementar) || 0, anterior: anoAnterior?.frete_complementar, inverter: true },
  ];

  return (
    <Box>
      <PageHeader
        titulo="Fechamento de Custo de Frete"
        subtitulo="Faturamento por região, devoluções e frete complementar do mês — frete realizado e budget são automáticos"
        acoes={
          <TextField select size="small" label="Competência" value={competencia} onChange={(e) => setCompetencia(e.target.value)} sx={{ width: 200 }}>
            {opcoesCompetencia().map((o) => (
              <MenuItem key={o.valor} value={o.valor}>{o.rotulo}</MenuItem>
            ))}
          </TextField>
        }
      />

      {isLoading ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={2.5}>
          {/* Fechamento do mês */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="h6">Fechamento do mês</Typography>
                  <Chip
                    size="small"
                    icon={fechado ? <LockIcon sx={{ fontSize: 15 }} /> : <LockOpenIcon sx={{ fontSize: 15 }} />}
                    label={`${rotuloCompetencia(competencia)} — ${fechado ? "fechado" : "em aberto"}`}
                    sx={{ bgcolor: fechado ? "rgba(46,125,91,0.12)" : "rgba(45,53,97,0.08)", color: fechado ? GD.ok : GD.indigo, fontWeight: 700 }}
                  />
                </Stack>

                <Typography variant="overline" color="text.secondary">Faturamento por região</Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mt: 0.25, mb: 2 }}>
                  {MACRO_REGIOES.map((m) => (
                    <TextField
                      key={m.valor}
                      type="number"
                      size="small"
                      label={m.rotulo}
                      value={form[CAMPO_FAT[m.valor]] ?? 0}
                      onChange={(e) => atualizarCampo(CAMPO_FAT[m.valor], e.target.value)}
                      disabled={fechado}
                      InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                      sx={{ flex: "1 1 170px" }}
                    />
                  ))}
                </Box>
                <Box sx={{ display: "flex", justifyContent: "space-between", bgcolor: "rgba(45,53,97,0.045)", borderRadius: 1, px: 2, py: 1, mb: 3 }}>
                  <Typography variant="body2" color="text.secondary">Total nacional (soma automática)</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmtMoeda(totalNacional)}</Typography>
                </Box>

                <Typography variant="overline" color="text.secondary">Totais nacionais</Typography>
                <Grid container spacing={2} sx={{ mt: 0.25, mb: 3, maxWidth: 560 }}>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth type="number" size="small" label="Devoluções"
                      value={form.devolucao ?? 0}
                      onChange={(e) => atualizarCampo("devolucao", e.target.value)}
                      disabled={fechado}
                      InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth type="number" size="small" label="Frete complementar"
                      value={form.frete_complementar ?? 0}
                      onChange={(e) => atualizarCampo("frete_complementar", e.target.value)}
                      disabled={fechado}
                      InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
                    />
                  </Grid>
                </Grid>

                <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
                  {!fechado ? (
                    <>
                      <Button variant="contained" startIcon={<SaveIcon />} onClick={salvarFechamento} disabled={salvar.isPending}>
                        {salvar.isPending ? "Salvando..." : "Salvar"}
                      </Button>
                      <Button variant="outlined" onClick={fecharMes} disabled={fechar.isPending}>
                        Fechar mês
                      </Button>
                    </>
                  ) : (
                    <Button variant="outlined" onClick={reabrirMes} disabled={reabrir.isPending}>
                      Reabrir mês
                    </Button>
                  )}
                  <Button
                    variant="outlined"
                    startIcon={gerandoRelatorio ? <CircularProgress size={16} /> : <DescriptionIcon />}
                    disabled={!fechado || Boolean(gerandoRelatorio)}
                    onClick={(e) => setMenuRelatorio(e.currentTarget)}
                    sx={{ borderColor: GD.amberDark, color: GD.amberDark, "&:hover": { borderColor: GD.amberDark, bgcolor: "rgba(201,168,76,0.08)" } }}
                  >
                    Gerar relatório do fechamento
                  </Button>
                  <Menu anchorEl={menuRelatorio} open={Boolean(menuRelatorio)} onClose={() => setMenuRelatorio(null)}>
                    <MenuItem onClick={() => gerarRelatorio("html")}>
                      <CodeIcon fontSize="small" sx={{ mr: 1.5, color: GD.indigo }} /> Baixar HTML
                    </MenuItem>
                    <MenuItem onClick={() => gerarRelatorio("pdf")}>
                      <PictureAsPdfIcon fontSize="small" sx={{ mr: 1.5, color: GD.blue }} /> Baixar PDF
                    </MenuItem>
                    <MenuItem onClick={() => gerarRelatorio("excel")}>
                      <GridOnIcon fontSize="small" sx={{ mr: 1.5, color: GD.amber }} /> Baixar Excel
                    </MenuItem>
                  </Menu>
                  <Typography variant="caption" color="text.secondary">
                    {fechado
                      ? "Frete contratado (" + fmtMoeda(data?.frete_contratado ?? 0) + ") já vem automático da soma dos CT-es do período — não precisa digitar."
                      : "Feche o mês para poder gerar o relatório para envio ao cliente."}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Resumo Geral */}
          <Grid item xs={12}>
            <Grid container spacing={2}>
              {kpis.map((k) => (
                <Grid item xs={12} sm={6} md={3} key={k.label}>
                  <Card sx={{ height: "100%" }}>
                    <CardContent>
                      <Typography variant="overline" color="text.secondary">{k.label}</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>{fmtMoeda(k.atual)}</Typography>
                      <Delta atual={k.atual} anterior={k.anterior} inverterCor={k.inverter} />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Grid>

          {/* Histórico */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1.5 }}>Histórico de fechamentos</Typography>
                {carregandoHistorico ? (
                  <CircularProgress size={22} />
                ) : historico.length === 0 ? (
                  <VazioEstado mensagem="Nenhum fechamento lançado ainda" />
                ) : (
                  <Box sx={{ overflowX: "auto" }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Competência</TableCell>
                          <TableCell align="right">Faturamento</TableCell>
                          <TableCell align="right">Devoluções</TableCell>
                          <TableCell align="right">Frete complementar</TableCell>
                          <TableCell align="right">Frete contratado</TableCell>
                          <TableCell align="right">Status</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {historico.map((h) => (
                          <TableRow key={h.competencia} selected={h.competencia === competencia}>
                            <TableCell sx={{ fontWeight: 600 }}>{rotuloCompetencia(h.competencia)}</TableCell>
                            <TableCell align="right">{fmtMoeda(h.faturamento_total)}</TableCell>
                            <TableCell align="right">{fmtMoeda(h.devolucao)}</TableCell>
                            <TableCell align="right">{fmtMoeda(h.frete_complementar)}</TableCell>
                            <TableCell align="right">{fmtMoeda(h.frete_contratado)}</TableCell>
                            <TableCell align="right">
                              <Chip
                                size="small"
                                icon={h.status === "FECHADO" ? <LockIcon sx={{ fontSize: 13 }} /> : <LockOpenIcon sx={{ fontSize: 13 }} />}
                                label={h.status === "FECHADO" ? "Fechado" : "Em aberto"}
                                sx={{ bgcolor: h.status === "FECHADO" ? "rgba(46,125,91,0.12)" : "rgba(45,53,97,0.08)", color: h.status === "FECHADO" ? GD.ok : GD.indigo, fontWeight: 700 }}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Regional */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 0.25 }}>Representatividade por região</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Frete realizado e budget são automáticos (CT-e e Metas Regionais); o faturamento vem do fechamento acima.
                </Typography>
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell rowSpan={2} sx={{ verticalAlign: "bottom" }}>Região</TableCell>
                        <TableCell colSpan={3} align="center" sx={{ borderBottom: "none", fontWeight: 700 }}>Realizado</TableCell>
                        <TableCell colSpan={3} align="center" sx={{ borderBottom: "none", fontWeight: 700 }}>Budget</TableCell>
                        <TableCell rowSpan={2} sx={{ verticalAlign: "bottom" }} align="right">Representatividade</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell align="right">Vlr. Net Net</TableCell>
                        <TableCell align="right">Frete líquido</TableCell>
                        <TableCell align="right">% Frete/Fat.</TableCell>
                        <TableCell align="right">Faturamento</TableCell>
                        <TableCell align="right">Frete</TableCell>
                        <TableCell align="right">% Frete/Fat.</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(data?.regional || []).map((r) => (
                        <TableRow key={r.macro_regiao}>
                          <TableCell sx={{ fontWeight: 600 }}>{rotuloMacro(r.macro_regiao)}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.fat_real)}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.frete_real)}</TableCell>
                          <TableCell align="right">{fmtPct(r.pct_frete_fat_real, 1)}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.fat_budget)}</TableCell>
                          <TableCell align="right">{fmtMoeda(r.frete_budget)}</TableCell>
                          <TableCell align="right">{fmtPct(r.pct_frete_fat_budget, 1)}</TableCell>
                          <TableCell align="right">
                            <BarraRepresentatividade real={r.representatividade_real} budget={r.representatividade_budget} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                    {data?.regional_total && (
                      <TableBody>
                        <TableRow sx={{ bgcolor: "rgba(45,53,97,0.045)" }}>
                          <TableCell sx={{ fontWeight: 700 }}>Total Geral</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtMoeda(data.regional_total.fat_real)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtMoeda(data.regional_total.frete_real)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtPct(data.regional_total.pct_frete_fat_real, 1)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtMoeda(data.regional_total.fat_budget)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtMoeda(data.regional_total.frete_budget)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>{fmtPct(data.regional_total.pct_frete_fat_budget, 1)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>100,0%</TableCell>
                        </TableRow>
                      </TableBody>
                    )}
                  </Table>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
