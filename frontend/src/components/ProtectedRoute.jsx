import { Navigate, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "../contexts/AuthContext";
import { useEmpresa } from "../contexts/EmpresaContext";

const ROTA_SELECAO_EMPRESA = "/selecionar-empresa";

export default function ProtectedRoute({ children, soAdmin = false }) {
  const { usuario, carregando } = useAuth();
  const { carregando: carregandoEmpresas, precisaEscolherEmpresa } = useEmpresa();
  const location = useLocation();

  if (carregando) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (carregandoEmpresas) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  const naTelaDeSelecao = location.pathname === ROTA_SELECAO_EMPRESA;

  // Vinculado a mais de uma empresa: obrigatório escolher antes de qualquer
  // outra tela do painel (v6.17 — evita lançar dados na empresa errada).
  if (precisaEscolherEmpresa && !naTelaDeSelecao) {
    return <Navigate to={ROTA_SELECAO_EMPRESA} replace />;
  }
  // Já escolhida (ou só há uma empresa): a tela de seleção não faz sentido.
  if (!precisaEscolherEmpresa && naTelaDeSelecao) {
    return <Navigate to="/" replace />;
  }

  if (soAdmin && !usuario.is_superuser) {
    return <Navigate to="/" replace />;
  }

  return children;
}
