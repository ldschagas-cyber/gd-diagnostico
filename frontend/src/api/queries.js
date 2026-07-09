/**
 * Hooks de dados (React Query) sobre a camada `endpoints.js` já existente.
 *
 * Cada hook de leitura (useX) entrega { data, isLoading, isFetching, error, refetch }.
 * Cada hook de escrita (useCriarX...) invalida automaticamente o cache afetado,
 * satisfazendo a política de invalidação: incluir / alterar / excluir recarrega
 * a lista; o botão "Atualizar" chama refetch(); o TTL cuida do resto.
 *
 * Nenhuma requisição HTTP nova foi criada — reutilizamos os módulos de `endpoints.js`.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  benchmarkApi,
  bidApi,
  cidadesApi,
  clustersApi,
  corredoresApi,
  dashboardApi,
  dlgApi,
  empresasApi,
  hubsApi,
  importacaoApi,
  inteligenciaApi,
  mercadoApi,
  metasApi,
  recomendacoesApi,
  regioesApi,
  transportadorasApi,
  usuariosApi,
} from "./endpoints";
import { qk } from "./queryKeys";

/* Só habilita a query quando há empresa ativa (multi-tenant). */
const comEmpresa = (empresaId) => ({ enabled: !!empresaId });

/* ───────────────────────────── Empresas / Filiais ───────────────────────── */

export function useEmpresas(opts = {}) {
  return useQuery({ queryKey: qk.empresas(), queryFn: empresasApi.listar, ...opts });
}

export function useFiliais(empresaId) {
  return useQuery({
    queryKey: qk.filiais(empresaId),
    queryFn: () => empresasApi.listarFiliais(empresaId),
    ...comEmpresa(empresaId),
  });
}

/* ───────────────────────────── Cadastros ────────────────────────────────── */

