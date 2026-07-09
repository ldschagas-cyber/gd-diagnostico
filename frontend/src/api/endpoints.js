import api from "./client";

// ----------------------------- Autenticação -----------------------------
// Os tokens vêm e vão só via cookie httpOnly (S-04) — o frontend não lê nem
// guarda o access_token/refresh_token do corpo da resposta.
export const authApi = {
  async login(email, senha) {
    // O endpoint usa OAuth2PasswordRequestForm (campos username/password).
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", senha);
    const { data } = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },
  me: () => api.get("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout"),
};

// ------------------------------- Usuários -------------------------------
export const usuariosApi = {
  listar: () => api.get("/usuarios").then((r) => r.data),
  criar: (payload) => api.post("/usuarios", payload).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/usuarios/${id}`, payload).then((r) => r.data),
  remover: (id) => api.delete(`/usuarios/${id}`),
};

// ------------------------------- Empresas -------------------------------
export const empresasApi = {
  listar: () => api.get("/empresas").then((r) => r.data),
  obter: (id) => api.get(`/empresas/${id}`).then((r) => r.data),
  criar: (payload) => api.post("/empresas", payload).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/empresas/${id}`, payload).then((r) => r.data),
  inativar: (id) => api.delete(`/empresas/${id}`),
  // Filiais
  listarFiliais: (empresaId) =>
    api.get(`/empresas/${empresaId}/filiais`).then((r) => r.data),
  criarFilial: (empresaId, payload) =>
    api.post(`/empresas/${empresaId}/filiais`, payload).then((r) => r.data),
  atualizarFilial: (filialId, payload) =>
    api.put(`/empresas/filiais/${filialId}`, payload).then((r) => r.data),
  removerFilial: (filialId) => api.delete(`/empresas/filiais/${filialId}`),
};

// ---------------------------- Transportadoras ----------------------------
export const transportadorasApi = {
  listar: (empresaId) =>
    api.get("/transportadoras", { params: { empresa_id: empresaId } }).then((r) => r.data),
  criar: (empresaId, payload) =>
    api.post("/transportadoras", payload, { params: { empresa_id: empresaId } }).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/transportadoras/${id}`, payload).then((r) => r.data),
  remover: (id) => api.delete(`/transportadoras/${id}`),
};

// ------------------------------- Regiões --------------------------------
export const regioesApi = {
  listar: () => api.get("/regioes").then((r) => r.data),
  criar: (payload) => api.post("/regioes", payload).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/regioes/${id}`, payload).then((r) => r.data),
  remover: (id) => api.delete(`/regioes/${id}`),
  importarCsv: (file) => {
    const fd = new FormData();
    fd.append("arquivo", file);
    return api
      .post("/regioes/importar-csv", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};

// ------------------------------- Cidades --------------------------------
export const cidadesApi = {
  listar: () => api.get("/cidades").then((r) => r.data),
  criar: (payload) => api.post("/cidades", payload).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/cidades/${id}`, payload).then((r) => r.data),
  remover: (id) => api.delete(`/cidades/${id}`),
  baixarModelo: async () => {
    const { data } = await api.get("/cidades/modelo", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = "modelo_cidades.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  importarExcel: (file) => {
    const fd = new FormData();
    fd.append("arquivo", file);
    return api
      .post("/cidades/importar", fd, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
};

// -------------------------------- Metas ---------------------------------
export const metasApi = {
  obterNacional: () => api.get("/metas/nacional").then((r) => r.data),
  salvarNacional: (payload) => api.put("/metas/nacional", payload).then((r) => r.data),
  listarRegionais: () => api.get("/metas/regionais").then((r) => r.data),
  salvarRegional: (payload) => api.put("/metas/regionais", payload).then((r) => r.data),
};

// ------------------------------ Importação ------------------------------
export const importacaoApi = {
  importarCte: (empresaId, files, onProgress) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("arquivos", f));
    return api
      .post(`/importacao/cte/${empresaId}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
      })
      .then((r) => r.data);
  },
  importarExcel: (empresaId, file, atualizarExistentes = false) => {
    const fd = new FormData();
    fd.append("arquivo", file);
    fd.append("atualizar_existentes", atualizarExistentes ? "true" : "false");
    return api
      .post(`/importacao/excel/${empresaId}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  importarCancelamento: (empresaId, files, onProgress) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("arquivos", f));
    return api
      .post(`/importacao/cte/cancelamento/${empresaId}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
      })
      .then((r) => r.data);
  },
  cancelamentos: (empresaId) =>
    api.get(`/importacao/dados/${empresaId}/cancelamentos`).then((r) => r.data),
  contarDados: (empresaId) =>
    api.get(`/importacao/dados/${empresaId}/contagem`).then((r) => r.data),
  competencias: (empresaId) =>
    api.get(`/importacao/dados/${empresaId}/competencias`).then((r) => r.data),
  baixarModeloExcel: async () => {
    const { data } = await api.get(`/importacao/excel/modelo`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = "modelo_importacao_frete.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  excluirDados: (empresaId, quantidade, origem = null) => {
    const params = { confirmar_quantidade: quantidade };
    if (origem) params.origem = origem;
    return api
      .delete(`/importacao/dados/${empresaId}`, { params })
      .then((r) => r.data);
  },
};

