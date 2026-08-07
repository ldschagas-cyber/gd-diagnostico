import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardExecutivoPage from "./pages/DashboardExecutivoPage.jsx";
import OportunidadesPage from "./pages/OportunidadesPage.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardExecutivoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/oportunidades"
        element={
          <ProtectedRoute>
            <OportunidadesPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