export function useTransportadoras(empresaId) {
  return useQuery({
    queryKey: qk.transportadoras(empresaId),
    queryFn: () => transportadorasApi.listar(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useMutacoesTransportadora(empresaId) {
  const qc = useQueryClient();
  const invalidar = () =>
    qc.invalidateQueries({ queryKey: qk.transportadoras(empresaId) });
  return {
    criar: useMutation({
      mutationFn: (payload) => transportadorasApi.criar(empresaId, payload),
      onSuccess: invalidar,
    }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => transportadorasApi.atualizar(id, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (id) => transportadorasApi.remover(id),
      onSuccess: invalidar,
    }),
  };
}

export function useRegioes(opts = {}) {
  return useQuery({ queryKey: qk.regioes(), queryFn: regioesApi.listar, ...opts });
}

export function useCidades(opts = {}) {
  return useQuery({ queryKey: qk.cidades(), queryFn: cidadesApi.listar, ...opts });
}

export function useUsuarios(opts = {}) {
  return useQuery({ queryKey: qk.usuarios(), queryFn: usuariosApi.listar, ...opts });
}

/* Factory genérica de mutações para cadastros globais (regiões, cidades, usuários). */
export function useMutacoesCadastro(api, queryKey) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey });
  return {
    criar: useMutation({ mutationFn: (p) => api.criar(p), onSuccess: invalidar }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => api.atualizar(id, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({ mutationFn: (id) => api.remover(id), onSuccess: invalidar }),
  };
}

/* ───────────────────────────── Metas ────────────────────────────────────── */

export function useMetaNacional(opts = {}) {
  return useQuery({
    queryKey: qk.metasNacional(),
    queryFn: metasApi.obterNacional,
    ...opts,
  });
}

export function useMetasRegionais(opts = {}) {
  return useQuery({
    queryKey: qk.metasRegionais(),
    queryFn: metasApi.listarRegionais,
    ...opts,
  });
}

export function useSalvarMetas() {
  const qc = useQueryClient();
  return {
    nacional: useMutation({
      mutationFn: (payload) => metasApi.salvarNacional(payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.metasNacional() }),
    }),
    regional: useMutation({
      mutationFn: (payload) => metasApi.salvarRegional(payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.metasRegionais() }),
    }),
  };
}

/* ───────────────────── Diagnóstico Logístico / Dashboard ─────────────────── */

export function useDashboard(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.dashboard(empresaId, params),
    queryFn: () => dashboardApi.obter(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useDlgResumo(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.dlgResumo(empresaId, params),
    queryFn: () => dlgApi.resumo(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useDlgAnalitico(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.dlgAnalitico(empresaId, params),
    queryFn: () => dlgApi.analitico(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useProcessarDlg(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params) => dlgApi.processar(empresaId, params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dlg"] }),
  });
}

/* ───────────────────────────── Recomendações ────────────────────────────── */

export function useRecomendacoes(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.recomendacoes(empresaId, params),
    queryFn: () => recomendacoesApi.listar(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useRecomendacoesResumo(empresaId) {
  return useQuery({
    queryKey: qk.recomendacoesResumo(empresaId),
    queryFn: () => recomendacoesApi.resumo(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useMutacoesRecomendacao(empresaId) {
  const qc = useQueryClient();
  const invalidar = () =>
    qc.invalidateQueries({ queryKey: ["recomendacoes", empresaId] });
  return {
    consolidar: useMutation({
      mutationFn: () => recomendacoesApi.consolidar(empresaId),
      onSuccess: invalidar,
    }),
    atualizarStatus: useMutation({
      mutationFn: ({ recId, status }) =>
        recomendacoesApi.atualizarStatus(empresaId, recId, status),
      onSuccess: invalidar,
    }),
  };
}

/* ───────────────────────────── Importação ───────────────────────────────── */

export function useContagemDados(empresaId) {
  return useQuery({
    queryKey: qk.contagemDados(empresaId),
    queryFn: () => importacaoApi.contarDados(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useCompetencias(empresaId) {
  return useQuery({
    queryKey: qk.competencias(empresaId),
    queryFn: () => importacaoApi.competencias(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useCancelamentos(empresaId) {
  return useQuery({
    queryKey: qk.cancelamentos(empresaId),
    queryFn: () => importacaoApi.cancelamentos(empresaId),
    ...comEmpresa(empresaId),
  });
}

/**
 * Após qualquer importação/exclusão de dados, invalida TUDO que depende dos
 * CT-es da empresa (dashboard, DLG, benchmark, recomendações, contagens...).
 */
export function useInvalidarDadosEmpresa() {
  const qc = useQueryClient();
  return (empresaId) => {
    ["dashboard", "dlg", "benchmark", "recomendacoes", "importacao", "ia"].forEach(
      (dominio) => qc.invalidateQueries({ queryKey: [dominio] })
    );
  };
}

/* ───────────────────────────── Benchmark ────────────────────────────────── */

export function useBenchmarkNacional(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkNacional(empresaId, params),
    queryFn: () => benchmarkApi.nacional(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useBenchmarkRegional(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkRegional(empresaId, params),
    queryFn: () => benchmarkApi.regional(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useBenchmarkTransportadoras(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkTransportadoras(empresaId, params),
    queryFn: () => benchmarkApi.transportadoras(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useBenchmarkExecutivo(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkExecutivo(empresaId, params),
    queryFn: () => benchmarkApi.executivo(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useClusters(empresaId) {
  return useQuery({
    queryKey: qk.clusters(empresaId),
    queryFn: () => clustersApi.listar(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useHubs(apenasAtivos = false) {
  return useQuery({
    queryKey: qk.hubs(apenasAtivos),
    queryFn: () => hubsApi.listar(apenasAtivos),
  });
}

export function useCorredoresRef() {
  return useQuery({ queryKey: qk.corredoresRef(), queryFn: corredoresApi.listar });
}

export function useMercadoOD(params = {}) {
  return useQuery({ queryKey: qk.mercadoOD(params), queryFn: () => mercadoApi.listar(params) });
}

/* ───────────────────── Concorrência Logística (BID) ──────────────────────── */

export function useBidLista(empresaId) {
  return useQuery({
    queryKey: qk.bidLista(empresaId),
    queryFn: () => bidApi.listar(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useBid(id) {
  return useQuery({
    queryKey: qk.bid(id),
    queryFn: () => bidApi.obter(id),
    enabled: !!id,
  });
}

export function useBidDashboard(empresaId) {
  return useQuery({
    queryKey: qk.bidDashboard(empresaId),
    queryFn: () => bidApi.dashboard(empresaId),
    ...comEmpresa(empresaId),
  });
}

/* ───────────────────── Inteligência Logística (IA) ───────────────────────── */

export function useIaDashboard(empresaId) {
  return useQuery({
    queryKey: qk.iaDashboard(empresaId),
    queryFn: () => inteligenciaApi.dashboard(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useIaInsights(empresaId, apenasNaoLidos = false) {
  return useQuery({
    queryKey: qk.iaInsights(empresaId, apenasNaoLidos),
    queryFn: () => inteligenciaApi.listarInsights(empresaId, apenasNaoLidos),
    ...comEmpresa(empresaId),
  });
}

export function useIaScore(empresaId) {
  return useQuery({
    queryKey: qk.iaScore(empresaId),
    queryFn: () => inteligenciaApi.obterScore(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useIaOportunidades(empresaId) {
  return useQuery({
    queryKey: qk.iaOportunidades(empresaId),
    queryFn: () => inteligenciaApi.listarOportunidades(empresaId),
    ...comEmpresa(empresaId),
  });
}
