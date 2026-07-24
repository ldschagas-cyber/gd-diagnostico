import { useRef, useState, useEffect } from "react";
import {
  Box, Card, CardContent, Typography, Stack, TextField, Button,
  Table, TableHead, TableRow, TableCell, TableBody, MenuItem, IconButton,
  Alert, LinearProgress, InputAdornment, Chip, TableSortLabel,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import GridOnIcon from "@mui/icons-material/GridOn";
import DownloadIcon from "@mui/icons-material/Download";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { useMercadoOD, useMutacoesMercadoOD } from "../api/queries";
import { mercadoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

const REGIOES = ["NORTE", "NORDESTE", "CENTRO_OESTE", "SUDESTE", "SUL"];
const ROTULO_REGIAO = {
  NORTE: "Norte", NORDESTE: "Nordeste", CENTRO_OESTE: "Centro-Oeste",
  SUDESTE: "Sudeste", SUL: "Sul",
};
const TIPOS_OP = ["TODOS", "FTL", "LTL", "FRACIONADO"];
// Mesmo vocabulário controlado de SetorEnum (backend). "TODOS" = referência
// genérica, sem segmentação — comportamento anterior a esta dimensão.
const SETORES = [
  "TODOS", "Indústria", "Distribuidor", "Atacado", "Varejo", "E-commerce",
  "Transportadora", "Operador Logístico", "Agronegócio", "Saúde",
  "Farmacêutico", "Alimentício", "Automotivo",
];
const rotuloSetor = (s) => (s === "TODOS" ? "Todos os setores" : s);

const VAZIO = {
  origem_regiao: "", destino_regiao: "", modal: "", tipo_operacao: "TODOS", setor: "TODOS",
  faixa_peso_min: 0, faixa_peso_max: 0,
  rs_kg_p10: 0, rs_kg_p25: 0, rs_kg_p50: 0, rs_kg_p75: 0, rs_kg_p90: 0,
  frete_pct_min: 0, frete_pct_medio: 0, frete_pct_max: 0,
  amostra_tamanho: "", metodologia: "", data_pesquisa: "",
};

export default function MatrizOD() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { data: lista = [], isLoading: carregando, error } = useMercadoOD();
  const { salvar: salvarMut, remover: removerMut, importarExcel: importarExcelMut } = useMutacoesMercadoOD();
  const [form, setForm] = useState(VAZIO);
  const [orden, setOrden] = useState({ campo: "origem_regiao", asc: true });
  const [filtroSetor, setFiltroSetor] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    if (error) erroToast(extrairErro(error));
  }, [error, erroToast]);

  const baixarModelo = async () => {
    try {
      await mercadoApi.baixarModelo();
    } catch (e) { erroToast(extrairErro(e)); }
  };

  const importarExcel = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      const r = await importarExcelMut.mutateAsync(file);
      const partes = [`${r.importados} linha(s) importada(s)`];
      if (r.atualizados > 0) partes.push(`${r.atualizados} atualizada(s)`);
      if (r.ignorados > 0) partes.push(`${r.ignorados} ignorada(s) (região inválida ou sem P50)`);
      sucesso(partes.join(" · ") + ".");
    } catch (ex) { erroToast(extrairErro(ex)); }
  };

  const ordenar = (campo) =>
    setOrden((o) => ({ campo, asc: o.campo === campo ? !o.asc : true }));

  const setoresPresentes = [...new Set(lista.map((m) => m.setor || "TODOS"))];

  const listaFiltrada = filtroSetor ? lista.filter((m) => (m.setor || "TODOS") === filtroSetor) : lista;
  const listaOrdenada = [...listaFiltrada].sort((a, b) => {
    const { campo, asc } = orden;
    let va = a[campo], vb = b[campo];
    if (campo === "origem_regiao") { va = `${a.origem_regiao}|${a.destino_regiao}`; vb = `${b.origem_regiao}|${b.destino_regiao}`; }
    if (campo === "amostra_tamanho") { va = a.amostra_tamanho ?? -1; vb = b.amostra_tamanho ?? -1; }
    if (typeof va === "string") return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    return asc ? (va - vb) : (vb - va);
  });

  const set = (campo, valor) => setForm((p) => ({ ...p, [campo]: valor }));

  const salvando = salvarMut.isPending;

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
    try {
      await salvarMut.mutateAsync({
        origem_regiao: form.origem_regiao,
        destino_regiao: form.destino_regiao,
        modal: form.modal || "",
        tipo_operacao: form.tipo_operacao || "TODOS",
        setor: form.setor || "TODOS",
        faixa_peso_min: Number(form.faixa_peso_min) || 0,
        faixa_peso_max: Number(form.faixa_peso_max) || 0,
        rs_kg_p10: Number(form.rs_kg_p10) || 0,
        rs_kg_p25: Number(form.rs_kg_p25) || 0,
        rs_kg_p50: p50,
        rs_kg_p75: Number(form.rs_kg_p75) || 0,
        rs_kg_p90: Number(form.rs_kg_p90) || 0,
        frete_pct_min: Number(form.frete_pct_min) || 0,
        frete_pct_medio: Number(form.frete_pct_medio) || 0,
        frete_pct_max: Number(form.frete_pct_max) || 0,
        amostra_tamanho: form.amostra_tamanho === "" ? null : Number(form.amostra_tamanho),
        metodologia: form.metodologia || "",
        data_pesquisa: form.data_pesquisa || null,
      });
      sucesso("Referência de mercado salva.");
      setForm(VAZIO);
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const editar = (m) => setForm({
    origem_regiao: m.origem_regiao, destino_regiao: m.destino_regiao,
    modal: m.modal || "", tipo_operacao: m.tipo_operacao || "TODOS", setor: m.setor || "TODOS",
    faixa_peso_min: m.faixa_peso_min, faixa_peso_max: m.faixa_peso_max,
    rs_kg_p10: m.rs_kg_p10, rs_kg_p25: m.rs_kg_p25, rs_kg_p50: m.rs_kg_p50,
    rs_kg_p75: m.rs_kg_p75, rs_kg_p90: m.rs_kg_p90,
    frete_pct_min: m.frete_pct_min ?? 0, frete_pct_medio: m.frete_pct_medio ?? 0,
    frete_pct_max: m.frete_pct_max ?? 0,
    amostra_tamanho: m.amostra_tamanho ?? "", metodologia: m.metodologia || "",
    data_pesquisa: m.data_pesquisa || "",
  });

  const remover = async (id) => {
    try {
      await removerMut.mutateAsync(id);
      sucesso("Linha removida.");
    } catch (e) {
      erroToast(extrairErro(e));
    }
  };

  const pct = (campo) => (
    <TextField
      label={campo.replace("rs_kg_", "").toUpperCase()}
      type="number" size="small" value={form[campo] ?? 0}
      onChange={(e) => set(campo, e.target.value)}
      InputProps={{ startAdornment: <InputAdornment position="start">R$</InputAdornment> }}
    />
  );

  const ROTULO_FRETE_PCT = { frete_pct_min: "% Frete mín.", frete_pct_medio: "% Frete méd.", frete_pct_max: "% Frete máx." };
  const fretePct = (campo) => (
    <TextField
      label={ROTULO_FRETE_PCT[campo]}
      type="number" size="small" value={form[campo] ?? 0}
      onChange={(e) => set(campo, e.target.value)}
      InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
      sx={{
        "& .MuiInputBase-root": { bgcolor: `${GD.ok}14` },
        "& .MuiInputLabel-root": { color: GD.ok },
      }}
    />
  );

  return (
    <Box>
      <PageHeader
        titulo="Matriz Mercado"
        subtitulo="Parâmetros › Referência de mercado por Origem → Destino (source of truth)"
      />

      <Alert severity="info" icon={<GridOnIcon />} sx={{ mb: 2.5 }}>
        Esta é a <strong>fonte de verdade</strong> do benchmark de mercado, por par origem→destino:
        R$/kg em percentis (P10–P90) e a faixa de <strong>% Frete/Mercadoria</strong> (mín/méd/máx).
        Os valores são <strong>globais</strong> e alimentam o comparativo do BID, o diagnóstico e a
        IA. A mediana <strong>P50</strong> é a referência principal; <strong>P75</strong> marca o
        limite do que ainda é "mercado".
      </Alert>

      <Stack direction="row" spacing={1.5} sx={{ mb: 2.5 }}>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={baixarModelo}>
          Baixar modelo
        </Button>
        <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileRef.current?.click()}>
          Importar Excel
        </Button>
        <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={importarExcel} />
      </Stack>

      {carregando && <LinearProgress sx={{ mb: 2 }} />}

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
            Nova linha / editar
          </Typography>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(5, 1fr)" },
              gap: 1.5, mb: 2,
            }}
          >
            <TextField select label="Origem" size="small" value={form.origem_regiao}
              onChange={(e) => set("origem_regiao", e.target.value)}>
              {REGIOES.map((r) => <MenuItem key={r} value={r}>{ROTULO_REGIAO[r]}</MenuItem>)}
            </TextField>
            <TextField select label="Destino" size="small" value={form.destino_regiao}
              onChange={(e) => set("destino_regiao", e.target.value)}>
              {REGIOES.map((r) => <MenuItem key={r} value={r}>{ROTULO_REGIAO[r]}</MenuItem>)}
            </TextField>
            <TextField select label="Setor" size="small" value={form.setor}
              onChange={(e) => set("setor", e.target.value)}>
              {SETORES.map((s) => <MenuItem key={s} value={s}>{rotuloSetor(s)}</MenuItem>)}
            </TextField>
            <TextField select label="Operação" size="small" value={form.tipo_operacao}
              onChange={(e) => set("tipo_operacao", e.target.value)}>
              {TIPOS_OP.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </TextField>
            <TextField label="Modal (opcional)" size="small" value={form.modal}
              onChange={(e) => set("modal", e.target.value)} />
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "repeat(2, 1fr)", sm: "repeat(3, 1fr)", md: "repeat(5, 1fr)" },
              gap: 1.5, mb: 0.5,
            }}
          >
            {pct("rs_kg_p10")}{pct("rs_kg_p25")}{pct("rs_kg_p50")}{pct("rs_kg_p75")}{pct("rs_kg_p90")}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
            P10/P25/P50/P75/P90 já cobrem mínimo/mediana/máximo de R$/kg — sem campos redundantes.
          </Typography>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "repeat(2, 1fr)", sm: "repeat(3, 1fr)", md: "repeat(5, 1fr)" },
              gap: 1.5, mb: 0.5,
            }}
          >
            {fretePct("frete_pct_min")}{fretePct("frete_pct_medio")}{fretePct("frete_pct_max")}
            <TextField label="Peso mín (kg)" type="number" size="small" value={form.faixa_peso_min ?? 0}
              onChange={(e) => set("faixa_peso_min", e.target.value)} />
            <TextField label="Peso máx (kg)" type="number" size="small" value={form.faixa_peso_max ?? 0}
              onChange={(e) => set("faixa_peso_max", e.target.value)} />
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
            % Frete vem da antiga Referência de Frete, agora por corredor. Peso mín/máx são campos
            existentes, só reposicionados aqui por simetria.
          </Typography>

          <Typography variant="overline" sx={{ color: GD.blue, fontWeight: 700, display: "block", mb: 1 }}>
            Proveniência da pesquisa
          </Typography>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
              gap: 1.5, mb: 2, p: 1.5,
              border: `1px dashed ${GD.blue}66`, borderRadius: 1.5,
              bgcolor: `${GD.blue}0F`,
            }}
          >
            <TextField label="Amostra (nº de cotações)" type="number" size="small"
              value={form.amostra_tamanho}
              onChange={(e) => set("amostra_tamanho", e.target.value)}
              helperText="coluna: amostra_tamanho" />
            <TextField label="Data da pesquisa" type="date" size="small"
              value={form.data_pesquisa} InputLabelProps={{ shrink: true }}
              onChange={(e) => set("data_pesquisa", e.target.value)}
              helperText="coluna: data_pesquisa" />
            <TextField label="Metodologia" size="small" value={form.metodologia}
              onChange={(e) => set("metodologia", e.target.value)}
              placeholder="ex.: cotação direta com 5 transportadoras, jan/2026"
              helperText="coluna: metodologia" />
          </Box>

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

          <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", rowGap: 1 }}>
            <Chip size="small" label="Todos" clickable
              color={filtroSetor === null ? "primary" : "default"}
              variant={filtroSetor === null ? "filled" : "outlined"}
              onClick={() => setFiltroSetor(null)} />
            {setoresPresentes.map((s) => (
              <Chip key={s} size="small" label={rotuloSetor(s)} clickable
                color={filtroSetor === s ? "primary" : "default"}
                variant={filtroSetor === s ? "filled" : "outlined"}
                onClick={() => setFiltroSetor(s)} />
            ))}
          </Stack>

          <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sortDirection={orden.campo === "origem_regiao" ? (orden.asc ? "asc" : "desc") : false}>
                  <TableSortLabel active={orden.campo === "origem_regiao"}
                    direction={orden.campo === "origem_regiao" && !orden.asc ? "desc" : "asc"}
                    onClick={() => ordenar("origem_regiao")}>Origem → Destino</TableSortLabel>
                </TableCell>
                <TableCell>Setor</TableCell>
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
                <TableCell align="right" sx={{ color: GD.ok }}>%Frete mín</TableCell>
                <TableCell align="right" sx={{ color: GD.ok }}>%Frete méd</TableCell>
                <TableCell align="right" sx={{ color: GD.ok }}>%Frete máx</TableCell>
                <TableCell>
                  <TableSortLabel active={orden.campo === "amostra_tamanho"}
                    direction={orden.campo === "amostra_tamanho" && !orden.asc ? "desc" : "asc"}
                    onClick={() => ordenar("amostra_tamanho")}>Amostra</TableSortLabel>
                </TableCell>
                <TableCell>Pesquisado em</TableCell>
                <TableCell>Fonte</TableCell>
                <TableCell align="center">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lista.length === 0 && !carregando && (
                <TableRow><TableCell colSpan={15} sx={{ color: "text.secondary", fontStyle: "italic" }}>
                  Nenhuma linha cadastrada. Adicione uma linha acima ou importe em massa via Excel.
                </TableCell></TableRow>
              )}
              {listaOrdenada.map((m) => (
                <TableRow key={m.id} hover sx={{ cursor: "pointer" }} onClick={() => editar(m)}>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {ROTULO_REGIAO[m.origem_regiao] || m.origem_regiao} → {ROTULO_REGIAO[m.destino_regiao] || m.destino_regiao}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" variant={(m.setor || "TODOS") === "TODOS" ? "outlined" : "filled"}
                      color={(m.setor || "TODOS") === "TODOS" ? "default" : "primary"}
                      label={rotuloSetor(m.setor || "TODOS")} />
                  </TableCell>
                  <TableCell>{m.tipo_operacao}</TableCell>
                  <TableCell align="right">{m.rs_kg_p10?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p25?.toFixed(2)}</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>{m.rs_kg_p50?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p75?.toFixed(2)}</TableCell>
                  <TableCell align="right">{m.rs_kg_p90?.toFixed(2)}</TableCell>
                  <TableCell align="right" sx={{ color: GD.ok }}>{m.frete_pct_min?.toFixed(1)}%</TableCell>
                  <TableCell align="right" sx={{ color: GD.ok }}>{m.frete_pct_medio?.toFixed(1)}%</TableCell>
                  <TableCell align="right" sx={{ color: GD.ok }}>{m.frete_pct_max?.toFixed(1)}%</TableCell>
                  <TableCell>
                    {m.amostra_tamanho == null ? (
                      <Chip size="small" label="não pesquisado" sx={{ color: GD.danger, borderColor: GD.danger }} variant="outlined" />
                    ) : (
                      <Chip size="small" label={`${m.amostra_tamanho} cotações`}
                        sx={{ color: m.amostra_tamanho < 5 ? GD.amberDark : GD.ok, borderColor: m.amostra_tamanho < 5 ? GD.amberDark : GD.ok }}
                        variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell>{m.data_pesquisa ? new Date(m.data_pesquisa + "T00:00:00").toLocaleDateString("pt-BR") : "—"}</TableCell>
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
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Clique numa linha para carregar os valores no formulário e editar.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
