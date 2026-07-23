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
  benchmarksApi,
  bidApi,
  cidadesApi,
  clustersApi,
  corredoresApi,
  dashboardApi,
  dlgApi,
  empresasApi,
  fechamentoApi,
  hubsApi,
  importacaoApi,
  inteligenciaApi,
  mblApi,
  mclApi,
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

export function useEmpresa(id) {
  return useQuery({
    queryKey: qk.empresa(id),
    queryFn: () => empresasApi.obter(id),
    enabled: !!id,
  });
}

export function useMutacoesEmpresa() {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.empresas() });
  return {
    criar: useMutation({ mutationFn: (payload) => empresasApi.criar(payload), onSuccess: invalidar }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => empresasApi.atualizar(id, payload),
      onSuccess: invalidar,
    }),
    inativar: useMutation({ mutationFn: (id) => empresasApi.inativar(id), onSuccess: invalidar }),
  };
}

export function useMutacoesFilial(empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.filiais(empresaId) });
  return {
    criar: useMutation({
      mutationFn: (payload) => empresasApi.criarFilial(empresaId, payload),
      onSuccess: invalidar,
    }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => empresasApi.atualizarFilial(id, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (id) => empresasApi.removerFilial(id),
      onSuccess: invalidar,
    }),
  };
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

/* ───────────────────────────── Metas (por empresa) ──────────────────────── */

export function useMetaNacional(empresaId, opts = {}) {
  return useQuery({
    queryKey: qk.metasNacional(empresaId),
    queryFn: () => metasApi.obterNacional(empresaId),
    ...comEmpresa(empresaId),
    ...opts,
  });
}

export function useMetasRegionais(empresaId, opts = {}) {
  return useQuery({
    queryKey: qk.metasRegionais(empresaId),
    queryFn: () => metasApi.listarRegionais(empresaId),
    ...comEmpresa(empresaId),
    ...opts,
  });
}

export function useSalvarMetas(empresaId) {
  const qc = useQueryClient();
  return {
    nacional: useMutation({
      mutationFn: (payload) => metasApi.salvarNacional(empresaId, payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.metasNacional(empresaId) }),
    }),
    regional: useMutation({
      mutationFn: (payload) => metasApi.salvarRegional(empresaId, payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.metasRegionais(empresaId) }),
    }),
  };
}

/* ──────────────── Fechamento de Custo de Frete (fechamento mensal) ───────── */

export function useFechamentoMensal(empresaId, competencia, opts = {}) {
  return useQuery({
    queryKey: qk.fechamentoMensal(empresaId, competencia),
    queryFn: () => fechamentoApi.obter(empresaId, competencia),
    ...comEmpresa(empresaId),
    enabled: !!empresaId && !!competencia,
    ...opts,
  });
}

export function useHistoricoFechamentos(empresaId, limite = 13, opts = {}) {
  return useQuery({
    queryKey: qk.fechamentoHistorico(empresaId, limite),
    queryFn: () => fechamentoApi.historico(empresaId, limite),
    ...comEmpresa(empresaId),
    ...opts,
  });
}

export function useFechamentoMutacoes(empresaId) {
  const qc = useQueryClient();
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ["fechamento", "mensal", empresaId] });
    qc.invalidateQueries({ queryKey: qk.fechamentoHistorico(empresaId) });
  };
  return {
    salvar: useMutation({
      mutationFn: (payload) => fechamentoApi.salvar(empresaId, payload),
      onSuccess: invalidar,
    }),
    fechar: useMutation({
      mutationFn: (competencia) => fechamentoApi.fechar(empresaId, competencia),
      onSuccess: invalidar,
    }),
    reabrir: useMutation({
      mutationFn: (competencia) => fechamentoApi.reabrir(empresaId, competencia),
      onSuccess: invalidar,
    }),
  };
}

/* ──────────────── Benchmark % Frete (legado, tela Parâmetros de Mercado) ──── */

