import { Grid, Card, CardContent, Typography, Box, Alert, Stack } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ArticleIcon from "@mui/icons-material/Article";
import SyncIcon from "@mui/icons-material/Sync";
import EventBusyIcon from "@mui/icons-material/EventBusy";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import EditNoteIcon from "@mui/icons-material/EditNote";
import { GD } from "../theme";

function Quadro({ icone, valor, rotulo, cor }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ textAlign: "center", py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Box sx={{ color: cor, mb: 0.5, "& svg": { fontSize: 32 } }}>{icone}</Box>
        <Typography variant="h5" sx={{ fontWeight: 700, color: cor }}>
          {valor}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {rotulo}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function ResultadoImportacao({ resultado }) {
  if (!resultado) return null;
  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Resultado da importação
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={6} sm={4} md={2.4}>
          <Quadro
            icone={<CheckCircleIcon />}
            valor={resultado.importados}
            rotulo="Importados"
            cor={GD.ok}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2.4}>
          <Quadro
            icone={<LinkOffIcon />}
            valor={resultado.ignorados_sem_vinculo}
            rotulo="Sem vínculo"
            cor={GD.warn}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2.4}>
          <Quadro
            icone={<ContentCopyIcon />}
            valor={resultado.duplicados}
            rotulo="Duplicados"
            cor={GD.slate}
          />
        </Grid>
        {resultado.atualizados > 0 && (
          <Grid item xs={6} sm={4} md={2.4}>
            <Quadro
              icone={<SyncIcon />}
              valor={resultado.atualizados}
              rotulo="Atualizados"
              cor={GD.blue}
            />
          </Grid>
        )}
        {resultado.sem_identificador > 0 && (
          <Grid item xs={6} sm={4} md={2.4}>
            <Quadro
              icone={<ReportProblemIcon />}
              valor={resultado.sem_identificador}
              rotulo="Sem NF/CT-e"
              cor={GD.danger}
            />
          </Grid>
        )}
        {resultado.cancelados > 0 && (
          <Grid item xs={6} sm={4} md={2.4}>
            <Quadro
              icone={<EventBusyIcon />}
              valor={resultado.cancelados}
              rotulo="Cancelados"
              cor={GD.danger}
            />
          </Grid>
        )}
        {resultado.cartas_correcao > 0 && (
          <Grid item xs={6} sm={4} md={2.4}>
            <Quadro
              icone={<EditNoteIcon />}
              valor={resultado.cartas_correcao}
              rotulo="Cartas de Correção"
              cor={GD.warn}
            />
          </Grid>
        )}
        <Grid item xs={6} sm={4} md={2.4}>
          <Quadro
            icone={<ArticleIcon />}
            valor={resultado.total_processados}
            rotulo="Processados"
            cor={GD.indigo}
          />
        </Grid>
      </Grid>

      {resultado.ignorados_sem_vinculo > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {resultado.ignorados_sem_vinculo} documento(s) foram ignorados porque o
          tomador não corresponde à matriz nem a uma filial cadastrada da empresa.
        </Alert>
      )}

      {resultado.sem_identificador > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {resultado.sem_identificador} linha(s) da planilha foram descartadas por não
          ter Nota Fiscal nem CT-e preenchidos — nenhum dos dois identifica o
          documento, então a linha não pôde ser importada.
        </Alert>
      )}

      {resultado.cartas_correcao_ocorrencias?.length > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            Cartas de Correção registradas para revisão manual — NÃO aplicadas
            automaticamente ao CT-e:
          </Typography>
          <Stack spacing={0.5}>
            {resultado.cartas_correcao_ocorrencias.slice(0, 12).map((o, i) => (
              <Typography key={i} variant="body2">
                • CT-e ...{o.chave?.slice(-8)}: {o.mensagem.replace(
                  /^Correção proposta \(NÃO aplicada automaticamente — revisão manual necessária\): /,
                  "",
                )}
              </Typography>
            ))}
            {resultado.cartas_correcao_ocorrencias.length > 12 && (
              <Typography variant="body2">
                … e mais {resultado.cartas_correcao_ocorrencias.length - 12} ocorrência(s).
              </Typography>
            )}
          </Stack>
        </Alert>
      )}

      {resultado.erros?.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            Ocorrências:
          </Typography>
          <Stack spacing={0.5}>
            {resultado.erros.slice(0, 12).map((e, i) => (
              <Typography key={i} variant="body2">
                • {e}
              </Typography>
            ))}
            {resultado.erros.length > 12 && (
              <Typography variant="body2">
                … e mais {resultado.erros.length - 12} ocorrência(s).
              </Typography>
            )}
          </Stack>
        </Alert>
      )}
    </Box>
  );
}
