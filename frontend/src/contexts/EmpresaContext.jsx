import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useEmpresas } from "../api/queries";
import { qk } from "../api/queryKeys";
import { useAuth } from "./AuthContext";

const EmpresaContext = createContext(null);
const CHAVE_ATIVA = "gd_frete_empresa_ativa";

/**
 * Contexto da empresa ativa.
 *
 * A LISTA de empresas é servida pelo React Query (useEmpresas): fica em
 * cache, é deduplicada e compartilhada por toda a aplicação.
 *
 * Seleção de empresa no login (v6.17): usuário vinculado a mais de uma
 * empresa (inclui o superusuário global, que enxerga todas) precisa
 * escolher explicitamente em qual vai entrar — ver página
 * SelecionarEmpresa.jsx e o redirecionamento em ProtectedRoute.jsx.
 * Vinculado a uma única empresa continua entrando direto nela. Depois de
 * escolhida, a empresa ativa fica fixa para o restante da sessão — não há
 * troca pelo topo do painel; trocar exige sair e logar de novo (por isso o
 * logout limpa CHAVE_ATIVA do localStorage).
 */
export function EmpresaProvider({ children }) {
  const { usuario } = useAuth();
  const qc = useQueryClient();

  // Só busca quando há usuário autenticado.
  const { data: empresas = [], isLoading } = useEmpresas({ enabled: !!usuario });

  const [empresaAtivaId, setEmpresaAtivaId] = useState(
    () => Number(localStorage.getItem(CHAVE_ATIVA)) || null
  );

  // Auto-seleciona apenas quando há exatamente uma empresa vinculada — com
  // mais de uma, a escolha é explícita (tela de seleção pós-login).
  useEffect(() => {
    if (!empresas.length) return;
    setEmpresaAtivaId((atual) => {
      if (atual && empresas.some((e) => e.id === atual)) return atual;
      return empresas.length === 1 ? empresas[0].id : null;
    });
  }, [empresas]);

  // Persiste a empresa ativa para sobreviver a reloads dentro da mesma sessão.
  useEffect(() => {
    if (empresaAtivaId) localStorage.setItem(CHAVE_ATIVA, String(empresaAtivaId));
  }, [empresaAtivaId]);

  // Limpa a seleção no logout, inclusive do localStorage — assim o próximo
  // login sempre pede a escolha de novo quando há mais de uma empresa.
  useEffect(() => {
    if (!usuario) {
      setEmpresaAtivaId(null);
      localStorage.removeItem(CHAVE_ATIVA);
    }
  }, [usuario]);

  // "recarregar" mantém a assinatura antiga, agora invalidando o cache.
  const recarregar = () => qc.invalidateQueries({ queryKey: qk.empresas() });

  const empresaAtiva = empresas.find((e) => e.id === empresaAtivaId) || null;
  const precisaEscolherEmpresa = empresas.length > 1 && !empresaAtivaId;

  return (
    <EmpresaContext.Provider
      value={{
        empresas,
        empresaAtiva,
        empresaAtivaId,
        selecionar: setEmpresaAtivaId,
        recarregar,
        carregando: isLoading,
        precisaEscolherEmpresa,
      }}
    >
      {children}
    </EmpresaContext.Provider>
  );
}

export const useEmpresa = () => useContext(EmpresaContext);
