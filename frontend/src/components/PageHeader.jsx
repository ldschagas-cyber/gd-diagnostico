import { Box, Typography, Stack } from "@mui/material";

export default function PageHeader({ titulo, subtitulo, acoes, icone }) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "flex-start", sm: "center" }}
      spacing={2}
      sx={{ mb: 3 }}
    >
      <Box>
        <Stack direction="row" spacing={1.5} alignItems="center">
          {icone}
          <Typography variant="h4" component="h1">
            {titulo}
          </Typography>
        </Stack>
        {subtitulo && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {subtitulo}
          </Typography>
        )}
      </Box>
      {acoes && <Box>{acoes}</Box>}
    </Stack>
  );
}
