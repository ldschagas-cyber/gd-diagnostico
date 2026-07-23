/**
 * Pré-carregamento (prefetch) de telas frequentes.
 *
 * Ao passar o mouse sobre um item do menu, disparamos a busca dos dados da tela
 * de destino ANTES do clique. Quando o usuário entra, os dados já estão em cache
 * e a tela aparece instantânea. O prefetch respeita o staleTime — não refaz a
 * requisição se os dados já estiverem frescos.
 */
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  benchmarkApi,
  dashboardApi,
  dlgApi,
  recomendacoesApi,
  transportadorasApi,
} from "../api/endpoints";
import { qk } from "../api/queryKeys";
import { useEmpresa } from "../contexts/EmpresaContext";

export function usePrefetch() {
  const qc = useQueryClient();
  const { empresaAtivaId } = useEmpresa();

  return useCallback(
    (rota) => {
      if (!empresaAtivaId) return;
      const pre = (queryKey, queryFn) =>
        qc.prefetchQuery({ queryKey, queryFn, staleTime: 60 * 1000 });

      // Mapa rota → dados a aquecer. Só as telas de maior tráfego.
      switch (rota) {
        case "/":
          pre(qk.dashboard(empresaAtivaId, { dataInicio: "", dataFim: "" }), () =>
            dashboardApi.obter(empresaAtivaId, {})
          );
          break;
        case "/diagnostico/dlg":
          pre(qk.dlgResumo(empresaAtivaId, {}), () => dlgApi.resumo(empresaAtivaId));
          break;
        case "/diagnostico/recomendacoes":
          pre(qk.recomendacoes(empresaAtivaId, {}), () =>
            recomendacoesApi.listar(empresaAtivaId, {})
          );
          break;
        case "/transportadoras":
          pre(qk.transportadoras(empresaAtivaId), () =>
            transportadorasApi.listar(empresaAtivaId)
          );
          break;
        case "/benchmark/comparativo-mercado":
          pre(qk.benchmarkNacional(empresaAtivaId, {}), () =>
            benchmarkApi.nacional(empresaAtivaId)
          );
          break;
        default:
          break;
      }
    },
    [qc, empresaAtivaId]
  );
}
