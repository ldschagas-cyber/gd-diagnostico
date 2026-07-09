import { useEffect, useState } from "react";
import { useParams, useOutletContext, useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Grid, Stack, Divider, Chip,
  LinearProgress, Alert, Button,
} from "@mui/material";
import RouteIcon from "@mui/icons-material/Route";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import Inventory2Icon from "@mui/icons-material/Inventory2";
import NotesIcon from "@mui/icons-material/Notes";
import { bidApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

const ROTULO_AGRUPAMENTO = {
  CORREDOR: "Corredores OD",
  REGIAO: "Regiões",
  UF: "UFs",
  MACRO_REGIAO: "Macrorregiões",
  TRANSPORTADORA: "Transportadoras",
};

const SEG_LABEL = {
  REGIAO: "Região",
  CIDADE: "Cidade",
  REGIAO_LOGISTICA: "Região Logística",
};

function Linha({ icone, rotulo, valor }) {
  if (!valor) return null;
  return (
    <Stack direction="row" spacing={1.5} alignItems="flex-start" sx={{ py: 0.5 }}>
      <Box sx={{ color: GD.indigo, mt: 0.3 }}>{icone}</Box>
      <Box>
        <Typography variant="caption" color="text.secondary">{rotulo}</Typography>
        <Typography variant="body2" fontWeight={600}>{valor}</Typography>
      </Box>
    </Stack>
  );
}

export default function BidVisaoGeral() {
  const { id } = useParams();
  const nav = useNavigate();
  const ctx = useOutletContext() || {};
  const bid = ctx.bid;
  const [escopos, setEscopos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    bidApi.listarEscopo(id)
      .then(setEscopos)
      .catch((e) => setErro(extrairErro(e)))
      .finally(() => setCarregando(false));
  }, [id]);

  if (!bid) return <LinearProgress />;

  // Agrupa os itens de escopo por tipo (ex.: Corredores OD → lista de grupos)
  const porTipo = {};
  for (const e of escopos) {
    (porTipo[e.tipo_agrupamento] ||= []).push(e);
  }

  const totalEmbarques = escopos.reduce((s, e) => s + (e.qtd_embarques || 0), 0);
  const totalPeso = escopos.reduce((s, e) => s + (e.peso_total || 0), 0);
  const totalFrete = escopos.reduce((s, e) => s + (e.valor_frete_total || 0), 0);

  const fmtNum = (n) => (n || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  const fmtRS = (n) => (n || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <Box>
      {carregando && <LinearProgress sx={{ mb: 2 }} />}
      {erro && <Alert severity="error" sx={{ mb: 2 }}>{erro}</Alert>}

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }} flexWrap="wrap" useFlexGap>
            <RouteIcon sx={{ color: GD.indigo }} />
            <Typography variant="subtitle1" fontWeight={700}>
              Escopo da Concorrência
            </Typography>
            <Chip size="small" label={bid.status} variant="outlined" />
            {bid.segmentacao_tipo && bid.segmentacao_tipo !== "GERAL" && (
              <Chip
                size="small"
                color="primary"
                label={`Segmentação: ${SEG_LABEL[bid.segmentacao_tipo] || bid.segmentacao_tipo}${bid.segmentacao_valor ? " · " + bid.segmentacao_valor : ""}`}
              />
            )}
          </Stack>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Linha
                icone={<NotesIcon fontSize="small" />}
                rotulo="Objetivo"
                valor={bid.objetivo || bid.descricao}
              />
              <Linha
                icone={<CalendarMonthIcon fontSize="small" />}
                rotulo="Período analisado"
                valor={bid.periodo_analise_inicio
                  ? `${bid.periodo_analise_inicio} → ${bid.periodo_analise_fim || "—"}`
                  : null}
              />
              <Linha
                icone={<CalendarMonthIcon fontSize="small" />}
                rotulo="Vigência da concorrência"
                valor={bid.data_inicio
                  ? `Início ${bid.data_inicio}  ·  Encerramento ${bid.data_encerramento || "—"}`
                  : (bid.data_encerramento ? `Encerramento ${bid.data_encerramento}` : null)}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Linha
                icone={<Inventory2Icon fontSize="small" />}
                rotulo="Volume previsto (escopo)"
                valor={escopos.length ? `${fmtNum(totalEmbarques)} embarques` : null}
              />
              <Linha
                icone={<Inventory2Icon fontSize="small" />}
                rotulo="Peso / Frete total (base)"
                valor={escopos.length ? `${fmtNum(totalPeso)} kg  ·  ${fmtRS(totalFrete)}` : null}
              />
              <Linha
                icone={<NotesIcon fontSize="small" />}
                rotulo="Observações"
                valor={bid.observacoes}
              />
            </Grid>
          </Grid>

          {escopos.length > 0 ? (
            <>
              <Divider sx={{ my: 2 }} />
              {Object.entries(porTipo).map(([tipo, itens]) => (
                <Box key={tipo} sx={{ mb: 1.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    {ROTULO_AGRUPAMENTO[tipo] || tipo}
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                    {itens.map((e) => (
                      <Chip
                        key={e.id}
                        size="small"
                        label={`${e.valor_grupo} · ${fmtNum(e.qtd_embarques)} emb. · ${e.frete_rs_kg.toFixed(2)} R$/kg`}
                        sx={{ bgcolor: `${GD.indigo}11` }}
                      />
                    ))}
                  </Stack>
                </Box>
              ))}
            </>
          ) : (
            !carregando && (
              <Alert severity="info" sx={{ mt: 2 }} action={
                <Button color="inherit" size="small" onClick={() => nav(`/bid/${id}/escopo`)}>
                  Gerar escopo
                </Button>
              }>
                Nenhum escopo gerado ainda. Defina o período de análise e gere o escopo na aba “Escopo”.
              </Alert>
            )
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
