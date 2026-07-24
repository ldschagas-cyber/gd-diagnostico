import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useAuth } from "../contexts/AuthContext";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

export default function SelecionarEmpresa() {
  const { usuario, logout } = useAuth();
  const { empresas, selecionar } = useEmpresa();
  const navigate = useNavigate();
  const [selecionada, setSelecionada] = useState("");

  const confirmar = () => {
    if (!selecionada) return;
    selecionar(Number(selecionada));
    navigate("/", { replace: true });
  };

  const sair = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1.1fr 1fr" },
      }}
    >
      {/* Painel de marca — idêntico ao da tela de login */}
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
            Antes de continuar, escolha em qual empresa você quer trabalhar. Depois de
            entrar, a empresa ativa fica fixa até você sair e logar de novo.
          </Typography>
        </Box>

        <Typography sx={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>
          Governança de Frete · Análise de Dados · Torre de Controle
        </Typography>
      </Box>

      {/* Card de seleção — na mesma posição do card de login */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          alignItems: "center",
          p: { xs: 3, sm: 6 },
        }}
      >
        <Box />

        <Paper variant="outlined" sx={{ p: { xs: 3, sm: 5 }, width: "100%", maxWidth: 420 }}>
          <IconButton onClick={sair} size="small" sx={{ mb: 1, ml: -1 }} aria-label="Sair">
            <ArrowBackIcon fontSize="small" />
          </IconButton>

          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            Olá, {usuario?.nome?.split(" ")[0] || "usuário"}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Você está vinculado a mais de uma empresa. Selecione qual deseja acessar.
          </Typography>

          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel id="empresa-label">Empresa</InputLabel>
            <Select
              labelId="empresa-label"
              label="Empresa"
              value={selecionada}
              onChange={(e) => setSelecionada(e.target.value)}
            >
              {empresas.map((e) => (
                <MenuItem key={e.id} value={e.id}>
                  {e.nome_fantasia || e.razao_social}
                  {e.status === "INATIVO" ? " · inativa" : ""}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button variant="contained" size="large" fullWidth disabled={!selecionada} onClick={confirmar}>
            Entrar
          </Button>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 3, textAlign: "center" }}
          >
            Precisa acessar outra empresa depois? Saia e faça login novamente.
          </Typography>
        </Paper>

        <Typography variant="caption" color="text.secondary">
          GD Conecta © {new Date().getFullYear()}
        </Typography>
      </Box>
    </Box>
  );
}
