import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { EmpresaProvider } from "./contexts/EmpresaContext";
import { FeedbackProvider } from "./components/Feedback";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Empresas from "./pages/Empresas";
import Filiais from "./pages/Filiais";
import Transportadoras from "./pages/Transportadoras";
import Regioes from "./pages/Regioes";
import Cidades from "./pages/Cidades";
import Metas from "./pages/Metas";
import ImportacaoCte from "./pages/ImportacaoCte";
import ImportacaoExcel from "./pages/ImportacaoExcel";
import Relatorios from "./pages/Relatorios";
import Usuarios from "./pages/Usuarios";
import MatrizOD from "./pages/MatrizOD";
import DiagnosticoDLG from "./pages/DiagnosticoDLG";
import Recomendacoes from "./pages/Recomendacoes";
import BenchmarkMBL from "./pages/BenchmarkMBL";
import ConcorrenciaMCL from "./pages/ConcorrenciaMCL";
import BenchmarkDiagnostico from "./pages/BenchmarkDiagnostico";
import BenchmarkComparativoMercado from "./pages/BenchmarkComparativoMercado";
import PotencialEconomia from "./pages/PotencialEconomia";
import DashboardExecutivo from "./pages/DashboardExecutivo";
import HubsLogisticos from "./pages/HubsLogisticos";
import BenchmarksCorredor from "./pages/BenchmarksCorredor";
// Módulo Concorrência Logística (V3.1)
import BidDashboard from "./pages/BidDashboard";
import BidLista from "./pages/BidLista";
import BidFormulario from "./pages/BidFormulario";
import BidDetalhe from "./pages/BidDetalhe";
import BidVisaoGeral from "./pages/BidVisaoGeral";
import BidEscopo from "./pages/BidEscopo";
import BidTransportadoras from "./pages/BidTransportadoras";
import BidPropostas from "./pages/BidPropostas";
import BidComparativo from "./pages/BidComparativo";
import BidComparativoSelecao from "./pages/BidComparativoSelecao";
import BidSimulacao from "./pages/BidSimulacao";
import BidRelatorios from "./pages/BidRelatorios";

// V4 — Inteligência Logística com IA
import InteligenciaDashboard from "./pages/InteligenciaDashboard";
import DiagnosticoIA from "./pages/DiagnosticoIA";
import Insights from "./pages/Insights";
import ScoreLogistico from "./pages/ScoreLogistico";
import Oportunidades from "./pages/Oportunidades";
import AssistenteLogistico from "./pages/AssistenteLogistico";
import BaseConhecimento from "./pages/BaseConhecimento";

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
      <FeedbackProvider>
        <AuthProvider>
          <EmpresaProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                {/* ── Análise ── */}
                <Route path="/" element={<Dashboard />} />
                <Route path="/relatorios" element={<Relatorios />} />

                {/* ── Benchmark Logístico (v6.9 — módulo exclusivamente analítico) ── */}
                <Route path="/benchmark/executivo" element={<DashboardExecutivo />} />
                <Route path="/benchmark/diagnostico" element={<BenchmarkDiagnostico />} />
                <Route path="/benchmark/comparativo-mercado" element={<BenchmarkComparativoMercado />} />
                <Route path="/benchmark/economia" element={<PotencialEconomia />} />
                <Route path="/diagnostico/dlg" element={<DiagnosticoDLG />} />
                <Route path="/diagnostico/recomendacoes" element={<Recomendacoes />} />
                <Route path="/bid/decisao" element={<ConcorrenciaMCL />} />
                <Route path="/bid/mbl" element={<BenchmarkMBL />} />

                {/* ── Inteligência de Mercado ── */}
                <Route path="/inteligencia-mercado/matriz-od" element={<MatrizOD />} />

                {/* ── Rotas antigas (compatibilidade com links/favoritos salvos) ── */}
                <Route path="/benchmark/matriz-od" element={<Navigate to="/inteligencia-mercado/matriz-od" replace />} />
                <Route path="/benchmark/clusters" element={<Navigate to="/configuracoes/hubs-logisticos" replace />} />
                <Route path="/benchmark/nacional" element={<Navigate to="/benchmark/diagnostico" replace />} />
                <Route path="/benchmark/regional" element={<Navigate to="/benchmark/diagnostico" replace />} />
                <Route path="/benchmark/corredores" element={<Navigate to="/benchmark/diagnostico" replace />} />
                <Route path="/benchmark/transportadoras" element={<Navigate to="/benchmark/executivo" replace />} />
                <Route path="/benchmark/mbl" element={<Navigate to="/bid/mbl" replace />} />

                {/* ── Importação ── */}
                <Route path="/importar/cte" element={<ImportacaoCte />} />
                <Route path="/importar/excel" element={<ImportacaoExcel />} />

                {/* ── Concorrência Logística (V3.1) ── */}
                <Route path="/bid" element={<BidLista />} />
                <Route path="/bid/dashboard" element={<BidDashboard />} />
                <Route path="/bid/comparativo" element={<BidComparativoSelecao />} />
                <Route path="/bid/novo" element={<BidFormulario />} />
                <Route path="/bid/:id" element={<BidDetalhe />}>
                  <Route index element={<BidVisaoGeral />} />
                  <Route path="escopo" element={<BidEscopo />} />
                  <Route path="transportadoras" element={<BidTransportadoras />} />
                  <Route path="propostas" element={<BidPropostas />} />
                  <Route path="comparativo" element={<BidComparativo />} />
                  <Route path="simulacao" element={<BidSimulacao />} />
                  <Route path="relatorios" element={<BidRelatorios />} />
                </Route>

                {/* ── Inteligência Logística com IA (V4) ── */}
                <Route path="/inteligencia" element={<InteligenciaDashboard />} />
                <Route path="/inteligencia/insights" element={<Insights />} />
                <Route path="/inteligencia/diagnostico" element={<DiagnosticoIA />} />
                <Route path="/inteligencia/score" element={<ScoreLogistico />} />
                <Route path="/inteligencia/oportunidades" element={<Oportunidades />} />
                <Route path="/inteligencia/assistente" element={<AssistenteLogistico />} />
                <Route path="/inteligencia/conhecimento" element={<BaseConhecimento />} />

                {/* ── Cadastros ── */}
                <Route path="/empresas" element={<Empresas />} />
                <Route path="/filiais" element={<Filiais />} />
                <Route path="/transportadoras" element={<Transportadoras />} />
                <Route path="/regioes" element={<Regioes />} />
                <Route path="/cidades" element={<Cidades />} />
                <Route path="/metas" element={<Metas />} />
                <Route path="/configuracoes/hubs-logisticos" element={<HubsLogisticos />} />

                <Route
                  path="/configuracoes/corredores"
                  element={
                    <ProtectedRoute soAdmin>
                      <BenchmarksCorredor />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/usuarios"
                  element={
                    <ProtectedRoute soAdmin>
                      <Usuarios />
                    </ProtectedRoute>
                  }
                />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </EmpresaProvider>
        </AuthProvider>
      </FeedbackProvider>
    </BrowserRouter>
    </ErrorBoundary>
  );
}
