import { Box, Card, CardContent, Typography, Button } from "@mui/material";

export default function CartaoRelatorio({ icone, titulo, descricao, cor, textoBotao, onBaixar, ocupado }) {
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