// ------------------------------ Dashboard -------------------------------
export const dashboardApi = {
  obter: (empresaId, { dataInicio, dataFim } = {}) => {
    const params = {};
    if (dataInicio) params.data_inicio = dataInicio;
    if (dataFim) params.data_fim = dataFim;
    return api.get(`/dashboard/${empresaId}`, { params }).then((r) => r.data);
  },
};

// --------------------------- Recomendações (MELHORIA 8) ---------------------------
export const recomendacoesApi = {
  consolidar: (empresaId) =>
    api.post(`/recomendacoes/${empresaId}/consolidar`).then((r) => r.data),
  listar: (empresaId, params = {}) =>
    api.get(`/recomendacoes/${empresaId}`, { params }).then((r) => r.data),
  resumo: (empresaId) =>
    api.get(`/recomendacoes/${empresaId}/resumo`).then((r) => r.data),
  atualizarStatus: (empresaId, recId, status) =>
    api
      .patch(`/recomendacoes/${empresaId}/${recId}/status`, { status })
      .then((r) => r.data),
};

// ------------------------------ Relatórios ------------------------------
export const relatoriosApi = {
  baixar: async (empresaId, formato, params = {}) => {
    const { data, headers } = await api.get(
      `/relatorios/diagnostico/${empresaId}/${formato}`,
      { params, responseType: "blob" }
    );
    const url = window.URL.createObjectURL(new Blob([data]));
    const ext = formato === "excel" ? "xlsx" : "pdf";
    const link = document.createElement("a");
    link.href = url;
    link.download = `diagnostico_frete_${empresaId}.${ext}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return headers;
  },
};

// ------------------------------ Benchmarks ------------------------------
export const benchmarksApi = {
  listar: () => api.get("/benchmarks").then((r) => r.data),
  salvar: (regiao, payload) =>
    api.put(`/benchmarks/${regiao}`, payload).then((r) => r.data),
};

// ------------------------- Benchmark (análise) -------------------------
export const benchmarkApi = {
  nacional: (empresaId, params = {}) =>
    api.get(`/benchmark/nacional/${empresaId}`, { params }).then((r) => r.data),
  regional: (empresaId, params = {}) =>
    api.get(`/benchmark/regional/${empresaId}`, { params }).then((r) => r.data),
  transportadoras: (empresaId, params = {}) =>
    api.get(`/benchmark/transportadoras/${empresaId}`, { params }).then((r) => r.data),
};

// Economia e Dashboard Executivo (Fase D)
benchmarkApi.economia = (empresaId, params = {}) =>
  api.get(`/benchmark/economia/${empresaId}`, { params }).then((r) => r.data);
benchmarkApi.executivo = (empresaId, params = {}) =>
  api.get(`/benchmark/executivo/${empresaId}`, { params }).then((r) => r.data);

// V2.1 — Benchmark por Fluxo OD (corredores)
benchmarkApi.corredores = (empresaId, params = {}) =>
  api.get(`/benchmark/corredores/${empresaId}`, { params }).then((r) => r.data);

// ------------------------- Benchmark OD: cadastros -------------------------
// Catálogo global de hubs logísticos
export const hubsApi = {
  listar: (apenasAtivos = false) =>
    api.get("/hubs", { params: { apenas_ativos: apenasAtivos } }).then((r) => r.data),
  criar: (payload) => api.post("/hubs", payload).then((r) => r.data),
  atualizar: (id, payload) => api.put(`/hubs/${id}`, payload).then((r) => r.data),
  remover: (id) => api.delete(`/hubs/${id}`).then((r) => r.data),
};

// Mapa UF/município → hub, por empresa-cliente
export const clustersApi = {
  listar: (empresaId) =>
    api.get(`/empresas/${empresaId}/clusters`).then((r) => r.data),
  criar: (empresaId, payload) =>
    api.post(`/empresas/${empresaId}/clusters`, payload).then((r) => r.data),
  atualizar: (empresaId, id, payload) =>
    api.put(`/empresas/${empresaId}/clusters/${id}`, payload).then((r) => r.data),
  remover: (empresaId, id) =>
    api.delete(`/empresas/${empresaId}/clusters/${id}`).then((r) => r.data),
  baixarModelo: async (empresaId) => {
    const { data } = await api.get(`/empresas/${empresaId}/clusters/modelo`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = "modelo_clusters.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  importarExcel: (empresaId, file) => {
    const fd = new FormData();
    fd.append("arquivo", file);
    return api
      .post(`/empresas/${empresaId}/clusters/importar`, fd, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
};

// Referência de mercado por corredor (global, admin)
export const corredoresApi = {
  listar: () => api.get("/benchmarks-corredor").then((r) => r.data),
  salvar: (payload) => api.put("/benchmarks-corredor", payload).then((r) => r.data),
  remover: (id) => api.delete(`/benchmarks-corredor/${id}`).then((r) => r.data),
};

// Benchmark V2 — Matriz OD de mercado (source of truth, global, admin)
export const mercadoApi = {
  listar: (params = {}) => api.get("/benchmark-v2/mercado", { params }).then((r) => r.data),
  salvar: (payload) => api.put("/benchmark-v2/mercado", payload).then((r) => r.data),
  remover: (id) => api.delete(`/benchmark-v2/mercado/${id}`).then((r) => r.data),
};

// Download de relatório de Benchmark (PDF/Excel consolidado).
relatoriosApi.baixarBenchmark = async (empresaId, formato, params = {}) => {
  const { data, headers } = await api.get(
    `/relatorios/benchmark/${empresaId}/${formato}`,
    { params, responseType: "blob" }
  );
  const url = window.URL.createObjectURL(new Blob([data]));
  const ext = formato === "excel" ? "xlsx" : "pdf";
  const link = document.createElement("a");
  link.href = url;
  link.download = `benchmark_${empresaId}.${ext}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return headers;
};

// ════════════════════════════════════════════════════════
// BID — Concorrência Logística (V3.1)
// ════════════════════════════════════════════════════════
export const bidApi = {
  // BIDs
  listar:          (empresaId) => api.get("/bid", { params: { empresa_id: empresaId } }).then(r => r.data),
  obter:           (id) => api.get(`/bid/${id}`).then(r => r.data),
  criar:           (empresaId, payload) => api.post("/bid", payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  atualizar:       (id, payload) => api.put(`/bid/${id}`, payload).then(r => r.data),
  alterarStatus:   (id, status) => api.patch(`/bid/${id}/status`, { status }).then(r => r.data),
  deletar:         (id) => api.delete(`/bid/${id}`),
  dashboard:       (empresaId) => api.get("/bid/dashboard", { params: { empresa_id: empresaId } }).then(r => r.data),
  auditoria:       (id) => api.get(`/bid/${id}/auditoria`).then(r => r.data),

  // Escopo
  gerarEscopo:     (id, empresaId, payload) => api.post(`/bid/${id}/escopo/gerar`, payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  listarEscopo:    (id) => api.get(`/bid/${id}/escopo`).then(r => r.data),
  deletarEscopoItem: (id, eid) => api.delete(`/bid/${id}/escopo/${eid}`),

  // Transportadoras
  listarTransp:    (id) => api.get(`/bid/${id}/transportadoras`).then(r => r.data),
  convidarTransp:  (id, empresaId, payload) => api.post(`/bid/${id}/transportadoras`, payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  atualizarTransp: (id, tid, payload) => api.put(`/bid/${id}/transportadoras/${tid}`, payload).then(r => r.data),
  statusTransp:    (id, tid, status) => api.patch(`/bid/${id}/transportadoras/${tid}/status`, { status }).then(r => r.data),
  removerTransp:   (id, tid) => api.delete(`/bid/${id}/transportadoras/${tid}`),

  // Propostas
  listarPropostas: (id) => api.get(`/bid/${id}/propostas`).then(r => r.data),
  incluirProposta: (id, payload) => api.post(`/bid/${id}/propostas`, payload).then(r => r.data),
  importarPropostas: async (id, empresaId, arquivo) => {
    const form = new FormData(); form.append("arquivo", arquivo);
    return api.post(`/bid/${id}/propostas/importar`, form, { params: { empresa_id: empresaId }, headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
  },
  deletarProposta: (id, pid) => api.delete(`/bid/${id}/propostas/${pid}`),
  baixarModeloPropostas: async (id, empresaId) => {
    const r = await api.get(`/bid/${id}/propostas/modelo`, {
      params: { empresa_id: empresaId }, responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement("a"); a.href = url;
    a.download = `modelo_propostas_bid_${id}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  },

  // Análise
  comparativo:     (id, empresaId) => api.get(`/bid/${id}/comparativo`, { params: { empresa_id: empresaId } }).then(r => r.data),
  economia:        (id, empresaId) => api.get(`/bid/${id}/economia`, { params: { empresa_id: empresaId } }).then(r => r.data),
  scores:          (id, empresaId) => api.get(`/bid/${id}/score`, { params: { empresa_id: empresaId } }).then(r => r.data),

  // Simulação
  listarSimulacoes: (id) => api.get(`/bid/${id}/simulacoes`).then(r => r.data),
  calcularSimulacao: (id, empresaId, payload) => api.post(`/bid/${id}/simulacoes/calcular`, payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  salvarSimulacao: (id, empresaId, payload) => api.post(`/bid/${id}/simulacoes`, payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  deletarSimulacao: (id, sid) => api.delete(`/bid/${id}/simulacoes/${sid}`),

  // Relatórios
  baixarRelatorio: async (id, empresaId, tipo, formato) => {
    const r = await api.get(`/relatorios/bid/${id}/${tipo}/${formato}`, { params: { empresa_id: empresaId }, responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement("a"); a.href = url;
    a.download = `bid_${id}_${tipo}.${formato === "excel" ? "xlsx" : "pdf"}`;
    document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
  },
};


// ═══════════════ V4 — Inteligência Logística com IA ═══════════════
export const inteligenciaApi = {
  status: () => api.get("/inteligencia/status").then(r => r.data),

  // Insights
  gerarInsights:   (empresaId) => api.post("/inteligencia/insights/gerar", null, { params: { empresa_id: empresaId } }).then(r => r.data),
  listarInsights:  (empresaId, apenasNaoLidos = false) => api.get("/inteligencia/insights", { params: { empresa_id: empresaId, apenas_nao_lidos: apenasNaoLidos } }).then(r => r.data),
  marcarLido:      (insightId, empresaId) => api.patch(`/inteligencia/insights/${insightId}/lido`, null, { params: { empresa_id: empresaId } }).then(r => r.data),

  // Score
  calcularScore:   (empresaId) => api.post("/inteligencia/score/calcular", null, { params: { empresa_id: empresaId } }).then(r => r.data),
  obterScore:      (empresaId) => api.get("/inteligencia/score", { params: { empresa_id: empresaId } }).then(r => r.data),
  historicoScore:  (empresaId) => api.get("/inteligencia/score/historico", { params: { empresa_id: empresaId } }).then(r => r.data),

  // Diagnóstico IA
  gerarDiagnostico: (empresaId, forcar = false) => api.post("/inteligencia/diagnostico/gerar", null, { params: { empresa_id: empresaId, forcar } }).then(r => r.data),
  obterDiagnostico: (empresaId) => api.get("/inteligencia/diagnostico", { params: { empresa_id: empresaId } }).then(r => r.data),
  historicoDiagnostico: (empresaId) => api.get("/inteligencia/diagnostico/historico", { params: { empresa_id: empresaId } }).then(r => r.data),

  // Oportunidades
  detectarOportunidades: (empresaId) => api.post("/inteligencia/oportunidades/detectar", null, { params: { empresa_id: empresaId } }).then(r => r.data),
  listarOportunidades:   (empresaId) => api.get("/inteligencia/oportunidades", { params: { empresa_id: empresaId } }).then(r => r.data),

  // Assistente
  criarSessao:     (empresaId, titulo) => api.post("/inteligencia/assistente/sessoes", { titulo }, { params: { empresa_id: empresaId } }).then(r => r.data),
  listarSessoes:   (empresaId) => api.get("/inteligencia/assistente/sessoes", { params: { empresa_id: empresaId } }).then(r => r.data),
  listarMensagens: (sessaoId, empresaId) => api.get(`/inteligencia/assistente/sessoes/${sessaoId}/mensagens`, { params: { empresa_id: empresaId } }).then(r => r.data),
  enviarMensagem:  (sessaoId, empresaId, mensagem) => api.post(`/inteligencia/assistente/sessoes/${sessaoId}/mensagens`, { mensagem }, { params: { empresa_id: empresaId } }).then(r => r.data),

  // Dashboard e uso
  dashboard:       (empresaId) => api.get("/inteligencia/dashboard", { params: { empresa_id: empresaId } }).then(r => r.data),
  uso:             (empresaId) => api.get("/inteligencia/uso", { params: { empresa_id: empresaId } }).then(r => r.data),

  // Benchmark setorial
  benchmarkSetorial: (empresaId) => api.get("/inteligencia/benchmark-setorial", { params: { empresa_id: empresaId } }).then(r => r.data),
  listarSegmentos:   () => api.get("/inteligencia/benchmark-setorial/segmentos").then(r => r.data),

  // Relatório Executivo IA (download)
  baixarRelatorio: async (empresaId, formato) => {
    const ext = { pdf: "pdf", word: "docx", powerpoint: "pptx" }[formato] || "pdf";
    const r = await api.get(`/inteligencia/relatorio/${formato}`, { params: { empresa_id: empresaId }, responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement("a"); a.href = url;
    a.download = `relatorio_executivo_${empresaId}.${ext}`;
    document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
  },

  // RAG / Base de Conhecimento
  ragStatus:      (empresaId) => api.get("/inteligencia/rag/status", { params: { empresa_id: empresaId } }).then(r => r.data),
  ragDocumentos:  (empresaId) => api.get("/inteligencia/rag/documentos", { params: { empresa_id: empresaId } }).then(r => r.data),
  ragIndexar:     (empresaId, payload) => api.post("/inteligencia/rag/documentos", payload, { params: { empresa_id: empresaId } }).then(r => r.data),
  ragBuscar:      (empresaId, consulta, topK = 4) => api.post("/inteligencia/rag/buscar", { consulta, top_k: topK }, { params: { empresa_id: empresaId } }).then(r => r.data),
  ragSeedLegislacao: () => api.post("/inteligencia/rag/seed-legislacao").then(r => r.data),
};

// ───────────────────────────────────────────────────────────────
// DLG — Diagnóstico Logístico
// ───────────────────────────────────────────────────────────────
export const dlgApi = {
  processar: (empresaId, params = {}) =>
    api.post(`/dlg/${empresaId}/processar`, null, { params }).then((r) => r.data),
  analitico: (empresaId, params = {}) =>
    api.get(`/dlg/${empresaId}/analitico`, { params }).then((r) => r.data),
  outliers: (empresaId, params = {}) =>
    api.get(`/dlg/${empresaId}/outliers`, { params }).then((r) => r.data),
  resumo: (empresaId, params = {}) =>
    api.get(`/dlg/${empresaId}/resumo`, { params }).then((r) => r.data),
};

// ───────────────────────────────────────────────────────────────
// MBL — Benchmark Logístico (estatístico)
// ───────────────────────────────────────────────────────────────
export const mblApi = {
  processar: (empresaId, params = {}) =>
    api.post(`/mbl/${empresaId}/processar`, null, { params }).then((r) => r.data),
  benchmark: (empresaId, params = {}) =>
    api.get(`/mbl/${empresaId}/benchmark`, { params }).then((r) => r.data),
  comparar: (empresaId, params = {}) =>
    api.get(`/mbl/${empresaId}/comparar`, { params }).then((r) => r.data),
};

// ───────────────────────────────────────────────────────────────
// MCL — Concorrência Logística (motor de decisão de BID)
// ───────────────────────────────────────────────────────────────
export const mclApi = {
  previa: (bidId) => api.get(`/mcl/${bidId}/decidir`).then((r) => r.data),
  decidir: (bidId) => api.post(`/mcl/${bidId}/decidir`).then((r) => r.data),
  simular: (bidId, payload) => api.post(`/mcl/${bidId}/simular`, payload).then((r) => r.data),
  historico: (bidId) => api.get(`/mcl/${bidId}/historico`).then((r) => r.data),
};
