/**
 * Registro central das chaves de cache (queryKeys).
 *
 * Ter todas as chaves num único lugar garante:
 * - deduplicação: a mesma chave => uma única requisição / uma única entrada de cache;
 * - invalidação previsível: as mutações invalidam por prefixo (ex.: qk.transportadoras()
 *   invalida todas as listas de transportadoras, de qualquer empresa);
 * - consistência: nenhuma tela "inventa" uma chave divergente.
 *
 * Convenção: cada chave é um array [dominio, escopo?, params?]. O escopo costuma
 * ser o empresaAtivaId (multi-tenant), de modo que trocar de empresa troca o cache
 * automaticamente, sem misturar dados de clientes diferentes.
 */
export const qk = {
  // Autenticação / contexto
  me: () => ["me"],
  empresas: () => ["empresas"],
  empresa: (id) => ["empresas", id],
  filiais: (empresaId) => ["filiais", empresaId],

  // Cadastros
  transportadoras: (empresaId) => ["transportadoras", empresaId],
  regioes: () => ["regioes"],
  cidades: () => ["cidades"],
  usuarios: () => ["usuarios"],
  metasNacional: () => ["metas", "nacional"],
  metasRegionais: () => ["metas", "regionais"],

  // Diagnóstico Logístico
  dashboard: (empresaId, params = {}) => ["dashboard", empresaId, params],
  dlgResumo: (empresaId, params = {}) => ["dlg", "resumo", empresaId, params],
  dlgAnalitico: (empresaId, params = {}) => ["dlg", "analitico", empresaId, params],
  dlgOutliers: (empresaId, params = {}) => ["dlg", "outliers", empresaId, params],
  recomendacoes: (empresaId, params = {}) => ["recomendacoes", empresaId, params],
  recomendacoesResumo: (empresaId) => ["recomendacoes", "resumo", empresaId],

  // Importação
  contagemDados: (empresaId) => ["importacao", "contagem", empresaId],
  competencias: (empresaId) => ["importacao", "competencias", empresaId],
  cancelamentos: (empresaId) => ["importacao", "cancelamentos", empresaId],

  // Benchmark
  benchmarkNacional: (empresaId, params = {}) => ["benchmark", "nacional", empresaId, params],
  benchmarkRegional: (empresaId, params = {}) => ["benchmark", "regional", empresaId, params],
  benchmarkTransportadoras: (empresaId, params = {}) => ["benchmark", "transportadoras", empresaId, params],
  benchmarkEconomia: (empresaId, params = {}) => ["benchmark", "economia", empresaId, params],
  benchmarkExecutivo: (empresaId, params = {}) => ["benchmark", "executivo", empresaId, params],
  benchmarkCorredores: (empresaId, params = {}) => ["benchmark", "corredores", empresaId, params],
  benchmarksRegioes: () => ["benchmarks", "regioes"],
  hubs: (apenasAtivos = false) => ["hubs", apenasAtivos],
  clusters: (empresaId) => ["clusters", empresaId],
  corredoresRef: () => ["corredores-ref"],
  mercadoOD: (params = {}) => ["mercado-od", params],

  // Concorrência Logística (BID)
  bidLista: (empresaId) => ["bid", "lista", empresaId],
  bid: (id) => ["bid", id],
  bidDashboard: (empresaId) => ["bid", "dashboard", empresaId],
  bidEscopo: (id) => ["bid", id, "escopo"],
  bidTransp: (id) => ["bid", id, "transportadoras"],
  bidPropostas: (id) => ["bid", id, "propostas"],
  bidComparativo: (id, empresaId) => ["bid", id, "comparativo", empresaId],
  bidSimulacoes: (id) => ["bid", id, "simulacoes"],
  mclPrevia: (bidId) => ["mcl", bidId, "previa"],

  // Inteligência Logística (IA)
  iaStatus: () => ["ia", "status"],
  iaDashboard: (empresaId) => ["ia", "dashboard", empresaId],
  iaInsights: (empresaId, apenasNaoLidos = false) => ["ia", "insights", empresaId, apenasNaoLidos],
  iaScore: (empresaId) => ["ia", "score", empresaId],
  iaDiagnostico: (empresaId) => ["ia", "diagnostico", empresaId],
  iaOportunidades: (empresaId) => ["ia", "oportunidades", empresaId],
  iaSessoes: (empresaId) => ["ia", "sessoes", empresaId],
  iaMensagens: (sessaoId, empresaId) => ["ia", "mensagens", sessaoId, empresaId],
  ragDocumentos: (empresaId) => ["ia", "rag", "documentos", empresaId],
};
