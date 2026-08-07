import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function ProtectedRoute({ children }) {
  const { usuario, status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <div style={{ padding: 40, color: "var(--ink-dim)" }}>Carregando…</div>;
  }
  if (!usuario) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}
