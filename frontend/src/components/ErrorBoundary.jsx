import { Component } from "react";
import { Box, Typography, Button, Paper } from "@mui/material";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import { GD } from "../theme";

/**
 * ErrorBoundary — captura erros de runtime em componentes filhos e exibe
 * uma tela amigável em vez de crashar toda a aplicação.
 *
 * Uso: envolva seções críticas ou o App inteiro.
 *
 * Correção da auditoria: P-17 (Alta) — ausência de Error Boundary.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Em produção, aqui seria integrado ao Sentry ou similar.
    console.error("[ErrorBoundary] Erro capturado:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "60vh",
            p: 4,
          }}
        >
          <Paper elevation={2} sx={{ p: 4, maxWidth: 480, textAlign: "center" }}>
            <ErrorOutlineIcon sx={{ fontSize: 56, color: GD.amber, mb: 2 }} />
            <Typography variant="h6" sx={{ color: GD.indigo, mb: 1 }}>
              Algo deu errado
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Ocorreu um erro inesperado nesta seção. Você pode tentar recarregar
              a página ou retornar ao início.
            </Typography>
            <Button
              variant="contained"
              onClick={() => window.location.reload()}
              sx={{ mr: 1 }}
            >
              Recarregar
            </Button>
            <Button variant="outlined" onClick={() => (window.location.href = "/")}>
              Ir ao início
            </Button>
          </Paper>
        </Box>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
