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
 * A LISTA de empresas passou a ser servida pelo React Query (useEmpresas):
 * fica em cache, é deduplicada e compartilhada por toda a aplicação — não é
 * mais recarregada a cada tela. A API pública do contexto foi mantida
 * idêntica (empresas, empresaAtiva, empresaAtivaId, selecionar, recarregar,
 * carregando), então nenhuma tela precisou mudar.
 */
export function EmpresaProvider({ children }) {
  const { usuario } = useAuth();
  const qc = useQueryClient();

  // Só busca quando há usuário autenticado.
  const { data: empresas = [], isLoading } = useEmpresas({ enabled: !!usuario });

  const [empresaAtivaId, setEmpresaAtivaId] = useState(
    () => Number(localStorage.getItem(CHAVE_ATIVA)) || null
  );

  // Seleção automática da empresa ativa quando a lista chega/muda.
  useEffect(() => {
    if (!empresas.length) return;
    setEmpresaAtivaId((atual) => {
      if (atual && empresas.some((e) => e.id === atual)) return atual;
      const primeira = empresas.find((e) => e.status === "ATIVO") || empresas[0];
      return primeira ? primeira.id : null;
    });
  }, [empresas]);

  // Persiste a empresa ativa.
  useEffect(() => {
    if (empresaAtivaId) localStorage.setItem(CHAVE_ATIVA, String(empresaAtivaId));
  }, [empresaAtivaId]);

  // Limpa a seleção no logout.
  useEffect(() => {
    if (!usuario) setEmpresaAtivaId(null);
  }, [usuario]);

  // "recarregar" mantém a assinatura antiga, agora invalidando o cache.
  const recarregar = () => qc.invalidateQueries({ queryKey: qk.empresas() });

  const empresaAtiva = empresas.find((e) => e.id === empresaAtivaId) || null;

  return (
    <EmpresaContext.Provider
      value={{
        empresas,
        empresaAtiva,
        empresaAtivaId,
        selecionar: setEmpresaAtivaId,
        recarregar,
        carregando: isLoading,
      }}
    >
      {children}
    </EmpresaContext.Provider>
  );
}

export const useEmpresa = () => useContext(EmpresaContext);
