import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  InputAdornment,
  IconButton,
  Alert,
  Stack,
} from "@mui/material";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import { useAuth } from "../contexts/AuthContext";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = location.state?.from?.pathname || "/";

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  const submeter = async () => {
    setErro("");
    setCarregando(true);
    try {
      await login(email, senha);
      navigate(destino, { replace: true });
    } catch (e) {
      setErro(extrairErro(e, "Não foi possível entrar. Verifique suas credenciais."));
    } finally {
      setCarregando(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1.1fr 1fr" },
      }}
    >
      {/* Painel de marca */}
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "space-between",
          p: 6,
          bgcolor: GD.indigo,
          color: "#fff",
          backgroundImage:
            "radial-gradient(circle at 80% 10%, rgba(201,168,76,0.18), transparent 45%)",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 2,
              bgcolor: GD.amber,
              color: GD.indigo,
              display: "grid",
              placeItems: "center",
              fontFamily: "'Sora', sans-serif",
              fontWeight: 700,
            }}
          >
            GD
          </Box>
          <Typography sx={{ fontFamily: "'Sora', sans-serif", fontWeight: 600 }}>
            GD Conecta
          </Typography>
        </Box>

        <Box>
          <Typography
            variant="h3"
            sx={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, mb: 2 }}
          >
            Torre de Controle
            <br />
            de Frete
          </Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.75)", maxWidth: 420, lineHeight: 1.7 }}>
            O TMS mostra o número; o diagnóstico diz o que fazer com ele. Importe
            CT-es e planilhas, acompanhe indicadores por região e transportadora e
            transforme dados em redução de custo logístico.
          </Typography>
        </Box>

        <Typography sx={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>
          Governança de Frete · Análise de Dados · Torre de Controle
        </Typography>
      </Box>

      {/* Formulário */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          alignItems: "center",
          p: { xs: 3, sm: 6 },
        }}
      >
        <Box /> {/* espaçador — alinha o card à mesma altura do bloco de texto no painel de marca */}

        <Paper variant="outlined" sx={{ p: { xs: 3, sm: 5 }, width: "100%", maxWidth: 420 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            Entrar
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Acesse o painel de diagnóstico de frete.
          </Typography>

          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="E-mail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submeter()}
              autoFocus
            />
            <TextField
              label="Senha"
              type={mostrarSenha ? "text" : "password"}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submeter()}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setMostrarSenha((v) => !v)}
                      edge="end"
                      size="small"
                    >
                      {mostrarSenha ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="contained"
              size="large"
              onClick={submeter}
              disabled={carregando || !email || !senha}
            >
              {carregando ? "Entrando..." : "Entrar"}
            </Button>
          </Stack>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 3, textAlign: "center" }}
          >
            Acesso inicial: admin@gdconecta.com.br
          </Typography>
        </Paper>

        <Typography variant="caption" color="text.secondary">
          GD Conecta © {new Date().getFullYear()}
        </Typography>
      </Box>
    </Box>
  );
}
