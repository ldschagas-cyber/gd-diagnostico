import { useEffect, useState } from "react";
import {
  Box, Card, CardActionArea, CardContent, Typography, Stack, TextField, Grid,
  FormControl, InputLabel, Select, MenuItem,
} from "@mui/material";
import SpaceDashboardIcon from "@mui/icons-material/SpaceDashboard";
import InsightsIcon from "@mui/icons-material/Insights";
import GavelIcon from "@mui/icons-material/Gavel";
import CodeIcon from "@mui/icons-material/Code";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import GridOnIcon from "@mui/icons-material/GridOn";
import PageHeader from "../components/PageHeader";
import { VazioEstado } from "../components/Tabela";
import CartaoRelatorio from "../components/CartaoRelatorio";
import BidStatusChip from "../components/BidStatusChip";
import { useFeedback } from "../components/Feedback";
import { useBidLista } from "../api/queries";
import { relatoriosApi, bidApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useTelaEstado } from "../hooks/useTelaEstado";
import { GD } from "../theme";

const TIPOS = [
  {
    chave: "diagnostico",
    titulo: "Diagnóstico Logístico",
    descricao: "Indicadores por dimensão, outliers e recomendações da operação da empresa.",
    icone: <SpaceDashboardIcon />,
    formatos: ["html", "excel"],
  },
  {
    chave: "benchmark",
    titulo: "Benchmark de Mercado",
    descricao: "Comparativo nacional, regional, por transportadora e potencial de economia.",
    icone: <InsightsIcon />,
    formatos: ["html", "pdf", "excel"],
  },
  {
    chave: "concorrencia",
    titulo: "Concorrência Logística",
    descricao: "Relatório executivo de um BID: escopo, ranking de transportadoras e economia.",
    icone: <GavelIcon />,
    formatos: ["html", "pdf", "excel"],
  },
];

const FORMATOS = {
  html: { rotulo: "HTML", icone: <CodeIcon />, cor: GD.indigo },
  pdf: { rotulo: "PDF", icone: <PictureAsPdfIcon />, cor: GD.blue },
  excel: { rotulo: "Excel", icone: <GridOnIcon />, cor: GD.amber },
};

const DESCRICAO_FORMATO = {
  diagnostico: {
    html: "Documento com identidade visual GD Conecta, indicadores por dimensão, outliers e recomendações — abre em qualquer navegador, pronto para apresentar ao cliente.",
    excel: "Planilha com indicadores nacionais, regionais, por dimensão, outliers e recomendações — para análise e cruzamento de dados.",
  },
  benchmark: {
    html: "Documento com identidade visual GD Conecta, comparativo nacional/regional/transportadoras, economia potencial e recomendações — abre em qualquer navegador.",
    pdf: "Documento executivo de benchmark com classificações e economia potencial — pronto para a diretoria do cliente.",
    excel: "Planilha com benchmark nacional, regional, por transportadora e potencial de economia — para análise e cruzamento de dados.",
  },
  concorrencia: {
    html: "Documento com identidade visual GD Conecta — abre em qualquer navegador, pronto para apresentar ao cliente.",
    pdf: "Documento executivo do BID selecionado, pronto para impressão ou envio por e-mail.",
    excel: "Planilha com escopo, transportadoras convidadas, ranking e potencial de economia do BID selecionado.",
  },
};

