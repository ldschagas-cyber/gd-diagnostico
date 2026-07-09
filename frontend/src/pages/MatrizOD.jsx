import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, MenuItem, IconButton,
  Alert, LinearProgress, InputAdornment, Chip, TableSortLabel,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import GridOnIcon from "@mui/icons-material/GridOn";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { mercadoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";

const REGIOES = ["NORTE", "NORDESTE", "CENTRO_OESTE", "SUDESTE", "SUL"];
const ROTULO_REGIAO = {
  NORTE: "Norte", NORDESTE: "Nordeste", CENTRO_OESTE: "Centro-Oeste",
  SUDESTE: "Sudeste", SUL: "Sul",
};
const TIPOS_OP = ["TODOS", "FTL", "LTL", "FRACIONADO"];

const VAZIO = {
  origem_regiao: "", destino_regiao: "", modal: "", tipo_operacao: "TODOS",
  faixa_peso_min: 0, faixa_peso_max: 0,
  rs_kg_p10: 0, rs_kg_p25: 0, rs_kg_p50: 0, rs_kg_p75: 0, rs_kg_p90: 0,
};

export default function MatrizOD() {
  const { sucesso, erro: erroToast } = useFeedback();
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(VAZIO);
  const [orden, setOrden] = useState({ campo: "origem_regiao", asc: true });

  const ordenar = (campo) =>
    setOrden((o) => ({ campo, asc: o.campo === campo ? !o.asc : true }));

  const listaOrdenada = [...lista].sort((a, b) => {
    const { campo, asc } = orden;
    let va = a[campo], vb = b[campo];
    if (campo === "origem_regiao") { va = `${a.origem_regiao}|${a.destino_regiao}`; vb = `${b.origem_regiao}|${b.destino_regiao}`; }
    if (typeof va === "string") return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    return asc ? (va - vb) : (vb - va);
  });

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setLista(await mercadoApi.listar());
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [erroToast]);

  useEffect(() => { carregar(); }, [carregar]);

  const set = (campo, valor) => setForm((p) => ({ ...p, [campo]: valor }));

  const salvar = async () => {
    if (!form.origem_regiao || !form.destino_regiao) {
      erroToast("Selecione a região de origem e a de destino.");
      return;
    }
    const p50 = Number(form.rs_kg_p50) || 0;
    if (p50 <= 0) {
      erroToast("Informe ao menos a mediana (P50) em R$/kg.");
      return;
    }
    setSalvando(true);
    try {
      await mercadoApi.salvar({
        origem_regiao: form.origem_regiao,
        destino_regiao: form.destino_regiao,
        modal: form.modal || "",
        tipo_operacao: form.tipo_operacao || "TODOS",
        faixa_peso_min: Number(form.faixa_peso_min) || 0,
        faixa_peso_max: Number(form.faixa_peso_max) || 0,
        rs_kg_p10: Number(form.rs_kg_p10) || 0,
        rs_kg_p25: Number(form.rs_kg_p25) || 0,
        rs_kg_p50: p50,
        rs_kg_p75: Number(form.rs_kg_p75) || 0,
        rs_kg_p90: Number(form.rs_kg_p90) || 0,
      });
      sucesso("Referência de mercado salva.");
      setForm(VAZIO);
      carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const editar = (m) => setForm({
    origem_regiao: m.origem_regiao, destino_regiao: m.destino_regiao,
    modal: m.modal || "", tipo_operacao: m.tipo_operacao || "TODOS",
    faixa_peso_min: m.faixa_peso_min, faixa_peso_max: m.faixa_peso_max,
    rs_kg_p10: m.rs_kg_p10, rs_kg_p25: m.rs_kg_p25, rs_kg_p50: m.rs_kg_p50,
    rs_kg_p75: m.rs_kg_p75, rs_kg_p90: m.rs_kg_p90,
  });

  const remover = async (id) => {
    try {
      await mercadoApi.remover(id);
      sucesso("Linha removida.");
      carregar();
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const pct = (campo) => (
    <TextField
      label={campo.replace("rs_kg_", "").toUpperCase()}
      type="number" size="small" value={form[campo] ?? 0}
      onChange={(e) => set(campo, e.target.value)} sx={{ width: 96 }}
      InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
    />
  );

  return (
    <Box>
      <PageHeader
        titulo="Matriz OD — Mercado"
        subtitulo="Benchmark Logístico › Referência de mercado por Origem → Destino (source of truth)"
      />

      <Alert severity="info" icon={<GridOnIcon />} sx={{ mb: 2.5 }}>
        Esta é a <strong>fonte de verdade</strong> do benchmark de mercado em R$/kg,
        por par origem→destino e percentis (P10–P90). Os valores são <strong>globais</strong>
        {" "}e alimentam o comparativo do BID, o diagnóstico e a IA. A mediana <strong>P50</strong>
        {" "}é a referência principal; <strong>P75</strong> marca o limite do que ainda é
        “mercado”.
      </Alert>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
            Nova linha / editar
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
            <TextField select label="Origem" size="small" value={form.origem_regiao}
              onChange={(e) => set("origem_regiao", e.target.value)} sx={{ width: 160 }}>
              {REGIOES.map((r) => <MenuItem key={r} value={r}>{ROTULO_REGIAO[r]}</MenuItem>)}
            </TextField>
            <TextField select label="Destino" size="small" value={form.destino_regiao}
              onChange={(e) => set("destino_regiao", e.target.value)} sx={{ width: 160 }}>
              {REGIOES.map((r) => <MenuItem key={r} value={r}>{ROTULO_REGIAO[r]}</MenuItem>)}
            </TextField>
            <TextField select label="Operação" size="small" value={form.tipo_operacao}
              onChange={(e) => set("tipo_operacao", e.target.value)} sx={{ width: 150 }}>
              {TIPOS_OP.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </TextField>
            <TextField label="Modal (opcional)" size="small" value={form.modal}
              onChange={(e) => set("modal", e.target.value)} sx={{ width: 150 }} />
          </Stack>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
            {pct("rs_kg_p10")}{pct("rs_kg_p25")}{pct("rs_kg_p50")}{pct("rs_kg_p75")}{pct("rs_kg_p90")}
            <TextField label="Peso mín (kg)" type="number" size="small" value={form.faixa_peso_min ?? 0}
              onChange={(e) => set("faixa_peso_min", e.target.value)} sx={{ width: 120 }} />
            <TextField label="Peso máx (kg)" type="number" size="small" value={form.faixa_peso_max ?? 0}
              onChange={(e) => set("faixa_peso_max", e.target.value)} sx={{ width: 120 }} />
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={salvar} disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
            <Button variant="text" onClick={() => setForm(VAZIO)} disabled={salvando}>
              Limpar
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
            Matriz cadastrada
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sortDirection={orden.campo === "origem_regiao" ? (orden.asc ? "asc" : "desc") : false}>
                  <TableSortLabel active={orden.campo === "origem_regiao"}
                    direction={orden.campo === "origem_regiao" && !orden.asc ? "desc" : "asc"}
                    onClick={() => ordenar("origem_regiao")}>Origem → Destino</TableSortLabel>
                </TableCell>
                <TableCell>Operação</TableCell>
                <TableCell align="right">P10</TableCell>
                <TableCell align="right">P25</TableCell>
                <TableCell align="right">
                  <TableSortLabel active={orden.campo === "rs_kg_p50"}
                    direction={orden.campo === "rs_kg_p50" && !orden.asc ? "desc" : "asc"}
                    onClick={() => ordenar("rs_kg_p50")}>P50</TableSortLabel>
                </TableCell>
                <TableCell align="right">P75</TableCell>
                <TableCell align="right">
                  <TableSortLabel active={orden.campo === "rs_kg_p90"}
                    direction={orden.campo === "rs_kg_p90" && !orden.asc ? "desc" : "asc"}
                    onClick={() => ordenar("rs_kg_p90")}>P90</TableSortLabel>
                </TableCell>
                <TableCell>Fonte</TableCell>
                <TableCell align="center">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lista.length === 0 && !carregando && (
                <TableRow><TableCell colSpan={9} sx={{ color: "text.secondary", fontStyle: "italic" }}>
                  Nenhuma linha cadastrada. Adicione acima ou importe os corredores legados.
                </TableCell></TableRow>
              )}
              {listaOrdenada.map((m) => (
                <TableRow key={m.id} hover sx={{ cursor: "pointer" }} onClick={() => editar(m)}>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {ROTULO_REGIAO[m.origem_regiao] || m.origem_regiao} → {ROTULO_REGIAO[m.destino_regiao] || m.destino_regiao}
                  </TableCell>
                  <TableCell>{m.tipo_operacao}</TableCell>
                  <TableCell align="right">{m.rs_kg_p10?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p25?.toFixed(2)}</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>{m.rs_kg_p50?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p75?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p90?.toFixed(2)}</TableCell>
                  <TableCell>
                    <Chip size="small" label={m.fonte === "MERCADO_LEGADO" ? "Legado" : "Mercado"}
                      color={m.fonte === "MERCADO_LEGADO" ? "default" : "primary"} variant="outlined" />
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" color="error"
                      onClick={(e) => { e.stopPropagation(); remover(m.id); }}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Clique numa linha para carregar os valores no formulário e editar.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
