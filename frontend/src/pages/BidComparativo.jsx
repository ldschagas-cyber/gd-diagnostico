import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell,
  TableBody, Chip, LinearProgress, Alert, Stack, Tabs, Tab,
} from "@mui/material";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useBidComparativo, useBidScores } from "../api/queries";
import { extrairErro } from "../api/client";
import { fmtNumero, fmtMoeda } from "../utils/format";
import { corDesvio, fmtDesvio } from "../utils/benchmark";
import { SCORE_COLOR } from "../components/BidStatusChip";
import { GD } from "../theme";

const FAIXA_MERCADO = {
  ABAIXO_P50: { label: "Abaixo P50", cor: "#2e7d32" },     // competitivo
  ENTRE_P50_P75: { label: "No mercado", cor: "#b8860b" },  // dentro da faixa
  ACIMA_P75: { label: "Acima P75", cor: "#c62828" },       // caro
};

export default function BidComparativo() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const [aba, setAba] = useState(0);

  const { data: comparativo = [], isFetching: carregandoComp, error: erroComp } =
    useBidComparativo(id, empresaAtivaId);
  const { data: scores = [], isFetching: carregandoScores, error: erroScores } =
    useBidScores(id, empresaAtivaId);

  const carregando = carregandoComp || carregandoScores;
  const erro = erroComp || erroScores;

  return (
    <Box>
      <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ mb: 2 }}>
        <Tab label="Comparativo de Propostas" />
        <Tab label="Ranking / Score" />
      </Tabs>

      {carregando && <LinearProgress sx={{ mb: 1 }} />}
      {erro && <Alert severity="error">{extrairErro(erro)}</Alert>}

      {aba === 0 && (
        <Card>
          <CardContent>
            {comparativo.length === 0 && !carregando && (
              <Alert severity="info">Gere o escopo e adicione propostas para ver o comparativo.</Alert>
            )}
            <Box sx={{ overflowX: "auto" }}>
              {comparativo.map((linha) => (
                <Box key={linha.valor_grupo} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: GD.indigo, mb: 0.5 }}>
                    {linha.valor_grupo} — {fmtNumero(linha.peso_total, 0)} kg
                    {linha.mercado_p50 != null && (
                      <Typography component="span" variant="body2" sx={{ ml: 1, color: "text.secondary", fontWeight: 400 }}>
                        · Mercado P50 {fmtNumero(linha.mercado_p50, 2)} / P75 {fmtNumero(linha.mercado_p75, 2)} R$/kg
                      </Typography>
                    )}
                  </Typography>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Transportadora</TableCell>
                        <TableCell align="right">Atual R$/kg</TableCell>
                        <TableCell align="right">Proposta R$/kg</TableCell>
                        <TableCell align="right">Mercado P50</TableCell>
                        <TableCell align="center">vs Mercado</TableCell>
                        <TableCell align="right">Economia R$</TableCell>
                        <TableCell align="right">Economia %</TableCell>
                        <TableCell align="right">Prazo</TableCell>
                        <TableCell align="right">Cobertura</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {linha.propostas.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={9} sx={{ color: "text.secondary", fontStyle: "italic" }}>
                            Nenhuma proposta recebida para este grupo.
                          </TableCell>
                        </TableRow>
                      )}
                      {linha.propostas.map((p, i) => {
                        const fx = FAIXA_MERCADO[p.faixa_mercado] || null;
                        return (
                        <TableRow key={i} sx={{ bgcolor: i === 0 ? "rgba(201,168,76,0.08)" : "inherit" }}>
                          <TableCell>
                            {i === 0 && <EmojiEventsIcon sx={{ fontSize: 14, color: GD.amber, mr: 0.5 }} />}
                            {p.transportadora}
                          </TableCell>
                          <TableCell align="right">{fmtNumero(linha.frete_atual_rs_kg, 4)}</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>{fmtNumero(p.rs_kg, 4)}</TableCell>
                          <TableCell align="right" sx={{ color: "text.secondary" }}>
                            {linha.mercado_p50 != null ? fmtNumero(linha.mercado_p50, 2) : "—"}
                          </TableCell>
                          <TableCell align="center">
                            {fx ? (
                              <Box component="span" sx={{
                                px: 1, py: 0.25, borderRadius: 1, fontSize: 11, fontWeight: 600,
                                color: "#fff", bgcolor: fx.cor, whiteSpace: "nowrap",
                              }}>
                                {fx.label}{p.delta_mercado_p50_pct != null ? ` ${p.delta_mercado_p50_pct > 0 ? "+" : ""}${p.delta_mercado_p50_pct.toFixed(0)}%` : ""}
                              </Box>
                            ) : <span style={{ color: "#999" }}>—</span>}
                          </TableCell>
                          <TableCell align="right" sx={{ color: p.economia_rs > 0 ? GD.ok : "text.secondary", fontWeight: 600 }}>
                            {fmtMoeda(p.economia_rs)}
                          </TableCell>
                          <TableCell align="right">{p.economia_pct.toFixed(1)}%</TableCell>
                          <TableCell align="right">{p.prazo_dias}d</TableCell>
                          <TableCell align="right">{p.cobertura_pct}%</TableCell>
                        </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {aba === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>Ranking por Score</Typography>
            {scores.length === 0 && !carregando && (
              <Alert severity="info">Adicione propostas para calcular o score.</Alert>
            )}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>Transportadora</TableCell>
                  <TableCell align="center">Score</TableCell>
                  <TableCell>Classificação</TableCell>
                  <TableCell align="right">R$/kg médio</TableCell>
                  <TableCell align="right">Prazo médio</TableCell>
                  <TableCell align="right">Cobertura</TableCell>
                  <TableCell align="right">Preço (40%)</TableCell>
                  <TableCell align="right">Prazo (30%)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {scores.map((s, i) => (
                  <TableRow key={s.bid_transportadora_id}>
                    <TableCell>{i === 0 ? <EmojiEventsIcon sx={{ fontSize: 16, color: GD.amber }} /> : i + 1}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{s.nome}</TableCell>
                    <TableCell align="center">
                      <Chip size="small" label={s.score} color={SCORE_COLOR(s.score)} />
                    </TableCell>
                    <TableCell>{s.classificacao}</TableCell>
                    <TableCell align="right">{fmtNumero(s.proposta_media_rs_kg, 4)}</TableCell>
                    <TableCell align="right">{s.prazo_medio}d</TableCell>
                    <TableCell align="right">{s.cobertura_media}%</TableCell>
                    <TableCell align="right">{s.score_preco}</TableCell>
                    <TableCell align="right">{s.score_prazo}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