export function useBenchmarksPct(opts = {}) {
  return useQuery({ queryKey: qk.benchmarksRegioes(), queryFn: benchmarksApi.listar, ...opts });
}

export function useMutacoesBenchmarkPct() {
  const qc = useQueryClient();
  return {
    salvar: useMutation({
      mutationFn: ({ regiao, payload }) => benchmarksApi.salvar(regiao, payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.benchmarksRegioes() }),
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

export function useDlgOutliers(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.dlgOutliers(empresaId, params),
    queryFn: () => dlgApi.outliers(empresaId, params),
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
  // A chave do resumo é ["recomendacoes", "resumo", empresaId] — "resumo" na
  // posição 1, não empresaId — então invalidar só ["recomendacoes", empresaId]
  // bate com a lista mas não com o resumo, deixando os cards de totalizador
  // presos no valor do primeiro carregamento da tela.
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ["recomendacoes", empresaId] });
    qc.invalidateQueries({ queryKey: qk.recomendacoesResumo(empresaId) });
  };
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

export function useBenchmarkCorredores(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkCorredores(empresaId, params),
    queryFn: () => benchmarkApi.corredores(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useBenchmarkEconomia(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkEconomia(empresaId, params),
    queryFn: () => benchmarkApi.economia(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

/* v6.9 — Comparativo de Mercado, Simulador de Economia, Indicadores transversais */
export function useComparativoMercado(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkComparativoMercado(empresaId, params),
    queryFn: () => benchmarkApi.comparativoMercado(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useSimuladorEconomia(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkSimuladorEconomia(empresaId, params),
    queryFn: () => benchmarkApi.simuladorEconomia(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useIndicadoresMercado(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkIndicadoresMercado(empresaId, params),
    queryFn: () => benchmarkApi.indicadoresMercado(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

/* Só habilita quando os dois hubs foram escolhidos (além de haver empresa ativa) —
   evita disparar a simulação com um par incompleto. */
export function useSimuladorHub(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.benchmarkSimuladorHub(empresaId, params),
    queryFn: () => benchmarkApi.simuladorHub(empresaId, params),
    enabled: !!empresaId && !!params.hub_atual && !!params.hub_alt,
  });
}

export function useClusters(empresaId) {
  return useQuery({
    queryKey: qk.clusters(empresaId),
    queryFn: () => clustersApi.listar(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useMutacoesCluster(empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.clusters(empresaId) });
  return {
    criar: useMutation({
      mutationFn: (payload) => clustersApi.criar(empresaId, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (id) => clustersApi.remover(empresaId, id),
      onSuccess: invalidar,
    }),
    importarExcel: useMutation({
      mutationFn: (file) => clustersApi.importarExcel(empresaId, file),
      onSuccess: invalidar,
    }),
  };
}

export function useHubs(empresaId, apenasAtivos = false) {
  return useQuery({
    queryKey: qk.hubs(empresaId, apenasAtivos),
    queryFn: () => hubsApi.listar(empresaId, apenasAtivos),
    ...comEmpresa(empresaId),
  });
}

export function useMutacoesHub(empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.hubs(empresaId) });
  return {
    criar: useMutation({
      mutationFn: (payload) => hubsApi.criar(empresaId, payload),
      onSuccess: invalidar,
    }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => hubsApi.atualizar(empresaId, id, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (id) => hubsApi.remover(empresaId, id),
      onSuccess: invalidar,
    }),
  };
}

export function useCorredoresRef(empresaId) {
  return useQuery({
    queryKey: qk.corredoresRef(empresaId),
    queryFn: () => corredoresApi.listar(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useMutacoesCorredorRef(empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.corredoresRef(empresaId) });
  return {
    salvar: useMutation({
      mutationFn: (payload) => corredoresApi.salvar(empresaId, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (id) => corredoresApi.remover(empresaId, id),
      onSuccess: invalidar,
    }),
    importarExcel: useMutation({
      mutationFn: (file) => corredoresApi.importarExcel(empresaId, file),
      onSuccess: invalidar,
    }),
  };
}

export function useMercadoOD(params = {}) {
  return useQuery({ queryKey: qk.mercadoOD(params), queryFn: () => mercadoApi.listar(params) });
}

export function useMutacoesMercadoOD() {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: ["mercado-od"] });
  return {
    salvar: useMutation({ mutationFn: (payload) => mercadoApi.salvar(payload), onSuccess: invalidar }),
    remover: useMutation({ mutationFn: (id) => mercadoApi.remover(id), onSuccess: invalidar }),
    importarExcel: useMutation({ mutationFn: (file) => mercadoApi.importarExcel(file), onSuccess: invalidar }),
  };
}

/* ───────────────────────────── MBL ──────────────────────────────────────── */

export function useMblBenchmark(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.mblBenchmark(empresaId, params),
    queryFn: () => mblApi.benchmark(empresaId, params),
    ...comEmpresa(empresaId),
  });
}

export function useMblComparar(empresaId, params = {}) {
  return useQuery({
    queryKey: qk.mblComparar(empresaId, params),
    queryFn: () => mblApi.comparar(empresaId, params),
    enabled: !!empresaId && params.valor != null,
  });
}

export function useProcessarMbl(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params) => mblApi.processar(empresaId, params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mbl"] }),
  });
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

export function useMutacoesBid(empresaId) {
  const qc = useQueryClient();
  const invalidarLista = () => qc.invalidateQueries({ queryKey: qk.bidLista(empresaId) });
  return {
    criar: useMutation({
      mutationFn: (payload) => bidApi.criar(empresaId, payload),
      onSuccess: invalidarLista,
    }),
    atualizar: useMutation({
      mutationFn: ({ id, payload }) => bidApi.atualizar(id, payload),
      onSuccess: (_, { id }) => {
        invalidarLista();
        qc.invalidateQueries({ queryKey: qk.bid(id) });
      },
    }),
    alterarStatus: useMutation({
      mutationFn: ({ id, status }) => bidApi.alterarStatus(id, status),
      onSuccess: (_, { id }) => {
        invalidarLista();
        qc.invalidateQueries({ queryKey: qk.bid(id) });
      },
    }),
    deletar: useMutation({ mutationFn: (id) => bidApi.deletar(id), onSuccess: invalidarLista }),
  };
}

export function useBidEscopo(id) {
  return useQuery({ queryKey: qk.bidEscopo(id), queryFn: () => bidApi.listarEscopo(id), enabled: !!id });
}

export function useMutacoesEscopo(id, empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.bidEscopo(id) });
  return {
    gerar: useMutation({
      mutationFn: (payload) => bidApi.gerarEscopo(id, empresaId, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({
      mutationFn: (eid) => bidApi.deletarEscopoItem(id, eid),
      onSuccess: invalidar,
    }),
  };
}

export function useBidTransp(id) {
  return useQuery({ queryKey: qk.bidTransp(id), queryFn: () => bidApi.listarTransp(id), enabled: !!id });
}

export function useMutacoesTranspBid(id, empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.bidTransp(id) });
  return {
    convidar: useMutation({
      mutationFn: (payload) => bidApi.convidarTransp(id, empresaId, payload),
      onSuccess: invalidar,
    }),
    atualizar: useMutation({
      mutationFn: ({ tid, payload }) => bidApi.atualizarTransp(id, tid, payload),
      onSuccess: invalidar,
    }),
    status: useMutation({
      mutationFn: ({ tid, status }) => bidApi.statusTransp(id, tid, status),
      onSuccess: invalidar,
    }),
    remover: useMutation({ mutationFn: (tid) => bidApi.removerTransp(id, tid), onSuccess: invalidar }),
  };
}

export function useBidPropostas(id) {
  return useQuery({ queryKey: qk.bidPropostas(id), queryFn: () => bidApi.listarPropostas(id), enabled: !!id });
}

export function useMutacoesPropostas(id, empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.bidPropostas(id) });
  return {
    incluir: useMutation({ mutationFn: (payload) => bidApi.incluirProposta(id, payload), onSuccess: invalidar }),
    importar: useMutation({
      mutationFn: (arquivo) => bidApi.importarPropostas(id, empresaId, arquivo),
      onSuccess: invalidar,
    }),
    remover: useMutation({ mutationFn: (pid) => bidApi.deletarProposta(id, pid), onSuccess: invalidar }),
  };
}

export function useBidComparativo(id, empresaId) {
  return useQuery({
    queryKey: qk.bidComparativo(id, empresaId),
    queryFn: () => bidApi.comparativo(id, empresaId),
    enabled: !!id && !!empresaId,
  });
}

export function useBidEconomia(id, empresaId) {
  return useQuery({
    queryKey: qk.bidEconomia(id, empresaId),
    queryFn: () => bidApi.economia(id, empresaId),
    enabled: !!id && !!empresaId,
  });
}

export function useBidScores(id, empresaId) {
  return useQuery({
    queryKey: qk.bidScores(id, empresaId),
    queryFn: () => bidApi.scores(id, empresaId),
    enabled: !!id && !!empresaId,
  });
}

export function useBidSimulacoes(id) {
  return useQuery({ queryKey: qk.bidSimulacoes(id), queryFn: () => bidApi.listarSimulacoes(id), enabled: !!id });
}

export function useMutacoesSimulacoes(id, empresaId) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: qk.bidSimulacoes(id) });
  return {
    calcular: useMutation({ mutationFn: (payload) => bidApi.calcularSimulacao(id, empresaId, payload) }),
    salvar: useMutation({
      mutationFn: (payload) => bidApi.salvarSimulacao(id, empresaId, payload),
      onSuccess: invalidar,
    }),
    remover: useMutation({ mutationFn: (sid) => bidApi.deletarSimulacao(id, sid), onSuccess: invalidar }),
  };
}

export function useBidAuditoria(id) {
  return useQuery({ queryKey: qk.bidAuditoria(id), queryFn: () => bidApi.auditoria(id), enabled: !!id });
}

/* ───────────────────────────── MCL ──────────────────────────────────────── */

export function useMclPrevia(bidId) {
  return useQuery({ queryKey: qk.mclPrevia(bidId), queryFn: () => mclApi.previa(bidId), enabled: !!bidId });
}

export function useMclHistorico(bidId) {
  return useQuery({ queryKey: qk.mclHistorico(bidId), queryFn: () => mclApi.historico(bidId), enabled: !!bidId });
}

export function useMutacoesMcl(bidId) {
  const qc = useQueryClient();
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: qk.mclPrevia(bidId) });
    qc.invalidateQueries({ queryKey: qk.mclHistorico(bidId) });
  };
  return {
    decidir: useMutation({ mutationFn: () => mclApi.decidir(bidId), onSuccess: invalidar }),
    simular: useMutation({ mutationFn: (payload) => mclApi.simular(bidId, payload) }),
  };
}

