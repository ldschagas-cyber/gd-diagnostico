import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { EmpresaProvider } from "./contexts/EmpresaContext";
import { FeedbackProvider } from "./components/Feedback";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import SelecionarEmpresa from "./pages/SelecionarEmpresa";
import Dashboard from "./pages/Dashboard";
import Empresas from "./pages/Empresas";
import Filiais from "./pages/Filiais";
import Transportadoras from "./pages/Transportadoras";
import Regioes from "./pages/Regioes";
import Cidades from "./pages/Cidades";
import Metas from "./pages/Metas";
import FechamentoFrete from "./pages/FechamentoFrete";
import Importacao from "./pages/Importacao";
import Relatorios from "./pages/Relatorios";
import Usuarios from "./pages/Usuarios";
import MatrizOD from "./pages/MatrizOD";
import DiagnosticoDLG from "./pages/DiagnosticoDLG";
import Recomendacoes from "./pages/Recomendacoes";
import BenchmarkMBL from "./pages/BenchmarkMBL";
import ConcorrenciaMCL from "./pages/ConcorrenciaMCL";
import BenchmarkComparativoMercado from "./pages/BenchmarkComparativoMercado";
import PotencialEconomia from "./pages/PotencialEconomia";
import SimuladorHub from "./pages/SimuladorHub";
import DashboardExecutivo from "./pages/DashboardExecutivo";
import HubsLogisticos from "./pages/HubsLogisticos";
// Módulo Concorrência Logística (V3.1)
import BidDashboard from "./pages/BidDashboard";
import BidFormulario from "./pages/BidFormulario";
import BidDetalhe from "./pages/BidDetalhe";
import BidVisaoGeral from "./pages/BidVisaoGeral";
import BidEscopo from "./pages/BidEscopo";
import BidTransportadoras from "./pages/BidTransportadoras";
import BidPropostas from "./pages/BidPropostas";
import BidComparativo from "./pages/BidComparativo";
import BidSimulacao from "./pages/BidSimulacao";
import BidRelatorios from "./pages/BidRelatorios";

// V4 — Inteligência Logística com IA (Score foi absorvido pelo Dashboard
// Executivo, aba "Score Logístico"; Diagnóstico IA/Insights/Oportunidades/
// Visão Geral foram absorvidos por Recomendações, Potencial de Economia e
// Motor de Decisão — ver Recomendacoes.jsx/PotencialEconomia.jsx/ConcorrenciaMCL.jsx)
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
                path="/selecionar-empresa"
                element={
                  <ProtectedRoute>
                    <SelecionarEmpresa />
                  </ProtectedRoute>
                }
              />
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
                <Route path="/benchmark/comparativo-mercado" element={<BenchmarkComparativoMercado />} />
                <Route path="/benchmark/economia" element={<PotencialEconomia />} />
                <Route path="/benchmark/score" element={<Navigate to="/benchmark/executivo?aba=score" replace />} />
                <Route path="/benchmark/mbl" element={<BenchmarkMBL />} />
                <Route path="/benchmark/relatorios" element={<Navigate to="/relatorios" replace />} />
                <Route path="/concorrencia/relatorios" element={<Navigate to="/relatorios" replace />} />
                <Route path="/benchmark/simulador-hub" element={<Navigate to="/simulador/hub" replace />} />

                {/* ── Simulador ── */}
                <Route path="/simulador/hub" element={<SimuladorHub />} />
                <Route path="/diagnostico/dlg" element={<DiagnosticoDLG />} />
                <Route path="/diagnostico/recomendacoes" element={<Recomendacoes />} />
                <Route path="/bid/decisao" element={<ConcorrenciaMCL />} />

                {/* ── Parâmetros: Matriz Benchmark (admin — fonte global de mercado) ── */}
                <Route
                  path="/inteligencia-mercado/matriz-od"
                  element={
                    <ProtectedRoute soAdmin>
                      <MatrizOD />
                    </ProtectedRoute>
                  }
                />

                {/* ── Rotas antigas (compatibilidade com links/favoritos salvos) ── */}
                <Route path="/benchmark/matriz-od" element={<Navigate to="/inteligencia-mercado/matriz-od" replace />} />
                <Route path="/benchmark/clusters" element={<Navigate to="/configuracoes/hubs-logisticos" replace />} />
                <Route path="/benchmark/diagnostico" element={<Navigate to="/benchmark/comparativo-mercado" replace />} />
                <Route path="/benchmark/nacional" element={<Navigate to="/benchmark/comparativo-mercado" replace />} />
                <Route path="/benchmark/regional" element={<Navigate to="/benchmark/comparativo-mercado" replace />} />
                <Route path="/benchmark/corredores" element={<Navigate to="/benchmark/comparativo-mercado" replace />} />
                <Route path="/benchmark/transportadoras" element={<Navigate to="/benchmark/executivo" replace />} />
                <Route path="/bid/mbl" element={<Navigate to="/benchmark/mbl" replace />} />
                <Route path="/configuracoes/corredores" element={<Navigate to="/configuracoes/hubs-logisticos" replace />} />

                {/* ── Reorganização de menu (extinção do módulo IA + simplificação BID):
                     rotas antigas viram redirect para onde o conteúdo foi absorvido ── */}
                <Route path="/bid" element={<Navigate to="/bid/dashboard" replace />} />
                <Route path="/bid/comparativo" element={<Navigate to="/bid/dashboard" replace />} />
                <Route path="/inteligencia" element={<Navigate to="/diagnostico/recomendacoes" replace />} />
                <Route path="/inteligencia/diagnostico" element={<Navigate to="/diagnostico/recomendacoes" replace />} />
                <Route path="/inteligencia/insights" element={<Navigate to="/diagnostico/recomendacoes" replace />} />
                <Route path="/inteligencia/oportunidades" element={<Navigate to="/benchmark/economia" replace />} />
                <Route path="/inteligencia/score" element={<Navigate to="/benchmark/executivo?aba=score" replace />} />

                {/* ── Importação ── */}
                <Route path="/importar/cte" element={<Importacao />} />
                <Route path="/importar/excel" element={<Navigate to="/importar/cte" replace />} />

                {/* ── Concorrência Logística (V3.1) ── */}
                <Route path="/bid/dashboard" element={<BidDashboard />} />
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

                {/* ── Ferramentas globais (acessadas pelos ícones no topo, fora do menu) ── */}
                <Route path="/inteligencia/assistente" element={<AssistenteLogistico />} />
                <Route path="/inteligencia/conhecimento" element={<BaseConhecimento />} />

                {/* ── Cadastros ── */}
                <Route path="/empresas" element={<Empresas />} />
                <Route path="/filiais" element={<Filiais />} />
                <Route path="/transportadoras" element={<Transportadoras />} />
                <Route path="/regioes" element={<Regioes />} />
                <Route path="/cidades" element={<Cidades />} />
                <Route path="/metas" element={<Metas />} />
                <Route path="/fechamento-frete" element={<FechamentoFrete />} />
                {/* Referência de Frete aposentada — % Frete migrou para a Matriz Mercado (por corredor) */}
                <Route path="/configuracoes/parametros-mercado" element={<Navigate to="/inteligencia-mercado/matriz-od" replace />} />
                <Route path="/configuracoes/benchmark-pct" element={<Navigate to="/inteligencia-mercado/matriz-od" replace />} />
                <Route path="/configuracoes/hubs-logisticos" element={<HubsLogisticos />} />
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
