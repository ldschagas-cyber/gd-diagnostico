import { QueryClient } from "@tanstack/react-query";

/**
 * Cliente global do React Query — política de cache de toda a aplicação.
 *
 * Decisões (B2B, dados que mudam por ação do usuário, não em tempo real):
 * - staleTime 5 min: dentro desse período os dados são considerados "frescos";
 *   voltar para uma tela reaproveita o cache SEM nova requisição.
 * - gcTime 30 min: mesmo após sair da tela, o cache é mantido por 30 min
 *   (garbage collection), permitindo retorno instantâneo.
 * - refetchOnWindowFocus false: não recarrega ao trocar de aba/janela — evita
 *   chamadas desnecessárias num painel corporativo.
 * - refetchOnReconnect true: revalida ao reconectar a internet.
 * - retry 1: uma tentativa extra em caso de falha transitória.
 *
 * A deduplicação de requisições em voo é automática: se dois componentes
 * pedirem a MESMA queryKey ao mesmo tempo, apenas uma requisição vai ao backend.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min "fresco"
      gcTime: 30 * 60 * 1000, // 30 min em cache
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      retry: 1,
      retryDelay: (tentativa) => Math.min(1000 * 2 ** tentativa, 8000),
    },
    mutations: {
      retry: 0,
    },
  },
});
