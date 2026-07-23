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
 *
 * Login baseado em empresa (v6.14): um usuário pode estar vinculado a mais
 * de uma empresa (associação mantida no cadastro de Usuários), mas isso não
 * exige uma tela própria de seleção pós-login — ele entra normalmente e
 * troca de empresa pelo seletor do topo, que agora lista as empresas a que
 * ele está vinculado (antes só fazia sentido para superusuários).
 */
export function EmpresaProvider({ children }) {
  const { usuario } = useAuth();
  const qc = useQueryClient();

  // Só busca quando há usuário autenticado.
  const { data: empresas = [], isLoading } = useEmpresas({ enabled: !!usuario });

  const [empresaAtivaId, setEmpresaAtivaId] = useState(
    () => Number(localStorage.getItem(CHAVE_ATIVA)) || null
  );

  // Superusuário global (equipe GD Conecta, sem empresa_id): não é um cliente
  // vinculado a empresas — é quem administra a plataforma (cadastro geral de
  // empresas/usuários). Não entra automaticamente em nenhuma empresa de
  // cliente; escolhe pelo seletor do topo só quando precisar analisar dados
  // de uma empresa específica.
  const ehSuperusuarioGlobal = Boolean(usuario?.is_superuser) && usuario?.empresa_id == null;

  // Ao logar como superusuário global, garante que não sobra nenhuma empresa
  // ativa de uma sessão anterior (localStorage é compartilhado entre logins).
  useEffect(() => {
    if (ehSuperusuarioGlobal) setEmpresaAtivaId(null);
  }, [usuario, ehSuperusuarioGlobal]);

  // Seleção automática da empresa ativa quando a lista chega/muda — para
  // qualquer usuário vinculado a 1 ou mais empresas (não superusuário).
  useEffect(() => {
    if (!empresas.length || ehSuperusuarioGlobal) return;
    setEmpresaAtivaId((atual) => {
      if (atual && empresas.some((e) => e.id === atual)) return atual;
      const primeira = empresas.find((e) => e.status === "ATIVO") || empresas[0];
      return primeira ? primeira.id : null;
    });
  }, [empresas, ehSuperusuarioGlobal]);

  // Persiste a empresa ativa (superusuário global também pode fixar uma ao
  // trocar pelo seletor do topo, para analisar dados de um cliente).
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
