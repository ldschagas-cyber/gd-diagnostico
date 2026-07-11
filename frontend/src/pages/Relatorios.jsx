import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  TextField,
  Grid,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import GridOnIcon from "@mui/icons-material/GridOn";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import { useFeedback } from "../components/Feedback";
import { relatoriosApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { GD } from "../theme";

function CartaoRelatorio({ icone, titulo, descricao, cor, textoBotao, onBaixar, ocupado }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Box
          sx={{
            width: 52,
            height: 52,
            borderRadius: 2,
            bgcolor: cor,
            color: "#fff",
            display: "grid",
            placeItems: "center",
            mb: 2,
          }}
        >
          {icone}
        </Box>
        <Typography variant="h6">{titulo}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2, flex: 1 }}>
          {descricao}
        </Typography>
        <Button variant="contained" onClick={onBaixar} disabled={ocupado} sx={{ bgcolor: cor }}>
          {ocupado ? "Gerando..." : textoBotao}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function Relatorios() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [filtro, , patchFiltro] = useTelaEstado("relatorios", { dataInicio: "", dataFim: "" });
  const { dataInicio, dataFim } = filtro;
  const setDataInicio = (v) => patchFiltro({ dataInicio: v });
  const setDataFim = (v) => patchFiltro({ dataFim: v });
  const [ocupado, setOcupado] = useState(null);

  const baixar = async (formato) => {
    setOcupado(formato);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      await relatoriosApi.baixar(empresaAtivaId, formato, params);
      sucesso(`Relatório ${formato === "excel" ? "Excel" : "PDF"} gerado.`);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível gerar o relatório."));
    } finally {
      setOcupado(null);
    }
  };

  const baixarBenchmark = async (formato) => {
    const chave = `bench_${formato}`;
    setOcupado(chave);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      await relatoriosApi.baixarBenchmark(empresaAtivaId, formato, params);
      sucesso(`Relatório de benchmark ${formato === "excel" ? "Excel" : "PDF"} gerado.`);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível gerar o relatório de benchmark."));
    } finally {
      setOcupado(null);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Relatórios" subtitulo="Diagnóstico de frete em Excel e PDF" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Selecione a empresa ativa para gerar o relatório de diagnóstico."
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Relatórios"
        subtitulo={`Diagnóstico de ${empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}`}
      />

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            Período (opcional)
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ maxWidth: 420 }}>
            <TextField
              label="De"
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Até"
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6}>
          <CartaoRelatorio
            icone={<GridOnIcon />}
            titulo="Relatório Excel"
            descricao="Planilha com abas de resumo, indicadores regionais, transportadoras, prazos e oportunidades — ideal para análise detalhada."
            cor={GD.ok}
            textoBotao="Baixar Excel"
            onBaixar={() => baixar("excel")}
            ocupado={ocupado === "excel"}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <CartaoRelatorio
            icone={<PictureAsPdfIcon />}
            titulo="Relatório PDF"
            descricao="Documento de diagnóstico com identidade visual GD Conecta — pronto para apresentar ao cliente."
            cor={GD.danger}
            textoBotao="Baixar PDF"
            onBaixar={() => baixar("pdf")}
            ocupado={ocupado === "pdf"}
          />
        </Grid>
      </Grid>

      <Typography variant="subtitle1" sx={{ mt: 4, mb: 1.5, fontWeight: 700 }}>
        Benchmark Logístico
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Relatório consolidado comparando os indicadores da empresa com as referências de
        mercado — nacional, regional, transportadoras e potencial de economia.
      </Typography>
      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6}>
          <CartaoRelatorio
            icone={<GridOnIcon />}
            titulo="Benchmark — Excel"
            descricao="Planilha com abas de comparação nacional, regional, ranking de transportadoras e projeção de economia."
            cor={GD.blue}
            textoBotao="Baixar Excel"
            onBaixar={() => baixarBenchmark("excel")}
            ocupado={ocupado === "bench_excel"}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <CartaoRelatorio
            icone={<PictureAsPdfIcon />}
            titulo="Benchmark — PDF"
            descricao="Documento executivo de benchmark com classificações e economia potencial — pronto para a diretoria do cliente."
            cor={GD.indigo}
            textoBotao="Baixar PDF"
            onBaixar={() => baixarBenchmark("pdf")}
            ocupado={ocupado === "bench_pdf"}
          />
        </Grid>
      </Grid>
    </Box>
  );
}
