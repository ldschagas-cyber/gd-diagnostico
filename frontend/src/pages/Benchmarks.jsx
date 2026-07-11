import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  InputAdornment,
  CircularProgress,
  Alert,
  Divider,
  Chip,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import { useFeedback } from "../components/Feedback";
import { benchmarksApi } from "../api/endpoints";
import { extrairErro } from "../api/client";

// Ordem de exibição: Nacional primeiro, depois as macro-regiões.
const REGIOES = [
  { valor: "NACIONAL", rotulo: "Nacional", destaque: true },
  { valor: "NORTE", rotulo: "Norte" },
  { valor: "NORDESTE", rotulo: "Nordeste" },
  { valor: "CENTRO_OESTE", rotulo: "Centro-Oeste" },
  { valor: "SUDESTE", rotulo: "Sudeste" },
  { valor: "SUL", rotulo: "Sul" },
];

const VAZIO = {
  frete_kg_min: 0,
  frete_kg_medio: 0,
  frete_kg_max: 0,
  frete_pct_min: 0,
  frete_pct_medio: 0,
  frete_pct_max: 0,
};

export default function Benchmarks() {
  const { sucesso, erro: erroToast } = useFeedback();
  const [carregando, setCarregando] = useState(true);
  const [dados, setDados] = useState({});
  const [salvando, setSalvando] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const lista = await benchmarksApi.listar();
      const mapa = {};
      REGIOES.forEach((r) => {
        const existente = lista.find((b) => b.regiao === r.valor);
        mapa[r.valor] = existente ? { ...existente } : { regiao: r.valor, ...VAZIO };
      });
      setDados(mapa);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setCarregando(false);
    }
  }, [erroToast]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const atualizar = (regiao, campo, valor) =>
    setDados((prev) => ({ ...prev, [regiao]: { ...prev[regiao], [campo]: valor } }));

  const salvar = async (regiao) => {
    setSalvando(regiao);
    try {
      const d = dados[regiao];
      await benchmarksApi.salvar(regiao, {
        regiao,
        frete_kg_min: Number(d.frete_kg_min) || 0,
        frete_kg_medio: Number(d.frete_kg_medio) || 0,
        frete_kg_max: Number(d.frete_kg_max) || 0,
        frete_pct_min: Number(d.frete_pct_min) || 0,
        frete_pct_medio: Number(d.frete_pct_medio) || 0,
        frete_pct_max: Number(d.frete_pct_max) || 0,
      });
      sucesso(`Benchmark de ${REGIOES.find((r) => r.valor === regiao)?.rotulo} salvo.`);
    } catch (e) {
      erroToast(extrairErro(e));
    } finally {
      setSalvando(null);
    }
  };

  const campo = (regiao, nome, adorno, fim = false) => (
    <TextField
      type="number"
      size="small"
      value={dados[regiao]?.[nome] ?? 0}
      onChange={(e) => atualizar(regiao, nome, e.target.value)}
      sx={{ width: 104 }}
      InputProps={
        fim
          ? { endAdornment: <InputAdornment position="end">{adorno}</InputAdornment> }
          : { startAdornment: <InputAdornment position="start">{adorno}</InputAdornment> }
      }
    />
  );

  if (carregando) {
    return (
      <Box>
        <PageHeader titulo="Benchmark % Frete (legado)" subtitulo="Referência residual de % Frete/Mercadoria por região" />
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Benchmark % Frete (legado)"
        subtitulo="Configuração › cadastro remanescente do benchmark V1 — usado só para % Frete/Mercadoria"
      />

      <Alert severity="warning" sx={{ mb: 2.5 }}>
        <strong>Tela residual, escopo reduzido (v6.9.0).</strong> A referência de R$/kg
        deste cadastro não é mais consumida por nenhuma tela ou cálculo — foi
        substituída pela <strong>Matriz Benchmark (OD)</strong> em "Inteligência de
        Mercado". Os campos de <strong>% Frete/Mercadoria</strong> abaixo continuam
        ativos: alimentam a faixa de referência exibida no Dashboard e nas
        Recomendações, porque a Matriz Benchmark (OD) ainda não modela esse campo.
        Edite apenas as colunas de %.
      </Alert>

      <Card>
        <CardContent>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell rowSpan={2} sx={{ verticalAlign: "bottom" }}>
                    Região
                  </TableCell>
                  <TableCell colSpan={3} align="center" sx={{ borderLeft: "1px solid #eee" }}>
                    Frete por kg (R$)
                  </TableCell>
                  <TableCell colSpan={3} align="center" sx={{ borderLeft: "1px solid #eee" }}>
                    Frete s/ mercadoria (%)
                  </TableCell>
                  <TableCell rowSpan={2} sx={{ borderLeft: "1px solid #eee" }} />
                </TableRow>
                <TableRow>
                  <TableCell sx={{ borderLeft: "1px solid #eee" }}>Mín.</TableCell>
                  <TableCell>Médio</TableCell>
                  <TableCell>Máx.</TableCell>
                  <TableCell sx={{ borderLeft: "1px solid #eee" }}>Mín.</TableCell>
                  <TableCell>Médio</TableCell>
                  <TableCell>Máx.</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {REGIOES.map((r) => (
                  <TableRow key={r.valor}>
                    <TableCell>
                      <Chip
                        label={r.rotulo}
                        size="small"
                        color={r.destaque ? "primary" : "default"}
                        variant={r.destaque ? "filled" : "outlined"}
                      />
                    </TableCell>
                    <TableCell sx={{ borderLeft: "1px solid #eee" }}>
                      {campo(r.valor, "frete_kg_min", "R$")}
                    </TableCell>
                    <TableCell>{campo(r.valor, "frete_kg_medio", "R$")}</TableCell>
                    <TableCell>{campo(r.valor, "frete_kg_max", "R$")}</TableCell>
                    <TableCell sx={{ borderLeft: "1px solid #eee" }}>
                      {campo(r.valor, "frete_pct_min", "%", true)}
                    </TableCell>
                    <TableCell>{campo(r.valor, "frete_pct_medio", "%", true)}</TableCell>
                    <TableCell>{campo(r.valor, "frete_pct_max", "%", true)}</TableCell>
                    <TableCell sx={{ borderLeft: "1px solid #eee" }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => salvar(r.valor)}
                        disabled={salvando === r.valor}
                      >
                        {salvando === r.valor ? "..." : "Salvar"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
          <Divider sx={{ my: 2 }} />
          <Typography variant="caption" color="text.secondary">
            Os valores iniciais seguem a tabela de referência da especificação. Ajuste
            conforme a realidade de mercado do seu segmento.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