/* ───────────────────── Inteligência Logística (IA) ───────────────────────── */

export function useIaStatus(opts = {}) {
  return useQuery({ queryKey: qk.iaStatus(), queryFn: inteligenciaApi.status, ...opts });
}

export function useIaUso(empresaId) {
  return useQuery({
    queryKey: qk.iaUso(empresaId),
    queryFn: () => inteligenciaApi.uso(empresaId),
    ...comEmpresa(empresaId),
  });
}

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

export function useIaDiagnostico(empresaId) {
  return useQuery({
    queryKey: qk.iaDiagnostico(empresaId),
    queryFn: () => inteligenciaApi.obterDiagnostico(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useIaScoreHistorico(empresaId, opts = {}) {
  return useQuery({
    queryKey: qk.iaScoreHistorico(empresaId),
    queryFn: () => inteligenciaApi.historicoScore(empresaId),
    ...comEmpresa(empresaId),
    ...opts,
  });
}

export function useIaDiagnosticoHistorico(empresaId) {
  return useQuery({
    queryKey: qk.iaDiagnosticoHistorico(empresaId),
    queryFn: () => inteligenciaApi.historicoDiagnostico(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useIaBenchmarkSetorial(empresaId, opts = {}) {
  return useQuery({
    queryKey: qk.iaBenchmarkSetorial(empresaId),
    queryFn: () => inteligenciaApi.benchmarkSetorial(empresaId),
    ...comEmpresa(empresaId),
    ...opts,
  });
}

export function useIaSegmentos() {
  return useQuery({ queryKey: qk.iaSegmentos(), queryFn: inteligenciaApi.listarSegmentos });
}

export function useIaSessoes(empresaId) {
  return useQuery({
    queryKey: qk.iaSessoes(empresaId),
    queryFn: () => inteligenciaApi.listarSessoes(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useIaMensagens(sessaoId, empresaId) {
  return useQuery({
    queryKey: qk.iaMensagens(sessaoId, empresaId),
    queryFn: () => inteligenciaApi.listarMensagens(sessaoId, empresaId),
    enabled: !!sessaoId && !!empresaId,
  });
}

export function useRagStatus(empresaId) {
  return useQuery({
    queryKey: qk.ragStatus(empresaId),
    queryFn: () => inteligenciaApi.ragStatus(empresaId),
    ...comEmpresa(empresaId),
  });
}

export function useRagDocumentos(empresaId) {
  return useQuery({
    queryKey: qk.ragDocumentos(empresaId),
    queryFn: () => inteligenciaApi.ragDocumentos(empresaId),
    ...comEmpresa(empresaId),
  });
}

/* Mutações da Inteligência IA — cada uma invalida só o que ela afeta. */
export function useGerarInsights(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => inteligenciaApi.gerarInsights(empresaId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ia", "insights", empresaId] }),
  });
}

export function useMarcarLido(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (insightId) => inteligenciaApi.marcarLido(insightId, empresaId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ia", "insights", empresaId] }),
  });
}

export function useCalcularScore(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => inteligenciaApi.calcularScore(empresaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.iaScore(empresaId) });
      qc.invalidateQueries({ queryKey: qk.iaScoreHistorico(empresaId) });
    },
  });
}

export function useGerarDiagnosticoIA(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (forcar) => inteligenciaApi.gerarDiagnostico(empresaId, forcar),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.iaDiagnostico(empresaId) });
      qc.invalidateQueries({ queryKey: qk.iaDiagnosticoHistorico(empresaId) });
    },
  });
}

/* Compartilhada entre Inteligência IA (Oportunidades) e Benchmark Logístico
   (Recomendações) — mesma origem de dados (OportunidadeModel). */
export function useDetectarOportunidades(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => inteligenciaApi.detectarOportunidades(empresaId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.iaOportunidades(empresaId) }),
  });
}

export function useCriarSessaoAssistente(empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (titulo) => inteligenciaApi.criarSessao(empresaId, titulo),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.iaSessoes(empresaId) }),
  });
}

export function useEnviarMensagemAssistente(sessaoId, empresaId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mensagem) => inteligenciaApi.enviarMensagem(sessaoId, empresaId, mensagem),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.iaMensagens(sessaoId, empresaId) }),
  });
}

export function useMutacoesRag(empresaId) {
  const qc = useQueryClient();
  return {
    indexar: useMutation({
      mutationFn: (payload) => inteligenciaApi.ragIndexar(empresaId, payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.ragDocumentos(empresaId) }),
    }),
    buscar: useMutation({
      mutationFn: ({ consulta, topK }) => inteligenciaApi.ragBuscar(empresaId, consulta, topK),
    }),
    seedLegislacao: useMutation({
      mutationFn: () => inteligenciaApi.ragSeedLegislacao(),
      onSuccess: () => qc.invalidateQueries({ queryKey: qk.ragDocumentos(empresaId) }),
    }),
  };
}