export default function Relatorios() {
  const { sucesso, erro: erroToast } = useFeedback();
  const { empresaAtiva, empresaAtivaId } = useEmpresa();
  const [filtro, , patchFiltro] = useTelaEstado("relatorios", {
    tipo: "diagnostico", dataInicio: "", dataFim: "", bidId: "",
  });
  const { tipo, dataInicio, dataFim, bidId } = filtro;
  const [ocupado, setOcupado] = useState(null);

  const { data: bids = [], isFetching: carregandoBids } = useBidLista(empresaAtivaId);

  useEffect(() => {
    if (tipo === "concorrencia" && !bidId && bids.length > 0) {
      patchFiltro({ bidId: bids[0].id });
    }
  }, [tipo, bidId, bids, patchFiltro]);

  const tipoAtivo = TIPOS.find((t) => t.chave === tipo);
  const bidSelecionado = bids.find((b) => b.id === bidId);
  const semBids = tipo === "concorrencia" && !carregandoBids && bids.length === 0;

  const baixar = async (formato) => {
    setOcupado(formato);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      if (tipo === "diagnostico") {
        await relatoriosApi.baixar(empresaAtivaId, formato, params);
      } else if (tipo === "benchmark") {
        await relatoriosApi.baixarBenchmark(empresaAtivaId, formato, params);
      } else {
        await bidApi.baixarRelatorio(bidId, empresaAtivaId, "executivo", formato);
      }
      sucesso(`Relatório de ${tipoAtivo.titulo.toLowerCase()} gerado.`);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível gerar o relatório."));
    } finally {
      setOcupado(null);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Relatórios" subtitulo="Diagnóstico, benchmark e concorrência logística" />
        <VazioEstado
          mensagem="Selecione uma empresa"
          descricao="Selecione a empresa ativa para gerar relatórios."
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        titulo="Relatórios"
        subtitulo={empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}
      />

      <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
        1. Escolha o relatório
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {TIPOS.map((t) => {
          const ativo = t.chave === tipo;
          return (
            <Grid item xs={12} sm={4} key={t.chave}>
              <Card
                variant="outlined"
                sx={{
                  height: "100%",
                  borderColor: ativo ? GD.indigo : "divider",
                  borderWidth: ativo ? 2 : 1,
                  bgcolor: ativo ? "rgba(45,53,97,0.05)" : "background.paper",
                }}
              >
                <CardActionArea sx={{ height: "100%" }} onClick={() => patchFiltro({ tipo: t.chave })}>
                  <CardContent>
                    <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                      <Box sx={{ color: ativo ? GD.indigo : "text.secondary", display: "flex" }}>{t.icone}</Box>
                      <Typography variant="subtitle1" fontWeight={700}>{t.titulo}</Typography>
                    </Stack>
                    <Typography variant="body2" color="text.secondary">{t.descricao}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {(tipo === "diagnostico" || tipo === "benchmark") && (
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
                onChange={(e) => patchFiltro({ dataInicio: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                label="Até"
                type="date"
                value={dataFim}
                onChange={(e) => patchFiltro({ dataFim: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Stack>
          </CardContent>
        </Card>
      )}

      {tipo === "concorrencia" && !semBids && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Selecione o BID
            </Typography>
            <FormControl sx={{ minWidth: 320 }}>
              <InputLabel id="bid-select-label">BID</InputLabel>
              <Select
                labelId="bid-select-label"
                label="BID"
                value={bidId}
                onChange={(e) => patchFiltro({ bidId: e.target.value })}
              >
                {bids.map((b) => (
                  <MenuItem key={b.id} value={b.id}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <span>{b.nome}</span>
                      <BidStatusChip status={b.status} />
                    </Stack>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {bidSelecionado?.objetivo && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
                Objetivo do BID: {bidSelecionado.objetivo}
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {semBids ? (
        <VazioEstado
          mensagem="Nenhum BID criado ainda"
          descricao="Crie um BID em Concorrência Logística → Dashboard BIDs para poder gerar o relatório."
        />
      ) : (
        <>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            2. Escolha o formato
          </Typography>
          <Grid container spacing={2.5}>
            {tipoAtivo.formatos.map((formato) => {
              const f = FORMATOS[formato];
              return (
                <Grid item xs={12} sm={4} key={formato}>
                  <CartaoRelatorio
                    icone={f.icone}
                    titulo={`${tipoAtivo.titulo} — ${f.rotulo}`}
                    descricao={DESCRICAO_FORMATO[tipo][formato]}
                    cor={f.cor}
                    textoBotao={`Baixar ${f.rotulo}`}
                    onBaixar={() => baixar(formato)}
                    ocupado={ocupado === formato}
                  />
                </Grid>
              );
            })}
          </Grid>
        </>
      )}
    </Box>
  );
}
