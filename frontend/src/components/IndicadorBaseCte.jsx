import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, Chip, Divider,
  Table, TableHead, TableRow, TableCell, TableBody,
  LinearProgress, Tooltip,
} from "@mui/material";
import InsertChartOutlinedIcon from "@mui/icons-material/InsertChartOutlined";
import EventNoteIcon from "@mui/icons-material/EventNote";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useFeedback } from "./Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

const MESES_PT = [
  "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

/**
 * Indicador de Base de CT-e (MELHORIA 1).
 *
 * Demonstrativo tabular (sem gráfico) da quantidade de CT-es armazenados por
 * competência (mês/ano da emissão), do período mais recente para o mais
 * antigo. Competências sem registros não são exibidas. Recarrega
 * automaticamente após cada importação, via a prop `recarregarSinal`
 * (incrementada pela tela de importação ao concluir um lote).
 *
 * Permite ao usuário visualizar rapidamente o histórico de dados existente
 * antes de novas importações.
 */
export default function IndicadorBaseCte({ recarregarSinal = 0 }) {
  const { empresaAtivaId } = useEmpresa();
  const { erro: erroToast } = useFeedback();

  const [competencias, setCompetencias] = useState([]);
  const [carregando, setCarregando] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const dados = await importacaoApi.competencias(empresaAtivaId);
      setCompetencias(Array.isArray(dados) ? dados : []);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao carregar o indicador de base de CT-e."));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, erroToast]);

  // Carga inicial + recarga automática a cada importação concluída.
  useEffect(() => { carregar(); }, [carregar, recarregarSinal]);

  if (!empresaAtivaId) return null;

  const totalCtes = competencias.reduce((s, c) => s + (c.quantidade || 0), 0);
  const totalFormatado = totalCtes.toLocaleString("pt-BR");

  return (
    <Card sx={{ mt: 2.5, border: `1px solid ${GD.indigo}1F` }}>
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={1}
          sx={{ mb: 1 }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <InsertChartOutlinedIcon sx={{ color: GD.indigo }} />
            <Typography variant="subtitle1" fontWeight={700}>
              Base de CT-e por competência
            </Typography>
          </Stack>
          <Tooltip title="Total de CT-es armazenados (com data de emissão)">
            <Chip
              size="small"
              label={`${totalFormatado} CT-e(s)`}
              sx={{ bgcolor: `${GD.indigo}12`, color: GD.indigo, fontWeight: 700 }}
            />
          </Tooltip>
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Histórico de CT-es já armazenados, agrupados por mês de emissão. Use
          para conferir o que já existe antes de novas importações.
        </Typography>

        {carregando && <LinearProgress sx={{ mb: 1.5 }} />}

        {!carregando && competencias.length === 0 && (
          <Box sx={{ textAlign: "center", py: 3 }}>
            <EventNoteIcon sx={{ fontSize: 40, color: "action.disabled", mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              Nenhum CT-e armazenado para esta empresa ainda.
            </Typography>
          </Box>
        )}

        {competencias.length > 0 && (
          <Box
            sx={{
              maxHeight: 320,
              overflowY: "auto",
              border: "1px solid rgba(45,53,97,0.12)",
              borderRadius: 2,
            }}
          >
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Mês/Ano</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="right">
                    CT-es Emitidos
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="right">
                    CT-es Ativos
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="right">
                    CT-es Cancelados
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {competencias.map((c) => {
                  const emitidos = c.emitidos ?? c.quantidade ?? 0;
                  const ativos = c.ativos ?? emitidos;
                  const cancelados = c.cancelados ?? 0;
                  return (
                    <TableRow key={c.competencia} hover>
                      <TableCell>
                        <Stack direction="row" spacing={1} alignItems="baseline">
                          <Typography variant="body2" fontWeight={600}>
                            {c.rotulo}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {MESES_PT[c.mes] || ""} de {c.ano}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={700} sx={{ color: GD.indigo }}>
                          {Number(emitidos).toLocaleString("pt-BR")}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600} sx={{ color: GD.ok }}>
                          {Number(ativos).toLocaleString("pt-BR")}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {cancelados > 0 ? (
                          <Chip
                            size="small"
                            label={Number(cancelados).toLocaleString("pt-BR")}
                            sx={{
                              bgcolor: `${GD.danger}18`,
                              color: GD.danger,
                              fontWeight: 700,
                            }}
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            0
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>
        )}

        {competencias.length > 0 && (
          <>
            <Divider sx={{ my: 1.5 }} />
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" color="text.secondary">
                {competencias.length} competência(s) com registros
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total: <b>{totalFormatado}</b> CT-e(s)
              </Typography>
            </Stack>
          </>
        )}
      </CardContent>
    </Card>
  );
}
