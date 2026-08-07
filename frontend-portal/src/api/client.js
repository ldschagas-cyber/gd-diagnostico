import axios from "axios";

// Autenticação por cookie httpOnly (gd_frete_cliente_access/refresh) — o
// frontend nunca lê nem guarda token em JS, mesmo padrão do painel interno
// (mitigação S-04). withCredentials é o que faz o navegador anexar o cookie.
const baseURL = import.meta.env.VITE_API_URL || "/api/v1/portal";

export const api = axios.create({ baseURL, withCredentials: true });

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isAuthRoute = config?.url?.includes("/auth/");
    if (response?.status !== 401 || isAuthRoute || config._retried) {
      return Promise.reject(error);
    }
    config._retried = true;
    try {
      refreshPromise ??= api.post("/auth/refresh").finally(() => {
        refreshPromise = null;
      });
      await refreshPromise;
      return api(config);
    } catch (refreshError) {
      window.location.href = "/login";
      return Promise.reject(refreshError);
    }
  },
);
