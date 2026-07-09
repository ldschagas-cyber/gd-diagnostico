import axios from "axios";

// Base da API. Em dev, o proxy do Vite encaminha /api para o backend.
const baseURL = import.meta.env.VITE_API_URL || "/api/v1";

// Autenticação via cookie httpOnly (S-04): o token nunca fica acessível a
// JavaScript, então nunca é lido/gravado aqui — o navegador anexa o cookie
// sozinho em toda requisição (withCredentials) e o backend o valida.
const api = axios.create({ baseURL, withCredentials: true });

// ── Refresh automático do access token (R-05) ──────────────────────────────
let renovando = false;
let fila = [];

function resolverFila(ok) {
  fila.forEach((cb) => cb(ok));
  fila = [];
}

function irParaLogin() {
  if (!window.location.pathname.includes("/login")) {
    window.location.href = "/login";
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const ehLogin = original?.url?.includes("/auth/login");
    const ehRefresh = original?.url?.includes("/auth/refresh");

    if (status !== 401 || ehLogin || ehRefresh || original?._jaTentou) {
      if (status === 401 && !ehLogin && !original?._jaTentou) {
        irParaLogin();
      }
      return Promise.reject(error);
    }

    original._jaTentou = true;

    if (renovando) {
      return new Promise((resolve, reject) => {
        fila.push((ok) => (ok ? resolve(api(original)) : reject(error)));
      });
    }

    renovando = true;
    try {
      // Sem corpo: o refresh token vai no cookie httpOnly, não em JS.
      await axios.post(`${baseURL}/auth/refresh`, null, { withCredentials: true });
      resolverFila(true);
      return api(original);
    } catch (e) {
      resolverFila(false);
      irParaLogin();
      return Promise.reject(e);
    } finally {
      renovando = false;
    }
  }
);

export function extrairErro(error, padrao = "Ocorreu um erro inesperado.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return error?.message || padrao;
}

export default api;
