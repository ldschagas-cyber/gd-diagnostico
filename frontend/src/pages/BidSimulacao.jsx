import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Card, CardContent, Grid, Typography, Stack, Button, TextField,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, LinearProgress,
  Alert, Divider, IconButton, Slider,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import CalculateIcon from "@mui/icons-material/Calculate";
import { useFeedback } from "../components/Feedback";
import { useEmpresa } from "../contexts/EmpresaContext";
import { bidApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { fmtMoeda, fmtNumero } from "../utils/format";
import { GD } from "../theme";

export default function BidSimulacao() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();
  const [simulacoes, setSimulacoes] = useState([]);
  const [escopos, setEscopos] = useState([]);
  const [bts, setBts] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [itens, setItens] = useState([{ bid_transportadora_id: "", valor_grupo: "", pct_alocado: 100 }]);
  const [calculando, setCalculando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [sims, esc, t] = await Promise.all([
        bidApi.listarSimulacoes(id),
        bidApi.listarEscopo(id),
        bidApi.listarTransp(id),
      ]);
      setSimulacoes(sims); setEscopos(esc); setBts(t);
    } catch (e) { erroToast(extrairErro(e)); }
    finally { setCarregando(false); }
  }, [id, erroToast]);

  useEffect(() => { carregar(); }, [carregar]);

  const addItem = () => setItens([...itens, { bid_transportadora_id: "", valor_grupo: "", pct_alocado: 100 }]);
  const removeItem = (i) => setItens(itens.filter((_, j) => j !== i));
  const updateItem = (i, campo, val) => {
    const copia = [...itens];
    copia[i] = { ...copia[i], [campo]: val };
    setItens(copia);
  };

  const calcular = async () => {
    setCalculando(true);
    try {
      const r = await bidApi.calcularSimulacao(id, empresaAtivaId, {
        nome: nome || "Simulação",
        descricao,
        itens: itens.map((x) => ({
          bid_transportadora_id: Number(x.bid_transportadora_id),
          valor_grupo: x.valor_grupo,
          pct_alocado: Number(x.pct_alocado),
        })),
      });
      setResultado(r);
    } catch (e) { erroToast(extrairErro(e)); }
    finally { setCalculando(false); }
  };

  const salvar = async () => {
    if (!nome.trim()) { erroToast("Informe o nome do cenário."); return; }
    try {
      await bidApi.salvarSimulacao(id, empresaAtivaId, {
        nome, descricao,
        itens: itens.map((x) => ({
          bid_transportadora_id: Number(x.bid_transportadora_id),
          valor_grupo: x.valor_grupo,
          pct_alocado: Number(x.pct_alocado),
        })),
      });
      sucesso("Simulação salva."); setNome(""); setDescricao(""); setItens([{ bid_transportadora_id: "", valor_grupo: "", pct_alocado: 100 }]); setResultado(null);
      await carregar();
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const btNome = (btId) =>
    bts.find((b) => b.transportadora_id === btId)?.transportadora_nome || `Transp. ${btId}`;
  const grupos = [...new Set(escopos.map((e) => e.valor_grupo))];

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Construtor */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>Montar Cenário</Typography>
              <Stack spacing={2}>
                <TextField size="small" label="Nome do cenário" value={nome} onChange={(e) => setNome(e.target.value)} />
                <TextField size="small" label="Descrição" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
              </Stack>

              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>Alocações</Typography>

              {itens.map((item, i) => (
                <Grid container spacing={1} sx={{ mb: 1 }} key={i} alignItems="center">
                  <Grid item xs={4}>
                    <TextField size="small" fullWidth select label="Transportadora"
                      value={item.bid_transportadora_id}
                      onChange={(e) => updateItem(i, "bid_transportadora_id", e.target.value)}
                      SelectProps={{ native: true }}
                    >
                      <option value="" />
                      {bts.map((bt) => <option key={bt.id} value={bt.id}>{btNome(bt.transportadora_id)}</option>)}
                    </TextField>
                  </Grid>
                  <Grid item xs={4}>
                    <TextField size="small" fullWidth select label="Grupo"
                      value={item.valor_grupo}
                      onChange={(e) => updateItem(i, "valor_grupo", e.target.value)}
                      SelectProps={{ native: true }}
                    >
                      <option value="" />
                      {grupos.map((g) => <option key={g} value={g}>{g}</option>)}
                    </TextField>
                  </Grid>
                  <Grid item xs={3}>
                    <TextField size="small" fullWidth label="% Alocado" type="number"
                      value={item.pct_alocado}
                      onChange={(e) => updateItem(i, "pct_alocado", e.target.value)}
                      inputProps={{ min: 0, max: 100 }}
                    />
                  </Grid>
                  <Grid item xs={1}>
                    <IconButton size="small" onClick={() => removeItem(i)}><DeleteIcon fontSize="small" /></IconButton>
                  </Grid>
                </Grid>
              ))}

              <Button startIcon={<AddIcon />} size="small" onClick={addItem} sx={{ mt: 1 }}>Adicionar linha</Button>

              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button variant="outlined" startIcon={<CalculateIcon />} onClick={calcular} disabled={calculando}>
                  Calcular
                </Button>
                <Button variant="contained" startIcon={<SaveIcon />} onClick={salvar}>
                  Salvar Cenário
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Resultado */}
        <Grid item xs={12} md={5}>
          {resultado && (
            <Card sx={{ border: `2px solid ${GD.amber}` }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>Resultado do Cenário</Typography>
                <Stack spacing={1.5}>
                  <Box><Typography variant="caption" color="text.secondary">Custo atual</Typography>
                    <Typography variant="h6">{fmtMoeda(resultado.custo_atual)}</Typography></Box>
                  <Box><Typography variant="caption" color="text.secondary">Custo proposto</Typography>
                    <Typography variant="h6" sx={{ color: GD.blue }}>{fmtMoeda(resultado.custo_proposto)}</Typography></Box>
                  <Box><Typography variant="caption" color="text.secondary">Economia total</Typography>
                    <Typography variant="h5" sx={{ color: GD.ok, fontWeight: 700 }}>{fmtMoeda(resultado.economia_total)}</Typography></Box>
                  <Chip label={`Redução de ${resultado.reducao_pct.toFixed(1)}%`} color="success" sx={{ width: "fit-content" }} />
                </Stack>
              </CardContent>
            </Card>
          )}
        </Grid>

        {/* Histórico */}
        {simulacoes.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>Cenários Salvos</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Nome</TableCell>
                      <TableCell align="right">Custo atual</TableCell>
                      <TableCell align="right">Custo proposto</TableCell>
                      <TableCell align="right">Economia</TableCell>
                      <TableCell align="right">Redução %</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {simulacoes.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell sx={{ fontWeight: 600 }}>{s.nome}</TableCell>
                        <TableCell align="right">{fmtMoeda(s.custo_atual)}</TableCell>
                        <TableCell align="right">{fmtMoeda(s.custo_proposto)}</TableCell>
                        <TableCell align="right" sx={{ color: GD.ok, fontWeight: 600 }}>{fmtMoeda(s.economia_total)}</TableCell>
                        <TableCell align="right">{s.reducao_pct.toFixed(1)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {carregando && <LinearProgress />}
    </Box>
  );
}
