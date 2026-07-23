import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button, MenuItem,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, Alert, LinearProgress,
  Grid, Divider,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useHubs, useSimuladorHub } from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero, fmtPct, fmtRsKg } from "../utils/format";
import { GD } from "../theme";

const ROTULO_RECOMENDACAO = {
  avaliar_alternativo: { label: "Avaliar alternativo", color: "success" },
  manter_atual: { label: "Manter atual", color: "default" },
  dados_insuficientes: { label: "Dados insuficientes", color: "warning" },
};

function motivoInsuficiente(rota) {
  if (!rota.tem_referencia_alt) return "sem referência cadastrada";
  if (rota.baixa_confianca) return `amostra de ${rota.qtd_ctes} CT-e`;
  return "";
}

export default function SimuladorHub() {
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const navigate = useNavigate();

  const { data: hubs = [] } = useHubs(empresaAtivaId, true);
  const [tela, , patch] = useTelaEstado("simulador-hub", { hubAtual: "", hubAlt: "" });
  const { hubAtual, hubAlt } = tela;
  const mesmoHub = Boolean(hubAtual && hubAlt && hubAtual === hubAlt);

  const params = hubAtual && hubAlt && !mesmoHub ? { hub_atual: hubAtual, hub_alt: hubAlt } : {};
  const { data: res, isFetching: carregando, error, refetch } = useSimuladorHub(empresaAtivaId, params);
  const erro = error ? extrairErro(error) : "";

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Simulador de Hub de Origem" subtitulo="E se despachássemos de outro hub?" />
        <VazioEstado mensagem="Selecione uma empresa" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Simulador de Hub de Origem"
        subtitulo={`${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social} — custo e prazo reais do hub atual vs. referência de mercado do hub alternativo`}
      />

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "flex-end" }}>
            <TextField
              select label="Hub de origem atual" value={hubAtual} sx={{ minWidth: 240 }}
              onChange={(e) => patch({ hubAtual: e.target.value })}
            >
              {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
            </TextField>
            <TextField
              select label="Hub alternativo a simular" value={hubAlt} sx={{ minWidth: 240 }}
              onChange={(e) => patch({ hubAlt: e.target.value })}
            >
              {hubs.map((h) => <MenuItem key={h.id} value={h.codigo}>{h.nome}</MenuItem>)}
            </TextField>
            <Button
              variant="contained" startIcon={<PlayArrowIcon />}
              disabled={!hubAtual || !hubAlt || mesmoHub}
              onClick={() => refetch()}
            >
              Gerar simulação
            </Button>
          </Stack>
          {mesmoHub && (
            <Typography variant="caption" color="error" sx={{ display: "block", mt: 1 }}>
              Hub atual e hub alternativo não podem ser o mesmo.
            </Typography>
          )}
          {hubs.length < 2 && (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              Cadastre ao menos dois hubs em Parâmetros › Hubs Logísticos para simular.
            </Typography>
          )}
        </CardContent>
      </Card>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      {res && !res.opera_no_hub_atual && (
        <VazioEstado
          mensagem={`Sem operação real em ${res.hub_atual_nome}`}
          descricao="A empresa não tem CT-e ativo partindo deste hub no período — não há base real para simular."
        />
      )}

      {res && res.opera_no_hub_atual && (
        <>
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Frete atual — rotas comparáveis" valor={fmtMoeda(res.frete_comparavel_total)}
                legenda={res.rotas_sem_referencia
                  ? `${res.rotas_sem_referencia} de ${res.qtd_rotas} rotas fora (sem referência)`
                  : `todas as ${res.qtd_rotas} rotas com referência`}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard rotulo="Frete simulado (referência de mercado)" valor={fmtMoeda(res.frete_simulado_total)} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Δ custo total" valor={fmtPct(res.delta_custo_total_pct, 1)}
                cor={res.delta_custo_total_pct < 0 ? GD.ok : GD.danger}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                rotulo="Rotas com ganho" valor={`${res.rotas_com_ganho} de ${res.rotas_com_referencia}`}
                legenda={`${res.rotas_com_perda} com custo maior no hub alternativo`}
              />
            </Grid>
          </Grid>

          {res.prazo_atual_medio_dias != null && res.prazo_simulado_medio_dias != null ? (
            <Alert severity="info" sx={{ mb: 2.5 }}>
              Prazo médio ponderado (rotas comparáveis): <strong>{fmtNumero(res.prazo_atual_medio_dias, 1)}d</strong> hoje
              {" → "}<strong>{fmtNumero(res.prazo_simulado_medio_dias, 1)}d</strong> simulado.
            </Alert>
          ) : (
            <Alert severity="info" sx={{ mb: 2.5 }}>
              Prazo médio indisponível para compor uma média confiável — nem todas as rotas comparáveis
              têm prazo de referência cadastrado no corredor.
            </Alert>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Rotas de {res.hub_atual_nome} — comparadas contra {res.hub_alt_nome}
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Destino</TableCell>
                      <TableCell align="right">CT-e (amostra)</TableCell>
                      <TableCell align="right">Frete atual</TableCell>
                      <TableCell align="right">Frete simulado</TableCell>
                      <TableCell align="right">Δ custo</TableCell>
                      <TableCell align="right">Prazo atual → sim.</TableCell>
                      <TableCell>Recomendação</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {res.rotas.map((r) => {
                      const rec = ROTULO_RECOMENDACAO[r.recomendacao] || ROTULO_RECOMENDACAO.dados_insuficientes;
                      const motivo = motivoInsuficiente(r);
                      return (
                        <TableRow key={r.hub_destino} hover>
                          <TableCell sx={{ fontWeight: 600 }}>{r.hub_destino_nome}</TableCell>
                          <TableCell align="right">
                            {r.qtd_ctes}
                            {r.baixa_confianca && (
                              <Typography variant="caption" color="warning.main" sx={{ display: "block" }}>
                                amostra baixa
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {fmtRsKg(r.frete_atual_rs_kg)}
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              {fmtMoeda(r.frete_atual_total)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            {r.tem_referencia_alt ? (
                              <>
                                {fmtRsKg(r.frete_simulado_rs_kg)}
                                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                                  {fmtMoeda(r.frete_simulado_total)}
                                </Typography>
                              </>
                            ) : (
                              <Button size="small" variant="outlined" onClick={() => navigate("/configuracoes/hubs-logisticos")}>
                                Cadastrar referência
                              </Button>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {r.tem_referencia_alt ? (
                              <Typography sx={{ fontWeight: 700, color: r.delta_custo_pct < 0 ? GD.ok : GD.danger }}>
                                {fmtPct(r.delta_custo_pct, 1)}
                              </Typography>
                            ) : "—"}
                          </TableCell>
                          <TableCell align="right">
                            {r.prazo_atual_dias != null ? `${fmtNumero(r.prazo_atual_dias, 1)}d` : "—"}
                            {" → "}
                            {r.prazo_simulado_dias != null ? `${fmtNumero(r.prazo_simulado_dias, 1)}d` : "—"}
                          </TableCell>
                          <TableCell>
                            <Chip size="small" label={rec.label} color={rec.color} />
                            {motivo && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.3 }}>
                                {motivo}
                              </Typography>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Box>
              <Divider sx={{ my: 2 }} />
              <Stack direction="row" spacing={1} alignItems="flex-start">
                <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", mt: 0.2 }} />
                <Typography variant="caption" color="text.secondary">{res.nota}</Typography>
              </Stack>
            </CardContent>
          </Card>
        </>
      )}

      {!res && !carregando && (
        <VazioEstado mensagem="Selecione o hub atual e o hub alternativo para simular" />
      )}
    </Box>
  );
}
