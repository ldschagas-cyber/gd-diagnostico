import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box, Grid, Card, CardContent, CardActions, Typography,
  Button, Divider, Alert, Stack, Chip,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import TableChartIcon from "@mui/icons-material/TableChart";
import CodeIcon from "@mui/icons-material/Code";
import DescriptionIcon from "@mui/icons-material/Description";
import BarChartIcon from "@mui/icons-material/BarChart";
import SavingsIcon from "@mui/icons-material/Savings";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import { useEmpresa } from "../contexts/EmpresaContext";
import { bidApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useFeedback } from "../components/Feedback";
import { GD } from "../theme";

const RELATORIOS = [
  {
    tipo: "executivo",
    titulo: "Relatório Executivo",
    descricao: "Visão consolidada do BID: escopo, participantes, propostas recebidas e resultado geral.",
    icone: <DescriptionIcon sx={{ fontSize: 36, color: GD.indigo }} />,
    temExcel: false,
    temHtml: true,
  },
  {
    tipo: "comparativo",
    titulo: "Comparativo de Propostas",
    descricao: "Tabela detalhada comparando o custo atual com cada proposta recebida por grupo logístico.",
    icone: <BarChartIcon sx={{ fontSize: 36, color: GD.blue }} />,
    temExcel: true,
  },
  {
    tipo: "ranking",
    titulo: "Ranking Transportadoras",
    descricao: "Ordenação por score (Preço 40% + Prazo 30% + Cobertura 20% + Avaliação 10%).",
    icone: <EmojiEventsIcon sx={{ fontSize: 36, color: GD.amber }} />,
    temExcel: true,
  },
  {
    tipo: "economia",
    titulo: "Economia Potencial",
    descricao: "Projeções de saving: mensal, trimestral, semestral e anual por transportadora e grupo.",
    icone: <SavingsIcon sx={{ fontSize: 36, color: "#375623" }} />,
    temExcel: true,
  },
  {
    tipo: "resultado",
    titulo: "Resultado Final do BID",
    descricao: "Relatório de encerramento com transportadoras vencedoras, economia contratada e próximos passos.",
    icone: <EmojiEventsIcon sx={{ fontSize: 36, color: "#7030A0" }} />,
    temExcel: true,
  },
  {
    tipo: "pacote_cotacao",
    titulo: "Pacote de Cotação",
    descricao:
      "Documento para envio às transportadoras. Inclui volumes, regiões e perfil operacional — sem valores atuais pagos.",
    icone: <LocalShippingIcon sx={{ fontSize: 36, color: GD.indigo }} />,
    temExcel: false,
    destaque: true,
  },
];

export default function BidRelatorios() {
  const { id } = useParams();
  const { empresaAtivaId } = useEmpresa();
  const { erro: erroToast } = useFeedback();
  const [baixando, setBaixando] = useState({});

  const baixar = async (tipo, formato) => {
    const chave = `${tipo}_${formato}`;
    setBaixando((p) => ({ ...p, [chave]: true }));
    try {
      await bidApi.baixarRelatorio(id, empresaAtivaId, tipo, formato);
    } catch (e) {
      erroToast(extrairErro(e, "Não foi possível gerar o relatório."));
    } finally {
      setBaixando((p) => ({ ...p, [chave]: false }));
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 0.5, color: GD.indigo, fontWeight: 700 }}>
        Relatórios do BID
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Selecione o relatório desejado e escolha o formato de exportação.
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <strong>Pacote de Cotação:</strong> documento para envio às transportadoras — não expõe valores
        pagos atualmente nem dados de clientes finais.
      </Alert>

      <Grid container spacing={2}>
        {RELATORIOS.map((rel) => (
          <Grid item xs={12} md={6} key={rel.tipo}>
            <Card
              variant="outlined"
              sx={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                borderColor: rel.destaque ? GD.indigo : "divider",
                borderWidth: rel.destaque ? 2 : 1,
              }}
            >
              <CardContent sx={{ flex: 1 }}>
                <Stack direction="row" spacing={2} alignItems="flex-start" sx={{ mb: 1.5 }}>
                  {rel.icone}
                  <Box>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="subtitle1" fontWeight={700}>
                        {rel.titulo}
                      </Typography>
                      {rel.destaque && (
                        <Chip label="Enviar às transp." size="small" color="primary" />
                      )}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {rel.descricao}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>

              <Divider />

              <CardActions sx={{ px: 2, py: 1.5, gap: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<PictureAsPdfIcon />}
                  onClick={() => baixar(rel.tipo, "pdf")}
                  disabled={!!baixando[`${rel.tipo}_pdf`]}
                  sx={{ bgcolor: "#C00000", "&:hover": { bgcolor: "#9A0000" } }}
                >
                  {baixando[`${rel.tipo}_pdf`] ? "Gerando..." : "PDF"}
                </Button>

                {rel.temExcel && (
                  <Button
                    size="small"
                    variant="contained"
                    startIcon={<TableChartIcon />}
                    onClick={() => baixar(rel.tipo, "excel")}
                    disabled={!!baixando[`${rel.tipo}_excel`]}
                    sx={{ bgcolor: "#375623", "&:hover": { bgcolor: "#224016" } }}
                  >
                    {baixando[`${rel.tipo}_excel`] ? "Gerando..." : "Excel"}
                  </Button>
                )}

                {rel.temHtml && (
                  <Button
                    size="small"
                    variant="contained"
                    startIcon={<CodeIcon />}
                    onClick={() => baixar(rel.tipo, "html")}
                    disabled={!!baixando[`${rel.tipo}_html`]}
                    sx={{ bgcolor: GD.indigo, "&:hover": { bgcolor: GD.indigoDark } }}
                  >
                    {baixando[`${rel.tipo}_html`] ? "Gerando..." : "HTML"}
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
