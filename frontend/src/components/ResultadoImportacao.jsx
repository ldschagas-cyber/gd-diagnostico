import { Grid, Card, CardContent, Typography, Box, Alert, Stack } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ArticleIcon from "@mui/icons-material/Article";
import SyncIcon from "@mui/icons-material/Sync";
import { GD } from "../theme";

function Quadro({ icone, valor, rotulo, cor }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ textAlign: "center" }}>
        <Box sx={{ color: cor, mb: 0.5 }}>{icone}</Box>
        <Typography variant="h4" sx={{ fontWeight: 700, color: cor }}>
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
        <Grid item xs={6} sm={3}>
          <Quadro
            icone={<CheckCircleIcon fontSize="large" />}
            valor={resultado.importados}
            rotulo="Importados"
            cor={GD.ok}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <Quadro
            icone={<LinkOffIcon fontSize="large" />}
            valor={resultado.ignorados_sem_vinculo}
            rotulo="Sem vínculo"
            cor={GD.warn}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <Quadro
            icone={<ContentCopyIcon fontSize="large" />}
            valor={resultado.duplicados}
            rotulo="Duplicados"
            cor={GD.slate}
          />
        </Grid>
        {resultado.atualizados > 0 && (
          <Grid item xs={6} sm={3}>
            <Quadro
              icone={<SyncIcon fontSize="large" />}
              valor={resultado.atualizados}
              rotulo="Atualizados"
              cor={GD.blue}
            />
          </Grid>
        )}
        <Grid item xs={6} sm={3}>
          <Quadro
            icone={<ArticleIcon fontSize="large" />}
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
